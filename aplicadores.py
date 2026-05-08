import pandas as pd , logging
from elementos import Deployment
from explorador import Explorador

logger = logging.getLogger(__name__)

class Applicador_GCP:
    def __init__(self , project:str|Explorador):
        if isinstance(project, Explorador):
            self.explorer = project

        elif isinstance(project, str):
            self.explorer = Explorador(project_id=project)

        else:
            raise TypeError(
                "Analisys espera un project_id (str) o un Explorador"
            )

    def aplicador_lim_req(self , sheet:str|pd.DataFrame , apply=False):
        # Este aplicador esta estandarizado para el resultado de 
        # analisis.Analisys.limits_requests_format() -> csv|df
        if isinstance(sheet , str):
            suggestions = pd.read_csv(sheet)
            suggestions["Aprovado (T/F)"] = suggestions["Aprovado (T/F)"].astype(bool)

        elif isinstance(sheet , pd.DataFrame):
            suggestions = sheet

        for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
            row = suggestions.loc[suggestions.index == deployment.name]

            if row.empty:
                logger.warning(f"Deployment {deployment.name} no encontrado")
                continue

            row = row.iloc[0]

            if not row["Aprovado (T/F)"]:
                logger.info(f"Deployment {deployment.name} no aprovado")
                continue

            cpu_flag = row["nota_cpu"] != "Correcto"
            mem_flag = row["nota_memoria"] != "Correcto"

            cpu = mem = None
            if cpu_flag or mem_flag:
                cpu, mem = self.test_deployment(
                    deployment=deployment,
                    c_flag=cpu_flag,
                    m_flag=mem_flag
                )

            cpu_request = cpu[0] if cpu_flag else row["recommended_cpu_request"]
            cpu_limit   = cpu[1] if cpu_flag else row["recommended_cpu_limit"]
            memory_request = mem[0] if mem_flag else row["recommended_memory_request"]
            memory_limit   = mem[1] if mem_flag else row["recommended_memory_limit"]

            patch = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": deployment.name,
                                "resources": {
                                    "requests": {
                                        "cpu": cpu_request,
                                        "memory": memory_request
                                    },
                                    "limits": {
                                        "cpu": cpu_limit,
                                        "memory": memory_limit
                                    }
                                }
                            }]
                        }
                    }
                }
            }

            if apply:
                deployment.patch_deployment(patch_body=patch)
                self.security_check(deployment=deployment)

    def roll_back(self , sheet:str|pd.DataFrame):
        # Falta lidiar con los N/A o NaN
        if isinstance(sheet , str):
            suggestions = pd.read_csv(sheet)
            suggestions["Aprovado (T/F)"] = suggestions["Aprovado (T/F)"].astype(bool)

        elif isinstance(sheet , pd.DataFrame):
            suggestions = sheet

        for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
            row = suggestions.loc[suggestions.index == deployment.name]
            if row.empty:
                raise ValueError("Deployment no encontrado")
            
            if not row["Aprovado (T/F)"].iloc[0]:
                print("Deployment no abrobado")
                continue
            
            memory_request = row["mem_request"].iloc[0]
            memory_limit = row["mem_limit"].iloc[0]
            cpu_request = row["cpu_request"].iloc[0]
            cpu_limit = row["cpu_limit"].iloc[0]

            patch = {
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {
                                        "name": deployment.name,
                                        "resources": {
                                            "requests": {
                                                "cpu": cpu_request,
                                                "memory": memory_request
                                            },
                                            "limits": {
                                                "cpu": cpu_limit,
                                                "memory": memory_limit
                                            }
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            
            print(deployment.name , patch)
            break

            #deployment.patch_deployment(patch_body=patch)

    def test_deployment(self , deployment:Deployment , c_flag:bool , m_flag:bool):
        # Tomar el maximo entre el reinicio y el punto estable
        # Los regresa para asignarlos con un 15% más en formato necesario
        self._set_top(deployment) # Asignar limites altos para que no crashee
        deployment.restart() # Reiniciar el deployment 

        if deployment.wait_verification(): # Esperar a que se obtengan la salud de los pods
            deployment.get_cpu_hist_a(days=0)

        else:
            logger.warning(f"Problea con los pods de {deployment.name}")
    
    def security_check(self , deployment:Deployment , attempts:int , step:int):
        # Una revision de seguridad donde se cicla un aumento de recursos en caso 
        # de tener un error relacionado con recursos insuficientes
        pass

    def _set_top(deployment:Deployment):
        patch = {
                "spec": {
                    "template": {
                        "spec": {
                            "containers": [{
                                "name": deployment.name,
                                "resources": {
                                    "requests": {
                                        "cpu": "50m",
                                        "memory": "64Mi"
                                    },
                                    "limits": {
                                        "cpu": "2",
                                        "memory": "4Gi"
                                    }
                                }
                            }]
                        }
                    }
                }
            }
        
        deployment.patch_deployment(patch_body=patch)
 
# if __name__ == "__main__":
    # from analysis import Analisys
#     project_ids = [
#         "cpl-ssff-cnsulcc-dev-05122025",
#     ]

#     for project_id in project_ids:
#         explorador = Explorador(project_id=project_id)
#         analisis = Analisys(explorador)
#         recomendaciones = analisis.limits_requests_format(days=1 , rate="1m" , csv=False)
#         recomendaciones.loc[recomendaciones.index[0], 'Aprovado (T/F)'] = True
#         #print(recomendaciones)
#         aplicador = Applicador_GCP(explorador)
#         aplicador.aplicador_lim_req(recomendaciones)


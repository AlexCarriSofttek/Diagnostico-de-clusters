import pandas as pd , logging
from elementos import Deployment
from explorador import Explorador
from analysis import Metrics
from time import time
from analysis import CPU_MIN_REQUEST , CPU_MIN_LIMIT

logger = logging.getLogger(__name__)

class Limits_Requests:
    def __init__(self , project:str|Explorador , suggestions:str|pd.DataFrame , backup:str|pd.DataFrame , apply=False):
        if isinstance(project, Explorador):
            self.explorer = project

        elif isinstance(project, str):
            self.explorer = Explorador(project_id=project)

        else:
            raise TypeError(
                "Analisys espera un project_id (str) o un Explorador"
            )
        
        self.suggestions:pd.DataFrame = Limits_Requests.ensure_df(suggestions)
        self.backup:pd.DataFrame = Limits_Requests.ensure_df(backup)
        self.apply = apply

    def aplicador_lim_req(self):
        # Este aplicador esta estandarizado para el resultado de 
        self.suggestions["Aprovado (T/F)"] = self.suggestions["Aprovado (T/F)"].astype(bool)

        for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):    
            row = self.suggestions.loc[
                (self.suggestions["deployment"] == deployment.name) &
                (self.suggestions["namespace"] == deployment.namespace)
            ]

            if row.empty:
                logger.warning(f"Deployment {deployment.name} no encontrado")
                continue

            row = row.iloc[0]

            if not row["Aprovado (T/F)"]:
                logger.info(f"Deployment {deployment.name} no aprovado")
                continue

            cpu_flag = row["nota_cpu"] != "Correcto"
            mem_flag = row["nota_memoria"] != "Correcto"
            off_flag = not row["Habilitado"] # Se corrigio esta mayuscula en el analisis solo funcionara con mayuscula en recomendaciones generadas anteriormente
            cpu = mem = [None , None]

            if cpu_flag and not mem_flag: # CPU datos insuficientes and MEM correcto = CPU min
                cpu = [CPU_MIN_REQUEST , CPU_MIN_LIMIT]

            elif off_flag and (cpu_flag or mem_flag): # El deployment no esta encendido
                cpu, mem = self.stst_deployment(
                    deployment=deployment,
                    c_flag=cpu_flag,
                    m_flag=mem_flag
                )

            elif not off_flag and (cpu_flag or mem_flag): # El deployment esta encendido pero faltan datos
                cpu, mem = self.rat_deployment(
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

            if self.apply:
                deployment.patch_deployment(patch_body=patch)
                self.security_check(deployment=deployment)

    def stst_deployment(self , deployment:Deployment , c_flag:bool , m_flag:bool):
        # Start Then Shutdown Test
        cpu = mem = [None , None]
        start = int(time())
        deployment.scale(1)
        if deployment.wait_verification():
            if c_flag:
                _ , *cpu = deployment.get_cpu_hist(days=0 ,
                                                seconds=int(time()-start),
                                                fn=Metrics.max_parsed_c
                                                )
            if m_flag:
                _ , *mem = deployment.get_memory_hist(days=0 ,
                                                seconds=int(time()-start),
                                                fn=Metrics.max_parsed_m
                                                )
        else:
            logger.warning(f"{deployment.name} tuvo un error al inicar los pods")

        deployment.scale(0)
        logger.warning(f"{deployment.name} se regreso a 0 replicas")
        return cpu , mem

    def rat_deployment(self , deployment:Deployment , c_flag:bool , m_flag:bool):
        # Restart And Test
        cpu = mem = [None , None]
        # Tomar el maximo entre el reinicio y el punto estable
        # Los regresa para asignarlos con un 15% más en formato necesario
        self._set_top(deployment) # Asignar limites altos para que no crashee
        start = int(time())
        deployment.restart() # Reiniciar el deployment 
        if deployment.wait_verification(): # Esperar a que se obtengan la salud de los pods
            if c_flag:
                _ , *cpu = deployment.get_cpu_hist(days=0 ,
                                                seconds=int(time()-start),
                                                fn=Metrics.max_parsed_c
                                                )
            if m_flag:
                _ , *mem = deployment.get_memory_hist(days=0 ,
                                                seconds=int(time()-start),
                                                fn=Metrics.max_parsed_m
                                                )
        else:
            logger.warning(f"{deployment.name} tuvo un error al inicar los pods")

        return cpu , mem
    
    def security_check(self , deployment:Deployment , attempts=3 , step=20):
        # Una revision de seguridad donde se cicla un aumento de recursos en caso 
        # de tener un error relacionado con recursos insuficientes
        for attempt in range(attempts):
            if deployment.wait_verification():
                logger.info(f"{deployment.name} esta corriendo")

            elif not deployment.enough_mem():
                logger.info(f"{deployment.name} no es suficiente memoria, aumentando {step}%")

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
    
    def roll_back(self , deployment:Deployment):
        row = self.backup.loc[self.backup["deployment"] == deployment.name]

        row = row.iloc[0]
        
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

        deployment.patch_deployment(patch_body=patch)
    
    def full_roll_back(self):
        # Falta lidiar con los N/A o NaN
        for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
            row = self.backup.loc[self.backup["deployment"] == deployment.name]
            if row.empty:
                logger.warning(f"Deployment {deployment.name} no encontrado")
                continue

            row = row.iloc[0]
            
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

            deployment.patch_deployment(patch_body=patch)

    def ensure_df(df:str|pd.DataFrame):
        # analisis.Analisys.limits_requests_format() -> csv|df
        if isinstance(df , str):
            return pd.read_csv(df)
        
        elif isinstance(df , pd.DataFrame):
            return df
        
        else:
            raise TypeError(
                "Se espera un DataFrame de pandas o ruta de csv"
            )
        
# if __name__ == "__main__":
#     aplicador = Limits_Requests(project="cpl-corp-presyab-dev-30052024",
#                                 suggestions="cpl-corp-presyab-dev-30052024_2026-05-07_suggestions.csv",
#                                 backup="cpl-corp-presyab-dev-30052024_2026-05-07_back_up.csv",
#                                 apply=False)
    
#     aplicador.aplicador_lim_req()

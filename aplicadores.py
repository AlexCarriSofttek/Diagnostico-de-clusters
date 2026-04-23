import pandas as pd
from explorador import Explorador

import logging
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
        # Falta lidiar con los N/A o NaN
        # Este aplicador esta estandarizado para el resultado de 
        # analisis.Analisys.limits_requests_format() -> csv
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
            
            memory_request = row["recommended_memory_request"].iloc[0]
            memory_limit = row["recommended_memory_limit"].iloc[0]
            cpu_request = row["recommended_cpu_request"].iloc[0]
            cpu_limit = row["recommended_cpu_limit"].iloc[0]

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


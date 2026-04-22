import pandas as pd
from explorador import Explorador
from elementos import UnitsCon as uc

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
        # analisis.Analisys.limits_requests_format() -> csv
        if isinstance(sheet , str):
            suggestions = pd.read_csv(sheet)
            suggestions["Aprovado (T/F)"] = suggestions["Aprovado (T/F)"].astype(bool)

        elif isinstance(sheet , pd.DataFrame):
            suggestions = sheet

        for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
            row = suggestions.loc[suggestions["deployment"] == deployment.name]
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
            
            #deployment.patch_deployment(patch_body=patch)
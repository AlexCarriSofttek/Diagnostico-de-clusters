import pandas as pd
from explorador import Explorador
from elementos import UnitsCon as uc

class Applicador_GCP:
    # No es robusto así que se tiene que usar con precaucion 
    def aplicator_brute(sheet:str , project_id:str):
        table = pd.read_csv(sheet)
        explorer = Explorador(project_id=project_id)
        for deployment in explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
            row = table.loc[table["DEPLOYMENT"] == deployment.name]
            if row.empty:
                raise ValueError("Deployment no encontrado")
            
            memory_limit = str(
                uc.mb2mi(row["RECOMMENDED_MEMORY_LIMIT_MB"].iloc[0]))
            memory_request =  str(
                uc.mb2mi(row["RECOMMENDED_MEMORY_REQUEST_MB"].iloc[0]))
            cpu_limit = str(row["RECOMMENDED_CPU_LIMIT"].iloc[0] * 1000)
            cpu_request = str(row["RECOMMENDED_CPU_REQUEST"].iloc[0] * 1000)

            print(memory_limit , memory_request , cpu_limit , cpu_request)

class Aplicador_Azure:
    def patch_deployments_limits():
        pass
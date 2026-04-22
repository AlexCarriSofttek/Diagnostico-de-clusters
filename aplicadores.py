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

    # No es robusto así que se tiene que usar con precaucion 
    def aplicator_brute(self , sheet:str):
        table = pd.read_csv(sheet)
        for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
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

    def aplicador_lim_req(self , sheet:str|pd.DataFrame):
        # Este aplicador esta estandarizado para el resultado de 
        # analisis.Analisys.limits_requests_format() -> csv
        if isinstance(sheet , str):
            suggestions = pd.read_csv(sheet)
        elif isinstance(sheet , pd.DataFrame):
            suggestions = sheet

        for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
            row = suggestions.loc[suggestions["deployment"] == deployment.name]
            if row.empty:
                raise ValueError("Deployment no encontrado")
            
            memory_request = row["recommended_memory_request"].iloc[0]
            memory_limit = row["recommended_memory_limit"].iloc[0]
            cpu_request = row["recommended_cpu_request"].iloc[0]
            cpu_limit = row["recommended_cpu_limit"].iloc[0]

            print(memory_limit , memory_request , cpu_limit , cpu_request)

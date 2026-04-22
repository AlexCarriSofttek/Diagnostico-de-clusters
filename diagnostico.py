# Este script es el punto principal de la herramienta
# Cada funcion funge como ejemplo GENERAL de lo que puede  
# hacer con la herramienta
from pandas import DataFrame
from explorador import Explorador
from analysis import Analisys

def hist_cpu_mem(explorador:Explorador) -> DataFrame:
    # Este ejemplo analiza el histograma del consumo de 
    # Memoria y CPU por deployment. Tome en cuenta que 
    # se aplica un filtro de los deployments con las palabras
    # clave "kube" , "gmp" , "gke" , "default".
    result = Analisys(Explorador).limits_requests_format(days=30, # Días previos a hoy 
                                                  rate="30s", # Se agrupa cada 30 segundos
                                                  csv=False # Se guarda un csv
                                                  )
    print(result) # Por fines demostrativos
    return result
    

if __name__ == "__main__":
    project_ids = [
        "cpl-ssff-cnsulcc-dev-05122025",
    ]

    for project_id in project_ids:
        explorador = Explorador(project_id=project_id)
        recomendaciones = hist_cpu_mem(explorador=explorador)
        
        

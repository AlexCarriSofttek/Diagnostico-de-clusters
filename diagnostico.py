# Este script es el punto principal de la herramienta
# Cada funcion funge como ejemplo GENERAL de lo que puede  
# hacer con la herramienta
from pandas import DataFrame
from explorador import Explorador
from analysis import Metrics
# Pendientes
# - Documentacion 
# - Funciones en el aplicador para corregir si el deployment no tiene suficientes recursos
# - Funcion para quitar limites, reiniciar el deployment, y medir el arranque de CPU y Memoria

# Inventarios 
# - Todo lo relacionado con el aplicativo menos informacion sensible (No secretos)

# Comparar los numeros de rogelio con los de la herramienta. 

if __name__ == "__main__":
    project_id = "cpl-ec-gcobranza-dev-08082024"

    a = Metrics(project=project_id)
    recomendaciones = a.limits_requests_format(days=1 , rate="1m")

        

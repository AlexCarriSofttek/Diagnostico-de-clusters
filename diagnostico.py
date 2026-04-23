# Este script es el punto principal de la herramienta
# Cada funcion funge como ejemplo GENERAL de lo que puede  
# hacer con la herramienta
from pandas import DataFrame
from explorador import Explorador
from analysis import Analisys
# Pendientes
# - Agregar limpiar los NaN de los historiales
# - Considerar el CPU en arranque. 
# - Agregar el cargar pods
# - Documentacion 
# - Funciones en el aplicador para corregir si el deployment no tiene suficientes recursos

# Inventarios 
# - Todo lo relacionado con el aplicativo menos informacion sensible (No secretos)

# Prueba con los ingres con más de 250 aplicativos (Sin cambiar nada)sd-cobranza , rt-carteras
# Ni modificar NADA
# Comparar los numeros de rogelio con los de la herramienta. 
    

if __name__ == "__main__":
    project_id = "cpl-ec-gcobranza-qa-18032025"

    a = Analisys(project=project_id)
    a.limits_requests_format(days=30 , rate="1m") # Generar la tabla de sugerencias

        

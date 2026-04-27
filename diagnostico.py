# Este script es el punto principal de la herramienta
# Cada funcion funge como ejemplo GENERAL de lo que puede  
# hacer con la herramienta
from pandas import DataFrame
from explorador import Explorador
from analysis import Analisys
# Pendientes
# - Validar la conexion de Kubernetes y la de Proyecto (Pueden funcionar indivualmente pero no deberian)
# - Agregar limpiar los NaN de los historiales
# - Asegurar conexion entre constructor y ambiente
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
    project_id = "cpl-ec-gcobranza-dev-08082024"

    a = Analisys(project=project_id)
    recomendaciones = a.limits_requests_format(days=1 , rate="1m")
    recomendaciones.loc[recomendaciones.index[0], 'Aprovado (T/F)'] = True
    print(recomendaciones)
        

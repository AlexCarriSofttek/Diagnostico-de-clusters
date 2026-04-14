# Herramienta de diagnostico de Clusters

## Proposito 
El proposito de la herramienta es hacer una version versatil para el analisis de los clusters estrayendo información y generando reportes. 

## Componentes
- diagnostico.py: Script principal, es el que se ejecuta y tiene una salida estandar formato xml, yaml o csv junto con graficas utiles para saber el estado actual de los clusters o proyectos.
- explorador.py: Extrae la informacion de los componentes y los almacena en objetos de  "elementos". 
- elementos.py: Objetos que conforman los proyectos y contienen los metodo disponibles. 
- analysis.py: Opera a parte del diagnostico y hace recomendaciones de ajustes. 
- aplicador.py: Contiene los aplicadores soportados para GCP y Pipelines de Azure

## Uso
1. 

## Diagrama UML

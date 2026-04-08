# Herramienta de diagnostico de Clusters

## Proposito 
El proposito de la herramienta es hacer una version versatil para el analisis de los clusters estrayendo información y generando reportes. 

## Componentes
- diagnostico.py: Script principal, es el que se ejecuta y tiene una salida estandar formato xml, yaml o csv junto con graficas utiles para saber el estado actual de los clusters o proyectos.
- extractor.py: Extrae la informacion de los componentes y los almacena en formato elementos. 
- elementos.py: Objetos que conforman los proyectos y contienen los metodo disponibles. 
- analysis.py: Opera a parte del diagnostico y hace recomendaciones de ajustes. 
- aplicador_GKE.py: Aplica los cambios autorizados que se generaron en el formato de analysis al GKE
- aplicador_Azure.py: Aplica los cambios autorizados que se generaron en el formato de analysis a los pipelines de Azure. 

## Uso
1. 

## Diagrama UML

# Herramienta de diagnostico de Clusters

## Proposito 
El proposito de la herramienta es hacer una version versatil para el analisis de los clusters estrayendo información, generando reportes y aplicando cambios. 

## Componentes
- scm_contexts: Es un scripc que te atentica en los contexts (proyectos y clusters) reportados en el json, el json no es parte del repo por seguridad así debes solicitarlo. 
- grafos: crea un grafo del proyecto hasta los pods de la siguiente manera ->
>
    Project (context)

        └── Cluster (context)

            └── Namespace

                └── Deployment

                    └── Pod

## Uso
1. 

## Diagrama UML

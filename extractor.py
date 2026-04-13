# Este script es responsabe de invocar los metodos de los 
# elementos para dar como resultado los proyectos con sus 
# componentes. Además de moverse entre los proyectos visibles. 
import elementos as elements
import pandas as pd

# Estas variables son para definir si 
# se obtiene el componente de forma manual
# o automatica 
OBTAIN_CLUSTERS = True
OBTAIN_NAMESPACES = True
OBTAIN_DEPLOYMENTS = True
OBTAIN_PODS = False

class Extractor:
    def __init__(self, proyect:str , depth="Deployments"):
        self.project = elements.Project(project_id=proyect , get_clusters=OBTAIN_CLUSTERS)

    def __init__(self, proyect_ids:list):
        self.projects = [elements.Project(project_id=proyect , get_clusters=OBTAIN_CLUSTERS)
                         for proyect in proyect_ids]

    def get_clusters(self):
        for project in self.projects:
            for cluster in project.clusters:
                print(cluster.name , cluster.location)

    def get_historic(self , metric:str , period=10 , hours=0, days=0, weeks=0):
        for cluster in self.project.clusters:
            cluster.obtain_namespaces()
            for namespace in cluster.namespaces:
                if self.filter_namespace(namespace.name):
                    namespace.obtain_deployments()
                    for deployment in namespace.deployments:
                        history = deployment.get_history(METRICS , period=10 , hours=1)
                        
    def filter_namespace(self , namespace):
        ig = ["kube" , "gmp" , "gke" , "default"]
        return not any(exc in namespace for exc in ig)


class Histogram:
    # Esta clase convierte un historic de "elements" en un 
    # Histogram
    def __init__(self, file:str):
        self.df = pd.read_csv(file)
        self.df = self.df.set_index("segundos")

    def __init__(self , data:list , period=20):
        self.df = pd.DataFrame({
            "valor": data,
        })

        self.df["segundos"] = self.df.index * period
        self.df = self.df.set_index("segundos")

    def get_graph(self , metric_name:str , graph_title:str):
        ax = self.df.plot(
                    figsize=(10, 4),
                    grid=True,
                    legend=False
                )
                
        ax.set_xlabel("Tiempo (segundos)")
        ax.set_ylabel(metric_name)
        ax.set_title(graph_title)

    def download_csv(self):
        self.df.to_csv(f"histogram.csv")
# Este script es responsabe de invocar los metodos de los 
# elementos para dar como resultado los proyectos con sus 
# componentes. Además de moverse entre los proyectos visibles. 
import elementos as elements
import pandas as pd

class Extractor:
    def __init__(self, depth="Deployments" , proyect=""):
        project = elements.Project(project_id=proyect)
        print(project)

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
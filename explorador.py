# Este script es responsabe de invocar los metodos de los 
# elementos para dar como resultado los proyectos con sus 
# componentes. Además de moverse entre los proyectos visibles. 
from elementos import Project

class Explorador:
    def __init__(self, project_id: str):
        self.project = Project(project_id)

    def iter_clusters(self):
        self.project.load_clusters()
        yield from self.project.clusters

    def iter_namespaces(self):
        for cluster in self.iter_clusters():
            cluster.load_namespaces()
            yield from cluster.namespaces

    def iter_deployments(self):
        for namespace in self.iter_namespaces():
            namespace.load_deployments()
            yield from namespace.deployments

# if __name__ == "__main__":
#     explorer = ProjectExplorer("cpl-ssff-adqbbva-qa-13052025")

#     for deployment in explorer.iter_clusters():
#         print(deployment)
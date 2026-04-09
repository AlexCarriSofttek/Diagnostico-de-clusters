import sys
import logging
from google.cloud import container_v1 
from google.cloud import resourcemanager_v3 as resource_manager

class Project:
    def __init__(self , project_id):
        try:
            self.project = self.open_project(project_id)
            
        except Exception as e:
            print(f"Error al abrir project: {project_id}", file=sys.stderr)
            logging.error(f"Error al abrir project: {project_id}. {e}")
            sys.exit(1)

        try:
            self.clusters = self.extract_clusters(project_id)
            
        except Exception as e:
            print(f"Error al buscar clusters", file=sys.stderr)
            logging.error(f"Error al buscar clusters. {e}")
            sys.exit(1)

    def open_project(self , project_id):
        client = resource_manager.ProjectsClient()
        project = client.get_project(name=f"projects/{project_id}")
        return project

    def extract_clusters(self , project_id:str) -> list:
        client = container_v1.ClusterManagerClient()
        response = client.list_clusters(
            parent=f"projects/{project_id}/locations/-"
        )
        return [Cluster(cluster) for cluster in response.clusters]
    
    def __repr__(self):
        return (
            f"Project("
            f"project_id='{self.project.project_id}', "
            f"display_name='{self.project.display_name}', "
            f"state='{self.project.state.name}', "
            f"clusters={len(self.clusters)}"
            f")"
        )
    
    def __str__(self):
        return (
            f"Proyecto: {self.project.display_name}\n"
            f"ID: {self.project.project_id}\n"
            f"Estado: {self.project.state.name}\n"
            f"Clusters: {len(self.clusters)}"
        )


# Wrapper para 
class Cluster:
    def __init__(self , cluster:container_v1.types.Cluster):
        self.name = cluster.name

    def extract_namespaces(project_name:str) -> list:
        pass

class Namespace:
    def extract_deployments(project_name:str) -> list:
        pass

class Deployment:
    def extract_pipeline(self):
        pass

    def extract_pods(project_name:str) -> list:
        pass

    def set_config(self, config):
        pass

class Pod:
    def __init__(self):
        pass

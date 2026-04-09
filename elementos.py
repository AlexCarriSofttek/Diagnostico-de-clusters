import sys
import logging
from google.cloud import container_v1 
from google.cloud import resourcemanager_v3 as resource_manager

class Proyect:
    def __init__(self , project_id):
        try:
            self.project = self.open_proyect(project_id)
            
        except Exception as e:
            print(f"Error al abrir proyecto: {project_id}", file=sys.stderr)
            logging.error(f"Error al abrir proyecto: {project_id}. {e}")
            sys.exit(1)

        try:
            self.clusters = self.extract_clusters(project_id)
            print(self.clusters)
            
        except Exception as e:
            print(f"Error al buscar clusters", file=sys.stderr)
            logging.error(f"Error al buscar clusters. {e}")
            sys.exit(1)

    def open_proyect(self , project_id):
        client = resource_manager.ProjectsClient()
        project = client.get_project(name=f"projects/{project_id}")
        return project

    def extract_clusters(self , project_id:str) -> list:
        client = container_v1.ClusterManagerClient()
        response = client.list_clusters(
            parent=f"projects/{project_id}/locations/-"
        )
        return response.clusters

class Cluster:
    def __init__(self , cluster_id):
        pass

    def extract_namespaces(proyect_name:str) -> list:
        pass

class Namespace:
    def extract_deployments(proyect_name:str) -> list:
        pass

class Deployment:
    def extract_pipeline(self):
        pass

    def extract_pods(proyect_name:str) -> list:
        pass

    def set_config(self, config):
        pass

class Pod:
    def __init__(self):
        pass

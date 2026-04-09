import sys
import logging
from google.cloud import container_v1 , dataproc_v1 
from google.cloud import resourcemanager_v3 as resource_manager

class Proyect:
    def __init__(self , project_id):
        try:
            self.project = self.open_proyect(project_id)
            
        except Exception as e:
            print(f"Error al abrir proyecto: {project_id}", file=sys.stderr)
            logging.error(f"Error al abrir proyecto: {project_id}. {e}")
            sys.exit(1)

    def open_proyect(self , project_id):
        client = resource_manager.ProjectsClient()
        project = client.get_project(name=f"projects/{project_id}")
        return project

    def extract_clusters(self , project_id:str , project_region:str) -> list:
        def listar_regiones_dataproc(project_id: str) -> list[str]:
            client = container_v1.ClusterManagerClient()
            parent = f"projects/{project_id}/locations/-"

            response = client.list_clusters()

            return list({cluster.location for cluster in response.clusters})

        res = []
        for region in listar_regiones_dataproc(project_id):
            client = dataproc_v1.ClusterControllerClient(
                client_options={"api_endpoint": f"{region}-dataproc.googleapis.com:443"}
            )

            clusters = client.list_clusters(
            request={"project_id": project_id, "region": region}
            )

            res.append(clusters)

        return res

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

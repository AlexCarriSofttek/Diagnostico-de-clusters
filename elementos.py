import sys
import logging
from kubernetes.client import models
from kubernetes import client, config
from google.cloud.container_v1 import Cluster as Cluster_V1
from google.cloud import container_v1 
from google.cloud import resourcemanager_v3 as resource_manager

class Project:
    def __init__(self , project_id:str):
        try:
            self._raw = self.open_project(project_id)
            self.name = self._raw.display_name
            self.ID = self._raw.project_id
            
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
            f"project_id='{self._raw.project_id}', "
            f"display_name='{self._raw.display_name}', "
            f"state='{self._raw.state.name}', "
            f"clusters={len(self.clusters)}"
            f")"
        )
    
    def __str__(self):
        return (
            f"Proyecto: {self._raw.display_name}\n"
            f"ID: {self._raw.project_id}\n"
            f"Estado: {self._raw.state.name}\n"
            f"Clusters: {len(self.clusters)}"
        )

# Wrapper para cluster
class Cluster:
    def __init__(self , cluster:Cluster_V1):
        self._raw = cluster 
        self.name = cluster.name
        self.location = cluster.location
        self.status = cluster.status.name

        try:
            #config.load_incluster_config() # GCP
            config.load_kube_config()
            self.namespaces = self.extract_namespaces()
            
        except Exception as e:
            print(f"Error al buscar namespaces", file=sys.stderr)
            logging.error(f"Error al buscar namespaces. {e}")
            sys.exit(1)

    def extract_namespaces(project_name:str) -> list:
        v1 = client.CoreV1Api()
        namespaces = v1.list_namespace()
        return [Namespace(namespace) for namespace in namespaces.items]

    def __repr__(self):
        return (
            f"Cluster("
            f"cluster_name='{self.name}', "
            f"location='{self.location}', "
            f"status='{self.status}', "
            f"namespaces={len(self.namespaces)}"
            f")"
        )
    
    def __str__(self):
        return (
            f"Cluster: {self.name}\n"
            f"Ubicacion: {self.location}\n"
            f"Estatus: {self.status}\n"
            f"Namespaces: {len(self.namespaces)}"
        )

class Namespace:
    def __init__(self , namespace:models.V1Namespace):
        self._raw = namespace
        self.name = namespace.metadata.name
        self.status = namespace.status.phase

        try:
            #config.load_incluster_config() # GCP
            config.load_kube_config()
            self.deployments = self.extract_deployments()
            
        except Exception as e:
            print(f"Error al buscar deployments", file=sys.stderr)
            logging.error(f"Error al buscar deployments. {e}")
            sys.exit(1)

    def extract_deployments(self) -> list:
        apps_v1 = client.AppsV1Api()
        response = apps_v1.list_namespaced_deployment(
            namespace=self.name
        )

        return [Deployment(deployment) for deployment in response.items]
    
    def __repr__(self):
        return (f"Namespace("
                f"name='{self.name}'," 
                f"status='{self.status} , "
                f"deployemnts_num={len(self.deployments)}')"
            )
    
    def __str__(self):
        return (f"Nombre: {self.name}\n"
                f"Status: {self.status}\n"
                f"Deployments: {len(self.deployments)}")


class Deployment:
    def __init__(self , deployment:models.V1Deployment):
        self._raw = deployment
        self.name = deployment.metadata.name
        
        self.desired_replicas = deployment.spec.replicas or 0
        self.ready_replicas = deployment.status.ready_replicas or 0
        self.available_replicas = deployment.status.available_replicas or 0

        try:
            #config.load_incluster_config() # GCP
            config.load_kube_config()
            self.pods = self.extract_pods()
            
        except Exception as e:
            print(f"Error al obtener pods", file=sys.stderr)
            logging.error(f"Error al obtener pods. {e}")
            sys.exit(1)

    def get_pipeline(self):
        pass

    def extract_pods(self) -> list:
        v1 = client.CoreV1Api()
        dep_pods = []
        
        response = v1.list_namespaced_pod(
                namespace=self.namespace
            )

        for pod in response.items:
            if self.name in pod.metadata.name:
                dep_pods.append(pod)

        return dep_pods

    def set_config(self, config):
        pass

class Pod:
    def __init__(self , pod:models.V1Pod):
        pass

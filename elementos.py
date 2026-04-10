import sys
import logging
from kubernetes.client import models
from kubernetes import client, config
from datetime import datetime, timezone, timedelta
from google.cloud.container_v1 import Cluster as Cluster_V1
from google.cloud import container_v1 , monitoring_v3
from google.cloud import resourcemanager_v3 as resource_manager

def configurar_cliente_kubernetes():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        try:
            config.load_kube_config()
        except config.ConfigException as e:
            print(f"Error al configurar el cliente de Kubernetes: {e}", file=sys.stderr)
            sys.exit(1)

class Historic_Element:
    def get_history(self , metric:str , filter:str, project:str , err_data:list, hours=0, days=0, weeks=0 ):
        client = monitoring_v3.MetricServiceClient()
        
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours,days=days, weeks=weeks)

        interval = monitoring_v3.TimeInterval({
        "end_time": {"seconds": int(end_time.timestamp())},
        "start_time": {"seconds": int(start_time.timestamp())}
        })

        alineador = monitoring_v3.Aggregation.Aligner.ALIGN_RATE if "cpu" in metric else monitoring_v3.Aggregation.Aligner.ALIGN_MEAN

        agregacion = monitoring_v3.Aggregation(
            alignment_period={"seconds": 20},
            per_series_aligner=alineador,
            cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_MAX
        ) 

        peticion = {
            "name": project,
            "filter": filter,
            "interval": interval,
            "aggregation": agregacion,
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        }

        resultados = []
        try:
            for serie in client.list_time_series(request=peticion):
                for punto in serie.points:
                    resultados.append(punto.value.double_value)
        except Exception as e:
            print(f"Error obteniendo metricas para {'/'.join(err_data)}: {str(e)[:3]}", 
                file=sys.stderr
                )
            logging.error(f"Error al metricas en {'/'.join(err_data)}. {e}")
        return resultados 

class Project:
    def __init__(self , project_id:str):
        configurar_cliente_kubernetes()
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
        return [Cluster(cluster , self._raw.project_id) for cluster in response.clusters]
    
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

class Cluster:
    def __init__(self , cluster:Cluster_V1 , project_ID:str):
        self._raw = cluster 
        self.name = cluster.name
        self.location = cluster.location
        self.status = cluster.status.name
        self.project_ID = project_ID

        try:
            #config.load_incluster_config() # GCP
            #config.load_kube_config()
            self.namespaces = self.extract_namespaces()
            
        except Exception as e:
            print(f"Error al buscar namespaces", file=sys.stderr)
            logging.error(f"Error al buscar namespaces. {e}")
            sys.exit(1)

    def extract_namespaces(self) -> list:
        v1 = client.CoreV1Api()
        namespaces = v1.list_namespace()
        return [Namespace(namespace , self.project_ID , self.name) for namespace in namespaces.items]

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
    def __init__(self , namespace:models.V1Namespace , project_ID:str , cluster_name:str):
        self._raw = namespace
        self.name = namespace.metadata.name
        self.status = namespace.status.phase
        self.project_ID = project_ID
        self.cluster_name = cluster_name

        try:
            #config.load_incluster_config() # GCP
            #config.load_kube_config()
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

        return [Deployment(deployment , self.project_ID , self.cluster_name) for deployment in response.items]
    
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

class Deployment(Historic_Element):
    def __init__(self , deployment:models.V1Deployment , project_ID:str , cluster_name:str):
        self._raw = deployment
        self.name = deployment.metadata.name
        self.namespace = deployment.metadata.namespace
        self.replicas = deployment.spec.replicas or 0

        self.project_ID = project_ID
        self.cluster_name = cluster_name
        
        self.desired_replicas = deployment.spec.replicas or 0
        self.ready_replicas = deployment.status.ready_replicas or 0
        self.available_replicas = deployment.status.available_replicas or 0

        try:
            #config.load_incluster_config() # GCP
            #config.load_kube_config()
            self.pods = self.extract_pods()
            
        except Exception as e:
            print(f"Error al obtener pods", file=sys.stderr)
            logging.error(f"Error al obtener pods. {e}")
            sys.exit(1)

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
    
    def get_history(self , metrics:list[str] , hours=0, days=0, weeks=0):
        for metric in metrics:
            for container in self._raw.spec.template.spec.containers:
                filtro = (
                    f'metric.type = "{metric}" '
                    f'AND resource.labels.cluster_name = "{self.cluster_name}" '
                    f'AND resource.labels.namespace_name = "{self.namespace}" '
                    f'AND resource.labels.container_name = "{container.name}"'
                )

            results = super().get_history(metric=metric, filter=filtro , 
                                project=f"projects/{self.project_ID}",
                                err_data=[self.namespace,container.name],hours=hours, days=days, weeks=weeks)

            return results
    
    #def set_config(self, config): #Pendiente
    #def get_pipeline(self): #Pendiente
 
    def __repr__(self):
        return (f"Pod("
                f"name='{self.name}'," 
                f"namespace='{self.namespace} , "
                f"replicas='{self.replicas}"
                f")"
            )
    
    def __str__(self):
        return (f"Nombre: {self.name}\n"
                f"Namespace: {self.namespace}\n"
                f"Replicas: {self.replicas}")

class Pod:
    def __init__(self , pod:models.V1Pod):
        self._raw = pod
        
        self.name: str = pod.metadata.name
        self.namespace: str = pod.metadata.namespace
        self.labels: dict = pod.metadata.labels or {}

        # Label común para identificar la app (si existe)
        self.app: str | None = (
            self.labels.get("app")
            or self.labels.get("app.kubernetes.io/name")
            or self.labels.get("app.kubernetes.io/instance")
        )

        # --- Spec ---
        self.node: str | None = pod.spec.node_name
        self.service_account: str | None = pod.spec.service_account_name

        # --- Status ---
        self.phase: str = pod.status.phase
        self.pod_ip: str | None = pod.status.pod_ip
        self.host_ip: str | None = pod.status.host_ip

        # Reinicios totales (suma de todos los contenedores)
        self.restart_count: int = sum(
            cs.restart_count for cs in (pod.status.container_statuses or [])
        )

    def __repr__(self) -> str:
        return (
            f"Pod("
            f"name='{self.name}', "
            f"namespace='{self.namespace}', "
            f"phase='{self.phase}'"
            f")"
        )

    def __str__(self) -> str:
        return (
            f"Pod: {self.name}\n"
            f"  Namespace: {self.namespace}\n"
            f"  Phase: {self.phase}\n"
            f"  Node: {self.node}\n"
            f"  Restarts: {self.restart_count}"
        )


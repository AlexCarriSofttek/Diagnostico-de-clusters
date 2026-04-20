import logging , re
from kubernetes.client import models
from kubernetes import client, config
from datetime import datetime, timezone, timedelta
from google.cloud.container_v1 import Cluster as Cluster_V1
from google.cloud import container_v1 , monitoring_v3 ,resourcemanager_v3 as resource_manager
from google.api_core.exceptions import InvalidArgument
from pandas import DataFrame , to_datetime
from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class History_Result:
    deployment: str
    metric: str
    df: DataFrame

class Clients:
    _core_v1 = None
    _apps_v1 = None
    _monitoring = None

    @classmethod
    def core_v1(cls):
        if cls._core_v1 is None:
            cls._core_v1 = client.CoreV1Api()
        return cls._core_v1

    @classmethod
    def apps_v1(cls):
        if cls._apps_v1 is None:
            cls._apps_v1 = client.AppsV1Api()
        return cls._apps_v1

    @classmethod
    def monitoring(cls):
        if cls._monitoring is None:
            cls._monitoring = monitoring_v3.MetricServiceClient()
        return cls._monitoring
    
    @classmethod
    def ts_query(cls):
        if cls._monitoring is None:
            cls._monitoring = monitoring_v3.QueryServiceClient()
        return cls._monitoring

class Project:
    def __init__(self, project_id: str):
        self.configurar_cliente_kubernetes()
        self._raw = resource_manager.ProjectsClient().get_project(name=f"projects/{project_id}")
        self.id = self._raw.project_id
        self.name = self._raw.display_name
        self.clusters: list[Cluster] | None = None

    def load_clusters(self):
        if self.clusters is not None:
            return

        client = container_v1.ClusterManagerClient()
        response = client.list_clusters(
            parent=f"projects/{self.id}/locations/-"
        )
        self.clusters = [
            Cluster(c, self.id) for c in response.clusters
        ]

    def configurar_cliente_kubernetes(self):
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
    
    def __repr__(self):
        return (
            f"Project("
            f"project_id='{self._raw.project_id}', "
            f"display_name='{self._raw.display_name}', "
            f"state='{self._raw.state.name}'"
            f"{f", clusters={len(self.clusters)}" if self.clusters else ""}"
            f")"
        )
    
    def __str__(self):
        return (
            f"Proyecto: {self._raw.display_name}\n"
            f"ID: {self._raw.project_id}\n"
            f"Estado: {self._raw.state.name}\n"
            f"{f"Clusters: {len(self.clusters)}" if self.clusters else ""}"
        )

class Cluster:
    def __init__(self, raw:Cluster_V1, project_id: str):
        self._raw = raw
        self.name = raw.name
        self.location = raw.location
        self.status = raw.status.name
        self.project_id = project_id
        self.namespaces: list[Namespace] | None = None

    def load_namespaces(self):
        if self.namespaces is not None:
            return

        v1 = Clients.core_v1()
        response = v1.list_namespace()
        self.namespaces = [
            Namespace(ns, self.project_id, self.name , self.location)
            for ns in response.items
        ]

    def __repr__(self):
        return (
            f"Cluster("
            f"cluster_name='{self.name}', "
            f"location='{self.location}', "
            f"status='{self.status}"
            f"{f", namespaces={len(self.namespaces)}" if self.namespaces else""}"
            f")"
        )
    
    def __str__(self):
        return (
            f"Cluster: {self.name}\n"
            f"Ubicacion: {self.location}\n"
            f"Estatus: {self.status}\n"
            f"{f"Namespaces: {len(self.namespaces)}" if self.namespaces else""}"
        )

class Namespace:
    def __init__(self, raw: models.V1Namespace, project_id, cluster_name , location):
        self._raw = raw
        self.name = raw.metadata.name
        self.status = raw.status.phase
        self.project_id = project_id
        self.cluster_name = cluster_name
        self.location = location
        self.deployments: list[Deployment] | None = None

    def load_deployments(self):
        if self.deployments is not None:
            return

        apps = Clients.apps_v1()
        response = apps.list_namespaced_deployment(namespace=self.name)
        self.deployments = [
            Deployment(d, self.project_id, self.cluster_name , self.location)
            for d in response.items
        ]

    def __repr__(self):
        return (f"Namespace("
                f"name='{self.name}'," 
                f"status='{self.status}'"
                f"{f" , deployemnts_num='{len(self.deployments)}'" if self.deployments else ""}"
                f")"
            )
    
    def __str__(self):
        return (f"Nombre: {self.name}\n"
                f"Status: {self.status}\n"
                f"{f"Deployments: {len(self.deployments)}" if self.deployments else ""}"
                )

class Deployment():
    def __init__(self, raw: models.V1Deployment, project_id, cluster_name , location):
        self._raw:models.V1Deployment = raw
        self.name:str = raw.metadata.name
        self.namespace:str = raw.metadata.namespace
        self.project_id:str = project_id
        self.cluster_name:str = cluster_name
        self.location:str = location
        self.replicas:int = raw.spec.replicas or 0

        self.desired_replicas:int = raw.spec.replicas or 0
        self.ready_replicas:int = raw.status.ready_replicas or 0
        self.available_replicas:int = raw.status.available_replicas or 0

    def patch_deployment(self , patch_body):
        Clients.apps_v1().patch_namespaced_deployment(
            name=self.name,
            namespace=self.namespace,
            body=patch_body
        )
    
    def get_memory_hist(self , days:int , rate="1m" , fn=None):
        metric = "kubernetes.io/container/memory/used_bytes"
        query = f"""
        fetch k8s_container
        | metric '{metric}'
        | filter
            resource.cluster_name == '{self.cluster_name}'
            && resource.location == '{self.location}'
            && resource.namespace_name == '{self.namespace}'
            && metadata.system_labels.top_level_controller_name == '{self.name}'
            && metadata.system_labels.top_level_controller_type == 'Deployment'
            && metric.memory_type == 'non-evictable'
        | group_by {rate}, [value_used_bytes_mean: mean(value.used_bytes)]
        | every {rate}
        | within {days}d
        | group_by [],
            [value_used_bytes_mean_aggregate: aggregate(value_used_bytes_mean)]
        """

        df = DataFrame(self._time_series_query(query=query , metric=metric))

        if df.empty:
            return None
        
        df["time"] = to_datetime(df["time"])

        df.set_index("time", inplace=True)
        df.sort_index(ascending=True, inplace=True)
        
        try:
            if fn is not None:
                return fn(df)
            
            else:
                return History_Result(
                deployment= self.name,
                metric= metric,
                df= df
                ) 
            
        except Exception as e:
            logging.error("Error procesando historial")
        
        except InvalidArgument as e:
            print("Escediste el numero de muestras")
            print("Revisa que no excedan 100,000")
            return None   

    def get_cpu_hist(self , days:int , rate="1m" , fn=None):
        metric = "kubernetes.io/container/cpu/core_usage_time"
        query = f"""
        fetch k8s_container
        | metric '{metric}'
        | filter
            resource.cluster_name == '{self.cluster_name}'
            && resource.location == '{self.location}'
            && resource.namespace_name == '{self.namespace}'
            && metadata.system_labels.top_level_controller_name == '{self.name}'
            && metadata.system_labels.top_level_controller_type == 'Deployment'
        | align rate(1m)
        | every {rate}
        | within {days}d
        | group_by [],
            [value_core_usage_time_aggregate: aggregate(value.core_usage_time)]
        """

        df = DataFrame(self._time_series_query(query=query , metric=metric))

        if df.empty:
            return None
        
        df["time"] = to_datetime(df["time"])

        df.set_index("time", inplace=True)
        df.sort_index(ascending=True, inplace=True)
        
        try:
            if fn is not None:
                return fn(df)
            
            else:
                return History_Result(
                deployment= self.name,
                metric= metric,
                df= df
                ) 
            
        except Exception as e:
            logging.error(f"Error procesando historial {e}")

    def _time_series_query(self , query , metric:str):
        metric = metric.split("/")[-1]
        client = Clients.ts_query()

        request = monitoring_v3.QueryTimeSeriesRequest(
            name=f"projects/{self.project_id}",
            query=query,
        )

        try:
            pager = client.query_time_series(request=request)
            rows = []
            for series in pager:
                for points in series.point_data:
                    rows.append({
                        "time" : points.time_interval.end_time,
                        metric : points.values[0].double_value
                    })
            
            return rows

        except InvalidArgument as e:
            print("Escediste el numero de muestras")
            print("Revisa que no excedan 100,000")
            return None

    def iter_history(self, metrics: list[str], days=0):
        @dataclass(frozen=True)
        class MetricHistory:
            deployment: str
            metric: str
            container: str
            values: List[float]
            period: int
            results = []

        for metric in metrics:
            for container in self._raw.spec.template.spec.containers:
                filtro = (
                    f'metric.type = "{metric}" '
                    f'AND resource.labels.cluster_name = "{self.cluster_name}" '
                    f'AND resource.labels.namespace_name = "{self.namespace}" '
                    f'AND resource.labels.container_name = "{container.name}"'
                )

                values, period = self.get_history(
                    metric=metric,
                    filter=filtro,
                    project=f"projects/{self.project_id}",
                    err_data=[self.namespace, container.name],
                    days=days,
                )

                yield MetricHistory(
                                deployment=self.name,
                                metric=metric,
                                container=container.name,
                                values=values,
                                period=period,
                            )

    def iter_current_lr(self):
        @dataclass(frozen=True)
        class CurrentResources:
            deployment: str
            container: str
            limits: dict
            requests: dict

        for container in self._raw.spec.template.spec.containers:
            resources = container.resources
            yield CurrentResources(
                self.name,
                container.name,
                resources.limits,
                resources.requests,
            )
    
    def get_history(self, metric: str, filter: str,
                    project: str, err_data: list, *,
                    hours=0, days=0, weeks=0, period=10,):
        client = Clients.monitoring()

        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours, days=days, weeks=weeks)

        interval = monitoring_v3.TimeInterval(
            start_time={"seconds": int(start.timestamp())},
            end_time={"seconds": int(end.timestamp())},
        )

        aligner = (
            monitoring_v3.Aggregation.Aligner.ALIGN_RATE
            if "cpu" in metric
            else monitoring_v3.Aggregation.Aligner.ALIGN_MEAN
        )

        aggregation = monitoring_v3.Aggregation(
            alignment_period={"seconds": period},
            per_series_aligner=aligner,
            cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_MAX,
        )

        request = {
            "name": project,
            "filter": filter,
            "interval": interval,
            "aggregation": aggregation,
        }

        values = []

        try:
            for serie in client.list_time_series(request=request):
                values.extend(p.value.double_value for p in serie.points)
        except Exception:
            logging.exception(f"Metrics error: {'/'.join(err_data)}")

        return values, period

    def parse_interval(interval: str) -> int:
        UNITS_IN_SECONDS = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
        }

        """
        Convierte un intervalo como '5s', '10m', '2h' en segundos.
        """
        match = re.fullmatch(r"(\d+)\s*([smhd])", interval.lower())
        
        if not match:
            raise ValueError(f"Intervalo inválido: {interval}")
        
        value, unit = match.groups()
        return int(value) * UNITS_IN_SECONDS[unit]

    def __repr__(self):
        return (f"Deployment("
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

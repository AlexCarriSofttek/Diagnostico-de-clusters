import logging , re , math
from log_config import setup_logging
from kubernetes.client import models
from kubernetes import client, config
from datetime import datetime, timezone, timedelta 
from google.cloud.container_v1 import Cluster as Cluster_V1
from kubernetes.client.exceptions import ApiException
from google.cloud import container_v1 , monitoring_v3 , resourcemanager_v3
from google.api_core.exceptions import InvalidArgument , GoogleAPICallError, NotFound
from pandas import DataFrame , to_datetime
from dataclasses import dataclass
from typing import List

setup_logging()
logger = logging.getLogger(__name__)
logger.info("Inicio del proceso")

# Corregir el acceso a los proyectos

#region Utils
@dataclass(frozen=True)
class History_Result:
    deployment: str
    metric: str
    df: DataFrame

@dataclass(frozen=True)
class MetricHistory:
    deployment: str
    metric: str
    container: str
    values: List[float]
    period: int
    results = []

class UnitsCon:
    # Clase con conversion de unidades 
    def bytes2mi(bytes_value): 
        if bytes_value is None or (isinstance(bytes_value, float) and math.isnan(bytes_value)):
            return None
        return int(bytes_value) / (1024 * 1024)

    def bytes2gi(bytes_value: float) -> float:
        if bytes_value is None or (isinstance(bytes_value, float) and math.isnan(bytes_value)):
            return None
        return int(bytes_value) / (1024 ** 3)

    def cpu2millicores(cpu):
        if cpu is None or (isinstance(cpu, float) and math.isnan(cpu)):
            return None
        return math.ceil(cpu * 1000)

    def mb2mi(mb: float) -> float:
        if mb is None or (isinstance(mb, float) and math.isnan(mb)):
            return None
        return int(mb) * 1_000_000 / 1_048_576

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
#endregion 

#region Elements
class Project:
    def __init__(self, project_id: str):
        self.configurar_cliente_kubernetes()
        _ , active_context = config.list_kube_config_contexts()
        
        if not project_id in active_context['name']:
            logger.critical((f"El proyecto abierto no coincide con el configurado. Se recomienda volver a abrir y autenticarse"))
            raise ValueError("El cluster no coincide con el esperado.Se recomienda volver a abrir el proyecto, conectarse al cluster y autenticarse")

        try:
            self._raw = resourcemanager_v3.ProjectsClient().get_project(name=f"projects/{project_id}")

        except (NotFound , GoogleAPICallError) as e:
            logger.critical(
                f"Error cargando proyecto {project_id}: {e}",
                exc_info=True)
            raise RuntimeError(f"No se pudo cargar el proyecto {project_id}") from e

        else:
            self.name = self._raw.display_name
            logger.info(f"{project_id} cargado correctamente")
            self.id = self._raw.project_id

        finally:
            self.clusters: list[Cluster] | None = None

    def load_clusters(self):
        client = container_v1.ClusterManagerClient()
        try:
            response = client.list_clusters(
                parent=f"projects/{self.id}/locations/-"
            )
        except GoogleAPICallError as e:
            logger.error(
                f"Error cargando clusters en {self.name}: {e}",
                exc_info=True)
            raise
        
        else:
            self.clusters = [
                Cluster(c, self.id) for c in response.clusters
            ]

    def configurar_cliente_kubernetes(self):
        try:
            config.load_incluster_config()
        except config.ConfigException:
            try:
                config.load_kube_config()
            except Exception as e:
                logger.critical(f"Error creando el cliente de Kubernetes: {e}")
                raise
    
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
        logger.info(f"Cluster {self.name} cargado correctamente")
        
    def load_namespaces(self):
        try:
            if self.namespaces is not None:
                return

            v1 = Clients.core_v1()
            response = v1.list_namespace()
            self.namespaces = [
                Namespace(ns, self.project_id, self.name , self.location)
                for ns in response.items
            ]
        except ApiException as e:
            logger.error(f"Error cargando namespaces en {self.name}: {e}")
            raise

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
        try:
            if self.deployments is not None:
                return

            apps = Clients.apps_v1()
            response = apps.list_namespaced_deployment(namespace=self.name)
            self.deployments = [
                Deployment(d, self.project_id, self.cluster_name , self.location)
                for d in response.items
            ]
        
        except ApiException as e:
            logger.error(f"Error cargando deployments en {self.name}: {e}")

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

class Deployment:
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

    #------------- Acciones de valores actuales -------------#
    def patch_deployment(self , patch_body):
        try:
            Clients.apps_v1().patch_namespaced_deployment(
                name=self.name,
                namespace=self.namespace,
                body=patch_body
            )
        
        except Exception as e:
            logger.error(f"Error al aplicar el parche a {self.name}")
    
    def get_current_resources(self):
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

    #------------- Funciones en base a Query y MQL-------------#
    def get_memory_hist(self , days:int , rate="1m" , fn=None):
        metric = "kubernetes.io/container/memory/used_bytes"
        rows = []
        for interval in self._parse_interval(days , rate):
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
            | within {interval[0]} {f", {interval[1]}" if interval[1] != "0s" else ""}
            | group_by [],
                [value_used_bytes_mean_aggregate: aggregate(value_used_bytes_mean)]
            """
            result = self._time_series_query(query=query , metric=metric)

            if result:
                rows.extend(result)

        df = DataFrame(rows)

        if df.empty:
            logger.warning(f"Memory hist {self.name} no regreso datos")
            if fn is not None:
                return fn(df)
            return None
        
        df["time"] = to_datetime(df["time"])

        df.set_index("time", inplace=True)
        df.sort_index(ascending=True, inplace=True)

        df["time_delta_seconds"] = (
            df.index - df.index[0]
        ).total_seconds()
        
        if fn is not None:
            return fn(df)
        
        else:
            return History_Result(
            deployment= self.name,
            metric= metric,
            df= df
            ) 

    def get_cpu_hist(self , days:int , rate="1m" , fn=None):
        metric = "kubernetes.io/container/cpu/core_usage_time"
        rows = []
        for interval in self._parse_interval(days , rate):
            query = f"""
            fetch k8s_container
            | metric '{metric}'
            | filter
                resource.cluster_name == '{self.cluster_name}'
                && resource.location == '{self.location}'
                && resource.namespace_name == '{self.namespace}'
                && metadata.system_labels.top_level_controller_name == '{self.name}'
                && metadata.system_labels.top_level_controller_type == 'Deployment'
            | align rate({rate})
            | every {rate}
            | within {interval[0]} {f", {interval[1]}" if interval[1] != "0s" else ""}
            | group_by [],
                [value_core_usage_time_aggregate: aggregate(value.core_usage_time)]
            """

            result = self._time_series_query(query=query , metric=metric)

            if result:
                rows.extend(result)

        df = DataFrame(rows)

        if df.empty:
            logger.warning(f"CPU hist {self.name} no regreso datos")
            if fn is not None:
                return fn(df)
            return None
        
        df["time"] = to_datetime(df["time"])

        df.set_index("time", inplace=True)
        df.sort_index(ascending=True, inplace=True)

        df["time_delta_seconds"] = (
            df.index - df.index[0]
        ).total_seconds()

        if fn is not None:
            return fn(df)
        
        else:
            return History_Result(
            deployment= self.name,
            metric= metric,
            df= df
            )
            
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
            #logger.info(f"Historial de {metric} en {self.name} extraido")
            return rows

        except InvalidArgument:
            logger.exception(
                f"Excediste el número de muestras en {self.name}:{metric}"
            )
            return []
        except GoogleAPICallError:
            logger.exception(
                f"Error en time_series {self.name} {metric}"
            )
            return []

    def _parse_interval(self , days:int , interval: str) -> list[str]:
        chunk_size =  99999
        UNITS_IN_SECONDS = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
        }

        match = re.fullmatch(r"(\d+)\s*([smhd])", interval.lower())
        if not match:
            raise ValueError(f"Formato inválido: {interval}")
        value, unit = match.groups()

        days_s = days * UNITS_IN_SECONDS.get("d")
        interval = int(value) * UNITS_IN_SECONDS.get(unit)
        
        total = int(math.ceil(days_s/interval))
        rate_seconds = int(value) * UNITS_IN_SECONDS[unit]

        segments = []

        for start in range(0, total, chunk_size):
            end = min(start + chunk_size, total)
            
            start_sec = start * rate_seconds
            end_sec = end * rate_seconds

            segments.append((
                        f"-{end_sec}s",
                        f"-{start_sec}s" if start_sec > 0 else "0s",
                    ))

        return segments 

    #------------- Funciones en base a la API moderna-------------#
    def get_cpu_hist_a(self, days:int , fn=None):
        for container in self._raw.spec.template.spec.containers:
            filtro = (
                f'metric.type = "kubernetes.io/container/cpu/core_usage_time" '
                f'AND resource.labels.cluster_name = "{self.cluster_name}" '
                f'AND resource.labels.namespace_name = "{self.namespace}" '
                f'AND resource.labels.container_name = "{container.name}"'
            )

            try:
                values = self._get_list_time_series(
                    aligner= monitoring_v3.Aggregation.Aligner.ALIGN_RATE,
                    filter=filtro,
                    days=days,
                )

                if fn is not None:
                    yield fn(values)
                
                else:
                    yield MetricHistory(
                                    deployment=self.name,
                                    metric="kubernetes.io/container/cpu/core_usage_time",
                                    container=container.name,
                                    values=values,
                                    period=10,
                                )
            
            except Exception as e:
                logger.error(f"Error al obtener el historial de {container.name} en cpu: {e}")
                yield MetricHistory(
                                deployment=self.name,
                                metric="kubernetes.io/container/cpu/core_usage_time",
                                container=container.name,
                                values=None,
                                period=10,
                            )
    
    def get_memory_hist_a(self, days:int , fn=None):
        for container in self._raw.spec.template.spec.containers:
            filtro = (
                f'metric.type = "kubernetes.io/container/memory/used_bytes" '
                f'AND resource.labels.cluster_name = "{self.cluster_name}" '
                f'AND resource.labels.namespace_name = "{self.namespace}" '
                f'AND resource.labels.container_name = "{container.name}"'
            )

            try:
                values = self._get_list_time_series(
                    aligner= monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
                    filter=filtro,
                    days=days,
                )

                if fn is not None:
                    yield fn(values)
                
                else:
                    yield MetricHistory(
                                    deployment=self.name,
                                    metric="kubernetes.io/container/memory/used_bytes",
                                    container=container.name,
                                    values=values,
                                    period=10,
                                )
            
            except Exception as e:
                logger.error(f"Error al obtener el historial de {container.name} en memoria: {e}")
                yield MetricHistory(
                                deployment=self.name,
                                metric="kubernetes.io/container/memory/used_bytes",
                                container=container.name,
                                values=None,
                                period=10,
                            )
    
    def _get_list_time_series(self, aligner:monitoring_v3.Aggregation.Aligner, 
                              filter: str, days=30):
        client = Clients.monitoring()

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        interval = monitoring_v3.TimeInterval(
            start_time={"seconds": int(start.timestamp())},
            end_time={"seconds": int(end.timestamp())},
        )

        aggregation = monitoring_v3.Aggregation(
            alignment_period={"seconds": 10},
            per_series_aligner=aligner,
            cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_MAX,
        )

        request = {
            "name": self.project_id,
            "filter": filter,
            "interval": interval,
            "aggregation": aggregation,
        }

        values = []

        try:
            for serie in client.list_time_series(request=request):
                values.extend(p.value.double_value for p in serie.points)
        except GoogleAPICallError as e:
            logger.exception(f"Metrics error: {e}")
            return None

        return values
    
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
#endregion 
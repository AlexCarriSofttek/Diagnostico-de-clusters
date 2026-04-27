from explorador import Explorador
from elementos import Deployment , UnitsCon as uc
from collections import Counter
from typing import List
import pandas as pd
from datetime import date

import logging
logger = logging.getLogger(__name__)

# Minimos para requests y limites
CPU_MIN_REQUEST = 100
CPU_MIN_LIMIT = 300
MEMORY_MIN_REQUEST = None
MEMORY_MIN_LIMIT = None
RESOURCES_INFLATION = 1.35

class Analisys:
    def __init__(self , project:str|Explorador):
        if isinstance(project, Explorador):
            self.explorer:Explorador = project

        elif isinstance(project, str):
            self.explorer:Explorador = Explorador(project_id=project)

        else:
            raise TypeError(
                "Analisys espera un project_id (str) o un Explorador"
            )
        
        self.file_n_template = f"{self.explorer.project.id}_{date.today()}_"

    #------------- Valores actuales -------------#
    def export_metrics_json(self, days:int , rate="1m") -> None:
        import json

        if days > 20:
            fn = Analisys.segmented_stat
        else:
            fn = Analisys.resume_stat

        with open("metrics_history.json", "w") as f:
            f.write("[\n")
            first = True

            for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
                if not first:      
                    f.write("[\n")
                first = False

                cpu_hist = deployment.get_cpu_hist(days=days , rate=rate).df
                memory_hist = deployment.get_memory_hist(days=days , rate=rate).df

                if cpu_hist.empty and memory_hist.empty:
                    continue

                cpu_stat , cpu_request , cpu_limit = fn(cpu_hist)
                memory_stat , memory_request , memory_limit = fn(memory_hist)
                
                json.dump(
                    {
                        "deployment": deployment.name,
                        "cpu_values": cpu_hist.iloc[:,0].to_list(),
                        "cpu_times" : cpu_hist["time_delta_seconds"].to_list(),
                        "cpu_stat": cpu_stat,
                        "cpu_request" : cpu_request,
                        "cpu_limit" : cpu_limit,
                        "memory_values": memory_hist.iloc[:,0].to_list(),
                        "memory_times" : memory_hist["time_delta_seconds"].to_list(),
                        "memory_stat": memory_stat,
                        "memory_request" : memory_request,
                        "memory_limit" : memory_limit,
                    } , f , ensure_ascii=False,
                )
            f.write("\n]")
            print("Json guardado")
  
    def get_current_resources(self) -> pd.DataFrame:
        dfs = []
        try:
            for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
                dfs.append(self.get_current_resource(deployment=deployment))

            df = pd.concat(dfs).sort_index()

            return df
        except Exception as e:
            logger.warning(f"Advertencia cargando los recursos actuales")

    def get_current_resource(self , deployment:Deployment) -> pd.DataFrame:
        df_resources = pd.DataFrame([
            {   
                "deployment": r.deployment,
                "container": r.container,            
                "cpu_request": (
                    r.requests.get("cpu")
                    if r.requests and isinstance(r.requests, dict)
                    else "N/A"
                ),
                "cpu_limit": (
                    r.limits.get("cpu")
                    if r.limits and isinstance(r.limits, dict)
                    else "N/A"
                ),
                "mem_request": (
                    r.requests.get("memory")
                    if r.requests and isinstance(r.requests, dict)
                    else "N/A"
                ),
                "mem_limit": (
                    r.limits.get("memory")
                    if r.limits and isinstance(r.limits, dict)
                    else "N/A"
                )
            }
            for r in deployment.get_current_resources()
        ]).set_index("deployment")

        return df_resources

    #------------- Recomendaciones de recursos -------------#
    def limits_requests_format(self , days=1 , rate="1m"):
        df = self.get_resources_suggestions(days=days , rate=rate)
        
        df["static_cpu"] = df["static_cpu"].apply(uc.cpu2millicores)
        df["recommended_cpu_request"] = df["recommended_cpu_request"].apply(uc.cpu2millicores)
        df["recommended_cpu_limit"] = df["recommended_cpu_limit"].apply(uc.cpu2millicores)

        df["recommended_cpu_request"] = df["recommended_cpu_request"].clip(lower=CPU_MIN_REQUEST)
        df["recommended_cpu_limit"] = df["recommended_cpu_limit"].clip(lower=CPU_MIN_LIMIT)

        df["static_memory"] = df["static_memory"].apply(uc.bytes2mi)
        df["recommended_memory_request"] = df["recommended_memory_request"].apply(uc.bytes2mi)
        df["recommended_memory_limit"] = df["recommended_memory_limit"].apply(uc.bytes2mi)

        df["recommended_cpu_request"] = df["recommended_cpu_request"].apply(
            lambda x: f"{int(x)}m" if pd.notnull(x) else "N/A"
        )

        df["recommended_cpu_limit"] = df["recommended_cpu_limit"].apply(
            lambda x: f"{int(x)}m" if pd.notnull(x) else "N/A"
        )

        df["recommended_memory_request"] = df["recommended_memory_request"].apply(
            lambda x: f"{int(x)}Mi" if pd.notnull(x) else "N/A"
        )

        df["recommended_memory_limit"] = df["recommended_memory_limit"].apply(
            lambda x: f"{int(x)}Mi" if pd.notnull(x) else "N/A"
        )
  
        df["Aprovado (T/F)"] = False
        df["Aprovado (T/F)"] = df["Aprovado (T/F)"].astype(bool)

        # Backup
        self.get_current_resources().to_csv(f"{self.file_n_template}back_up.csv")

        df.to_csv(f"{self.file_n_template}suggestions.csv")

        return df

    def get_resources_suggestions(self , days=30 , rate="30s") -> pd.DataFrame:
        dfs = []
        for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
            dfs.append(self.mem_cpu_suggestion(deployment=deployment , days=days , rate=rate))

        df = pd.concat(dfs).sort_index()

        return df  

    def mem_cpu_suggestion(self , deployment:Deployment , days=30 , rate="30s") -> pd.DataFrame:
        if days > 20:
            fn = Analisys.segmented_stat
        else:
            fn = Analisys.resume_stat

        try:
            cpu_stat , cpu_request , cpu_limit = deployment.get_cpu_hist(days=days , rate=rate , fn=Analisys.cpu_suggestion)
            memory_stat , memory_request , memory_limit = deployment.get_memory_hist(days=days , rate=rate , fn=fn)
            print(deployment.name , cpu_stat , cpu_request , cpu_limit)
            sugestion = pd.DataFrame({
                "namespace" : deployment.namespace,
                "static_cpu" : cpu_stat,
                "static_memory" : memory_stat,
                "recommended_cpu_request": cpu_request,
                "recommended_cpu_limit" : cpu_limit,
                "recommended_memory_request": memory_request,
                "recommended_memory_limit" : memory_limit
                },index=[deployment.name])
                
            sugestion.index.name = "deployment"
            logger.info(f"Sugerencias de {deployment.name} fueron generadas")
            return sugestion
        
        except Exception as e:
            logger.error(f"Error al generar las sugerencias de {deployment.name}")
            raise

    #------------- Proceso de valores de CPU -------------#
    def cpu_suggestion(df:pd.DataFrame) -> float|None:
        values = df.iloc[:,0].round(1)
        filtered = values[values >= 0.1]
        ref = filtered.quantile(0.7) * 1.15 # Le damos un 15% de tolerancia
        request = ref * RESOURCES_INFLATION
        limit = max(ref * 2.5 , values.quantile(0.99) * RESOURCES_INFLATION)

        return ref , request , limit

    #------------- Calculos de valor estacionario -------------#
    def resume_stat(df:pd.DataFrame) -> float | None:
        if df.empty:
                return None
        
        period_seconds = (
            df.index.to_series()
            .diff()
            .dt.total_seconds()
            .median()
        )

        if pd.isna(period_seconds) or period_seconds <= 0:
                return None

        period = int(period_seconds)

        stat = Analisys.stationary_by_duration(
            values=df.iloc[:,0].to_list(),
            period=period,
            precision=4,
        )

        request = stat * RESOURCES_INFLATION
        limit = max(stat * 2.5 , df.iloc[:,0].quantile(0.999) * RESOURCES_INFLATION)

        return stat , request , limit

    def segmented_stat(df:pd.DataFrame) -> float |None:
        def stat_(values:pd.Series):      
            if values.empty:
                    return None

            period_seconds = (
                    values.index.to_series()
                    .diff()
                    .dt.total_seconds()
                    .median()
                )

            if pd.isna(period_seconds) or period_seconds <= 0:
                return None

            period = int(period_seconds)

            return Analisys.stationary_by_duration(
                values=values.to_list(),
                period=period,
                precision=4,
            )

        # Segmenta en intervalos de 10 días y elige el 
        # valor estatico más grande para referencia
        # Se recomienda en caso de histogramas grandes
        values = df.iloc[:,0]
        static = values.resample("10D").apply(stat_).max()
        request = static * RESOURCES_INFLATION
        limit = max(static * 2.5 , values.quantile(0.99) * RESOURCES_INFLATION)

        return static , request , limit

    def stationary_by_duration(values: List[float], period: int,
                               precision: int = 4) -> float | None:
        # Encuentra el valor en el que el deployment pasa más tiempo.         
        if not values:
            return None
        durations = Counter()
        for v in values:
            durations[round(v, precision)] += period

        # Valor con mayor tiempo acumulado
        return durations.most_common(1)[0][0]

if __name__ == "__main__":
    project_ids = [
        "cpl-ssff-cnsulcc-dev-05122025",
    ]

    for project_id in project_ids:
        explorador = Explorador(project_id=project_id)
        analisis = Analisys(explorador)
        recomendaciones = analisis.limits_requests_format(days=1 , rate="1m")
        recomendaciones.loc[recomendaciones.index[0], 'Aprovado (T/F)'] = True
        print(recomendaciones)

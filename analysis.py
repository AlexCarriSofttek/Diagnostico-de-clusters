from explorador import Explorador
from elementos import Deployment
from collections import Counter
from typing import List
from dataclasses import dataclass
from converters import bytes2mi , cpu2millicores
import pandas as pd

# Teoria para cuando stat values es = 0 sin motivo es que 
# haya que tomar el segundo acumulado mas concurrido 

class Analisys:
    def __init__(self , project_id: str):
        self.explorer = Explorador(project_id=project_id)

    def limits_requests_suggestions(self , metrics: List[str] , hours=0 , days=0 , weeks=0):
        df = self.get_resources_res(metrics=metrics , hours=hours , days=days , weeks=weeks)
        
        df["static_cpu"] = df["static_cpu"].apply(cpu2millicores)
        df["static_memory"] = df["static_memory"].apply(bytes2mi)

        df["recommended_cpu_request"] = (df["static_cpu"] * 1.35).round(0)
        df["recommended_cpu_limit"]   = (df["static_cpu"] * 2).round(0)

        df["recommended_mem_request"] = (df["static_memory"] * 1.35).round(0)
        df["recommended_mem_limit"]   = (df["static_memory"] * 2).round(0)

        df["recommended_cpu_request"] = df["recommended_cpu_request"].apply(
            lambda x: f"{int(x)}m" if pd.notnull(x) else "N/A"
        )

        df["recommended_cpu_limit"] = df["recommended_cpu_limit"].apply(
            lambda x: f"{int(x)}m" if pd.notnull(x) else "N/A"
        )

        df["recommended_mem_request"] = df["recommended_mem_request"].apply(
            lambda x: f"{int(x)}Mi" if pd.notnull(x) else "N/A"
        )

        df["recommended_mem_limit"] = df["recommended_mem_limit"].apply(
            lambda x: f"{int(x)}Mi" if pd.notnull(x) else "N/A"
        )

        return df

    def get_current_resources(deployment:Deployment):
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
            for r in deployment.iter_current_lr()
        ])

        return df_resources

    def get_resources_suggestion(self , deployment:Deployment , days=30 , rate="30s"):
        cpu = deployment.get_cpu_hist(days=days , rate=rate)
        memory = deployment.get_memory_hist(days=days , rate=rate)

        cpu_period = int(
            cpu.index.to_series()
            .diff()
            .dt.total_seconds()
            .median()
        )

        memory_period = int(
            memory.index.to_series()
            .diff()
            .dt.total_seconds()
            .median()
        )

        stat_cpu = self.stationary_by_duration(
            values=cpu["cores"].to_list(),
            period=cpu_period,
            precision=4
        )

        stat_memory = self.stationary_by_duration(
            values=memory["bytes"].to_list(),
            period=memory_period,
            precision=4
        )

        return pd.DataFrame({
            "deployment" : deployment.name,
            "namespace" : deployment.namespace,
            "cpu_static" : stat_cpu,
            "memory_static" : stat_memory,
            "recomended_cpu_request": stat_cpu * 1.4,
            "recomended_cpu_limit" : "",
            "recomended_memory_request": stat_memory * 1.4,
            "recomended_memory_limit" : ""
            }).set_index("deployment")

    def get_resources_suggestions(self):
        dfs = []
        for deployment in Explorador.iter_deployments():
            dfs.append(self.get_resources_suggestion(deployment=deployment))

        df = pd.concat(dfs).sort_index()

        return df  
    
    def export_metrics_json(self, days:int , rate="1m"):
        import json
        metrics_json = []

        for deployment in self.explorer.iter_deployments_filter(["kube" , "gmp" , "gke" , "default"]):
            cpu = deployment.get_cpu_hist(days=days , rate=rate)
            memory = deployment.get_memory_hist(days=days , rate=rate)

            cpu_period = int(
                cpu.index.to_series()
                .diff()
                .dt.total_seconds()
                .median()
            )

            memory_period = int(
                memory.index.to_series()
                .diff()
                .dt.total_seconds()
                .median()
            )

            stat_cpu = self.stationary_by_duration(
                values=cpu["cores"].to_list(),
                period=cpu_period,
                precision=4
            )

            stat_memory = self.stationary_by_duration(
                values=memory["bytes"].to_list(),
                period=memory_period,
                precision=4
            )
            
            metrics_json.append(
                {
                    "deployment": deployment.name,
                    "cpu_values": cpu["cores"].to_list(),
                    "cpu_times" : cpu["time"].to_list(),
                    "cpu_period": cpu_period,
                    "cpu_stat" : stat_cpu,
                    "memory_values": memory["bytes"].to_list(),
                    "memory_times" : memory["time"].to_list(),
                    "memory_period": memory_period,
                    "memory_stat" : stat_memory,
                }
            )

        with open("metrics_history.json", "w") as f:
            json.dump(metrics_json, f, indent=2)
    # En este caso funciona por encontrar el valor en el que el 
    # deployment pasa más tiempo. 
    def stationary_by_duration(self , values: List[float], period: int,
                               precision: int = 4) -> float | None:
        
        if not values:
            return None
        durations = Counter()
        for v in values:
            durations[round(v, precision)] += period

        # Valor con mayor tiempo acumulado
        return durations.most_common(1)[0][0]


if __name__ == "__main__":
    METRICS = ["kubernetes.io/container/memory/used_bytes" , "kubernetes.io/container/cpu/core_usage_time"]

    a = Analisys("cpl-ssff-adqbbva-qa-13052025").get_resources_res(metrics=METRICS , hours=1)
    print(a)
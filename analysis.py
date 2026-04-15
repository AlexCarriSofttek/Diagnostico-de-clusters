from explorador import Explorador
from collections import Counter
from typing import List
import pandas as pd
import json

# Nota: 7 días de datos es pesado pero deberia de cubrir la
# mayoria de los casos
# 
# Teoria para cuando stat values es = 0 sin motivo es que 
# haya que tomar el segundo acumulado mas concurrido 

class Analisys:
    def __init__(self , project_id: str):
        self.explorer = Explorador(project_id=project_id)

    def limits_requests(self , metrics: List[str] , hours=0 , days=0 , weeks=0):
        pass

    def get_resources_history(self , metrics: List[str] , hours=0 , days=0 , weeks=0):
        dfs = []
        for deployment in self.explorer.iter_deployments():
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
            
            df_metrics = pd.DataFrame([
                {
                    "deployment": m.deployment,
                    "container": m.container,
                    "metric": m.metric,
                    "Stat value": self.stationary_by_duration(m.values , m.period),
                    #"period": m.period
                }
                for m in deployment.iter_history(metrics=metrics,
            hours=hours , days=days , weeks=weeks)
            ])
            
            df_metrics = (
                df_metrics
                .pivot_table(
                    index=["deployment", "container"],
                    columns="metric",
                    values="Stat value",
                    aggfunc="first"
                )
                .reset_index().rename(columns={"kubernetes.io/container/cpu/core_usage_time": "cpu_stat",
                                        "kubernetes.io/container/memory/used_bytes": "memory_stat"})
            )

            dfs.append(pd.merge(
                df_resources,
                df_metrics,
                on=["deployment", "container"],
                how="left"
            ))
            
        return pd.concat(dfs , ignore_index=True)
    
    def export_metrics_json(self, metrics: List[str], hours=0, days=0, weeks=0):
        metrics_json = []

        for deployment in self.explorer.iter_deployments():
            for m in deployment.iter_history(
                metrics=metrics,
                hours=hours,
                days=days,
                weeks=weeks
            ):
                stat_value = self.stationary_by_duration(m.values, m.period)

                metrics_json.append(
                    {
                        "deployment": m.deploymentdeployment,
                        "container": m.container,
                        "metric": m.metric,
                        "period": m.period,
                        "values": m.values,
                        "stat_value": stat_value
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

    a = Analisys("cpl-ssff-adqbbva-qa-13052025").get_resources_history(metrics=METRICS , hours=1)
    print(a)
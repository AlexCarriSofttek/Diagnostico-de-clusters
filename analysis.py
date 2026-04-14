from explorador import Explorador
from collections import Counter
from typing import List
import pandas as pd

MIN_CPU_REQUEST = 0.010   # 10m
MIN_MEMORY_REQUEST = 64  # 64 MB

class Analisys:
    def __init__(self , project_id: str):
        self.explorer = Explorador(project_id=project_id)

    def limits_requests(self , metrics: List[str] , hours=0 , days=0 , weeks=0):
        pass

    def get_resources_history(self , metrics: List[str] , hours=0 , days=0 , weeks=0):
        for deployment in self.explorer.iter_deployments():
            for resources in deployment.get_current_lr():
                print(resources.limits)
            for history in deployment.iter_history(metrics=metrics,
            hours=hours , days=days , weeks=weeks):
                print(history)

    def HPA_recomendations():
        pass
    
    def stationary_by_duration(values: List[float], period: int,
                               precision: int = 4) -> float | None:
        
        if not values:
            return None

        durations = Counter()
        for v in values:
            durations[round(v, precision)] += period

        # Valor con mayor tiempo acumulado
        return durations.most_common(1)[0][0]
    
class Safety:
    def request_safety(recommended_request: float, current_request: float, 
                             avg_usage: float, min_request: float, max_observed: float) -> float:
        # Regla R2: mínimo absoluto
        recommended_request = max(recommended_request, min_request)

        # Regla R3: el request no debe representar picos
        recommended_request = min(recommended_request, max_observed)

        # Regla R1: no reducir si ya va justo (>70%)
        if current_request > 0:
            usage_pct = avg_usage / current_request
            if usage_pct > 0.70:
                recommended_request = max(recommended_request, current_request)

        return recommended_request


if __name__ == "__main__":
    METRICS = ["kubernetes.io/container/memory/used_bytes" , "kubernetes.io/container/cpu/core_usage_time"]
    explorer = Explorador("cpl-ssff-adqbbva-qa-13052025")

    for deployment in explorer.iter_deployments():
        for history in deployment.iter_history(
            metrics=METRICS,
            hours=1,
        ):
            print(
                history.deployment,
                history.metric,
                Analisys.stationary_by_duration(history.values , history.period) if history.values else 0
            )
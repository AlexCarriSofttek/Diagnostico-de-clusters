# Este script es el punto principal de la herramienta
from analysis import Metrics , Inventario
import argparse
# Pendientes
# - Documentacion 

# Inventarios 
# - Todo lo relacionado con el aplicativo menos informacion sensible (No secretos)
def get_args():
    parser = argparse.ArgumentParser(
        description="Analiza proyectos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="" # Pendiente
    )

    parser.add_argument(
        "-m", "--modo",
        default="inventario",
        help="Que se va a hacer si inventario o sugerencias"
    )

    parser.add_argument(
        "--project-id",
        default=None,
        help="GCP Project ID (auto-detecta si no se especifica)"
    )

    parser.add_argument(
        "--cluster-name",
        help="GKE Cluster name (auto-detecta si no se especifica)"
    )

    parser.add_argument(
        "-o", "--output",
        default="gke_resource_analysis.csv",
        help="Archivo de salida CSV (default: gke_resource_analysis.csv)"
    )

    return parser.parse_args()

if __name__ == "__main__":
    arg = get_args()

    if arg.project_id is None:
        raise ValueError("El proyecto esta vacío")
    
    project_id = arg.project_id

    if arg.mode == "inventario":
        inventario = Inventario(project_id)
    
    elif arg.mode == "sugerencias":
        metricas = Metrics(project_id)
        recomendaciones = metricas.limits_requests_format(days=1 , rate="1m")

        

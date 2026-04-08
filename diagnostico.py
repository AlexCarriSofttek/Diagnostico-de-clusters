# Este script es el punto principal de la herramienta
# Sin embargo considere que se esta segmentando los puntos 
# de la herramienta con base a su funcion 

import sys
import os

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from google.cloud import monitoring_v3
    from google.protobuf.timestamp_pb2 import Timestamp
    HAS_MONITORING = True
except ImportError:
    HAS_MONITORING = False
    print("⚠️  google-cloud-monitoring no instalado. Instala con: pip install google-cloud-monitoring")


import json
from parsers.mercado_inmobiliario import obtener_mediana_cluster

# Verificar cluster para Martin 1 dorm
valor, n = obtener_mediana_cluster("Martin", 1, "venta")
print(f"Cluster Martin 1 dorm: {valor} ({n} muestras)")

# Verificar el ancla que se usa
from parsers.location_engine import cargar_anclas
anclas = cargar_anclas()

# Buscar martin
for a in anclas.get('anclas', []):
    if 'martin' in a.get('id', '').lower():
        print(f"Ancla: {a['id']} = ${a['usd_m2']}")
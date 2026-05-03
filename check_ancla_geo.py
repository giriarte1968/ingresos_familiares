import json
from parsers.location_engine import cargar_anclas
import math

anclas = cargar_anclas()
lat, lon = -32.9541101, -60.6316406

min_dist = float('inf')
ancla_cercana = None
valor_ancla = 1500

anclas_list = anclas.get('anclas', list(anclas.values())) if isinstance(anclas, dict) else anclas

for a in anclas_list:
    a_lat = a.get('lat')
    a_lon = a.get('lon')
    if a_lat is None or a_lon is None:
        continue
    R = 6371
    lat1, lon1, lat2, lon2 = math.radians(lat), math.radians(lon), math.radians(a_lat), math.radians(a_lon)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    dist = 2 * R * math.asin(math.sqrt(math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2))
    
    if dist < min_dist:
        min_dist = dist
        ancla_cercana = a.get('id')
        valor_ancla = a.get('usd_m2', 1500)

print(f"Coordenadas: lat={lat}, lon={lon}")
print(f"Ancla mas cercana: {ancla_cercana}")
print(f"USD/m2: {valor_ancla}")
print(f"Distancia: {min_dist:.3f}km")
import json
import math

def get_dist(lat1, lon1, lat2, lon2):
    R = 6371.0 # km
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

with open('cache_scraping.json', encoding='utf-8') as f:
    data = json.load(f)
props = data.get('propiedades', [])

targets = [
    {'nombre': 'Mabel', 'lat': -32.9541101, 'lon': -60.6316406},
    {'nombre': 'Ayacucho', 'lat': -32.960323, 'lon': -60.6299652}
]

for t in targets:
    total_nearby = 0
    qualified_nearby = 0
    for p in props:
        p_lat, p_lon = p.get('lat'), p.get('lon')
        if p_lat and p_lon:
            if get_dist(t['lat'], t['lon'], p_lat, p_lon) <= 1.5:
                total_nearby += 1
                if p.get('anio_construccion') is not None:
                    qualified_nearby += 1
    print(f'--- {t["nombre"]} ---')
    print(f'Propiedades en radio 1.5km: {total_nearby}')
    print(f'Propiedades CON año (Calificadas): {qualified_nearby}')
    print(f'Cobertura de datos: {(qualified_nearby/total_nearby*100 if total_nearby > 0 else 0):.2f}%')

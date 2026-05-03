import json
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

anclas = json.load(open('anclas_rosario_v2_grid.json', 'r', encoding='utf-8'))['anclas']
props = json.load(open('propiedades.json', 'r', encoding='utf-8'))['propiedades']

for p in props:
    lat, lon = p.get('lat'), p.get('lon')
    direccion = p.get('direccion', '')
    print(f"\n{direccion} -> lat:{lat}, lon:{lon}")
    
    # Encontrar las 3 anclas más cercanas
    distancias = [(a['id'], a['usd_m2'], haversine(lat, lon, a['lat'], a['lon'])) for a in anclas]
    sorted_dists = sorted(distancias, key=lambda x: x[2])
    for i, (aid, ausd, dist) in enumerate(sorted_dists[:3]):
        print(f"  {i+1}. {aid}: ${ausd}/m2 a {dist:.3f}km")
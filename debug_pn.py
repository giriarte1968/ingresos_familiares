import json
from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371 
    return c * r

base = r'C:\Users\Gustavo\ingresos_familiares_st'
with open(base + r'\propiedades.json', 'r', encoding='utf-8') as f:
    portfolio_data = json.load(f)

with open(base + r'\cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

portfolio = portfolio_data.get('propiedades', [])
props_cache = cache.get('propiedades', [])
pn_props = [p for p in props_cache if p.get('zona', '').replace(' ','').lower() == 'puertonorte']

# Find Subject in portfolio
sujeto = next((p for p in portfolio if p.get('nombre') == 'Francia 250b'), None)
if not sujeto:
    print('Sujeto Francia 250b not found in propiedades.json')
    for p in portfolio:
        if 'Francia' in p.get('nombre', ''):
            print(f"Found similar: {p.get('nombre')}")
    exit()

s_lat = sujeto.get('lat') or sujeto.get('latitud')
s_lon = sujeto.get('lon') or sujeto.get('longitud')
print(f'Sujeto: {s_lat}, {s_lon}')

print('\nDistances and Dates in PN Cache:')
for p in pn_props:
    p_lat = p.get('lat') or p.get('latitud')
    p_lon = p.get('lon') or p.get('longitud')
    fecha = p.get('fecha')
    nombre = p.get('nombre', 'Unknown')
    if p_lat and p_lon:
        dist = haversine(s_lon, s_lat, p_lon, p_lat)
        status = 'IN' if dist <= 1.5 else 'OUT'
        print(f'{nombre} | dist: {dist:.2f}km | {status} | fecha: {fecha}')
    else:
        print(f'{nombre} | NO COORDS | fecha: {fecha}')

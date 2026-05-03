import json
import math

mabel_lat = -32.9541101
mabel_lon = -60.6316406

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

print('=== COORDENADAS DE PROPIEDADES ALQUILER EN MARTIN (1 DORMITORIO) ===')

props = []
for p in cache.get('propiedades', []):
    if p.get('zona', '').lower() != 'martin':
        continue
    if p.get('dormitorios') != 1:
        continue
    if p.get('operacion') != 'alquiler':
        continue
    if p.get('moneda') != 'ARS':
        continue
    
    lat = p.get('lat')
    lon = p.get('lon')
    
    dist = None
    if lat and lon:
        R = 6371
        lat1 = math.radians(mabel_lat)
        lon1 = math.radians(mabel_lon)
        lat2 = math.radians(lat)
        lon2 = math.radians(lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        dist = R * c
    
    props.append({
        'direccion': p.get('direccion', 'N/A'),
        'lat': lat,
        'lon': lon,
        'dist_km': dist,
        'm2': p.get('m2', 0),
        'precio': p.get('precio', 0),
        'valor_m2': p.get('valor_m2', 0)
    })

props.sort(key=lambda x: x['dist_km'] if x['dist_km'] else 999)

print('Total properties:', len(props))
print('')

for i, p in enumerate(props, 1):
    dist_str = 'N/A'
    if p['dist_km']:
        dist_str = '%.1f km' % p['dist_km']
    
    lat_str = 'SIN COORD'
    lon_str = 'SIN COORD'
    if p['lat']:
        lat_str = '%.6f' % p['lat']
    if p['lon']:
        lon_str = '%.6f' % p['lon']
    
    dir_short = p['direccion'][:25]
    print('%s | %s | %s | %s | m2=%s' % (dir_short.ljust(25), lat_str.ljust(14), lon_str.ljust(14), dist_str.ljust(8), p['m2']))

print('')
print('=== RESUMEN ===')
with_coords = sum(1 for p in props if p['dist_km'])
print('Con coordenadas: %d/%d' % (with_coords, len(props)))

if with_coords > 0:
    real_dists = [p['dist_km'] for p in props if p['dist_km']]
    print('Rango distancia: %.0fm - %.0fm' % (min(real_dists)*1000, max(real_dists)*1000))
    within_1km = sum(1 for d in real_dists if d <= 1.0)
    print('A menos de 1km: %d' % within_1km)
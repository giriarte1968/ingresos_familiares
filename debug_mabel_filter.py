import json
from parsers.location_engine import distancia

lat_ref = -32.9541
lon_ref = -60.6316

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

props = data.get('propiedades', [])
candidatos = []

for p in props:
    # Same filters as model
    tipo = p.get('tipo', '').lower()
    if tipo != 'departamento': continue
    if p.get('dormitorios') != 1: continue
    if p.get('operacion') != 'venta': continue
    if p.get('moneda') != 'USD': continue
    
    lat = p.get('lat')
    lon = p.get('lon')
    if lat and lon:
        d = distancia(lat_ref, lon_ref, lat, lon)
        if d <= 1.0:
            vm2 = p.get('valor_m2', 0)
            candidatos.append({**p, 'distancia_km': d})

# Sort by distance
candidatos.sort(key=lambda x: x['distancia_km'])

print(f"Found {len(candidatos)} properties within 1km matching filters")
print("-" * 100)
for i, p in enumerate(candidatos[:50], 1):
    print(f"{i:3}. {p.get('direccion', 'N/A')[:30]:<30} | vm2: {p.get('valor_m2', 0):>8.2f} | dist: {p['distancia_km']:>6.4f}km")

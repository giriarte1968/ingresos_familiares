import json
from parsers.location_engine import distancia

lat_ref = -32.9541
lon_ref = -60.6316

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

props = data.get('propiedades', [])
close_props = []

for p in props:
    lat = p.get('lat')
    lon = p.get('lon')
    if lat and lon:
        d = distancia(lat_ref, lon_ref, lat, lon)
        if d < 0.1:
            close_props.append({**p, 'dist': d})

print(f"Properties within 100m: {len(close_props)}")
print("-" * 100)
for p in close_props:
    print(f"Dir: {p.get('direccion', 'N/A')[:30]:<30} | Tipo: {p.get('tipo', 'N/A'):<12} | Dorms: {p.get('dormitorios')} | Op: {p.get('operacion', 'N/A'):<6} | Mon: {p.get('moneda', 'N/A'):<4} | Dist: {p['dist']:.4f}")

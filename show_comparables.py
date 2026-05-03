import json
import math
from parsers.location_engine import distancia

# Load cache
with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

# Mabel coordinates
lat_ref = -32.9541
lon_ref = -60.6316

# Filter: department, 1 bedroom, venta, USD, within 800m
propiedades = cache.get('propiedades', [])
candidatos = []

for p in propiedades:
    if p.get('tipo', '').lower() != 'departamento':
        continue
    if p.get('dormitorios') != 1:
        continue
    if p.get('operacion') != 'venta':
        continue
    if p.get('moneda') != 'USD':
        continue
    
    lat = p.get('lat')
    lon = p.get('lon')
    if lat and lon:
        d = distancia(lat_ref, lon_ref, lat, lon)
        if d <= 800:
            vm2 = p.get('valor_m2', 0)
            if vm2 and 400 <= vm2 <= 5000:  # filtro outlier abs
                candidatos.append({**p, 'distancia_m': d})

# Sort by distancia
candidatos.sort(key=lambda x: x['distancia_m'])

print(f"=== COMPARABLES PARA MABEL (radio 800m) ===")
print(f"Total encontrados: {len(candidatos)}")
print()

# Calcular mediana
vals = [c['valor_m2'] for c in candidatos]
vals.sort()
n = len(vals)
mediana = vals[n//2] if n else 0
print(f"Mediana cluster: ${mediana:.2f} USD/m2")
print()

# Lista completa
print("-" * 120)
for i, c in enumerate(candidatos, 1):
    direccion = c.get('direccion', 'N/A')[:45]
    m2 = c.get('m2', 0)
    precio = c.get('precio', 0)
    zona = c.get('zona', 'N/A')[:20]
    vm2 = c.get('valor_m2', 0)
    dist = c.get('distancia_m', 0)
    url = c.get('url', '')
    fuente = c.get('fuente', 'N/A')
    
    print(f"{i:3}. {direccion}")
    print(f"    m2:{m2:6.1f}  precio:${precio:>10,.0f}  vm2:${vm2:>6.0f}  zona:{zona:<20}  dist:{dist:>5.0f}m  fuente:{fuente}")
    print()
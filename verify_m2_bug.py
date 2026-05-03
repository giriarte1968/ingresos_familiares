import json
import numpy as np
from parsers.location_engine import distancia

# Mabel's coordinates
lat_ref = -32.9541
lon_ref = -60.6316

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

props = cache.get('propiedades', [])
candidatos = []

# Model filters
for p in props:
    if p.get('tipo', '').lower() != 'departamento': continue
    if p.get('dormitorios') != 1: continue
    if p.get('operacion') != 'venta': continue
    if p.get('moneda') != 'USD': continue
    
    lat, lon = p.get('lat'), p.get('lon')
    if lat and lon:
        d = distancia(lat_ref, lon_ref, lat, lon)
        if d <= 0.8:
            vm2 = p.get('valor_m2', 0)
            if vm2 and 400 <= vm2 <= 5000:
                candidatos.append({**p, 'dist': d})

# IQR Filter
if candidatos:
    vals = sorted([c['valor_m2'] for c in candidatos])
    q1, q3 = np.percentile(vals, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    final_pool = [c for c in candidatos if lower <= c['valor_m2'] <= upper]
    final_pool.sort(key=lambda x: x['dist'])
else:
    final_pool = []

print(f"VERIFICACION DE M2 - COMPARABLES DE MABEL")
print(f"Total: {len(final_pool)}")
print("-" * 100)
print(f"{'#':<4} {'Dirección':<40} {'REAL m2':<12} {'vm2':<10} {'Dist':<8}")
print("-" * 100)

for i, p in enumerate(final_pool[:50], 1):
    # The most critical check: what is the m2 in the cache for this property?
    m2 = p.get('m2', p.get('m2_cubiertos', 'N/A'))
    print(f"{i:<4} {p.get('direccion', 'N/A')[:39]:<40} {str(m2):<12} {p.get('valor_m2', 0):>8.2f} {p['dist']:>6.3f}km")

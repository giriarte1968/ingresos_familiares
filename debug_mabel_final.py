import json
import numpy as np
from parsers.location_engine import distancia

lat_ref = -32.9541
lon_ref = -60.6316

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

# 1. Basic Filters
props = cache.get('propiedades', [])
candidatos = []
for p in props:
    if p.get('tipo', '').lower() != 'departamento': continue
    if p.get('dormitorios') != 1: continue
    if p.get('operacion') != 'venta': continue
    if p.get('moneda') != 'USD': continue
    
    lat, lon = p.get('lat'), p.get('lon')
    if lat and lon:
        d = distancia(lat_ref, lon_ref, lat, lon)
        if d <= 0.8: # 800m
            vm2 = p.get('valor_m2', 0)
            if vm2 and 400 <= vm2 <= 5000:
                candidatos.append({**p, 'dist': d})

print(f"Candidatos en radio 800m: {len(candidatos)}")

# 2. IQR Filter
if candidatos:
    vals = sorted([c['valor_m2'] for c in candidatos])
    q1, q3 = np.percentile(vals, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    print(f"IQR: q1={q1:.2f}, q3={q3:.2f}, iqr={iqr:.2f}")
    print(f"Rango aceptable: {lower:.2f} - {upper:.2f}")
    
    final_pool = [c for c in candidatos if lower <= c['valor_m2'] <= upper]
    print(f"Pool final después de IQR: {len(final_pool)}")
    
    final_pool.sort(key=lambda x: x['dist'])
    
    print("-" * 110)
    print(f"{'#':<4} {'Dirección':<45} {'vm2':<10} {'dist':<8} {'Zona'}")
    print("-" * 110)
    for i, p in enumerate(final_pool, 1):
        print(f"{i:<4} {p.get('direccion', 'N/A')[:44]:<45} {p.get('valor_m2', 0):>8.2f} {p['dist']:>6.3f}km {p.get('zona', 'N/A')}")
else:
    print("No se encontraron candidatos")

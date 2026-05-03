import json
from parsers.location_engine import distancia

# Mabel's coordinates
lat_ref = -32.9541
lon_ref = -60.6316

# Load cache
with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

propiedades = cache.get('propiedades', [])
candidatos = []

# 1. Basic Filters (type, dorms, operation, currency, distance)
for p in propiedades:
    # The model uses 'tipo' or 'tipo_inmueble' depending on source, 
    # but usually 'tipo' in cache_scraping.json
    tipo = p.get('tipo', '').lower()
    if tipo != 'departamento':
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
            if vm2 and 400 <= vm2 <= 5000:  # Absolute outlier filter
                candidatos.append({**p, 'distancia_m': d})

# 2. IQR Filter (as done in obtener_mediana_cluster)
if candidatos:
    vals = sorted([c['valor_m2'] for c in candidatos])
    import numpy as np
    q1, q3 = np.percentile(vals, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    
    final_pool = [c for c in candidatos if lower <= c['valor_m2'] <= upper]
    # Sort by distance for the final list
    final_pool.sort(key=lambda x: x['distancia_m'])
else:
    final_pool = []

print(f"Propiedades que contribuyeron al cálculo de Mabel")
print(f"Total: {len(final_pool)} propiedades")
print("-" * 110)
print(f"{'#':<4} {'Dirección':<45} {'m2':<8} {'Precio':<12} {'USD/m2':<10} {'Dist':<8} {'Zona'}")
print("-" * 110)

for i, p in enumerate(final_pool, 1):
    dir_text = p.get('direccion', 'N/A')[:44]
    m2 = p.get('m2', 0)
    precio = p.get('precio', 0)
    vm2 = p.get('valor_m2', 0)
    dist = p.get('distancia_m', 0)
    zona = p.get('zona', 'N/A')
    print(f"{i:<4} {dir_text:<45} {m2:<8.1f} ${precio:>10,.0f} {vm2:>8.0f} {dist:>6.0f}m {zona}")

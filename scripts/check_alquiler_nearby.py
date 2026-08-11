import json
import os
import sys
sys.path.insert(0, '.')

from parsers.mercado_inmobiliario import obtener_mediana_cluster_v2
from datetime import date

# Load cache
cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache_scraping.json')
with open(cache_path, encoding='utf-8') as f:
    cache_scraping = json.load(f)

props = cache_scraping.get('propiedades', [])

# Check alquileres near Ayacucho coordinates
lat_ref = -32.9333
lon_ref = -60.6407

print("=== ALQUILERES CERCANOS A AYACUCHO (500m) ===")
from math import radians, cos, sin, asin, sqrt

def haversine(lon1, lat1, lon2, lat2):
    """Calculate distance in meters between two points."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371000  # Radius of earth in meters
    return c * r

nearby_alquileres = []
for prop in props:
    if isinstance(prop, dict) and prop.get('operacion') == 'alquiler':
        lat = prop.get('lat')
        lon = prop.get('lon')
        if lat and lon:
            dist = haversine(lon_ref, lat_ref, lon, lat)
            if dist <= 500:
                m2 = prop.get('valor_m2', 0)
                precio = prop.get('precio', 0)
                dorm = prop.get('dormitorios', 0)
                addr = prop.get('direccion', 'N/A')[:50]
                zona = prop.get('zona', 'N/A')
                fuente = prop.get('fuente', 'N/A')
                moneda = prop.get('moneda', 'N/A')
                nearby_alquileres.append({
                    'direccion': addr,
                    'dist': dist,
                    'm2': m2,
                    'precio': precio,
                    'dormitorios': dorm,
                    'zona': zona,
                    'fuente': fuente,
                    'moneda': moneda
                })

nearby_alquileres.sort(key=lambda x: x['dist'])
print(f"Total nearby alquileres: {len(nearby_alquileres)}")
for a in nearby_alquileres[:20]:
    print(f"  {a['dist']:>6.0f}m {a['direccion']:50} m2=${a['m2']:>10,.0f}  precio=${a['precio']:>12,.0f}  dorm={a['dormitorios']}  {a['moneda']}  zona={a['zona']}  fuente={a['fuente']}")

# Now run the cluster calculation
print()
print("=== CLUSTER CALCULATION ===")
m2_base_alq_raw, n_alq, meta_alq = obtener_mediana_cluster_v2(
    zona='Centro',
    dormitorios=3,
    operacion='alquiler',
    lat_ref=lat_ref,
    lon_ref=lon_ref,
    fecha_ref=date(2026, 7, 28),
    tipo_inmueble='departamento',
    cache_scraping=cache_scraping,
    flex_dormitorios=None
)
print(f"m2_base_alq_raw: {m2_base_alq_raw}")
print(f"n_alq: {n_alq}")
print(f"meta_alq: {meta_alq}")

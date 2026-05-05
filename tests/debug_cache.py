"""Debug distance calc"""
import sys
import os
sys.path.insert(0, 'C:/Users/Gustavo/ingresos_familiares_st')

from parsers.motor_vpp_core import load_cache
from parsers.mercado_inmobiliario import calcular_distancia_km

# Test distance directly
d = calcular_distancia_km(-32.9541, -60.6316, -60.660698, -32.93869)
print(f"Distance test: {d} km")

cache = load_cache()
props = cache.get('propiedades', [])
print(f"Total: {len(props)}")

# Check first 10 props with coords
mabel_lat, mabel_lon = -32.9541, -60.6316

count = 0
for p in props:
    lat = p.get('lat')
    lon = p.get('lon')
    if lat and lon:
        count += 1
        if count <= 5:
            d = calcular_distancia_km(mabel_lat, mabel_lon, lon, lat)
            print(f"{p.get('zona')}: ({lat},{lon}) -> dist={d:.3f}")

print(f"\nProps con coords: {count}")
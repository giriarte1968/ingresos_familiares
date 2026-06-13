import json
import sys
import os

# Add the root directory to sys.path to allow imports from parsers
sys.path.insert(0, r'C:\Users\Gustavo\ingresos_familiares_st')

try:
    from parsers.mercado_inmobiliario import obtener_mediana_cluster_v2
    from parsers.time_adjustment import get_natural_window_dias
except ImportError as e:
    print(f"Import Error: {e}")
    exit(1)

# Load cache
cache_path = r'C:\Users\Gustavo\ingresos_familiares_st\cache_scraping.json'
with open(cache_path, 'r', encoding='utf-8') as f:
    cache = json.load(f)

print(f"Ventana natural: {get_natural_window_dias()} días")

# Test with different retro values
# Use 'Puerto Norte' as it was the problematic zone
test_cases = [0, 12, 36]
for retro in test_cases:
    # We mock some required parameters for the function
    precio, n, meta = obtener_mediana_cluster_v2(
        zona='Puerto Norte',
        dormitorios=2,
        operacion='venta',
        lat_ref=-32.9304159, 
        lon_ref=-60.6620818,
        fecha_ref='2026-04-01',
        cache_scraping=cache,
        retro_dias=retro
    )
    print(f"retro_dias={retro}: precio=${precio:.0f}, n={n}, meta_n={meta.get('n_filtradas', 0)}")

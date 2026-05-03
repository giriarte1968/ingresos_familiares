
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from parsers.mercado_inmobiliario import obtener_mediana_geo_simple
    print("IMPORT_OK")
except Exception as e:
    print(f"IMPORT_ERROR: {e}")
    sys.exit(1)

# Mabel's Data
m_lat = -32.9541101
m_lon = -60.6316406
m_tipo = 'departamento'
m_op = 'venta'

print(f"Testing obtener_mediana_geo_simple for Mabel...")
try:
    val, n = obtener_mediana_geo_simple(m_lat, m_lon, m_tipo, m_op)
    print(f"RESULT -> Value: {val}, Samples: {n}")
    if val == 0:
        print("❌ FAIL: Returned 0")
    else:
        print("✅ SUCCESS: Found data")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"CRASH: {e}")

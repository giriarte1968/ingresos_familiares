
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from parsers.mercado_inmobiliario import obtener_mediana_cluster, obtener_mediana_geo_simple
    print("IMPORT_OK")
except Exception as e:
    print(f"IMPORT_ERROR: {e}")
    sys.exit(1)

# Mabel's Data
m_lat, m_lon = -32.9541101, -60.6316406
m_zona = "Martin"
m_dorms = 1
m_tipo = 'departamento'
m_op = 'venta'

print(f"Comparing Zonal vs Geo for Mabel...")

# 1. Zonal
val_zonal, n_zonal = obtener_mediana_cluster(m_zona, m_dorms, m_tipo, m_op)
print(f"ZONAL -> Value: {val_zonal}, Samples: {n_zonal}")

# 2. Geo (Recovery)
val_geo, n_geo = obtener_mediana_geo_simple(m_lat, m_lon, m_tipo, m_op)
print(f"GEO   -> Value: {val_geo}, Samples: {n_geo}")

diff = abs(val_zonal - val_geo)
print(f"Difference: {diff:.2f}")
if diff == 0:
    print("⚠️ Values are IDENTICAL. This explains why the price didn't change.")
else:
    print("✅ Values are DIFFERENT. The price should have changed.")

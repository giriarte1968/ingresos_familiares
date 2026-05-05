import sys
import os
sys.path.insert(0, 'C:/Users/Gustavo/ingresos_familiares_st')

from parsers.mercado_inmobiliario import obtener_mediana_cluster_v2

# Cluster alquiler Mabel
valor, n, meta = obtener_mediana_cluster_v2(
    zona='Martin',
    dormitorios=1,
    operacion='alquiler',
    lat_ref=-32.9541101,
    lon_ref=-60.6316406
)

print("=== CLUSTER ALQUILER MABEL ===")
print(f"m2_base_alquiler: {valor} ARS/m2")
print(f"Muestras: {n}")
print(f"radio: {meta.get('radio_usado')}")
print(f"percentil: {meta.get('percentil_usado')}")
print(f"zona: {meta.get('zona_resolucion')}")
import json
from parsers.mercado_inmobiliario import cargar_datos

datos = cargar_datos()
indice_data = datos.get('indice_ciudad', {}).get('data', {})
print("Indice data:", indice_data)

anio_actual = 2026
anio_tasacion = 2026

idx_actual = indice_data.get(str(anio_actual), 1.25)
idx_destino = indice_data.get(str(anio_tasacion), 1.25)
factor_temporal = idx_destino / idx_actual

print(f"idx_actual: {idx_actual}")
print(f"idx_destino: {idx_destino}")
print(f"factor_temporal: {factor_temporal}")
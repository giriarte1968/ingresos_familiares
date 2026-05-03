from parsers.mercado_inmobiliario import calcular_factores, calcular_m2_equivalentes, calcular_base_calibrada
import math

mabel = {
    'nombre': 'Mabel',
    'zona': 'Martin',
    'lat': -32.9541101,
    'lon': -60.6316406,
    'm2': 48.5,
    'm2_cubiertos': 41.0,
    'm2_semicubiertos': 7.5,
    'anio_construccion': 2000,
    'estado_detalle': 'muy bueno',
    'calidad_edificio': 'media',
    'descripcion_libre': 'luminoso, con aire acondicionado'
}
mabel['antiguedad'] = 2026 - 2000

me = calcular_m2_equivalentes(mabel)
# Window 1 for test
fd = calcular_factores(mabel, ventana_usada=1)
print(f'Suma Cruda: {fd["suma_cruda"]}')
print(f'Suma Cruda Details: {fd["detalles"]}')

m2_base = 1765.71
nlp = 0.05
valor = me * m2_base * math.sqrt((1 + fd['suma_cruda']) * (1 + nlp))
print(f'Calculated: {valor:.0f}')

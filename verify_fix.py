import sys
sys.path.insert(0, 'C:/Users/Gustavo/ingresos_familiares_st')

from parsers.mercado_inmobiliario import calcular_factores

# Test property matching Mabel's characteristics
prop = {
    'estado_detalle': 'muy bueno',
    'calidad_edificio': 'media',
    'piso': 2,
    'total_pisos': 6,
    'antiguedad': 24,
    'tipo_inmueble': 'departamento',
    'ventilacion': 'cruzada',
    'detalles_categoria': ['seguridad_camaras', 'seguridad_tag'],
    'propiedad_exterior': 'propio',
    'glaseado_completo': True,
    'doble_ingreso': False,
    'lavadero_independiente': True,
    'reciclado_tipo': 'ninguno',
    'placares_completos': True,
    'despensa': False,
    'ascensores_edificio': 1,
}

f = calcular_factores(prop, ajuste_nlp=0.15)
print(f'total: {f["total"]:.4f}')
print(f'sqrt_factor: {f["sqrt_factor"]:.4f}')
print(f'depreciacion: {f["depreciacion"]:.4f}')
print(f'factor_pasillo: {f["factor_pasillo"]:.4f}')

# Now test full valuation
from parsers.mercado_inmobiliario import valuar_propiedad_v7
import json

with open('C:/Users/Gustavo/ingresos_familiares_st/propiedades.json', encoding='utf-8') as fp:
    data = json.load(fp)
    props = data['propiedades']
    mabel = [p for p in props if p['nombre'] == 'Mabel'][0]
    result = valuar_propiedad_v7(mabel)

print(f'\nValor Mabel: {result["valor_propiedad_usd"]}')
print(f'Nodos: {len(result["resolution_metadata"]["nodes"])}')
print(f'n_propiedades: {result["resolution_metadata"].get("n_propiedades", "NOT FOUND")}')
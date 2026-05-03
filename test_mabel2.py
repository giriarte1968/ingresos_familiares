import json
import math
from parsers.mercado_inmobiliario import (
    calcular_base_calibrada, calcular_m2_equivalentes, calcular_factores,
    obtener_mediana_cluster, sanitizar_propiedad
)
from parsers.nlp_inmobiliario import calcular_ajuste_nlp_detallado

data = json.load(open('propiedades.json'))
mabel = [p for p in data['propiedades'] if p.get('nombre') == 'Mabel'][0]

print(f"Ancla: {mabel.get('ancla_mas_cercana')}")
print(f"ancla_usd_m2: {mabel.get('ancla_usd_m2')}")
print(f"lat: {mabel.get('lat')}")
print(f"lon: {mabel.get('lon')}")

prop = sanitizar_propiedad(mabel)
anio_const = prop.get('anio_construccion', 2020)
prop['antiguedad'] = 2026 - anio_const

m2_equiv = calcular_m2_equivalentes(prop)
f_dict = calcular_factores(prop)

dorms = prop.get('dormitorios', 2)
zona = prop.get('zona')

ancla_input = mabel.get('ancla_usd_m2', 1500)
print(f"\nInput ancla: {ancla_input}")

m2_base, metodo = calcular_base_calibrada(ancla_input, {
    'zona': zona, 'dormitorios': dorms, 'lat': mabel.get('lat'), 
    'lon': mabel.get('lon'), 'anio_construccion': anio_const
})

cluster, n = obtener_mediana_cluster(zona, dorms, 'venta')

print(f"\nm2_base: {m2_base}")
print(f"cluster: {cluster}")
print(f"metodo: {metodo}")

ajuste_nlp, _ = calcular_ajuste_nlp_detallado(prop.get('descripcion_libre', ''))

m2_base_nlp = m2_base * math.sqrt(1 + ajuste_nlp)

valor_lista = m2_equiv * m2_base_nlp * f_dict['total']

print(f"\nCalculo:")
print(f"m2_equiv: {m2_equiv}")
print(f"m2_base: {m2_base}")
print(f"sqrt(NLP): {math.sqrt(1+ajuste_nlp)}")
print(f"m2_base_nlp: {m2_base_nlp}")
print(f"factor_total: {f_dict['total']}")
print(f"resultado: {valor_lista}")
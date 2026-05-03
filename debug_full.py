import json
import math
from parsers.mercado_inmobiliario import (
    calcular_base_calibrada, calcular_m2_equivalentes, calcular_factores,
    obtener_mediana_cluster, sanitizar_propiedad
)
from parsers.nlp_inmobiliario import calcular_ajuste_nlp_detallado

data = json.load(open('propiedades.json'))
mabel = [p for p in data['propiedades'] if p.get('nombre') == 'Mabel'][0]

anio_const = mabel.get('anio_construccion', 2000)
antiguedad = 2026 - anio_const

# m2 equiv
m2_equiv = calcular_m2_equivalentes(mabel)

# Factores sin setear antiguedad
mabel_san = sanitizar_propiedad(mabel)
mabel_san['antiguedad'] = antiguedad

f_dict = calcular_factores(mabel_san)

# Base calibrada
ancla_input = mabel.get('ancla_usd_m2', 1500)
zona = mabel.get('zona')
dorms = mabel.get('dormitorios', 2)

m2_base, metodo = calcular_base_calibrada(ancla_input, {
    'zona': zona, 'dormitorios': dorms, 
    'lat': mabel.get('lat'), 
    'lon': mabel.get('lon'), 
    'anio_construccion': anio_const
})

cluster, n = obtener_mediana_cluster(zona, dorms, 'venta')

print(f"DATOS:")
print(f"  ancla_input: {ancla_input}")
print(f"  zona: {zona}")
print(f"  dorms: {dorms}")
print(f"  anio_const: {anio_const}")
print(f"  antiguedad: {antiguedad}")
print(f"\nBASE:")
print(f"  m2_base: {m2_base}")
print(f"  cluster: {cluster}")
print(f"  n_cluster: {n}")
print(f"  metodo: {metodo}")

# NLP
ajuste_nlp, _ = calcular_ajuste_nlp_detallado(mabel.get('descripcion_libre', ''))
m2_base_nlp = m2_base * math.sqrt(1 + ajuste_nlp)

print(f"\nNLP:")
print(f"  ajuste: {ajuste_nlp}")
print(f"  sqrt: {math.sqrt(1+ajuste_nlp)}")
print(f"  m2_base_nlp: {m2_base_nlp}")

# Factor
print(f"\nFACTOR:")
print(f"  f_dict[total]: {f_dict['total']}")
print(f"  f_dict[estructural_puro]: {f_dict['estructural_puro']}")
print(f"  f_dict[sqrt_factor]: {f_dict['sqrt_factor']}")
print(f"  f_dict[depreciacion]: {f_dict['depreciacion']}")

# Resultado
valor = m2_equiv * m2_base_nlp * f_dict['total']
print(f"\nRESULTADO:")
print(f"  {m2_equiv} * {m2_base_nlp} * {f_dict['total']} = {valor}")
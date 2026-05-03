from parsers.mercado_inmobiliario import calcular_m2_equivalentes, calcular_factores
from parsers.nlp_inmobiliario import calcular_ajuste_nlp_detallado
import json
props = json.load(open('propiedades.json', encoding='utf-8'))['propiedades']
mabel = [p for p in props if p['nombre']=='Mabel'][0]

mabel['antiguedad'] = 2026 - mabel['anio_construccion']
me = calcular_m2_equivalentes(mabel)
aj_nlp, _ = calcular_ajuste_nlp_detallado(mabel.get('descripcion_libre', ''))
fd = calcular_factores(mabel, aj_nlp)

print(f'm2_equiv: {me}')
print(f'aj_nlp: {aj_nlp}')
print(f'fd[total]: {fd["total"]}')
print(f'sqrt(1+nlp): {(1 + aj_nlp)**0.5}')

m2_base = 1765.7142857142858
import math
valor_old = me * m2_base * fd['total']
valor_new = me * m2_base * math.sqrt(1 + aj_nlp) * fd['total']
print(f'Old formula: {me} * {m2_base} * {fd["total"]} = {valor_old:.0f}')
print(f'New formula: {me} * {m2_base} * sqrt(1+{aj_nlp}) * {fd["total"]} = {valor_new:.0f}')
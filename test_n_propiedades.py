import sys
sys.path.insert(0, 'C:/Users/Gustavo/ingresos_familiares_st')
from parsers.mercado_inmobiliario import valuar_propiedad_v7
import json

props = json.load(open('C:/Users/Gustavo/ingresos_familiares_st/propiedades.json', encoding='utf-8'))['propiedades']
mabel = [p for p in props if p['nombre']=='Mabel'][0]
res = valuar_propiedad_v7(mabel)

print('Valor:', res['valor_propiedad_usd'])
print('Resolución:', res['resolution_metadata']['resolution'])
print('Metadata keys:', list(res['resolution_metadata'].keys()))
print('n_propiedades:', res['resolution_metadata'].get('n_propiedades', 'NOT FOUND'))
print('Nodes count:', len(res['resolution_metadata'].get('nodes', [])))
if res['resolution_metadata'].get('nodes'):
    print('First node qualified:', res['resolution_metadata']['nodes'][0].get('qualified', 'NOT FOUND'))
    print('First node muestras:', res['resolution_metadata']['nodes'][0].get('muestras', 'NOT FOUND'))

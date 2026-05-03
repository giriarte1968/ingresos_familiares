from parsers.mercado_inmobiliario import valuar_propiedad_v7
import json

props = json.load(open('propiedades.json', encoding='utf-8'))['propiedades']
mabel = [p for p in props if p['nombre']=='Mabel'][0]

res = valuar_propiedad_v7(mabel)

print('Valor:', res['valor_propiedad_usd'])
print('Resolucion:', res['resolution_metadata']['resolution'])
print('n_propiedades:', res['resolution_metadata'].get('n_propiedades'))
print('n_props_raw:', res['resolution_metadata'].get('n_props_raw', '?'))
print('n_props_filtradas:', res['resolution_metadata'].get('n_props_filtradas', '?'))
print('valor_realizable:', res['valor_realizable_usd'])
print('descuento:', ((res['valor_propiedad_usd'] - res['valor_realizable_usd']) / res['valor_propiedad_usd']) * 100)

print('\nNodos influyentes:')
for i, n in enumerate(res['resolution_metadata'].get('nodes', [])[:10]):
    print(f'  {i+1}. dist: {n.get("dist_m", 0):.0f}m | USD/m2: {n.get("value", 0):.0f} | weight: {n.get("weight", 0):.1f}%')
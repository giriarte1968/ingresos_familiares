from parsers.mercado_inmobiliario import valuar_propiedad_v7
import json

props = json.load(open('propiedades.json', encoding='utf-8'))['propiedades']
mabel = [p for p in props if p['nombre']=='Mabel'][0]
res = valuar_propiedad_v7(mabel)

print(f'Valor Lista: {res["valor_propiedad_usd"]}')
print(f'Alquiler Estimado: {res["alquiler_estimado_ars"]}')
print(f'Cap Rate: {res["cap_rate_anual"]}%')

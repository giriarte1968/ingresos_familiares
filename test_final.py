from parsers.mercado_inmobiliario import valuar_propiedad_v7
import json

props = json.load(open('propiedades.json', encoding='utf-8'))['propiedades']
mabel = [p for p in props if p['nombre']=='Mabel'][0]

res = valuar_propiedad_v7(mabel)

print(f'Sincero Rental: {res["alquiler_estimado_ars"]}')
print(f'Sincero Value: {res["valor_propiedad_usd"]}')
print(f'Sincero ROI: {res["cap_rate_anual"]}%')

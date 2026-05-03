import json
from parsers.mercado_inmobiliario import valuar_propiedad_v7

data = json.load(open('propiedades.json'))
mabel = [p for p in data['propiedades'] if p.get('nombre') == 'Mabel'][0]

print(f"Input:")
print(f"  lat: {mabel.get('lat')}")
print(f"  lon: {mabel.get('lon')}")
print(f"  ancla: {mabel.get('ancla_mas_cercana')}")
print(f"  ancla_usd: {mabel.get('ancla_usd_m2')}")

result = valuar_propiedad_v7(mabel)

print(f"\nResultado:")
print(f"  valor_lista: {result['valor_propiedad_usd']}")
print(f"  m2_base_venta: {result['m2_base_venta']}")
import json
import math
from parsers.mercado_inmobiliario import valuar_propiedad_v7
from parsers.geocoder import geocode_property

# Cargar propiedad Mabel
data = json.load(open('propiedades.json'))
mabel = [p for p in data['propiedades'] if p.get('nombre') == 'Mabel'][0]

# Geocodificar para asegurar coordenadas
mabel = geocode_property(mabel)

print(f"Despues de geocode:")
print(f"  ancla: {mabel.get('ancla_mas_cercana')}")
print(f"  ancla_usd: {mabel.get('ancla_usd_m2')}")

result = valuar_propiedad_v7(mabel)

print(f"\nResultado:")
print(f"  valor_lista: {result['valor_propiedad_usd']}")
print(f"  valor_cierre: {result['valor_realizable_usd']}")
print(f"  m2_base_venta: {result['m2_base_venta']}")
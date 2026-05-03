import json
from parsers.mercado_inmobiliario import valuar_propiedad_v7

# Cargar propiedad P1200
data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
p1200 = [p for p in data['propiedades'] if p.get('id') == 'prop_b8ec28ba'][0]

# Ejecutar valuación
result = valuar_propiedad_v7(p1200)

print("=== Resultado FINAL ===")
print(f"valor_propiedad_usd: {result['valor_propiedad_usd']}")
print(f"valor_realizable_usd: {result['valor_realizable_usd']}")
print(f"m2_equivalentes: {result['m2_equivalentes']}")
print(f"m2_base_venta: {result['m2_base_venta']}")
print(f"m2_efectivo: {result['valor_m2_actual_usd']}")

# Comparar con esperado
print("\n=== Comparación ===")
print(f"ESPERADO: valor_lista=$120,400, valor_cierre=$110,768, m2_efectivo=$1,355")
print(f"CALCULADO: valor_lista=${result['valor_propiedad_usd']}, valor_cierre=${result['valor_realizable_usd']}, m2_efectivo=${result['valor_m2_actual_usd']}")
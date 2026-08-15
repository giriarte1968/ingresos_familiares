"""Debug: por qué Entre Ríos cambió de USD 79,630 a USD 64,976"""
from parsers.mercado_inmobiliario import valuar_propiedad_v7
import json

with open('propiedades.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

er = next(p for p in data['propiedades'] if 'Entre' in p.get('nombre',''))

res = valuar_propiedad_v7(er, retro_dias=60, flex_dormitorios=None)

rm = res.get('resolution_metadata', {})
print("=" * 60)
print("VALUACION ACTUAL DE ENTRE RIOS 1372")
print("=" * 60)
print(f"valor_propiedad_usd: {res['valor_propiedad_usd']}")
print(f"m2_base_venta: {res.get('m2_base_venta')}")
print(f"m2_microzona: {res.get('m2_microzona')}")
print(f"n_comps: {rm.get('n_propiedades')}")
print(f"n_comps_final: {rm.get('n_comps_final')}")
print(f"radio: {rm.get('radio_usado')}")
print(f"p25_cluster: {rm.get('p25_cluster')}")
print(f"p50_cluster: {rm.get('p50_cluster')}")
print(f"p75_cluster: {rm.get('p75_cluster')}")
print(f"m2_equiv: {res.get('m2_equivalentes')}")
print(f"valor_activos: {res.get('valor_activos_total')}")
print(f"size_discount: {res.get('size_discount')}")

m2_prop = float(er.get('superficie_m2', 0) or er.get('m2', 0) or 71.14)
print(f"\nm2 propiedad: {m2_prop}")
val = res['valor_propiedad_usd']
print(f"valor/m2 implicito: {val / m2_prop:.2f}")

print("\n" + "=" * 60)
print("COMPARACION CON PDF TTL ORIGINAL")
print("=" * 60)
print(f"PDF TTL (13/08/2026): USD 79,630 | m2_base=1,119 | 16 comps")
print(f"Motor Actual:         USD {val:,.0f} | m2_base={res.get('m2_base_venta'):.2f} | {rm.get('n_propiedades')} comps")
print(f"\nDiferencia USD: {val - 79630:+,.0f}")
print(f"Diferencia m2_base: {res.get('m2_base_venta', 0) - 1119:+,.2f}")

# Mostrar dormitorios de la propiedad
print(f"\nDormitorios prop: {er.get('dormitorios')}")
print(f"Retro: 60 dias")
print(f"Flex: None")

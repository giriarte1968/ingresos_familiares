import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
vera = None
for p in props:
    if 'vera' in p.get('nombre', '').lower():
        vera = p
        break

if vera:
    res = valuar_propiedad_v7(vera)
    print("==================================================")
    print("VALUACIÓN DE VERA MUJICA CON FACTOR DISPOSICION:")
    print("==================================================")
    print("  valor_propiedad_usd:", res.get('valor_propiedad_usd'))
    print("  m2_base_venta:", res.get('m2_base_venta'))
    print("  m2_equivalentes:", res.get('m2_equivalentes'))
    print("  valor_venta_conservador:", res.get('valor_venta_conservador'))
    print("  valor_venta_optimista:", res.get('valor_venta_optimista'))

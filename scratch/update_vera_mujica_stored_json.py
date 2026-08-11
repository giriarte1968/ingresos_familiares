import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props_path = 'propiedades.json'
data = json.load(open(props_path, 'r', encoding='utf-8'))
props = data.get('propiedades', [])

for p in props:
    if 'vera' in p.get('nombre', '').lower():
        res = valuar_propiedad_v7(p)
        print("Valuación recalculada para Vera Mujica:", res.get('valor_propiedad_usd'))
        p['_ultima_valuacion'] = {
            'valor_usd': res.get('valor_propiedad_usd'),
            'auto_valor_usd': res.get('valor_propiedad_usd'),
            'manual_valor_usd': 0,
            'alquiler_ars': res.get('alquiler_estimado_ars'),
            'cap_rate': res.get('cap_rate'),
            'm2_equivalentes': res.get('m2_equivalentes'),
            'comps': len(res.get('comparables_venta', [])),
            'm2_base_venta': res.get('m2_base_venta'),
            'm2_microzona': res.get('m2_microzona'),
            'size_discount': res.get('size_discount', 1.0),
            'valor_activos_total': res.get('valor_activos_total', 0),
            'usdt_ars': res.get('usdt_ars', 1585),
            'fecha': '11/08/2026 17:35',
            'cache_version': 'v8f_pb_interno_fix',
            'fuente': 'auto',
            'fuente_activa': 'auto',
            '_comp_exclusion_applied': False
        }
        break

with open(props_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("propiedades.json actualizado con éxito")

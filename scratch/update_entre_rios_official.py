import sys, os
sys.path.insert(0, os.path.abspath('.'))
import json
from parsers.motor_vpp_core import valuar_con_cache
from parsers.mercado_inmobiliario import generar_razonamiento_valuacion

with open('propiedades.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

props = data['propiedades'] if isinstance(data, dict) and 'propiedades' in data else data

for i, p in enumerate(props):
    if p.get('nombre') == 'Entre Rios 1372':
        res = valuar_con_cache(p, forzar_recalculo=True, retro_dias=0, flex_dormitorios=1)
        razon = generar_razonamiento_valuacion(p, res, res.get('resolution_metadata', {}))
        res['razonamiento'] = razon
        
        uv = {
            'valor_usd': res['valor_propiedad_usd'],
            'auto_valor_usd': res['valor_propiedad_usd'],
            'manual_valor_usd': 0,
            'alquiler_ars': res.get('alquiler_estimado_ars', 0),
            'cap_rate': res.get('cap_rate', 0),
            'm2_equivalentes': res.get('m2_equivalentes', 0),
            'comps': len(res.get('comparables_venta', [])),
            'm2_base_venta': res.get('m2_base_venta', 0),
            'm2_microzona': res.get('m2_microzona', 0),
            'size_discount': res.get('factor_tamano', 1.0),
            'valor_activos_total': 0.0,
            'usdt_ars': res.get('usdt_ars', 1590),
            'fecha': '13/08/2026 21:42',
            'cache_version': 'v8b_import_fix_alquiler',
            'timestamp': '2026-08-13T21:42:00.000000',
            'fuente': 'auto',
            'fuente_activa': 'auto',
            'manual_params': None,
            'retro_dias': 0,
            'flex_dormitorios': 1,
            '_comp_excluded': [],
            '_comp_exclusion_applied': True
        }
        props[i]['_ultima_valuacion'] = uv
        print(f"Recalculado {p['nombre']}: valor=${uv['valor_usd']:,.0f}, comps={uv['comps']}, m2_base={uv['m2_base_venta']:.2f}")
        print("\n--- RAZONAMIENTO NARRATIVO GENERADO ---")
        print(razon)
        break

with open('propiedades.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

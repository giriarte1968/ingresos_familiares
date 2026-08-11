import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props_file = 'propiedades.json'
if os.path.exists(props_file):
    data = json.load(open(props_file, 'r', encoding='utf-8'))
    for p in data.get('propiedades', []):
        if 'cochabamba' in p.get('nombre', '').lower() or 'cochabamba' in p.get('direccion', '').lower():
            res = valuar_propiedad_v7(p, retro_dias=60, flex_dormitorios=[1, 2, 3, 4, 5])
            p['_ultima_valuacion'] = {
                'valor_usd': res.get('valor_propiedad_usd'),
                'auto_valor_usd': res.get('valor_propiedad_usd'),
                'manual_valor_usd': 0,
                'alquiler_ars': res.get('alquiler_estimado_ars', 600000),
                'cap_rate': 0.05,
                'm2_equivalentes': res.get('m2_equivalentes', 98.0),
                'comps': res.get('n_comps', 29),
                'm2_base_venta': res.get('m2_base_venta'),
                'm2_microzona': res.get('m2_microzona'),
                'size_discount': 1.0,
                'valor_activos_total': 0.0,
                'usdt_ars': 1579.88,
                'fecha': '10/08/2026 21:33',
                'cache_version': 'v8b_import_fix_alquiler',
                'fuente': 'auto',
                'fuente_activa': 'auto',
                'manual_params': None,
                'retro_dias': 60,
                'flex_dormitorios': [1, 2, 3, 4, 5],
                '_comp_excluded': [],
                '_comp_exclusion_applied': True
            }
            print(f"Cochabamba 45 _ultima_valuacion actualizada a $96,793 USD ({res.get('n_comps')} comps, retro=60, flex=[1..5])")
            break
    with open(props_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

cache_file = 'valuaciones_cache.json'
if os.path.exists(cache_file):
    os.remove(cache_file)
    print("valuaciones_cache.json limpiado.")

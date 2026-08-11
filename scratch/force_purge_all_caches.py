import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7
from parsers.valuacion_cache import guardar_cache_valuaciones

# 1. Recalculate official result for Cochabamba 45 with retro_dias=60, flex_dormitorios=[1,2,3,4,5]
props_path = 'propiedades.json'
data = json.load(open(props_path, 'r', encoding='utf-8'))

for p in data.get('propiedades', []):
    if 'cochabamba' in p.get('nombre', '').lower():
        res = valuar_propiedad_v7(p, retro_dias=60, flex_dormitorios=[1, 2, 3, 4, 5])
        val_usd = res.get('valor_propiedad_usd')
        m2_m = res.get('m2_microzona')
        comps = res.get('n_comps', 29)
        print(f"Recalculado Cochabamba 45: valor=${val_usd:,.0f} USD, m2=${m2_m:.2f}/m2, comps={comps}")
        
        p['_ultima_valuacion'] = {
            'valor_usd': val_usd,
            'auto_valor_usd': val_usd,
            'manual_valor_usd': 0,
            'alquiler_ars': res.get('alquiler_estimado_ars', 600000),
            'cap_rate': 0.05,
            'm2_equivalentes': 98.0,
            'comps': comps,
            'm2_base_venta': m2_m,
            'm2_microzona': m2_m,
            'size_discount': 1.0,
            'valor_activos_total': 0.0,
            'usdt_ars': 1579.88,
            'fecha': '10/08/2026 21:35',
            'cache_version': 'v8b_import_fix_alquiler',
            'fuente': 'auto',
            'fuente_activa': 'auto',
            'manual_params': None,
            'retro_dias': 60,
            'flex_dormitorios': [1, 2, 3, 4, 5],
            '_comp_excluded': [],
            '_comp_exclusion_applied': True
        }
        break

with open(props_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print("propiedades.json actualizado.")

# 2. Wipe valuaciones_cache.json entirely
cache_path = 'valuaciones_cache.json'
if os.path.exists(cache_path):
    os.remove(cache_path)
    print("valuaciones_cache.json eliminado.")

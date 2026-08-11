import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.motor_vpp_core import valuar_con_cache
from parsers.valuacion_cache import cargar_cache_valuaciones

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
cochabamba = None
for p in props_data.get('propiedades', []):
    if 'cochabamba' in p.get('nombre', '').lower() or 'cochabamba' in p.get('direccion', '').lower():
        cochabamba = p
        break

print("=" * 80)
print("1. PROPIEDADES.JSON (_ultima_valuacion para Cochabamba 45):")
print("=" * 80)
if cochabamba:
    uv = cochabamba.get('_ultima_valuacion', {})
    for k, v in uv.items():
        print(f"  {k}: {v}")

print("=" * 80)
print("2. VALUACIONES_CACHE.JSON (Cache en disco):")
print("=" * 80)
cache_v = cargar_cache_valuaciones()
print("  Entrada Cochabamba 45 en cache_v:", cache_v.get('Cochabamba 45', {}).keys() if 'Cochabamba 45' in cache_v else 'NO EXISTE')
if 'Cochabamba 45' in cache_v:
    res_c = cache_v['Cochabamba 45'].get('resultado_completo', {})
    print("  valor_propiedad_usd en cache_v:", res_c.get('valor_propiedad_usd'))
    print("  m2_microzona en cache_v:", res_c.get('m2_microzona'))
    print("  n_comps en cache_v:", res_c.get('n_comps'))

print("=" * 80)
print("3. LLAMADA DIRECTA A valuar_con_cache(cochabamba, forzar_recalculo=True):")
print("=" * 80)
if cochabamba:
    res_direct = valuar_con_cache(cochabamba, forzar_recalculo=True, retro_dias=cochabamba.get('_ultima_valuacion',{}).get('retro_dias', 60), flex_dormitorios=cochabamba.get('_ultima_valuacion',{}).get('flex_dormitorios'))
    print("  valor_propiedad_usd:", res_direct.get('valor_propiedad_usd'))
    print("  m2_microzona:", res_direct.get('m2_microzona'))
    print("  n_comps:", res_direct.get('n_comps'))

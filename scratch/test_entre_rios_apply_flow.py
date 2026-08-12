import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7
from parsers.valuacion_cache import cargar_cache_valuaciones, persistir_valuacion

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
er = None
for p in props:
    if '1372' in p.get('nombre', '') or '1372' in p.get('direccion', ''):
        er = p
        break

if er:
    # 1. Simular "Limpiar"
    print("1. SIMULANDO LIMPIAR:")
    er.pop('_ultima_valuacion', None)
    
    # 2. Simular "Comparables" (preview natural)
    print("\n2. SIMULANDO PREVIEW NATURAL (Comparables):")
    res_preview = valuar_propiedad_v7(er)
    print("  preview valor_usd:", res_preview.get('valor_propiedad_usd'))
    print("  preview m2_base_venta:", res_preview.get('m2_base_venta'))
    print("  preview m2_cubiertos:", er.get('m2_cubiertos'))
    
    # 3. Simular "Aplicar selección"
    print("\n3. SIMULANDO APLICAR SELECCIÓN:")
    res_apply = dict(res_preview)
    res_apply['_comp_exclusion_applied'] = True
    res_apply['_comp_excluded'] = []
    
    cache_v = cargar_cache_valuaciones()
    persistir_valuacion(er.get('nombre'), er, res_apply, cache_v, commit=True)
    
    # Re-cargar propiedades.json para verificar lo grabado en disco
    data_disk = json.load(open('propiedades.json', 'r', encoding='utf-8'))
    for p_disk in data_disk.get('propiedades', []):
        if p_disk.get('nombre') == er.get('nombre'):
            uv_disk = p_disk.get('_ultima_valuacion', {})
            print("  DISK valor_usd:", uv_disk.get('valor_usd'))
            print("  DISK m2_base_venta:", uv_disk.get('m2_base_venta'))
            print("  DISK _comp_exclusion_applied:", uv_disk.get('_comp_exclusion_applied'))
            break

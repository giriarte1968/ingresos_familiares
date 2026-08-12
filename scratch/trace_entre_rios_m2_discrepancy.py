import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
er = None
for p in props:
    if '1372' in p.get('nombre', '') or '1372' in p.get('direccion', ''):
        er = p
        break

if er:
    print("==========================================")
    print("ANALIZANDO ENTRE RIOS 1372:")
    print("==========================================")
    print("  nombre:", er.get('nombre'))
    print("  m2_cubiertos:", er.get('m2_cubiertos'))
    print("  m2_semicubiertos:", er.get('m2_semicubiertos'))
    print("  m2_descubiertos:", er.get('m2_descubiertos'))
    print("  stored _ultima_valuacion:", json.dumps(er.get('_ultima_valuacion', {}), indent=2))
    
    # 1. Run engine with retro=0 / flex=None
    res_default = valuar_propiedad_v7(er)
    print("\n--- RES CON RETRO=0 FLEX=NONE ---")
    print("  valor_propiedad_usd:", res_default.get('valor_propiedad_usd'))
    print("  m2_base_venta:", res_default.get('m2_base_venta'))
    print("  m2_microzona:", res_default.get('m2_microzona'))
    print("  m2_equivalentes:", res_default.get('m2_equivalentes'))
    print("  valor_m2_actual_usd:", res_default.get('valor_m2_actual_usd'))
    print("  m2_cubiertos:", er.get('m2_cubiertos'))
    if er.get('m2_cubiertos'):
        print("  valor / m2_cubiertos:", round(res_default.get('valor_propiedad_usd', 0) / er.get('m2_cubiertos'), 2))

    # 2. Run engine with retro=60 / flex=[1,2,3,4,5]
    res_retro = valuar_propiedad_v7(er, retro_dias=60, flex_dormitorios=[1,2,3,4,5])
    print("\n--- RES CON RETRO=60 FLEX=[1..5] ---")
    print("  valor_propiedad_usd:", res_retro.get('valor_propiedad_usd'))
    print("  m2_base_venta:", res_retro.get('m2_base_venta'))
    print("  m2_microzona:", res_retro.get('m2_microzona'))
    print("  m2_equivalentes:", res_retro.get('m2_equivalentes'))
    print("  valor_m2_actual_usd:", res_retro.get('valor_m2_actual_usd'))
    if er.get('m2_cubiertos'):
        print("  valor / m2_cubiertos:", round(res_retro.get('valor_propiedad_usd', 0) / er.get('m2_cubiertos'), 2))

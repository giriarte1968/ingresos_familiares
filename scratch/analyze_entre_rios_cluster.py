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
    print("ANALIZANDO CLUSTER DE ENTRE RIOS 1372:")
    print("==========================================")
    print("  nombre:", er.get('nombre'))
    print("  dormitorios:", er.get('dormitorios'))
    print("  piso:", er.get('piso'))
    print("  ascensores_edificio:", er.get('ascensores_edificio'))
    
    # 1. flex_dormitorios = None (dorms exactos = 2 dorms)
    res_exact = valuar_propiedad_v7(er, flex_dormitorios=None)
    print("\n1. FLEX=NONE (Exacto 2 dorms):")
    print("   m2_base_venta:", res_exact.get('m2_base_venta'))
    print("   valor_usd:", res_exact.get('valor_propiedad_usd'))
    print("   n_comps:", len(res_exact.get('comparables_venta', [])))
    
    # 2. flex_dormitorios = 1 (Natural selection D+-1: dorms 1, 2, 3)
    res_nat = valuar_propiedad_v7(er, flex_dormitorios=1)
    print("\n2. FLEX=1 (Natural D+-1: 1, 2, 3 dorms):")
    print("   m2_base_venta:", res_nat.get('m2_base_venta'))
    print("   valor_usd:", res_nat.get('valor_propiedad_usd'))
    print("   n_comps:", len(res_nat.get('comparables_venta', [])))

    # 3. flex_dormitorios = [1, 2, 3, 4, 5] (Todos los dormitorios)
    res_all = valuar_propiedad_v7(er, flex_dormitorios=[1, 2, 3, 4, 5])
    print("\n3. FLEX=[1..5] (Todos los dormitorios):")
    print("   m2_base_venta:", res_all.get('m2_base_venta'))
    print("   valor_usd:", res_all.get('valor_propiedad_usd'))
    print("   n_comps:", len(res_all.get('comparables_venta', [])))

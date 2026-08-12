import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
mitre = None
for p in props:
    if 'mitre' in p.get('nombre', '').lower() or 'mitre' in p.get('direccion', '').lower():
        mitre = p
        break

if mitre:
    print("==========================================")
    print("DATOS DE MITRE 1473 EN PROPIEDADES.JSON:")
    print("==========================================")
    print("  nombre:", mitre.get('nombre'))
    print("  piso:", mitre.get('piso'))
    print("  disposicion:", mitre.get('disposicion'))
    print("  vista:", mitre.get('vista'))
    print("  m2_cubiertos:", mitre.get('m2_cubiertos'))
    print("  m2_equivalentes:", mitre.get('m2_equivalentes'))
    print("  stored _ultima_valuacion:", mitre.get('_ultima_valuacion'))
    
    res = valuar_propiedad_v7(mitre)
    print("\nRESULTADO RECALCULADO MOTOR EN VIVO:")
    print("  valor_propiedad_usd:", res.get('valor_propiedad_usd'))
    print("  m2_base_venta:", res.get('m2_base_venta'))
    print("  m2_microzona:", res.get('m2_microzona'))
    print("  m2_equivalentes:", res.get('m2_equivalentes'))
    print("  valor_venta_conservador:", res.get('valor_venta_conservador'))
    print("  valor_venta_optimista:", res.get('valor_venta_optimista'))
    print("  n_comps:", res.get('resolution_metadata',{}).get('n_propiedades'))

import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
for p in props:
    name = p.get('nombre', '')
    if 'entre' in name.lower() or '1372' in name or '1347' in name:
        res = valuar_propiedad_v7(p)
        print("==========================================")
        print("PROPIEDAD:", name)
        print("  direccion:", p.get('direccion'))
        print("  piso:", p.get('piso'))
        print("  ascensores_edificio:", p.get('ascensores_edificio'))
        print("  m2_cubiertos:", p.get('m2_cubiertos'))
        print("  m2_equivalentes:", res.get('m2_equivalentes'))
        print("  valor_propiedad_usd:", res.get('valor_propiedad_usd'))
        print("  m2_base_venta:", res.get('m2_base_venta'))
        print("  rango_venta:", res.get('rango_venta'))

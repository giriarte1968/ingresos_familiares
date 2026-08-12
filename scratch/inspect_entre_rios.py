import json, sys, os

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
er = None
for p in props:
    if 'entre rios' in p.get('nombre', '').lower() or 'entre rios' in p.get('direccion', '').lower() or '1372' in p.get('nombre', '').lower() or '1372' in p.get('direccion', '').lower():
        er = p
        break

if er:
    print("==========================================")
    print("ENTRE RIOS 1372 PROPIEDAD:")
    print("==========================================")
    print("  nombre:", er.get('nombre'))
    print("  piso:", er.get('piso'))
    print("  ascensores:", er.get('ascensores'))
    print("  disposicion:", er.get('disposicion'))
    print("  vista:", er.get('vista'))
    print("  m2_cubiertos:", er.get('m2_cubiertos'))
    print("  m2_equivalentes:", er.get('m2_equivalentes'))
    print("  _ultima_valuacion:", json.dumps(er.get('_ultima_valuacion', {}), indent=2))
else:
    print("Entre Rios 1372 no encontrada en propiedades.json")

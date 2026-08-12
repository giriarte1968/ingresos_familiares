import json, sys, os

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
print("Propiedades encontradas con 'entre' o 'rios' o '1347':")
for p in props:
    name = p.get('nombre', '')
    dir_txt = p.get('direccion', '')
    if 'entre' in name.lower() or 'entre' in dir_txt.lower() or '1347' in name or '1347' in dir_txt:
        print("--------------------------------------------------")
        print("  nombre:", name)
        print("  direccion:", dir_txt)
        print("  piso:", p.get('piso'))
        print("  ascensores:", p.get('ascensores'))
        print("  ascensores_edificio:", p.get('ascensores_edificio'))
        print("  m2_cubiertos:", p.get('m2_cubiertos'))
        print("  _ultima_valuacion:", json.dumps(p.get('_ultima_valuacion', {}), indent=2))

import json, sys, os

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
mitre = None
for p in props:
    if 'mitre' in p.get('nombre', '').lower() or 'mitre' in p.get('direccion', '').lower():
        mitre = p
        break

if mitre:
    print("Mitre 1473 prop entry:")
    print("  nombre:", mitre.get('nombre'))
    print("  piso:", mitre.get('piso'))
    print("  disposicion:", mitre.get('disposicion'))
    print("  vista:", mitre.get('vista'))
    print("  _ultima_valuacion:", json.dumps(mitre.get('_ultima_valuacion', {}), indent=2))

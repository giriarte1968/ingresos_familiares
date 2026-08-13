import json

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
for p in props:
    if '1372' in p.get('nombre', ''):
        print("PROPIEDAD:", p.get('nombre'))
        print("_ultima_valuacion:", json.dumps(p.get('_ultima_valuacion', {}), indent=2))

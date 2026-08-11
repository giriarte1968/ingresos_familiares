import json, os

props_file = 'propiedades.json'
if os.path.exists(props_file):
    data = json.load(open(props_file, 'r', encoding='utf-8'))
    for p in data.get('propiedades', []):
        uv = p.get('_ultima_valuacion', {})
        if uv.get('flex_dormitorios') == [1, 2, 3, 4, 5]:
            uv['flex_dormitorios'] = 1
            print(f"Propiedad {p.get('nombre')}: flex_dormitorios actualizado de [1,2,3,4,5] a 1 (D±1)")
    with open(props_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("propiedades.json actualizado con exito.")

cache_file = 'valuaciones_cache.json'
if os.path.exists(cache_file):
    os.remove(cache_file)
    print("valuaciones_cache.json limpiado.")

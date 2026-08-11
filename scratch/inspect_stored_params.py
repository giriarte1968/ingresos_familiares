import json

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
print("PARAMETROS ALMACENADOS EN _ultima_valuacion DE CADA PROPIEDAD:")
print("=" * 80)
for p in props_data.get('propiedades', []):
    uv = p.get('_ultima_valuacion', {})
    print(f"  Propiedad: {p.get('nombre'):<18} | retro_dias: {uv.get('retro_dias')} | flex_dormitorios: {uv.get('flex_dormitorios')} | comps: {uv.get('comps')}")

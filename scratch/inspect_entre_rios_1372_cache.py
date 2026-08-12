import json, os

print("=== CHECK PROPIEDADES.JSON ===")
props_path = 'propiedades.json'
data = json.load(open(props_path, 'r', encoding='utf-8'))
for p in data.get('propiedades', []):
    if '1372' in p.get('nombre', '') or '1372' in p.get('direccion', ''):
        print("PROPIEDAD:", p.get('nombre'))
        print("  _ultima_valuacion:", json.dumps(p.get('_ultima_valuacion', {}), indent=2))

print("\n=== CHECK VALUACIONES_CACHE.JSON ===")
cache_path = os.path.join('data', 'valuaciones_cache.json')
if os.path.exists(cache_path):
    cache = json.load(open(cache_path, 'r', encoding='utf-8'))
    for k, v in cache.items():
        if '1372' in k or 'entre' in k.lower():
            print("CACHE KEY:", k)
            res = v.get('resultado_completo', {})
            print("  valor_usd:", res.get('valor_propiedad_usd'))
            print("  m2_base_venta:", res.get('m2_base_venta'))
            print("  _comp_exclusion_applied:", res.get('_comp_exclusion_applied'))
            print("  _comp_excluded:", res.get('_comp_excluded'))

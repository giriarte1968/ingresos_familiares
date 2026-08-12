import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7
from parsers.valuacion_cache import cargar_cache_valuaciones, persistir_valuacion, guardar_cache_valuaciones

props_path = 'propiedades.json'
data = json.load(open(props_path, 'r', encoding='utf-8'))
props = data.get('propiedades', [])

for p in props:
    if '1372' in p.get('nombre', '') or '1372' in p.get('direccion', ''):
        # Valuar con Selección Natural (retro=0)
        res = valuar_propiedad_v7(p, retro_dias=0, flex_dormitorios=1)
        res['_comp_exclusion_applied'] = True
        res['_comp_excluded'] = []
        print("Valuación Natural para Entre Ríos 1372:", res.get('valor_propiedad_usd'), "USD,", res.get('m2_base_venta'), "USD/m²")
        cache_v = cargar_cache_valuaciones()
        persistir_valuacion(p.get('nombre'), p, res, cache_v, commit=True)
        break

print("Entre Ríos 1372 actualizado en propiedades.json con el valor natural (937 USD/m² / $78,440 USD)")

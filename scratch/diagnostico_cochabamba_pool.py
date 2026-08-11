import json, sys, os
from contextlib import redirect_stdout

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, normalizar_zona, obtener_cv_ref
)
from parsers.zonas_manager import resolver_macrozona
from scratch.simulate_v8f import valuar_v8f, precio_norm_sa_v8f

with open('propiedades.json', 'r', encoding='utf-8') as f:
    props = json.load(f)

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

cochabamba = None
for p in props['propiedades']:
    if 'Cochabamba' in p['nombre']:
        cochabamba = p
        break

lat, lon = cochabamba['lat'], cochabamba['lon']
dorms = cochabamba['dormitorios']
m2 = cochabamba['m2_cubiertos']
zona = cochabamba['zona']
uv = cochabamba['_ultima_valuacion']

f_out = open(os.devnull, 'w')
with redirect_stdout(f_out):
    vm2_s1, _, meta_s1 = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
        lat_ref=lat, lon_ref=lon, fecha_ref='2026-08-10',
        anio_sujeto=1966, tipo_inmueble='departamento',
        cache_scraping=cache, retro_dias=60,
        flex_dormitorios=uv.get('flex_dormitorios'), m2_equiv=m2
    )

pool = meta_s1.get('_pool_final', [])
mz_info = resolver_macrozona({'lat': lat, 'lon': lon, 'zona': normalizar_zona(zona) or ''})
macrozona_id = mz_info.get('macrozona_id') if isinstance(mz_info, dict) else 'macrocentro'

print("=" * 110)
print(f"DIAGNOSTICO DETALLADO: POOL DE COCHABAMBA 45 (4d, {m2}m2, lat={lat}, lon={lon})")
print("=" * 110)
print(f"Total comps en pool: {len(pool)}")
print(f"{'#':<3} {'Direccion/Zona':<32} {'d':>2} {'m2':>5} {'ant':>4} | {'Precio USD':>10} | {'raw $/m2':>9} | {'norm v8f $/m2':>13} | {'_cross_soft'}")
print("-" * 110)

comps_norm = []
for idx, c in enumerate(pool, 1):
    precio = c.get('precio', 0)
    c_m2 = c.get('m2', 0)
    c_dorms = c.get('dormitorios', 1)
    ant = c.get('antiquity', 'N/A')
    dir_str = (c.get('direccion') or c.get('zona') or 'Depto')[:32]
    raw_vm2 = c.get('valor_m2', 0)
    
    p_norm = precio_norm_sa_v8f(c, m2, dorms, macrozona_id)
    is_cross = c.get('_cross_soft', False)
    
    if p_norm:
        comps_norm.append((p_norm, c))
        
    print(f"{idx:<3} {dir_str:<32} {c_dorms:>2} {c_m2:>5.1f} {str(ant):>4} | ${precio:>9,.0f} | ${raw_vm2:>8,.0f} | ${p_norm:>12,.0f} | {str(is_cross)}")

print("=" * 110)
v8f_res = valuar_v8f(pool, m2, dorms, macrozona_id, lat, lon, 0.25)
print(f"Mediana $/m2 v8f: ${v8f_res['vm2']:,.0f}/m2  -->  Valuacion total: USD ${round(v8f_res['vm2'] * m2):,}")

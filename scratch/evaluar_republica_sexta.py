import json, math, sys, os
from contextlib import redirect_stdout

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, normalizar_zona, obtener_cv_ref
)
from parsers.zonas_manager import resolver_macrozona
from scratch.simulate_v8f import valuar_v8f

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

props = cache.get('propiedades', [])

# Coordenadas rectangulo Republica de la Sexta / Macrocentro Sur
# Lat: -32.968 a -32.955 | Lon: -60.635 a -60.620
sexta_props = []
for p in props:
    if p.get('operacion') != 'venta':
        continue
    
    lat = p.get('lat')
    lon = p.get('lon')
    if not lat or not lon: continue
    
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except: continue
    
    zona = p.get('zona', '')
    norm_z = normalizar_zona(zona) or ''
    
    # Match por zona o por bounding box geografico de Republica de la Sexta
    in_geo = (-32.970 <= lat_f <= -32.952) and (-60.638 <= lon_f <= -60.620)
    in_text = ('sexta' in norm_z.lower()) or ('republica' in norm_z.lower())
    
    if in_geo or in_text:
        vm2 = p.get('valor_m2', 0)
        m2 = p.get('m2', 0)
        precio = p.get('precio', 0) or p.get('precio_usd', 0)
        dorms = p.get('dormitorios')
        
        if 20 < m2 < 300 and 15000 < precio < 400000 and dorms:
            sexta_props.append(p)

print(f"Total propiedades encontradas en zona Republica de la Sexta: {len(sexta_props)}", flush=True)

# Tomar 10 variadas por tipo
selected = []
by_dorm = {}
for p in sexta_props:
    d = p.get('dormitorios', 1)
    if d not in by_dorm:
        by_dorm[d] = []
    by_dorm[d].append(p)

for d in [1, 2, 3, 4]:
    if d in by_dorm:
        selected.extend(by_dorm[d][:3])

selected = selected[:10]

print("=" * 125, flush=True)
print(f"{'#':<3} {'Titulo / Direccion':<38} {'d':>2} {'m2':>4} | {'Precio Pub.':>12} | {'Valuacion v8f':>14} | {'Delta USD':>10} | {'Gap %':>8}", flush=True)
print("=" * 125, flush=True)

f_out = open(os.devnull, 'w')
results = []

for idx, p in enumerate(selected, 1):
    lat = float(p['lat'])
    lon = float(p['lon'])
    dorms = p['dormitorios']
    m2 = p['m2']
    precio_pub = p.get('precio') or p.get('precio_usd') or (p.get('valor_m2', 0) * m2)
    zona = p.get('zona', 'República de la Sexta')
    
    mz_info = resolver_macrozona({'lat': lat, 'lon': lon, 'zona': normalizar_zona(zona) or ''})
    macrozona_id = mz_info.get('macrozona_id') if isinstance(mz_info, dict) else 'macrocentro'
    cv_ref = obtener_cv_ref(macrozona_id)
    
    with redirect_stdout(f_out):
        vm2_s1, _, meta_s1 = obtener_mediana_cluster_v2(
            zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
            lat_ref=lat, lon_ref=lon, fecha_ref='2026-08-10',
            anio_sujeto=2015, tipo_inmueble='departamento',
            cache_scraping=cache, retro_dias=180,
            flex_dormitorios=[max(1, dorms-1), dorms, min(4, dorms+1)], m2_equiv=m2
        )
    pool = meta_s1.get('_pool_final', [])
    
    v8f_res = valuar_v8f(pool, m2, dorms, macrozona_id, lat, lon, cv_ref)
    vm2_v8f = v8f_res['vm2']
    val_v8f = round(vm2_v8f * m2) if vm2_v8f else 0
    
    gap_pct = ((val_v8f - precio_pub) / precio_pub * 100) if precio_pub else 0
    delta_usd = val_v8f - precio_pub
    
    title = p.get('titulo') or p.get('direccion') or f"Depto {dorms}d {m2}m2"
    title_short = title[:36]
    
    print(f"{idx:<3} {title_short:<38} {dorms:>2} {m2:>4.0f} | ${precio_pub:>11,.0f} | ${val_v8f:>13,.0f} | ${delta_usd:>+9,.0f} | {gap_pct:>+7.1f}%", flush=True)
    
    results.append({
        'precio_pub': precio_pub,
        'val_v8f': val_v8f,
        'gap_pct': gap_pct,
        'abs_gap_pct': abs(gap_pct)
    })

print("=" * 125, flush=True)
avg_gap = sum(r['gap_pct'] for r in results) / len(results) if results else 0
avg_abs_gap = sum(r['abs_gap_pct'] for r in results) / len(results) if results else 0
print(f"Gap promedio (Sesgo del modelo): {avg_gap:+.2f}%  |  MAPE local (Error medio absoluto): {avg_abs_gap:.2f}%", flush=True)

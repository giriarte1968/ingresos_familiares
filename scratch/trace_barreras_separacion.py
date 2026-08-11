import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7, obtener_mediana_cluster_v2
from parsers.location_engine import check_barrier_crossing, cargar_barreras
from parsers.cluster_filters import separar_por_barreras

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
cochabamba = None
for p in props_data.get('propiedades', []):
    if 'cochabamba' in p.get('nombre', '').lower():
        cochabamba = p
        break

barreras = cargar_barreras()
lat, lon = cochabamba['lat'], cochabamba['lon']

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache_scraping = json.load(f)

# Find comps within 1000m of Cochabamba 45 (lat, lon) with operacion=venta, dorms in [3, 4]
from parsers.mercado_inmobiliario import calcular_distancia_km
raw_comps = []
for p in cache_scraping.get('propiedades', []):
    if p.get('operacion') != 'venta': continue
    if p.get('dormitorios') not in [3, 4]: continue
    plat = p.get('lat') or p.get('latitud')
    plon = p.get('lon') or p.get('longitud')
    if not (plat and plon): continue
    d_km = calcular_distancia_km(lat, lon, float(plat), float(plon))
    if d_km <= 1.0:
        p_copy = dict(p)
        p_copy['distancia_m'] = round(d_km * 1000, 1)
        raw_comps.append(p_copy)

print(f"Total raw comps 3d/4d en 1000m: {len(raw_comps)}")

b_res = separar_por_barreras(
    props=raw_comps,
    lat_ref=lat,
    lon_ref=lon,
    check_barrier_fn=lambda p1, p2: check_barrier_crossing(p1, p2, barreras),
    zona_ref='sexta'
)

print(f"same_side count: {len(b_res['same_side'])}")
print(f"cross_soft count: {len(b_res['cross_soft'])}")
print(f"excluded_hard count: {len(b_res['excluded_hard'])}")

print("\n--- SAME SIDE COMPS ---")
for c in b_res['same_side']:
    print(f"  {c.get('direccion','?'):<35} | {c.get('dormitorios')}d | {c.get('m2')}m2 | ${c.get('precio',0):,.0f} USD | ${c.get('valor_m2',0):.1f}/m2")

print("\n--- CROSS SOFT COMPS ---")
for c in b_res['cross_soft']:
    print(f"  {c.get('direccion','?'):<35} | {c.get('dormitorios')}d | {c.get('m2')}m2 | ${c.get('precio',0):,.0f} USD | ${c.get('valor_m2',0):.1f}/m2")

print("\n--- EXCLUDED HARD COMPS ---")
for c in b_res['excluded_hard']:
    print(f"  {c.get('direccion','?'):<35} | {c.get('dormitorios')}d | {c.get('m2')}m2 | ${c.get('precio',0):,.0f} USD | ${c.get('valor_m2',0):.1f}/m2")

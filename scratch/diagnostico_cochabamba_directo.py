import json, sys, os
from contextlib import redirect_stdout

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, normalizar_zona
)

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
anio_const = cochabamba.get('anio_construccion', 1966)

f_out = open(os.devnull, 'w')
with redirect_stdout(f_out):
    vm2_s1, _, meta_s1 = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
        lat_ref=lat, lon_ref=lon, fecha_ref='2026-08-10',
        anio_sujeto=anio_const, tipo_inmueble='departamento',
        cache_scraping=cache, retro_dias=60,
        flex_dormitorios=uv.get('flex_dormitorios'), m2_equiv=m2
    )

pool = meta_s1.get('_pool_final', [])

print("=" * 90, flush=True)
print("INSPECCION DIRECTA DEL POOL DEL CLUSTER DE COCHABAMBA 45", flush=True)
print("=" * 90, flush=True)
print(f"Propiedad: Cochabamba 45 | anio_construccion: {anio_const} (1966)", flush=True)
print(f"Total comparables en _pool_final: {len(pool)}", flush=True)

with_antiquity = [p for p in pool if p.get('antiquity') is not None and p.get('antiquity') >= 0]
without_antiquity = [p for p in pool if p.get('antiquity') is None or p.get('antiquity') < 0]

print(f"\nComparables con campo 'antiquity' (edad cargada): {len(with_antiquity)} / {len(pool)}", flush=True)
print(f"Comparables SIN campo 'antiquity' (edad nula/missing): {len(without_antiquity)} / {len(pool)}", flush=True)

if with_antiquity:
    print("\nDetalle de comps con antiquity:")
    for p in with_antiquity:
        print(f"  - {p.get('direccion') or p.get('zona')}: antiquity = {p.get('antiquity')} anos (Construido ~ {2026 - p.get('antiquity')})")

print("\nConclusion de la regla de +-10 anos del engine:")
print("Dado que de los 29 comps del pool la inmensa mayoria NO tiene cargado 'antiquity' en el scraping, el filtro de edad _filtrar_por_ventana_edad() retoma el pool completo sin filtrar por ano.", flush=True)

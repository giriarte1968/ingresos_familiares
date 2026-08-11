import json, sys, os
from contextlib import redirect_stdout

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, calcular_m2_equivalentes, normalizar_zona, obtener_cv_ref
)
from parsers.zonas_manager import resolver_macrozona
from scratch.simulate_v8f import valuar_v8f

with open('propiedades.json', 'r', encoding='utf-8') as f:
    props = json.load(f)

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

vera = None
for p in props['propiedades']:
    if 'Vera' in p['nombre']:
        vera = p
        break

print("=" * 90)
print("DIAGNOSTICO DETALLADO: VERA MUJICA 912")
print("=" * 90)

print(f"Piso: {vera.get('piso')} (Planta Baja / Interno)")
print(f"Disposicion/Vista: {vera.get('vista')}")
print(f"m2 cubiertos: {vera.get('m2_cubiertos')}")
print(f"m2 descubiertos patio: {vera.get('m2_descubiertos_comun_exclusivo')}")
print(f"m2 equivalentes actual: {calcular_m2_equivalentes(vera)}")
print(f"Fecha compra: {vera.get('fecha_compra')} | Precio compra: USD ${vera.get('valor_compra_usd'):,}")
print(f"Target objetivo mercado: USD $50,000 - $55,000")

lat, lon = vera['lat'], vera['lon']
dorms = vera['dormitorios']
zona = vera['zona']
uv = vera['_ultima_valuacion']

f_out = open(os.devnull, 'w')
with redirect_stdout(f_out):
    vm2_s1, _, meta_s1 = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
        lat_ref=lat, lon_ref=lon, fecha_ref='2026-08-10',
        anio_sujeto=vera.get('anio_construccion', 2009), tipo_inmueble='departamento',
        cache_scraping=cache, retro_dias=60,
        flex_dormitorios=uv.get('flex_dormitorios'), m2_equiv=calcular_m2_equivalentes(vera)
    )

pool = meta_s1.get('_pool_final', [])
print(f"\nPool final traido por el cluster: {len(pool)} comparables")

print("\nAtributos de los comps del pool:")
pb_internos = 0
frentes_balcon = 0

for c in pool:
    title = (c.get('titulo') or c.get('descripcion') or '').lower()
    piso = c.get('piso')
    if piso == 0 or 'pb' in title or 'planta baja' in title or 'interno' in title:
        pb_internos += 1
    else:
        frentes_balcon += 1

print(f"  - Comps PB/Interno en el pool: {pb_internos}")
print(f"  - Comps Piso medio/Frente/Balcon en el pool: {frentes_balcon}")

# Check m2_equiv weight for patio
print("\n--- IMPACTO DE FACTOR PATIO Y FACTOR PB INTERNO ---")
m2_cub = vera.get('m2_cubiertos', 35.54)
patio_m2 = vera.get('m2_descubiertos_comun_exclusivo', 12.7)

for factor_patio in [0.40, 0.20, 0.15, 0.10, 0.0]:
    m2_eq_test = m2_cub + (patio_m2 * factor_patio)
    val_s1 = round(vm2_s1 * m2_eq_test)
    
    # Apply PB Interno discount (typically -15% to -20% in Rosario real estate)
    for pb_discount in [1.0, 0.85, 0.80]:
        v8f_res = valuar_v8f(pool, m2_eq_test, dorms, 'macrocentro', lat, lon, 0.25)
        val_v8f = round(v8f_res['vm2'] * m2_eq_test * pb_discount)
        print(f"Factor Patio={factor_patio:.2f} (m2_eq={m2_eq_test:.2f}) | Desc PB/Interno={pb_discount:.2f} -> S1: ${val_s1:,} | v8f: ${val_v8f:,}")

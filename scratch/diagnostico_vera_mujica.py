import json, sys, os
from contextlib import redirect_stdout

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, calcular_m2_equivalentes, normalizar_zona, obtener_cv_ref
)
from parsers.zonas_manager import resolver_macrozona
from scratch.simulate_v8f import (
    valuar_v8f, precio_norm_sa_v8f, get_beta_continuous, sa_factor_continuous
)

with open('propiedades.json', 'r', encoding='utf-8') as f:
    props = json.load(f)

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

# Find Vera Mujica
vera = None
for p in props['propiedades']:
    if 'Vera' in p['nombre']:
        vera = p
        break

print("PROPIEDAD:", vera['nombre'])
lat, lon = vera['lat'], vera['lon']
m2_cub = vera.get('m2_cubiertos', 35.54)
m2_eq = calcular_m2_equivalentes(vera)
dorms = vera['dormitorios']
zona = vera['zona']
uv = vera['_ultima_valuacion']

print(f"m2 cubiertos: {m2_cub} | m2 equivalentes: {m2_eq} | dorms: {dorms} | zona: {zona}")

mz_info = resolver_macrozona({'lat': lat, 'lon': lon, 'zona': normalizar_zona(zona) or ''})
macrozona_id = mz_info.get('macrozona_id')
cv_ref = obtener_cv_ref(macrozona_id)

print(f"Macrozona: {macrozona_id} | Beta continuo 1d: {get_beta_continuous(macrozona_id, dorms)}")

f_out = open(os.devnull, 'w')
with redirect_stdout(f_out):
    vm2_s1, _, meta_s1 = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
        lat_ref=lat, lon_ref=lon, fecha_ref='2026-08-10',
        anio_sujeto=2009, tipo_inmueble='departamento',
        cache_scraping=cache, retro_dias=60,
        flex_dormitorios=uv.get('flex_dormitorios'), m2_equiv=m2_eq
    )

pool = meta_s1.get('_pool_final', [])
print(f"\nPool final del cluster: {len(pool)} comparables")

# Inspect individual comps and SA adjustments
adjusted_comps = []
for c in pool:
    precio_m2 = c.get('precio_m2', c.get('valor_m2', 0))
    ct = c.get('_time_adjustment', c.get('time_adjustment', 1.0))
    raw = precio_m2 * ct
    m2_comp = c.get('m2') or c.get('m2_cubiertos', 0) or 0
    dorms_comp = c.get('dormitorios', dorms)
    
    # SA factor with m2_cub vs m2_eq
    sa_ratio_cub = sa_factor_continuous(m2_cub, m2_comp, macrozona_id, dorms)
    sa_ratio_eq = sa_factor_continuous(m2_eq, m2_comp, macrozona_id, dorms)
    
    p_norm = precio_norm_sa_v8f(c, m2_cub, dorms, macrozona_id)
    p_norm_eq = precio_norm_sa_v8f(c, m2_eq, dorms, macrozona_id)
    
    adjusted_comps.append({
        'comp_m2': m2_comp,
        'dorms': dorms_comp,
        'raw_vm2': raw,
        'sa_ratio_cub': sa_ratio_cub,
        'sa_ratio_eq': sa_ratio_eq,
        'p_norm_cub': p_norm,
        'p_norm_eq': p_norm_eq,
        'is_cross': c.get('_cross_soft', False)
    })

print("\n--- PRIMEROS 10 COMPS DEL POOL Y SUS AJUSTES ---")
print(f"{'Comp m2':<8} {'d':>2} {'raw $/m2':>10} | {'SA ratio (m2_cub=35.5)':>22} | {'p_norm ($/m2)':>14} | {'Val. final 40.6m2 eq':>20}")
print("-" * 85)
for ac in adjusted_comps[:10]:
    val_eq = round(ac['p_norm_cub'] * m2_eq) if ac['p_norm_cub'] else 0
    print(f"{ac['comp_m2']:<8.1f} {ac['dorms']:>2} ${ac['raw_vm2']:>9,.0f} | {ac['sa_ratio_cub']:>22.4f} | ${ac['p_norm_cub']:>13,.0f} | ${val_eq:>19,}")

# Run valuar_v8f
res_cub = valuar_v8f(pool, m2_cub, dorms, macrozona_id, lat, lon, cv_ref)
res_eq = valuar_v8f(pool, m2_eq, dorms, macrozona_id, lat, lon, cv_ref)

print("\n--- RESULTADOS GENERALES ---")
print(f"Engine S1 $/m2: ${vm2_s1:,.0f} -> Val. S1 (40.6m2 eq): ${round(vm2_s1 * m2_eq):,}")
print(f"v8f (m2_cub=35.54) $/m2: ${res_cub['vm2']:,.0f} -> Val. v8f (40.6m2 eq): ${round(res_cub['vm2'] * m2_eq):,}")
print(f"v8f (m2_eq=40.62) $/m2: ${res_eq['vm2']:,.0f} -> Val. v8f (40.6m2 eq): ${round(res_eq['vm2'] * m2_eq):,}")

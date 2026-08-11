"""
DIAGNOSTICO MITRE 1473: Por qué v8f da $256k cuando target es $200-220k
==========================================================================
Descompone paso a paso qué está pasando con los ajustes SA + flex_dorm
para Mitre 1473: 3d, 206m², centro_premium
"""

import sys, os, json, math, io
from contextlib import redirect_stdout
from collections import Counter

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')
import warnings; warnings.filterwarnings('ignore')

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, calcular_m2_equivalentes, normalizar_zona, obtener_cv_ref
)
from parsers.zonas_manager import resolver_macrozona
from scratch.simulate_v8f import (
    sa_factor_v8f, factor_dorm_flex, precio_norm_sa_v8f,
    m2_percentile, clasificar_por_dorm, BARRIER_VECTOR_INFO
)

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache_scraping = json.load(f)
with open('propiedades.json', 'r', encoding='utf-8') as f:
    props_data = json.load(f)

# Encontrar Mitre
mitre = next(p for p in props_data['propiedades'] if 'Mitre' in p.get('nombre','') or 'mitre' in p.get('nombre','').lower())

nombre = mitre['nombre']
lat, lon = mitre['lat'], mitre['lon']
dorms = mitre['dormitorios']
m2 = mitre.get('m2_cubiertos', 0) or mitre.get('m2', 0)
zona = mitre.get('zona', '')
uv = mitre.get('_ultima_valuacion', {})
m2_equiv = calcular_m2_equivalentes(mitre)
FECHA = '2026-08-08'

_mz = resolver_macrozona({'zona': normalizar_zona(zona) or '', 'lat': lat, 'lon': lon})
macrozona_id = _mz.get('macrozona_id')

print("=" * 80)
print(f"DIAGNOSTICO: {nombre}")
print(f"  {dorms}d | {m2}m² | {m2_equiv:.1f}m²eq | {macrozona_id} | {zona}")
print("=" * 80)

# Obtener pool del engine
f_out = io.StringIO()
with redirect_stdout(f_out):
    vm2_s1, _, meta_s1 = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
        lat_ref=lat, lon_ref=lon, fecha_ref=FECHA,
        anio_sujeto=mitre.get('anio_construccion', 2000),
        tipo_inmueble=mitre.get('tipo_inmueble') or 'departamento',
        cache_scraping=cache_scraping,
        retro_dias=uv.get('retro_dias', 0),
        flex_dormitorios=uv.get('flex_dormitorios'),
        m2_equiv=m2_equiv,
    )
pool = meta_s1.get('_pool_final', [])

print(f"\n1. POOL DEL ENGINE: {len(pool)} comparables")
value_s1 = round(vm2_s1 * m2_equiv) if vm2_s1 else 0
print(f"   Engine vm2=${vm2_s1:,.0f}  -> Valor=${value_s1:,}")

# Composicion del pool
dorm_counter = Counter(c.get('dormitorios') for c in pool)
cross_counter = Counter(c.get('dormitorios') for c in pool if c.get('_cross_soft'))
same_counter  = Counter(c.get('dormitorios') for c in pool if not c.get('_cross_soft'))
print(f"\n   Composicion por dormitorios:")
for d in sorted(dorm_counter):
    s = same_counter.get(d, 0)
    x = cross_counter.get(d, 0)
    print(f"   {d}d: {dorm_counter[d]:>3} total ({s} same-dorm, {x} cross/flex)")

# SA factor del sujeto
f_suj = sa_factor_v8f(m2, macrozona_id, dorms)
cat_suj = clasificar_por_dorm(m2, dorms)
pct_suj = m2_percentile(m2, dorms)
print(f"\n2. AJUSTE SA DEL SUJETO (Mitre)")
print(f"   m2={m2}  categoria={cat_suj}  percentil={pct_suj:.1f}%")
print(f"   sa_factor_sujeto = {f_suj:.4f}")

print(f"\n3. DESCOMPOSICION COMP A COMP (primeros 20 cross-dorm)")
print(f"   {'vm2_raw':>9} {'ct':>6} {'d_c':>4} {'m2_c':>5} {'cat_c':>7} | "
      f"{'f_suj':>6} {'f_comp':>6} {'ratio_SA':>8} {'f_dorm':>7} | "
      f"{'precio_norm':>11} | {'pass_pct':>8} {'pass_band':>9}")
print("   " + "-"*115)

n_cross = 0
cross_precios = []
cross_raw = []
cross_details = []

for comp in pool:
    is_cross = comp.get('_cross_soft', False)
    if not is_cross: continue
    n_cross += 1

    vm2_raw = comp.get('precio_m2', comp.get('valor_m2', 0))
    ct = comp.get('_time_adjustment', comp.get('time_adjustment', 1.0))
    d_c = comp.get('dormitorios', dorms)
    m2_c = comp.get('m2', 0) or 0

    cat_c = clasificar_por_dorm(m2_c, d_c)
    pct_c = m2_percentile(m2_c, d_c)
    pass_pct = abs(pct_c - pct_suj) <= 30

    f_c = sa_factor_v8f(m2_c, macrozona_id, d_c)
    ratio_sa = (f_suj / f_c) if f_c > 0 else 1.0
    ratio_sa = max(0.75, min(1.33, ratio_sa))
    f_dorm = factor_dorm_flex(dorms, d_c, macrozona_id)
    precio_norm = vm2_raw * ct * ratio_sa * f_dorm

    # Banda de precio (ancla desde mediana del pool flex)
    cross_details.append({
        'raw': vm2_raw, 'ct': ct, 'd_c': d_c, 'm2_c': m2_c, 'cat_c': cat_c,
        'pct_c': pct_c, 'pass_pct': pass_pct, 'f_suj': f_suj, 'f_c': f_c,
        'ratio_sa': ratio_sa, 'f_dorm': f_dorm, 'precio_norm': precio_norm,
    })
    cross_raw.append(vm2_raw * ct)

# Calcular ancla
if cross_raw:
    ancla = sorted(cross_raw)[len(cross_raw)//2]
    lo_b, hi_b = ancla * 0.40, ancla * 1.60
else:
    ancla, lo_b, hi_b = 0, 0, 999999

for r in cross_details[:20]:
    pass_band = lo_b <= r['raw']*r.get('ct',1.0) <= hi_b
    print(f"   ${r['raw']:>8,.0f} {r['ct']:>6.3f} {r['d_c']:>4} {r['m2_c']:>5.0f} {r['cat_c']:>7} | "
          f"{r['f_suj']:>6.3f} {r['f_c']:>6.3f} {r['ratio_sa']:>8.3f} {r['f_dorm']:>7.3f} | "
          f"${r['precio_norm']:>10,.0f} | {'OK':>8} {'OK' if pass_band else 'FILT':>9}")

print(f"\n   Ancla precio: ${ancla:,.0f}/m²  Banda: ${lo_b:,.0f} - ${hi_b:,.0f}/m²")

# Stats de los precios normalizados cross
pn_all = [r['precio_norm'] for r in cross_details]
pn_pct = [r['precio_norm'] for r in cross_details if r['pass_pct']]
if pn_pct:
    pn_pct.sort()
    print(f"\n4. MEDIANA PRECIOS NORMALIZADOS (comps cross-dorm)")
    print(f"   Todos ({len(pn_all)} comps): mediana=${sorted(pn_all)[len(pn_all)//2]:,.0f}/m²")
    print(f"   Pasaron filtro pct ({len(pn_pct)} comps): mediana=${pn_pct[len(pn_pct)//2]:,.0f}/m²")
    print(f"   Estimacion v8f: $256,552 → ${256552/m2_equiv:,.0f}/m² sobre {m2_equiv:.1f}m²eq")
    print(f"\n   CONCLUSION: El SA ratio y flex_dorm llevan los comps cross a que precio?")
    for d_tipo in [1,2,3]:
        sub = [r for r in cross_details if r['d_c']==d_tipo]
        if sub:
            med = sorted([r['precio_norm'] for r in sub])[len(sub)//2]
            f_d = factor_dorm_flex(dorms, d_tipo, macrozona_id)
            f_c_typ = sub[len(sub)//2]['f_c']
            print(f"   Comps {d_tipo}d (n={len(sub)}): precio_norm mediana=${med:,.0f}  f_dorm={f_d:.3f}  f_comp_SA={f_c_typ:.3f}")

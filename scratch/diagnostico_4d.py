"""
DIAGNOSTICO PROFUNDO: PROBLEMA 4 DORMITORIOS
=============================================
Analiza las causas del MAPE 47% en departamentos de 4 dormitorios:
1. Distribucion geografica de 4d en el cache
2. Disponibilidad de pool de comparables
3. Distribucion de errores (sobrevalua o subvalua?)
4. Caracteristicas de los outliers de error
5. Analisis de tamano (m2) y su impacto
"""

import sys, os, json, math, random, io, time
from contextlib import redirect_stdout
from collections import defaultdict

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

import warnings
warnings.filterwarnings('ignore')
import numpy as np

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, calcular_m2_equivalentes, normalizar_zona, obtener_cv_ref
)
from parsers.zonas_manager import resolver_macrozona
from scratch.simulate_v8f import valuar_v8f, BARRIER_VECTOR_INFO

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache_scraping = json.load(f)

print("=" * 90)
print("DIAGNOSTICO 4 DORMITORIOS")
print("=" * 90)

# ============================================================
# 1. STOCK DE 4d EN EL CACHE
# ============================================================
props_4d = [p for p in cache_scraping['propiedades']
            if p.get('operacion') == 'venta'
            and p.get('dormitorios') == 4
            and 300 < p.get('valor_m2', 0) < 6000
            and 20 < p.get('m2', 0) < 400
            and p.get('lat') and p.get('lon')]

print(f"\n1. STOCK DE 4 DORMITORIOS EN CACHE")
print(f"   Total 4d en venta validos: {len(props_4d)}")
print(f"   Total propiedades validas todas: {sum(1 for p in cache_scraping['propiedades'] if p.get('operacion')=='venta' and 300<p.get('valor_m2',0)<6000 and 20<p.get('m2',0)<400)}")

# Por macrozona
mz_count = defaultdict(int)
mz_vm2 = defaultdict(list)
for p in props_4d:
    lat, lon = p['lat'], p['lon']
    zona = p.get('zona', '') or ''
    try:
        _mz = resolver_macrozona({'zona': normalizar_zona(zona) or '', 'lat': lat, 'lon': lon})
        mz = _mz.get('macrozona_id', 'sin_mz')
    except:
        mz = 'sin_mz'
    mz_count[mz] += 1
    mz_vm2[mz].append(p['valor_m2'])

print(f"\n   Distribucion por macrozona:")
for mz, n in sorted(mz_count.items(), key=lambda x: -x[1]):
    vm2 = sorted(mz_vm2[mz])
    p50 = vm2[len(vm2)//2] if vm2 else 0
    print(f"   {mz:<22}: n={n:>3}  P50 $/m2=${p50:>6,.0f}")

# Distribucion de m2
m2_vals = [p['m2'] for p in props_4d]
print(f"\n   Distribucion de m2 (4d):")
print(f"   Min={min(m2_vals):.0f}  P25={np.percentile(m2_vals,25):.0f}  P50={np.percentile(m2_vals,50):.0f}  P75={np.percentile(m2_vals,75):.0f}  Max={max(m2_vals):.0f}")

# ============================================================
# 2. BACKTEST FOCALIZADO EN 4d (muestra completa)
# ============================================================
print(f"\n2. BACKTEST FOCALIZADO EN 4d ({len(props_4d)} propiedades)")
print("   (cada prop valuada excluyéndose a sí misma del pool)")

random.seed(42)
muestra_4d = props_4d if len(props_4d) <= 80 else random.sample(props_4d, 80)

FECHA = '2026-08-08'
resultados = []
f_out = io.StringIO()

for i, p in enumerate(muestra_4d):
    lat, lon = p['lat'], p['lon']
    zona = p.get('zona', '') or ''
    m2 = p.get('m2', 0)
    vm2_real = p.get('valor_m2', 0)
    valor_real = p.get('valor_usd', vm2_real * m2) if p.get('valor_usd') else vm2_real * m2

    macrozona_id = None
    try:
        _mz = resolver_macrozona({'zona': normalizar_zona(zona) or '', 'lat': lat, 'lon': lon})
        macrozona_id = _mz.get('macrozona_id')
    except: pass

    cv_ref = obtener_cv_ref(macrozona_id)
    m2_equiv = calcular_m2_equivalentes(p)
    anio = p.get('anio_construccion', 2010)

    try:
        with redirect_stdout(f_out):
            vm2_s1, _, meta_s1 = obtener_mediana_cluster_v2(
                zona=normalizar_zona(zona), dormitorios=4, operacion='venta',
                lat_ref=lat, lon_ref=lon, fecha_ref=FECHA,
                anio_sujeto=anio, tipo_inmueble='departamento',
                cache_scraping=cache_scraping, retro_dias=60*30,
                flex_dormitorios=[1, 2, 3], m2_equiv=m2_equiv,
            )
        pool = meta_s1.get('_pool_final', [])
        n_pool = len(pool)
        n_same_dorm = sum(1 for c in pool if c.get('dormitorios') == 4)
        n_flex = n_pool - n_same_dorm

        # Excluir sujeto del pool
        url_suj = p.get('url', '')
        pool_clean = [c for c in pool if c.get('url', '') != url_suj
                      and not (abs(c.get('lat',0) - lat) < 0.0001 and abs(c.get('lon',0) - lon) < 0.0001)]

        value_s1 = round(vm2_s1 * m2_equiv) if vm2_s1 else 0

        v8f = valuar_v8f(pool_clean, m2, 4, macrozona_id, lat, lon, cv_ref)
        value_v8f = round(v8f['vm2'] * m2_equiv) if v8f['vm2'] else 0

        if not value_s1 or not value_v8f or not valor_real: continue

        err_s1 = abs(value_s1 - valor_real) / valor_real * 100
        err_v8f = abs(value_v8f - valor_real) / valor_real * 100
        bias_v8f = (value_v8f - valor_real) / valor_real * 100

        resultados.append({
            'zona': zona, 'mz': macrozona_id or '?', 'm2': m2,
            'vm2_real': vm2_real, 'valor_real': valor_real,
            'value_s1': value_s1, 'value_v8f': value_v8f,
            'err_s1': err_s1, 'err_v8f': err_v8f, 'bias_v8f': bias_v8f,
            'n_pool': n_pool, 'n_same': n_same_dorm, 'n_flex': n_flex,
        })
    except Exception as e:
        if i < 3:  # Solo mostrar primeros errores
            print(f"   [ERR prop {i}]: {e}")

    if (i+1) % 20 == 0:
        print(f"   Procesando {i+1}/{len(muestra_4d)}... ({len(resultados)} validos hasta ahora)")

print(f"\n   Resultados validos: {len(resultados)}/{len(muestra_4d)}")

# ============================================================
# 3. ESTADISTICAS DE ERROR
# ============================================================
errs_s1 = [r['err_s1'] for r in resultados]
errs_v8f = [r['err_v8f'] for r in resultados]
bias_v8f = [r['bias_v8f'] for r in resultados]

print(f"\n3. ESTADISTICAS DE ERROR (4d)")
if not resultados:
    print("   [SIN RESULTADOS VALIDOS - revisar parametros de llamada]")
else:
    n = len(resultados)
    print(f"   {'Metrica':<25} {'Engine':>10} {'v8f':>10}")
    print(f"   {'-'*48}")
    print(f"   {'MAPE':<25} {np.mean(errs_s1):>9.2f}% {np.mean(errs_v8f):>9.2f}%")
    print(f"   {'MedAPE':<25} {np.median(errs_s1):>9.2f}% {np.median(errs_v8f):>9.2f}%")
    print(f"   {'Hits +-10%':<25} {sum(1 for e in errs_s1 if e<=10)/n*100:>9.1f}% {sum(1 for e in errs_v8f if e<=10)/n*100:>9.1f}%")
    print(f"   {'Hits +-20%':<25} {sum(1 for e in errs_s1 if e<=20)/n*100:>9.1f}% {sum(1 for e in errs_v8f if e<=20)/n*100:>9.1f}%")
    print(f"   {'Bias medio (sesgo)':<25} {'—':>10} {np.mean(bias_v8f):>+9.1f}%")
    pos_bias = sum(1 for b in bias_v8f if b > 0)
    print(f"   {'Sobrestima (bias>0)':<25} {'—':>10} {pos_bias}/{n} ({pos_bias/n*100:.0f}%)")

# ============================================================
# 4. POOL DE COMPARABLES
# ============================================================
n_pools = [r['n_pool'] for r in resultados]
n_sames = [r['n_same'] for r in resultados]
n_flexs = [r['n_flex'] for r in resultados]

print(f"\n4. CALIDAD DEL POOL DE COMPARABLES (4d)")
print(f"   Pool total:  Media={np.mean(n_pools):.1f}  Min={min(n_pools)}  Max={max(n_pools)}  P50={np.median(n_pools):.0f}")
print(f"   Comps 4d:    Media={np.mean(n_sames):.1f}  Min={min(n_sames)}  Max={max(n_sames)}  P50={np.median(n_sames):.0f}")
print(f"   Comps flex:  Media={np.mean(n_flexs):.1f}  Min={min(n_flexs)}  Max={max(n_flexs)}  P50={np.median(n_flexs):.0f}")

# Correlacion: n_same vs error
print(f"\n   Correlacion n_same_dorm vs error v8f:")
for n_lim in [0, 3, 7, 15]:
    sub = [r for r in resultados if r['n_same'] <= n_lim]
    if sub:
        print(f"   Props con <=  {n_lim:>2} comps 4d: n={len(sub):>3}  MAPE_v8f={np.mean([r['err_v8f'] for r in sub]):.1f}%")

# ============================================================
# 5. OUTLIERS EXTREMOS
# ============================================================
print(f"\n5. CASOS CON ERROR > 40% (los que inflan el MAPE)")
outliers = sorted([r for r in resultados if r['err_v8f'] > 40], key=lambda x: -x['err_v8f'])
print(f"   {'Zona':<22} {'m2':>4} {'macrozona':<15} {'Real':>10} {'v8f':>10} {'error%':>7} {'n_same':>7} {'n_flex':>7}")
print(f"   {'-'*90}")
for r in outliers[:15]:
    print(f"   {r['zona']:<22} {r['m2']:>4.0f} {r['mz']:<15} ${r['valor_real']:>8,.0f} ${r['value_v8f']:>8,.0f} {r['bias_v8f']:>+6.1f}% {r['n_same']:>7} {r['n_flex']:>7}")

# ============================================================
# 6. CONCLUSION
# ============================================================
print(f"\n6. CONCLUSION")
escasez = sum(1 for r in resultados if r['n_same'] < 5) / len(resultados) * 100
print(f"   Props con < 5 comps 4d: {escasez:.1f}% del total")
sobrevalua = sum(1 for b in bias_v8f if b > 10) / len(bias_v8f) * 100
subvalua  = sum(1 for b in bias_v8f if b < -10) / len(bias_v8f) * 100
print(f"   Sobrestima > 10%: {sobrevalua:.1f}%  |  Subestima > 10%: {subvalua:.1f}%")

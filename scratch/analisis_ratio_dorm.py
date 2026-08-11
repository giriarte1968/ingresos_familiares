"""
ANALISIS EMPIRICO: RATIO $/m2 POR DORMITORIOS POR MACROZONA
============================================================
Calcula el factor real de diferencia de $/m2 entre tipos de dormitorio
segmentado por macrozona, usando las 16.946 ventas del cache.

Esto reemplaza el factor_dorm_flex hardcodeado (0.08/dorm) por valores
medidos directamente en el mercado de Rosario.
"""

import sys, os, json, math
from collections import defaultdict

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

import warnings
warnings.filterwarnings('ignore')

from parsers.zonas_manager import resolver_macrozona
from parsers.mercado_inmobiliario import normalizar_zona

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

print("=" * 90)
print("ANALISIS EMPIRICO: FACTOR $/m2 POR DORMITORIOS (16.946 ventas)")
print("=" * 90)

# Filtro base
ventas = [p for p in cache['propiedades']
          if p.get('operacion') == 'venta'
          and 300 < p.get('valor_m2', 0) < 6000
          and 20 < p.get('m2', 0) < 400
          and p.get('lat') and p.get('lon')
          and p.get('dormitorios') in [1, 2, 3, 4]]

print(f"\nVentas validas para analisis: {len(ventas)}")

# Asignar macrozona a cada venta
grupos = defaultdict(lambda: defaultdict(list))  # grupos[macrozona][dorms] = [vm2, ...]

sin_mz = 0
for p in ventas:
    lat, lon = p.get('lat'), p.get('lon')
    zona = p.get('zona', '') or ''
    try:
        _mz = resolver_macrozona({'zona': normalizar_zona(zona) or '', 'lat': lat, 'lon': lon})
        mz = _mz.get('macrozona_id')
    except:
        mz = None
    if not mz:
        sin_mz += 1
        mz = 'sin_macrozona'
    dorms = int(p['dormitorios'])
    grupos[mz][dorms].append(float(p['valor_m2']))

print(f"Sin macrozona asignada: {sin_mz}")

def p50(l):
    if not l: return None
    s = sorted(l)
    return s[int(len(s) * 0.50)]

def p25(l):
    if not l: return None
    s = sorted(l)
    return s[int(len(s) * 0.25)]

def p75(l):
    if not l: return None
    s = sorted(l)
    return s[int(len(s) * 0.75)]

print("\n" + "=" * 90)
print("RATIOS $/m2 POR MACROZONA Y DORMITORIOS")
print("(Mediana del grupo 2d = 1.00 como referencia)")
print("=" * 90)

# Tabla de ratios por macrozona
all_ratios = defaultdict(list)  # all_ratios[(d_base, d_target)] = [ratio_mz1, ratio_mz2, ...]

header = f"{'Macrozona':<22} {'N':>5} | {'1d P50':>9} {'2d P50':>9} {'3d P50':>9} {'4d P50':>9} | {'rat 1d/2d':>9} {'rat 3d/2d':>9} {'rat 4d/2d':>9}"
print(header)
print("-" * len(header))

resultados_mz = {}

for mz in sorted(grupos.keys()):
    if mz == 'sin_macrozona':
        continue
    g = grupos[mz]
    n_total = sum(len(v) for v in g.values())
    if n_total < 20:
        continue

    p50_1 = p50(g.get(1, []))
    p50_2 = p50(g.get(2, []))
    p50_3 = p50(g.get(3, []))
    p50_4 = p50(g.get(4, []))

    if not p50_2:
        continue

    rat_1_2 = p50_1 / p50_2 if p50_1 else None
    rat_3_2 = p50_3 / p50_2 if p50_3 else None
    rat_4_2 = p50_4 / p50_2 if p50_4 else None

    def fmt(v, n):
        return f"${v:>7,.0f}" if v else f"{'—':>9}"
    def fmtr(v):
        return f"{v:>9.3f}" if v else f"{'—':>9}"

    print(f"{mz:<22} {n_total:>5} | {fmt(p50_1,1)} {fmt(p50_2,1)} {fmt(p50_3,1)} {fmt(p50_4,1)} | {fmtr(rat_1_2)} {fmtr(rat_3_2)} {fmtr(rat_4_2)}")

    resultados_mz[mz] = {
        'n': n_total,
        'p50_1': p50_1, 'p50_2': p50_2, 'p50_3': p50_3, 'p50_4': p50_4,
        'rat_1_2': rat_1_2, 'rat_3_2': rat_3_2, 'rat_4_2': rat_4_2,
        'n_1': len(g.get(1,[])), 'n_2': len(g.get(2,[])),
        'n_3': len(g.get(3,[])), 'n_4': len(g.get(4,[])),
    }

    if rat_1_2: all_ratios['1vs2'].append(rat_1_2)
    if rat_3_2: all_ratios['3vs2'].append(rat_3_2)
    if rat_4_2: all_ratios['4vs2'].append(rat_4_2)

# ============================================================
# RESUMEN GLOBAL: RATIO PROMEDIO EN TODA LA CIUDAD
# ============================================================
import numpy as np

print("\n" + "=" * 90)
print("RATIOS GLOBALES EN TODA ROSARIO (ponderados por N)")
print("(Mediana de 2 dormitorios = 1.00 como referencia)")
print("=" * 90)

# Calcular con todas las ventas sin segmentar por macrozona
all_vm2 = defaultdict(list)
for p in ventas:
    all_vm2[int(p['dormitorios'])].append(float(p['valor_m2']))

p50_global = {d: p50(all_vm2[d]) for d in [1,2,3,4]}

print(f"\n{'Tipologia':<12} {'N':>6} {'P25 $/m2':>10} {'P50 $/m2':>10} {'P75 $/m2':>10} {'Ratio vs 2d':>12}")
print("-" * 65)
for d in [1, 2, 3, 4]:
    vals = all_vm2[d]
    v25, v50, v75 = p25(vals), p50(vals), p75(vals)
    rat = v50 / p50_global[2] if v50 and p50_global[2] else None
    rat_str = f"{rat:>11.3f}x" if rat else "—"
    print(f"{d}d {'depto':<6} {len(vals):>6} ${v25:>8,.0f}  ${v50:>8,.0f}  ${v75:>8,.0f}  {rat_str}")

print("\n")

# Factor entre tipologias adjacentes
r12 = p50_global[1] / p50_global[2] if p50_global[1] and p50_global[2] else None
r23 = p50_global[2] / p50_global[3] if p50_global[2] and p50_global[3] else None
r34 = p50_global[3] / p50_global[4] if p50_global[3] and p50_global[4] else None

print(f"Diferencia real entre tipologias (ratio P50):")
print(f"  1d vs 2d: {r12:.3f}  (1d es {(r12-1)*100:+.1f}% vs 2d en $/m2)" if r12 else "")
print(f"  2d vs 3d: {r23:.3f}  (2d es {(r23-1)*100:+.1f}% vs 3d en $/m2)" if r23 else "")
print(f"  3d vs 4d: {r34:.3f}  (3d es {(r34-1)*100:+.1f}% vs 4d en $/m2)" if r34 else "")

print(f"\n  -> Factor empirico por salto de dormitorios:")
print(f"     1 nivel de dorm = {( (r12-1)+(r23-1)+(r34-1) )/3 * 100:.1f}% promedio" if r12 and r23 and r34 else "")
print(f"     Factor actual hardcodeado: 8.0% por nivel <- comparar contra el dato real arriba")

# ============================================================
# VARIANZA POR MACROZONA: QUE TAN CONSISTENTE ES EL FACTOR?
# ============================================================
print("\n" + "=" * 90)
print("VARIANZA DEL RATIO 1d/2d POR MACROZONA (¿es consistente la diferencia?)")
print("=" * 90)

r12_vals = all_ratios['1vs2']
r32_vals = all_ratios['3vs2']
r42_vals = all_ratios['4vs2']

if r12_vals:
    print(f"\nRatio 1d/2d -> Media={np.mean(r12_vals):.3f} | Std={np.std(r12_vals):.3f} | Min={min(r12_vals):.3f} | Max={max(r12_vals):.3f}")
if r32_vals:
    print(f"Ratio 3d/2d -> Media={np.mean(r32_vals):.3f} | Std={np.std(r32_vals):.3f} | Min={min(r32_vals):.3f} | Max={max(r32_vals):.3f}")
if r42_vals:
    print(f"Ratio 4d/2d -> Media={np.mean(r42_vals):.3f} | Std={np.std(r42_vals):.3f} | Min={min(r42_vals):.3f} | Max={max(r42_vals):.3f}")

print("\nConclusion:")
if r12_vals and r32_vals:
    cv_12 = np.std(r12_vals) / np.mean(r12_vals)
    cv_32 = np.std(r32_vals) / np.mean(r32_vals)
    if cv_12 < 0.12:
        print(f"  1d/2d: CV={cv_12:.2f} -> Ratio CONSISTENTE en toda la ciudad (puede usarse factor global)")
    else:
        print(f"  1d/2d: CV={cv_12:.2f} -> Ratio VARIABLE por zona (necesita factor por macrozona)")
    if cv_32 < 0.12:
        print(f"  3d/2d: CV={cv_32:.2f} -> Ratio CONSISTENTE en toda la ciudad")
    else:
        print(f"  3d/2d: CV={cv_32:.2f} -> Ratio VARIABLE por zona")

"""
Simulate dynamic gap exclusion vs current formula.
Re-runs engine for each property, captures intermediate values,
and compares both formulas against stored valuations.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.mercado_inmobiliario import obtener_mediana_cluster_v2, calcular_m2_equivalentes, normalizar_zona
from datetime import datetime

# Load properties
with open('propiedades.json', 'r', encoding='utf-8') as f:
    propiedades_data = json.load(f)

# Load cache_scraping once
cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache_scraping.json')
with open(cache_path, 'r', encoding='utf-8') as f:
    cache_scraping = json.load(f)

print("=" * 120)
print("DYNAMIC GAP EXCLUSION SIMULATION")
print("=" * 120)
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Properties: {len(propiedades_data['propiedades'])}")
print()

# Results table header
print(f"{'Property':>18} {'Stored':>10} {'Current':>10} {'P33_same':>10} {'P33_cross':>10} {'Gap%':>7} {'n_same':>7} {'n_cross':>7} {'NewFormula':>10} {'Delta%':>8}")
print("-" * 120)

results = []

for prop in propiedades_data['propiedades']:
    nombre = prop['nombre']
    uv = prop.get('_ultima_valuacion', {})
    stored = uv.get('auto_valor_usd', 0)
    stored_m2b = uv.get('m2_base_venta', 0)
    
    # Property params
    zona = prop.get('zona', 'Centro')
    dorms = prop.get('dormitorios', 2)
    lat = prop.get('lat')
    lon = prop.get('lon')
    m2_cub = prop.get('m2_cubiertos', 0)
    anio_const = prop.get('anio_construccion', 2020)
    retro_dias = uv.get('retro_dias', 0)
    flex_dorm = uv.get('flex_dormitorios', None)
    
    # Calculate m2_equivalentes
    m2_equiv = calcular_m2_equivalentes(prop)
    
    # Run engine to get intermediate values
    try:
        valor, muestras, meta = obtener_mediana_cluster_v2(
            zona=normalizar_zona(zona),
            dormitorios=dorms,
            operacion='venta',
            lat_ref=lat,
            lon_ref=lon,
            fecha_ref=datetime.now().strftime('%Y-%m-%d'),
            anio_sujeto=anio_const,
            tipo_inmueble=prop.get('tipo_inmueble', 'departamento'),
            cache_scraping=cache_scraping,
            retro_dias=retro_dias,
            flex_dormitorios=flex_dorm,
            m2_equiv=m2_equiv,
            ancla_id=None
        )
    except Exception as e:
        print(f"{nombre:>18} ERROR: {e}")
        continue
    
    # Extract intermediate values
    pct_same = meta.get('pct_same', None)
    pct_cross = meta.get('pct_cross', None)
    n_same = meta.get('n_same_side', 0)
    n_cross = meta.get('n_cross_soft', 0)
    n_total = n_same + n_cross
    barrier_pct = meta.get('barrier_pct', 0)
    current_m2 = valor
    
    # Calculate current USD
    current_usd = current_m2 * m2_equiv if current_m2 and m2_equiv else 0
    
    # Calculate gap
    if pct_same and pct_cross and pct_same > 0:
        gap = (pct_same - pct_cross) / pct_same
    else:
        gap = 0
    
    # PROPOSED FORMULA: Dynamic exclusion by gap
    if pct_same is None:
        new_m2 = current_m2  # No change if no same-side data
    elif gap > 0.20:
        # HARD barrier (>20% gap): exclude cross entirely
        new_m2 = pct_same
    elif gap > 0.10:
        # MODERATE barrier (10-20% gap): reduced penalty
        blend = 0.70 * pct_same + 0.30 * pct_cross if pct_cross else pct_same
        penalty = gap * 0.5  # Half the gap
        new_m2 = blend * (1 - penalty)
    else:
        # NONE/WEAK (<10% gap): current blend is fine
        new_m2 = current_m2
    
    new_usd = new_m2 * m2_equiv if new_m2 and m2_equiv else 0
    
    # Calculate delta
    delta_pct = ((new_usd - stored) / stored * 100) if stored > 0 else 0
    
    # Print row
    gap_pct_str = f"{gap*100:.1f}%" if gap else "N/A"
    pct_same_str = f"${pct_same:,.0f}" if pct_same else "N/A"
    pct_cross_str = f"${pct_cross:,.0f}" if pct_cross else "N/A"
    print(f"{nombre:>18} ${stored:>9,.0f} ${current_usd:>9,.0f} {pct_same_str:>10} {pct_cross_str:>10} {gap_pct_str:>7} {n_same:>7} {n_cross:>7} ${new_usd:>9,.0f} {delta_pct:>+7.1f}%")
    
    results.append({
        'nombre': nombre,
        'stored': stored,
        'current_usd': current_usd,
        'pct_same': pct_same,
        'pct_cross': pct_cross,
        'gap': gap,
        'n_same': n_same,
        'n_cross': n_cross,
        'new_usd': new_usd,
        'delta_pct': delta_pct,
        'barrier_pct': barrier_pct,
    })

# Summary
print()
print("=" * 120)
print("SUMMARY")
print("=" * 120)

total_stored = sum(r['stored'] for r in results)
total_current = sum(r['current_usd'] for r in results)
total_new = sum(r['new_usd'] for r in results)

print(f"Total Stored:    ${total_stored:>12,.0f}")
print(f"Total Current:   ${total_current:>12,.0f} ({(total_current-total_stored)/total_stored*100:+.1f}% vs stored)")
print(f"Total New:       ${total_new:>12,.0f} ({(total_new-total_stored)/total_stored*100:+.1f}% vs stored)")
print()

# Gap distribution
print("Gap Distribution:")
gaps = [r['gap'] for r in results if r['gap'] is not None and r['gap'] > 0]
hard = sum(1 for g in gaps if g > 0.20)
moderate = sum(1 for g in gaps if 0.10 < g <= 0.20)
weak = sum(1 for g in gaps if g <= 0.10)
print(f"  HARD (>20%):     {hard} properties")
print(f"  MODERATE (10-20%): {moderate} properties")
print(f"  WEAK (<10%):     {weak} properties")
print()

# Detailed per-property analysis
print("=" * 120)
print("DETAILED ANALYSIS")
print("=" * 120)
for r in results:
    print(f"\n{r['nombre']}:")
    print(f"  Stored: ${r['stored']:,.0f}")
    print(f"  Current: ${r['current_usd']:,.0f}")
    pct_same_str = f"${r['pct_same']:,.0f}" if r['pct_same'] else "N/A"
    pct_cross_str = f"${r['pct_cross']:,.0f}" if r['pct_cross'] else "N/A"
    print(f"  P33_same: {pct_same_str}, P33_cross: {pct_cross_str}")
    print(f"  Gap: {r['gap']*100:.1f}% | n_same: {r['n_same']}, n_cross: {r['n_cross']}")
    print(f"  Barrier_pct: {r['barrier_pct']*100:.2f}%")
    if r['gap'] and r['gap'] > 0.20:
        print(f"  -> HARD BARRIER: Excluding cross, using P33_same=${r['pct_same']:,.0f}")
    elif r['gap'] and r['gap'] > 0.10:
        print(f"  -> MODERATE: Reduced penalty ({r['gap']*50:.1f}% vs current {r['barrier_pct']*100:.2f}%)")
    else:
        print(f"  -> WEAK/NONE: No change needed")
    print(f"  New: ${r['new_usd']:,.0f} ({r['delta_pct']:+.1f}% vs stored)")

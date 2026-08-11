"""
Simulate valuations with corrected barriers.
Uses barreras_rosario_corrected.json instead of original.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Temporarily patch the barrier loading to use corrected file
import parsers.location_engine as le
original_cargar_barreras = le.cargar_barreras

def patched_cargar_barreras():
    """Load corrected barriers instead of original."""
    corrected_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'barreras_rosario_corrected.json')
    if os.path.exists(corrected_path):
        with open(corrected_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get('features', [])
    return original_cargar_barreras()

le.cargar_barreras = patched_cargar_barreras

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
print("VALUACIONES CON BARRERAS CORREGIDAS")
print("=" * 120)
print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Barriers: 529 (corrected: 27-Feb=HARD, Pellegrini/Oroño=REMOVED)")
print()

# Results table header
print(f"{'Property':>18} {'Stored':>10} {'Old':>10} {'New':>10} {'Delta%':>8} {'P33_same':>10} {'P33_cross':>10} {'Gap':>8} {'n_same':>7} {'n_cross':>7}")
print("-" * 120)

results = []

for prop in propiedades_data['propiedades']:
    nombre = prop['nombre']
    uv = prop.get('_ultima_valuacion', {})
    stored = uv.get('auto_valor_usd', 0)
    
    # Property params
    zona = prop.get('zona', 'Centro')
    dorms = prop.get('dormitorios', 2)
    lat = prop.get('lat')
    lon = prop.get('lon')
    m2_cub = prop.get('m2_cubiertos', 0)
    anio_const = prop.get('anio_construccion', 2020)
    retro_dias = uv.get('retro_dias', 0)
    flex_dorm = uv.get('flex_dormitorios', None)
    m2_equiv = uv.get('m2_equivalentes', 0)
    
    # Run engine with corrected barriers
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
    current_m2 = valor
    
    # Calculate USD
    current_usd = current_m2 * m2_equiv if current_m2 and m2_equiv else 0
    
    # Calculate gap
    if pct_same and pct_cross and pct_same > 0:
        gap = (pct_same - pct_cross) / pct_same
    else:
        gap = 0
    
    # Delta vs stored
    delta_pct = ((current_usd - stored) / stored * 100) if stored > 0 else 0
    
    # Print row
    gap_str = f"{gap*100:+.1f}%" if gap else "N/A"
    pct_same_str = f"${pct_same:,.0f}" if pct_same else "N/A"
    pct_cross_str = f"${pct_cross:,.0f}" if pct_cross else "N/A"
    print(f"{nombre:>18} ${stored:>9,.0f} ${stored:>9,.0f} ${current_usd:>9,.0f} {delta_pct:>+7.1f}% {pct_same_str:>10} {pct_cross_str:>10} {gap_str:>8} {n_same:>7} {n_cross:>7}")
    
    results.append({
        'nombre': nombre,
        'stored': stored,
        'new_usd': current_usd,
        'delta_pct': delta_pct,
        'pct_same': pct_same,
        'pct_cross': pct_cross,
        'gap': gap,
        'n_same': n_same,
        'n_cross': n_cross,
    })

# Summary
print()
print("=" * 120)
print("RESUMEN")
print("=" * 120)

total_stored = sum(r['stored'] for r in results)
total_new = sum(r['new_usd'] for r in results)

print(f"Total Stored:    ${total_stored:>12,.0f}")
print(f"Total New:       ${total_new:>12,.0f} ({(total_new-total_stored)/total_stored*100:+.1f}%)")
print(f"Diferencia:      ${total_new-total_stored:>+12,.0f}")
print()

# Gap analysis
print("Gap Analysis:")
for r in results:
    if r['gap'] and r['gap'] > 0:
        print(f"  {r['nombre']}: +{r['gap']*100:.1f}% (cross más barato)")
    elif r['gap'] and r['gap'] < 0:
        print(f"  {r['nombre']}: {r['gap']*100:.1f}% (cross más caro)")

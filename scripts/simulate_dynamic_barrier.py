"""
Dynamic Barrier Penalty Simulation — Compare static 3% vs dynamic gap-based vs IDW.
Uses real engine functions (obtener_mediana_cluster_v2, _precio_ajustado).
"""
import json
import math
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.mercado_inmobiliario import (
    _precio_ajustado, calcular_m2_equivalentes,
    normalizar_zona, calcular_distancia_km, _calcular_percentil_linear,
    _calcular_mediana, obtener_mediana_cluster_v2
)
from parsers.cluster_filters import seleccionar_percentil_por_calidad_pool, _calcular_cv
from parsers.zonas_manager import resolver_macrozona

ANIO_ACTUAL = datetime.now().year


def idw_weighted_pct(comps, dist_power=2, percentile=33):
    """IDW-weighted percentile: weight by 1/d^power, then find percentile of weighted values."""
    if not comps:
        return None
    items = []
    for c in comps:
        precio = c['precio_normalizado']
        dist = max(c['dist_m'], 1.0)
        weight = 1.0 / (dist ** dist_power)
        items.append((precio, weight))
    items.sort(key=lambda x: x[0])
    total_w = sum(w for _, w in items)
    target = total_w * (percentile / 100.0)
    cum_w = 0
    for val, w in items:
        cum_w += w
        if cum_w >= target:
            return val
    return items[-1][0]


def compute_dynamic_penalty(pct_same, pct_cross, n_same, n_cross, n_total):
    """
    Dynamic penalty based on observed price gap between same-side and cross comps.
    
    Formula:
      gap_ratio = (pct_same - pct_cross) / pct_same
      max_penalty = gap_ratio * 0.5  (use 50% of observed gap — conservative)
      penalty = min(max_penalty, 0.15) * (n_cross / n_total)
    
    Rationale:
      - If cross comps are 30% cheaper, the barrier IS significant → bigger penalty
      - If cross comps are similar price, barrier is NOT significant → small penalty
      - Cap at 15% to avoid over-penalizing in edge cases
      - Scale by fraction of comps that cross (more cross = more impact)
    """
    if pct_same is None or pct_cross is None or pct_same <= 0 or n_total <= 0 or n_cross <= 0:
        return 0.0
    
    gap_ratio = (pct_same - pct_cross) / pct_same
    
    # Only penalize if cross comps are CHEAPER (gap_ratio > 0)
    # If cross comps are MORE EXPENSIVE, no penalty (barrier doesn't suppress prices)
    if gap_ratio <= 0:
        return 0.0
    
    max_penalty = gap_ratio * 0.5  # conservative: use 50% of observed gap
    max_penalty = min(max_penalty, 0.15)  # cap at 15%
    penalty = max_penalty * (n_cross / n_total)
    
    return penalty


def compute_static_penalty(n_cross, n_total):
    """Current static 3% max penalty."""
    if n_total <= 0 or n_cross <= 0:
        return 0.0
    return (n_cross / n_total) * 0.03


def compute_dynamic_alpha(pct_same, pct_cross, n_same):
    """
    Dynamic alpha based on observed price gap direction.
    
    Current system always favors same-side (alpha 0.50-0.70 based on count).
    Problem: when cross comps are MORE EXPENSIVE, blend pulls DOWN the result.
    
    New logic:
      - If cross CHEAPER (barrier suppresses prices) → favor same-side MORE (alpha high)
      - If cross MORE EXPENSIVE (no barrier effect) → favor cross MORE (alpha low)
      - If gap near zero → default alpha based on count
    
    This prevents double-penalizing: blend already handles barrier via weighting,
    so barrier penalty on top is redundant.
    """
    # Default alpha based on count (same as current)
    if n_same >= 15: default_alpha = 0.70
    elif n_same >= 8: default_alpha = 0.60
    elif n_same >= 5: default_alpha = 0.55
    else: default_alpha = 0.50
    
    if pct_same is None or pct_cross is None or pct_same <= 0:
        return default_alpha
    
    gap_pct = (pct_same - pct_cross) / pct_same
    
    if gap_pct > 0.05:
        # Cross is significantly CHEAPER → barrier matters → favor same MORE
        # Scale alpha up: 0.70 + up to 0.15 based on gap
        return min(0.70 + gap_pct * 0.5, 0.85)
    elif gap_pct < -0.05:
        # Cross is significantly MORE EXPENSIVE → no barrier → favor cross MORE
        # Scale alpha down: 0.50 - up to 0.15 based on gap (floor at 0.40)
        return max(0.50 + gap_pct * 0.5, 0.40)
    else:
        return default_alpha


def main():
    print("Loading cache...")
    with open("cache_scraping.json", "r", encoding="utf-8") as f:
        cache = json.load(f)

    with open("propiedades.json", "r", encoding="utf-8") as f:
        props_json = json.load(f)
    if isinstance(props_json, dict):
        props_json = props_json.get('propiedades', [])
    props = [p for p in props_json if p and isinstance(p, dict) and p.get('nombre')]

    print(f"Cache: {len(cache.get('propiedades', []))} props. Evaluando: {len(props)}\n")

    results = []

    for prop in props:
        nombre = prop.get('nombre', '?')
        dorm = prop.get('dormitorios', 0)
        m2 = prop.get('m2_cubiertos', 0)
        year = prop.get('anio_construccion', 0)
        lat = prop.get('lat')
        lon = prop.get('lon')
        zona = prop.get('zona', '')
        tipo = prop.get('tipo_inmueble', 'departamento')

        uv = prop.get('_ultima_valuacion') or {}
        auto_stored = uv.get('auto_valor_usd', 0) or 0
        m2b_stored = uv.get('m2_base_venta', 0) or 0
        retro_dias = uv.get('retro_dias', 0) or 0
        flex_dorm = uv.get('flex_dormitorios')

        if not lat or not lon:
            print(f"{nombre}: sin coordenadas, skip")
            continue

        m2eq = calcular_m2_equivalentes(prop)

        # 1. Get pool from real engine
        m2_base_raw, n_v, meta = obtener_mediana_cluster_v2(
            zona=normalizar_zona(zona),
            dormitorios=dorm,
            operacion='venta',
            lat_ref=float(lat),
            lon_ref=float(lon),
            fecha_ref=datetime.now().strftime('%Y-%m-%d'),
            anio_sujeto=year,
            tipo_inmueble=tipo,
            cache_scraping=cache,
            retro_dias=retro_dias,
            flex_dormitorios=flex_dorm,
            m2_equiv=m2eq,
            ancla_id=None
        )

        pool = meta.get('_pool_final', [])
        if not pool:
            print(f"{nombre}: pool vacio (n_v={n_v})")
            continue

        # 2. Resolve macrozona
        macrozona_id = None
        try:
            _mz = resolver_macrozona({'zona': zona, 'lat': float(lat), 'lon': float(lon)})
            macrozona_id = _mz.get('macrozona_id')
        except:
            pass

        # 3. Normalize comps with real _precio_ajustado + distance
        lat_suj = float(lat)
        lon_suj = float(lon)
        comps_norm = []
        for c in pool:
            p_lat = c.get('lat') or c.get('latitud')
            p_lon = c.get('lon') or c.get('longitud')
            if not p_lat or not p_lon:
                continue
            try:
                dist_m = calcular_distancia_km(lat_suj, lon_suj, float(p_lat), float(p_lon)) * 1000
            except:
                continue
            precio_norm = _precio_ajustado(
                c, macrozona_id=macrozona_id, ancla_id=None,
                dormitorios_sujeto=dorm
            )
            comps_norm.append({
                'precio_normalizado': precio_norm,
                'dist_m': dist_m,
                '_cross_soft': c.get('_cross_soft', False),
            })

        n_total = len(comps_norm)
        n_same = sum(1 for c in comps_norm if not c['_cross_soft'])
        n_cross = sum(1 for c in comps_norm if c['_cross_soft'])

        # 4. Compute percentile for same and cross (using dynamic percentile like engine)
        same_prices = sorted([c['precio_normalizado'] for c in comps_norm if not c['_cross_soft']])
        cross_prices = sorted([c['precio_normalizado'] for c in comps_norm if c['_cross_soft']])

        # Select percentile dynamically based on pool quality (same logic as engine)
        _cv_pool = _calcular_cv(same_prices) if len(same_prices) >= 3 else 0.3
        _cv_ref = 0.339
        percentil_venta, _ = seleccionar_percentil_por_calidad_pool(len(same_prices), _cv_pool, cv_ref=_cv_ref)

        pct_same = _calcular_percentil_linear(same_prices, percentil_venta) if len(same_prices) >= 2 else None
        pct_cross = _calcular_percentil_linear(cross_prices, percentil_venta) if len(cross_prices) >= 2 else None

        # Alpha (same-side weight)
        if n_same >= 15: alpha = 0.70
        elif n_same >= 8: alpha = 0.60
        elif n_same >= 5: alpha = 0.55
        else: alpha = 0.50

        # Blend P33
        if pct_same is not None and pct_cross is not None:
            blend_vm2 = alpha * pct_same + (1 - alpha) * pct_cross
        elif pct_same is not None:
            blend_vm2 = pct_same
        else:
            blend_vm2 = 0

        # --- Method 1: Current static 3% ---
        static_penalty = compute_static_penalty(n_cross, n_total)
        static_vm2 = blend_vm2 * (1 - static_penalty) if blend_vm2 > 0 else 0

        # --- Method 2: Dynamic gap-based ---
        dynamic_penalty = compute_dynamic_penalty(pct_same, pct_cross, n_same, n_cross, n_total)
        dynamic_vm2 = blend_vm2 * (1 - dynamic_penalty) if blend_vm2 > 0 else 0

        # --- Method 3: No barrier (baseline) ---
        no_barrier_vm2 = blend_vm2

        # --- Method 4: IDW power=2 ---
        idw_p2 = idw_weighted_pct(comps_norm, dist_power=2, percentile=percentil_venta)

        # --- Method 5: IDW power=1.5 ---
        idw_p15 = idw_weighted_pct(comps_norm, dist_power=1.5, percentile=percentil_venta)

        # --- Method 6: Dynamic with floor (never less than 1% when cross > 0) ---
        dynamic_floor_penalty = max(dynamic_penalty, 0.01) if n_cross > 0 else 0
        dynamic_floor_vm2 = blend_vm2 * (1 - dynamic_floor_penalty) if blend_vm2 > 0 else 0

        # --- Method 7: Dynamic alpha (gap-based blend) + dynamic penalty ---
        dyn_alpha = compute_dynamic_alpha(pct_same, pct_cross, n_same)
        if pct_same is not None and pct_cross is not None:
            dyn_alpha_blend = dyn_alpha * pct_same + (1 - dyn_alpha) * pct_cross
        elif pct_same is not None:
            dyn_alpha_blend = pct_same
        else:
            dyn_alpha_blend = 0
        dyn_alpha_vm2 = dyn_alpha_blend * (1 - dynamic_penalty) if dyn_alpha_blend > 0 else 0

        # --- Method 8: Dynamic alpha ONLY (no penalty) ---
        dyn_alpha_only_vm2 = dyn_alpha_blend

        # 6. USD values
        current_usd = m2eq * static_vm2  # current engine value
        static_usd = m2eq * static_vm2
        dynamic_usd = m2eq * dynamic_vm2
        no_barrier_usd = m2eq * no_barrier_vm2
        idw_p2_usd = m2eq * (idw_p2 or 0)
        idw_p15_usd = m2eq * (idw_p15 or 0)
        dynamic_floor_usd = m2eq * dynamic_floor_vm2
        dyn_alpha_usd = m2eq * dyn_alpha_vm2
        dyn_alpha_only_usd = m2eq * dyn_alpha_only_vm2

        # Gap info
        if pct_same and pct_cross and pct_same > 0:
            gap_pct = ((pct_same - pct_cross) / pct_same) * 100
        else:
            gap_pct = 0

        radio = meta.get('radio_usado')

        results.append({
            'nombre': nombre, 'dorm': dorm, 'm2': m2, 'm2eq': m2eq,
            'year': year, 'n_total': n_total, 'n_same': n_same, 'n_cross': n_cross,
            'radio': radio, 'macrozona': macrozona_id, 'retro': retro_dias,
            'auto_stored': auto_stored, 'm2b_stored': m2b_stored,
            'pct_same': pct_same, 'pct_cross': pct_cross, 'gap_pct': gap_pct,
            'static_penalty': static_penalty, 'static_usd': static_usd,
            'dynamic_penalty': dynamic_penalty, 'dynamic_usd': dynamic_usd,
            'no_barrier_usd': no_barrier_usd,
            'idw_p2_usd': idw_p2_usd, 'idw_p15_usd': idw_p15_usd,
            'dynamic_floor_penalty': dynamic_floor_penalty, 'dynamic_floor_usd': dynamic_floor_usd,
            'dyn_alpha': dyn_alpha, 'dyn_alpha_usd': dyn_alpha_usd,
            'dyn_alpha_only_usd': dyn_alpha_only_usd,
        })

    # === TABLE ===
    print("\n" + "=" * 200)
    print("DYNAMIC BARRIER + DYNAMIC ALPHA SIMULATION — ALL PROPERTIES")
    print("=" * 200)
    print("Methods: Static 3% | Dynamic Gap | No Barrier | IDW-p2 | IDW-p15 | DynAlpha+DynPen | DynAlpha Only")
    print("=" * 200)

    hdr = (f"{'Prop':<18} {'D':>2} {'m2':>5} {'N':>3} {'S':>3} {'X':>3} {'Gap%':>6} "
           f"{'Stored':>10} {'Static':>10} {'Dyn':>10} {'NoB':>10} {'IDW2':>10} {'IDW15':>10} "
           f"{'DynA+P':>10} {'DynA':>10} "
           f"{'S_Pen':>6} {'D_Pen':>6} {'DynA':>5}")
    print(hdr)
    print("-" * 200)

    t_store = t_stat = t_dyn = t_nob = t_idw2 = t_idw15 = t_dynf = t_dynap = t_dyna = 0
    for r in results:
        s = r['auto_stored']
        st = r['static_usd']
        dy = r['dynamic_usd']
        nb = r['no_barrier_usd']
        i2 = r['idw_p2_usd']
        i15 = r['idw_p15_usd']
        df = r['dynamic_floor_usd']
        dap = r['dyn_alpha_usd']
        da = r['dyn_alpha_only_usd']
        t_store += s; t_stat += st; t_dyn += dy; t_nob += nb; t_idw2 += i2; t_idw15 += i15; t_dynf += df; t_dynap += dap; t_dyna += da

        def fmt(v):
            return f"${v:,.0f}" if v else "$0"

        def pen_pct(p):
            return f"{p*100:.1f}%" if p else "0%"

        print(f"{r['nombre']:<18} {r['dorm']:>2} {r['m2']:>5} {r['n_total']:>3} {r['n_same']:>3} {r['n_cross']:>3} {r['gap_pct']:>5.1f}% "
              f"{fmt(s):>10} {fmt(st):>10} {fmt(dy):>10} {fmt(nb):>10} {fmt(i2):>10} {fmt(i15):>10} "
              f"{fmt(dap):>10} {fmt(da):>10} "
              f"{pen_pct(r['static_penalty']):>6} {pen_pct(r['dynamic_penalty']):>6} {r['dyn_alpha']:.2f}")

    print("-" * 200)
    print(f"{'TOTAL':<18} {'':>2} {'':>5} {'':>3} {'':>3} {'':>3} {'':>6} "
          f"{fmt(t_store):>10} {fmt(t_stat):>10} {fmt(t_dyn):>10} {fmt(t_nob):>10} {fmt(t_idw2):>10} {fmt(t_idw15):>10} "
          f"{fmt(t_dynap):>10} {fmt(t_dyna):>10}")

    # Delta vs stored
    print("\n" + "=" * 120)
    print("DELTA vs STORED (auto_valor_usd)")
    print("=" * 120)
    hdr2 = f"{'Prop':<18} {'Stored':>10} | {'Static':>10} {'d%':>7} | {'DynA+P':>10} {'d%':>7} | {'IDW-p2':>10} {'d%':>7} | {'DynA':>10} {'d%':>7}"
    print(hdr2)
    print("-" * 120)
    for r in results:
        s = r['auto_stored']
        if s <= 0:
            continue
        st_d = ((r['static_usd'] / s) - 1) * 100
        dap_d = ((r['dyn_alpha_usd'] / s) - 1) * 100
        i2_d = ((r['idw_p2_usd'] / s) - 1) * 100
        da_d = ((r['dyn_alpha_only_usd'] / s) - 1) * 100
        print(f"{r['nombre']:<18} {fmt(s):>10} | {fmt(r['static_usd']):>10} {st_d:>+6.1f}% | {fmt(r['dyn_alpha_usd']):>10} {dap_d:>+6.1f}% | {fmt(r['idw_p2_usd']):>10} {i2_d:>+6.1f}% | {fmt(r['dyn_alpha_only_usd']):>10} {da_d:>+6.1f}%")

    # Summary stats
    print("\n" + "=" * 120)
    print("PENALTY + ALPHA ANALYSIS")
    print("=" * 120)
    for r in results:
        if r['n_cross'] == 0:
            continue
        print(f"{r['nombre']:<18}: gap={r['gap_pct']:.1f}% | static={r['static_penalty']*100:.2f}% | dynamic={r['dynamic_penalty']*100:.2f}% "
              f"| alpha={r['dyn_alpha']:.2f} | same_P33=${r['pct_same']:.0f} cross_P33=${r['pct_cross']:.0f}")


if __name__ == '__main__':
    main()

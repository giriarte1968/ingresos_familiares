"""
Comparacion REAL: Motor actual (blend+barrier) vs IDW gradient.
Usa obtener_mediana_cluster_v2 con los MISMOS params que el UV stored.
Luego aplica IDW sobre el pool_final que el motor ya selecciono.
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
    obtener_mediana_cluster_v2
)
from parsers.zonas_manager import resolver_macrozona

ANIO_ACTUAL = datetime.now().year


def idw_weighted_p33(comps, dist_power=2):
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
    target = total_w * 0.33
    cum_w = 0
    for val, w in items:
        cum_w += w
        if cum_w >= target:
            return val
    return items[-1][0]


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
        comp_excluded = uv.get('_comp_excluded') or []

        if not lat or not lon:
            print(f"{nombre}: sin coordenadas, skip")
            continue

        m2eq = calcular_m2_equivalentes(prop)

        # 1. Llamar al motor con los MISMOS params del stored
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

        # 2. Resolver macrozona
        macrozona_id = None
        try:
            _mz = resolver_macrozona({'zona': zona, 'lat': float(lat), 'lon': float(lon)})
            macrozona_id = _mz.get('macrozona_id')
        except:
            pass

        # 3. Aplicar _precio_ajustado REAL + distancia
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

        # 4. METODO ACTUAL: blend P33 same/cross + barrier
        same_prices = sorted([c['precio_normalizado'] for c in comps_norm if not c['_cross_soft']])
        cross_prices = sorted([c['precio_normalizado'] for c in comps_norm if c['_cross_soft']])

        pct_same = _calcular_percentil_linear(same_prices, 33) if len(same_prices) >= 2 else None
        pct_cross = _calcular_percentil_linear(cross_prices, 33) if len(cross_prices) >= 2 else None

        if n_same >= 15: alpha = 0.70
        elif n_same >= 8: alpha = 0.60
        elif n_same >= 5: alpha = 0.55
        else: alpha = 0.50

        if pct_same is not None and pct_cross is not None:
            current_vm2 = alpha * pct_same + (1 - alpha) * pct_cross
        elif pct_same is not None:
            current_vm2 = pct_same
        else:
            current_vm2 = 0

        if n_total > 0 and n_cross > 0:
            barrier_pct = (n_cross / n_total) * 0.03
            current_vm2 = current_vm2 * (1 - barrier_pct)

        # 5. METODO IDW: misma normalizacion, ponderacion por distancia
        idw_p2 = idw_weighted_p33(comps_norm, dist_power=2)
        idw_p15 = idw_weighted_p33(comps_norm, dist_power=1.5)

        # 6. Valores USD
        current_usd = m2eq * current_vm2
        idw_p2_usd = m2eq * (idw_p2 or 0)
        idw_p15_usd = m2eq * (idw_p15 or 0)

        radio = meta.get('radio_usado')

        results.append({
            'nombre': nombre, 'dorm': dorm, 'm2': m2, 'm2eq': m2eq,
            'year': year, 'n_total': n_total, 'n_same': n_same, 'n_cross': n_cross,
            'radio': radio, 'macrozona': macrozona_id, 'retro': retro_dias,
            'flex': flex_dorm is not None,
            'auto_stored': auto_stored, 'm2b_stored': m2b_stored,
            'current_vm2': current_vm2, 'current_usd': current_usd,
            'idw_p2_vm2': idw_p2, 'idw_p2_usd': idw_p2_usd,
            'idw_p15_vm2': idw_p15, 'idw_p15_usd': idw_p15_usd,
        })

    # === TABLA RESUMEN ===
    print("=" * 140)
    print("VALUACIONES REALES: Motor Actual (blend+barrier) vs IDW Gradient")
    print("Mismos params del stored (retro, flex), mismos comps, misma normalizacion, distinta ponderacion")
    print("=" * 140)

    hdr = f"{'Prop':<18} {'D':>2} {'m2':>5} {'m2eq':>5} {'N':>4} {'Same':>4} {'X':>3} {'Radio':>5} {'Retro':>5} {'Flex':>4} | {'Stored':>10} {'Current':>10} {'IDW-p2':>10} {'IDW-p15':>10} | {'d2':>7} {'d15':>7}"
    print(hdr)
    print("-" * 140)

    t_stored = t_curr = t_idw2 = t_idw15 = 0
    for r in results:
        s, c, i2, i15 = r['auto_stored'], r['current_usd'], r['idw_p2_usd'], r['idw_p15_usd']
        t_stored += s; t_curr += c; t_idw2 += i2; t_idw15 += i15
        d2 = ((i2/c)-1)*100 if c else 0
        d15 = ((i15/c)-1)*100 if c else 0
        flex_str = 'Y' if r['flex'] else 'N'
        radio_str = f"{r['radio']}m" if r['radio'] else '?'
        print(f"{r['nombre']:<18} {r['dorm']:>2} {r['m2']:>5} {r['m2eq']:>5.0f} {r['n_total']:>4} {r['n_same']:>4} {r['n_cross']:>3} {radio_str:>5} {r['retro']:>4}d {flex_str:>4} | {s:>10,.0f} {c:>10,.0f} {i2:>10,.0f} {i15:>10,.0f} | {d2:>+6.1f}% {d15:>+6.1f}%")

    print("-" * 140)
    dt2 = ((t_idw2/t_curr)-1)*100 if t_curr else 0
    dt15 = ((t_idw15/t_curr)-1)*100 if t_curr else 0
    print(f"{'TOTAL':<18} {'':>2} {'':>5} {'':>5} {'':>4} {'':>4} {'':>3} {'':>5} {'':>5} {'':>4} | {t_stored:>10,.0f} {t_curr:>10,.0f} {t_idw2:>10,.0f} {t_idw15:>10,.0f} | {dt2:>+6.1f}% {dt15:>+6.1f}%")

    print()
    print("=== m2_base por metodo ===")
    print(f"{'Prop':<18} {'Stored':>10} {'Current':>10} {'IDW-p2':>10} {'IDW-p15':>10}")
    for r in results:
        print(f"{r['nombre']:<18} {r['m2b_stored']:>10.0f} {r['current_vm2']:>10.0f} {r['idw_p2_vm2'] or 0:>10.0f} {r['idw_p15_vm2'] or 0:>10.0f}")


if __name__ == '__main__':
    main()

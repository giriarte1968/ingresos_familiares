#!/usr/bin/env python3
"""
Diagnóstico comparativo del fallback del age-filter (FASE 4A).

Compara 3 estrategias: ventanas progresivas (A), mínimo flexible (B), blend (C).
NO modifica código productivo. Solo genera reporte.

Uso:
    python scripts/diagnostico_age_filter_fallback.py

Salida:
    Reporte tabular en consola.
"""
import json
import os
import math
import sys
from datetime import datetime
from typing import List, Dict, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# Import enrichment function from production (read-only, not modifying)
import importlib
prod_module = importlib.import_module("parsers.mercado_inmobiliario")
enriquecer_anio_comparable = prod_module.enriquecer_anio_comparable
calcular_distancia_km = prod_module.calcular_distancia_km

CACHE_PATH = os.path.join(REPO_ROOT, "cache_scraping.json")
PROPS_PATH = os.path.join(REPO_ROOT, "propiedades.json")

ANIO_ACTUAL = datetime.now().year
RADIOS_PROGRESIVOS = [300, 500, 800, 1000, 1500]
MIN_COMPARABLES = 10
MIN_COMPARABLES_FALLBACK = 5


# ── Helpers de distancia (Haversine) ──────────────────────────────────
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


# ── Helpers de cluster (replican parsers/cluster_filters.py) ──────────
def filtrar_por_radio(props, lat_ref, lon_ref, radio_m):
    result = []
    radio_km = radio_m / 1000
    for p in props:
        p_lat = p.get("lat") or p.get("latitud")
        p_lon = p.get("lon") or p.get("longitud")
        if p_lat is None or p_lon is None:
            continue
        try:
            dist = haversine_km(lat_ref, lon_ref, float(p_lat), float(p_lon))
            if dist <= radio_km:
                result.append(p)
        except Exception:
            continue
    return result


def filtrar_por_tipo_operacion_dorms(props, tipo=None, operacion=None, dormitorios=None, tolerancia_dorms=1):
    result = []
    for p in props:
        if tipo:
            p_tipo = str(p.get("tipo", p.get("tipo_inmueble", "")))
            if not p_tipo or tipo.lower() not in p_tipo.lower():
                continue
        if operacion:
            p_oper = str(p.get("operacion", ""))
            if not p_oper or operacion.lower() not in p_oper.lower():
                continue
        if dormitorios is not None:
            p_dorms = p.get("dormitorios")
            if p_dorms is None:
                continue
            if abs(int(p_dorms) - dormitorios) > tolerancia_dorms:
                continue
        result.append(p)
    return result


def filtrar_por_fecha(props, fecha_ref_str, dias=180):
    if not fecha_ref_str:
        return props
    try:
        fecha_ref_dt = datetime.strptime(fecha_ref_str, "%Y-%m-%d")
        from datetime import timedelta
        fecha_limite = fecha_ref_dt - timedelta(days=dias)
        result = []
        for p in props:
            date_upd = p.get("date_updated", "")
            if not date_upd:
                continue
            try:
                dt = datetime.strptime(date_upd[:10], "%Y-%m-%d")
                if fecha_limite <= dt <= fecha_ref_dt:
                    result.append(p)
            except Exception:
                continue
        return result
    except Exception:
        return props


def aplicar_filtro_fecha(props, fecha_filtro):
    if not fecha_filtro:
        return props
    props_180 = filtrar_por_fecha(props, fecha_filtro, dias=180)
    if len(props_180) >= 5:
        return props_180
    props_365 = filtrar_por_fecha(props, fecha_filtro, dias=365)
    return props_365


def calcular_percentil(precios, percentil):
    if not precios:
        return None
    s = sorted(precios)
    n = len(s)
    idx = int(n * percentil / 100)
    idx = min(idx, n - 1)
    idx = max(idx, 0)
    return float(s[idx])


def calcular_blend_p33(p33_same, p33_cross, alpha=0.70):
    if p33_same is not None and p33_cross is not None:
        return alpha * p33_same + (1 - alpha) * p33_cross
    elif p33_same is not None:
        return p33_same
    elif p33_cross is not None:
        return p33_cross
    return None


def seleccionar_percentil_por_edad(age_filter_applied, n_age_filtered):
    if not age_filter_applied:
        return 33, "P33"
    if n_age_filtered >= 20:
        return 50, "P50_age"
    elif n_age_filtered >= 10:
        return 45, "P45_age"
    elif n_age_filtered >= 8:
        return 40, "P40_age"
    else:
        return 33, "P33"


# ── Age-filter actual (replica _filtrar_por_ventana_edad) ─────────────
def age_filter_actual(pool, anio_sujeto, ventana=15, min_con_anio=10, min_n=8):
    """Estrategia actual: ±15 → ±30 → pool completo (min_n=8)."""
    if not anio_sujeto:
        return pool, False, 0, 0, 0
    pool_con_anio = [p for p in pool if p.get("anio_estimado")]
    if len(pool_con_anio) < min_con_anio:
        return pool, False, 0, 0, 0
    for ventana_actual in [ventana, 30]:
        anio_min = anio_sujeto - ventana_actual
        anio_max = anio_sujeto + ventana_actual
        pool_filtered = [p for p in pool_con_anio if anio_min <= p["anio_estimado"] <= anio_max]
        if len(pool_filtered) >= min_n:
            return pool_filtered, True, len(pool_filtered), anio_min, anio_max
    return pool, False, 0, 0, 0


# ── Estrategia A: Ventanas progresivas ────────────────────────────────
def age_filter_estrategia_a(pool, anio_sujeto, min_con_anio=10, min_n=8):
    """±10 → ±15 → ±20 → ±30 → pool completo."""
    if not anio_sujeto:
        return pool, False, 0, 0, 0, "N/A"
    pool_con_anio = [p for p in pool if p.get("anio_estimado")]
    if len(pool_con_anio) < min_con_anio:
        return pool, False, 0, 0, 0, "pool_completo"
    for ventana in [10, 15, 20, 30]:
        anio_min = anio_sujeto - ventana
        anio_max = anio_sujeto + ventana
        pool_filtered = [p for p in pool_con_anio if anio_min <= p["anio_estimado"] <= anio_max]
        if len(pool_filtered) >= min_n:
            return pool_filtered, True, len(pool_filtered), anio_min, anio_max, f"±{ventana}"
    return pool, False, 0, 0, 0, "pool_completo"


# ── Estrategia B: Mínimo flexible ─────────────────────────────────────
def age_filter_estrategia_b(pool, anio_sujeto, ventana=15, min_con_anio=10, min_n=5):
    """±15 → ±30 → pool completo, con min_n=5."""
    if not anio_sujeto:
        return pool, False, 0, 0, 0
    pool_con_anio = [p for p in pool if p.get("anio_estimado")]
    if len(pool_con_anio) < min_con_anio:
        return pool, False, 0, 0, 0
    for ventana_actual in [ventana, 30]:
        anio_min = anio_sujeto - ventana_actual
        anio_max = anio_sujeto + ventana_actual
        pool_filtered = [p for p in pool_con_anio if anio_min <= p["anio_estimado"] <= anio_max]
        if len(pool_filtered) >= min_n:
            return pool_filtered, True, len(pool_filtered), anio_min, anio_max
    return pool, False, 0, 0, 0


# ── Estrategia C: Blend con pool completo ─────────────────────────────
def age_filter_estrategia_c(pool, anio_sujeto, ventana=15, min_con_anio=10, min_n=8):
    """
    Si n_age_filtered < 8 pero > 0, hace blend entre pool filtrado y pool total.
    alpha = n_age_filtered / 8 (cap en 1.0).
    """
    if not anio_sujeto:
        return pool, False, 0, 0, 0, 1.0
    pool_con_anio = [p for p in pool if p.get("anio_estimado")]
    if len(pool_con_anio) < min_con_anio:
        return pool, False, 0, 0, 0, 1.0
    for ventana_actual in [ventana, 30]:
        anio_min = anio_sujeto - ventana_actual
        anio_max = anio_sujeto + ventana_actual
        pool_filtered = [p for p in pool_con_anio if anio_min <= p["anio_estimado"] <= anio_max]
        n_f = len(pool_filtered)
        if n_f >= min_n:
            return pool_filtered, True, n_f, anio_min, anio_max, 1.0
        if n_f > 0:
            # Blend: usar pool filtrado + pool total
            alpha = min(1.0, n_f / 8.0)
            return pool_filtered, True, n_f, anio_min, anio_max, alpha
    return pool, False, 0, 0, 0, 1.0


# ── Simulación de cluster ────────────────────────────────────────────
def simular_cluster(cache, prop, operacion="venta", fecha_ref=None):
    """
    Replica la lógica de obtener_mediana_cluster_v2 para diagnóstico.
    Retorna (pool_unicos, radio_usado, meta_dict).
    """
    if fecha_ref is None:
        fecha_ref = datetime.now().strftime("%Y-%m-%d")

    lat = prop.get("lat")
    lon = prop.get("lon")
    zona = prop.get("zona", "")
    dorms = prop.get("dormitorios", 2)
    anio_sujeto = prop.get("anio_construccion")
    tipo_inmueble = prop.get("tipo_inmueble", "departamento")

    todas = cache.get("propiedades", [])

    mejor_resultado = None
    radio_usado = None

    if lat is not None and lon is not None:
        for radio in RADIOS_PROGRESIVOS:
            props_geo = filtrar_por_radio(todas, lat, lon, radio)
            props_geo = filtrar_por_tipo_operacion_dorms(
                props_geo, tipo=tipo_inmueble, operacion=operacion, dormitorios=dorms, tolerancia_dorms=0
            )
            props_geo = [p for p in props_geo if p.get("valor_m2", 0) > 0]
            props_geo = aplicar_filtro_fecha(props_geo, fecha_ref)
            if len(props_geo) >= MIN_COMPARABLES:
                mejor_resultado = (props_geo, radio)
                radio_usado = radio
                break
        else:
            # Fallback: 1500m sin umbral
            props_geo = []
            for p in todas:
                p_lat = p.get("lat") or p.get("latitud")
                p_lon = p.get("lon") or p.get("longitud")
                if not (p_lat and p_lon):
                    continue
                dist = haversine_km(lat, lon, float(p_lat), float(p_lon))
                if dist > 1.5:
                    continue
                if p.get("dormitorios") != dorms:
                    continue
                if p.get("operacion") != operacion:
                    continue
                if p.get("valor_m2", 0) <= 0:
                    continue
                if tipo_inmueble and tipo_inmueble not in str(p.get("tipo", p.get("tipo_inmueble", ""))).lower():
                    continue
                props_geo.append(p)
            props_geo = aplicar_filtro_fecha(props_geo, fecha_ref)
            if len(props_geo) >= 2:
                mejor_resultado = (props_geo, 1500)
                radio_usado = 1500

    if mejor_resultado is None:
        return [], None, {"error": "sin datos"}

    props, radio_usado = mejor_resultado

    # Dedup basico
    seen = set()
    unicos = []
    for p in props:
        key = (int(p.get("precio", 0)), int(p.get("m2", 0)), p.get("zona", ""))
        if key not in seen:
            seen.add(key)
            unicos.append(p)

    # Enriquecer con anyo (replica paso FASE 1 del motor productivo)
    for comp in unicos:
        if comp.get("anio_construccion") or comp.get("anio_estimado"):
            continue
        try:
            enriq = enriquecer_anio_comparable(comp)
            if enriq:
                comp["anio_estimado"] = enriq["anio_estimado"]
                comp["anio_confianza"] = enriq.get("confianza", "BAJA")
        except Exception:
            pass

    return unicos, radio_usado, {}


# ── Calcular valor base desde pool ──────────────────────────────────
def calcular_base(pool_final, age_filter_applied, n_age_filtered, operacion="venta"):
    """Replica el cálculo de percentil + blend de obtener_mediana_cluster_v2."""
    precios = [p["valor_m2"] for p in pool_final if p.get("valor_m2", 0) > 0]
    if not precios:
        return 0, {}, 0, 0

    n_raw = len(precios)

    # IQR + filtro robusto
    import numpy as np
    mediana_raw = np.median(precios)
    lower_robust = mediana_raw * 0.6
    upper_robust = mediana_raw * 1.6
    precios_filt = [p for p in precios if lower_robust <= p <= upper_robust]

    if len(precios_filt) < 3:
        precios_ord = sorted(precios)
        q1 = np.percentile(precios_ord, 25)
        q3 = np.percentile(precios_ord, 75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        precios_filt = [p for p in precios if lower <= p <= upper]

    precios_filt = precios_filt or precios

    # Separar same/cross
    precios_same = [p["valor_m2"] for p in pool_final if not p.get("_cross_soft") and p.get("valor_m2", 0) > 0]
    precios_cross = [p["valor_m2"] for p in pool_final if p.get("_cross_soft") and p.get("valor_m2", 0) > 0]

    # Percentil
    if operacion == "alquiler":
        percentil_venta = 50
        percentil_usado = "P50_alquiler"
    else:
        percentil_venta, percentil_usado = seleccionar_percentil_por_edad(age_filter_applied, n_age_filtered)

    pct_same = calcular_percentil(precios_same, percentil_venta)
    pct_cross = calcular_percentil(precios_cross, percentil_venta)

    # Percentiles del cluster
    precios_todos = precios_same + precios_cross
    if len(precios_todos) >= 4:
        p25 = float(np.percentile(precios_todos, 25))
        p33 = float(np.percentile(precios_todos, 33))
        p50 = float(np.percentile(precios_todos, 50))
        p75 = float(np.percentile(precios_todos, 75))
    else:
        p25 = p33 = p50 = p75 = None

    # Blends
    ALPHA_CONS = 0.70
    ALPHA_MKT = 0.60

    if pct_same is not None and pct_cross is not None:
        blend_cons = calcular_blend_p33(pct_same, pct_cross, alpha=ALPHA_CONS)
        blend_mkt = calcular_blend_p33(pct_same, pct_cross, alpha=ALPHA_MKT)
        ratio = pct_cross / pct_same if pct_same > 0 else 1.0
        if ratio <= 1.05:
            alpha_opt = 0.70
        elif ratio <= 1.15:
            alpha_opt = 0.60
        else:
            alpha_opt = 0.55
        alpha_opt = max(0.55, min(0.70, alpha_opt))
        blend_opt = calcular_blend_p33(pct_same, pct_cross, alpha=alpha_opt)
        valor_principal = blend_cons
    elif len(precios_todos) >= 4:
        valor_principal = p33 if p33 else p50
        blend_cons = blend_mkt = blend_opt = valor_principal
    else:
        valor_principal = pct_same if pct_same else (pct_cross if pct_cross else p50)
        blend_cons = blend_mkt = blend_opt = valor_principal

    meta = {
        "n_raw": n_raw,
        "n_filtradas": len(precios_filt),
        "percentil_usado": percentil_usado,
        "pct_same": pct_same,
        "pct_cross": pct_cross,
        "p25_cluster": p25,
        "p33_cluster": p33,
        "p50_cluster": p50,
        "p75_cluster": p75,
        "blend_cons": blend_cons,
        "blend_mkt": blend_mkt,
        "blend_opt": blend_opt,
        "n_same": len(precios_same),
        "n_cross": len(precios_cross),
    }

    return valor_principal, meta, n_raw, len(precios_filt)


# ── Cargar datos ────────────────────────────────────────────────────
def cargar_cache():
    if not os.path.exists(CACHE_PATH):
        print(f"ERROR: No se encuentra {CACHE_PATH}")
        sys.exit(1)
    with open(CACHE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def cargar_props():
    if not os.path.exists(PROPS_PATH):
        print(f"ERROR: No se encuentra {PROPS_PATH}")
        sys.exit(1)
    with open(PROPS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "propiedades" in data:
        return data["propiedades"]
    return data if isinstance(data, list) else [data]


# ── Diagnóstico principal ────────────────────────────────────────────
def diagnosticar(cache, props, fecha_ref=None):
    if fecha_ref is None:
        fecha_ref = datetime.now().strftime("%Y-%m-%d")

    resultados = []

    for prop in props:
        nombre = prop.get("nombre", "?").strip()
        anio = prop.get("anio_construccion")
        dorms = prop.get("dormitorios", 2)
        zona = prop.get("zona", "")
        tipo = prop.get("tipo_inmueble", "?")

        print(f"\n{'=' * 72}")
        print(f"  PROPIEDAD: {nombre}  ({tipo}, {anio}, {dorms}d, {zona})")
        print(f"{'=' * 72}")

        # 1. Obtener pool base (cluster geográfico)
        pool, radio, _ = simular_cluster(cache, prop, operacion="venta", fecha_ref=fecha_ref)
        if not pool:
            print("  ⚠ Sin datos de cluster. Saltando.")
            continue

        n_total = len(pool)
        pool_con_anio = [p for p in pool if p.get("anio_estimado")]
        n_con_anio = len(pool_con_anio)

        print(f"  Pool total: {n_total} props, con anyo: {n_con_anio}")
        print(f"  Radio usado: {radio}m")

        # -- ESTRATEGIA ACTUAL --
        pool_act, age_on_act, n_age_act, lo_act, hi_act = age_filter_actual(
            pool, anio, ventana=15, min_con_anio=10, min_n=8
        )
        pct_act, pct_label = seleccionar_percentil_por_edad(age_on_act, n_age_act)
        val_act, meta_act, _, _ = calcular_base(pool_act, age_on_act, n_age_act)
        ventana_act = f"{lo_act}-{hi_act}" if age_on_act else "N/A"

        print(f"\n  -- ACTUAL --")
        print(f"     age_filter_applied: {age_on_act}  |  n_age: {n_age_act}  |  ventana: {ventana_act}")
        print(f"     percentil: {pct_label}  |  m2_base: ${val_act:.2f}")
        print(f"     fallback: {'SI (pool completo)' if not age_on_act else 'NO - age-filter activo'}")

        # -- ESTRATEGIA A: Ventanas progresivas --
        pool_a, age_on_a, n_age_a, lo_a, hi_a, ventana_a = age_filter_estrategia_a(
            pool, anio, min_con_anio=10, min_n=8
        )
        if age_on_a:
            pct_a, pct_a_label = seleccionar_percentil_por_edad(True, n_age_a)
            val_a, meta_a, _, _ = calcular_base(pool_a, True, n_age_a)
        else:
            pct_a, pct_a_label = 33, "P33_fallback"
            val_a, meta_a, _, _ = calcular_base(pool, False, 0)
        print(f"\n  -- ESTRATEGIA A (ventanas progresivas) --")
        print(f"     ventana elegida: {ventana_a}  |  n_age: {n_age_a}")
        print(f"     percentil: {pct_a_label}  |  m2_base: ${val_a:.2f}")

        # -- ESTRATEGIA B: Minimo flexible n>=5 --
        pool_b, age_on_b, n_age_b, lo_b, hi_b = age_filter_estrategia_b(
            pool, anio, ventana=15, min_con_anio=10, min_n=5
        )
        if age_on_b:
            pct_b, pct_b_label = seleccionar_percentil_por_edad(True, n_age_b)
            val_b, meta_b, _, _ = calcular_base(pool_b, True, n_age_b)
        else:
            pct_b, pct_b_label = 33, "P33_fallback"
            val_b, meta_b, _, _ = calcular_base(pool, False, 0)
        print(f"\n  -- ESTRATEGIA B (minimo flexible n>=5) --")
        print(f"     age_filter_applied: {age_on_b}  |  n_age: {n_age_b}")
        print(f"     percentil: {pct_b_label}  |  m2_base: ${val_b:.2f}")
        if age_on_b and not age_on_act:
            print(f"     ** Resuelve: ahora entra en filtro de edad (antes caia al pool completo) **")

        # -- ESTRATEGIA C: Blend --
        pool_c, age_on_c, n_age_c, lo_c, hi_c, blend_alpha = age_filter_estrategia_c(
            pool, anio, ventana=15, min_con_anio=10, min_n=8
        )
        if age_on_c:
            if blend_alpha < 1.0 and n_age_c > 0:
                pool_filtrado = pool_c
                pct_c_filt, pct_c_label_filt = seleccionar_percentil_por_edad(True, n_age_c)
                val_c_filt, meta_c_filt, _, _ = calcular_base(pool_filtrado, True, n_age_c)

                val_c_all, meta_c_all, _, _ = calcular_base(pool, False, 0)

                alpha = blend_alpha
                val_c = alpha * val_c_filt + (1 - alpha) * val_c_all
                blend_desc = f"blend a={alpha:.2f} (age={val_c_filt:.2f} x {alpha:.2f} + total={val_c_all:.2f} x {1 - alpha:.2f})"
                pct_c_label = f"blend_{alpha:.2f}"
            else:
                val_c, meta_c, _, _ = calcular_base(pool_c, True, n_age_c)
                pct_c_label = seleccionar_percentil_por_edad(True, n_age_c)[1]
                blend_desc = f"age-filter puro (n={n_age_c})"
        else:
            pct_c_label = "P33_fallback"
            val_c, meta_c, _, _ = calcular_base(pool, False, 0)
            blend_desc = "pool completo (fallback)"
        print(f"\n  -- ESTRATEGIA C (blend) --")
        print(f"     n_age: {n_age_c}  |  alpha: {blend_alpha:.2f}")
        print(f"     {blend_desc}")
        print(f"     m2_base: ${val_c:.2f}")

        # -- Diferencia vs Actual --
        print(f"\n  -- COMPARACION vs ACTUAL (${val_act:.2f}) --")
        diff_a = val_a - val_act if val_act else 0
        diff_b = val_b - val_act if val_act else 0
        diff_c = val_c - val_act if val_act else 0
        print(f"     Estr. A: ${val_a:.2f}  (diff ${diff_a:+.2f}, {diff_a / val_act * 100:+.2f}%)" if val_act else "")
        print(f"     Estr. B: ${val_b:.2f}  (diff ${diff_b:+.2f}, {diff_b / val_act * 100:+.2f}%)" if val_act else "")
        print(f"     Estr. C: ${val_c:.2f}  (diff ${diff_c:+.2f}, {diff_c / val_act * 100:+.2f}%)" if val_act else "")

        resultados.append({
            "nombre": nombre,
            "anio": anio,
            "dorms": dorms,
            "zona": zona,
            "n_total": n_total,
            "n_con_anio": n_con_anio,
            # Actual
            "act_age_on": age_on_act,
            "act_n_age": n_age_act,
            "act_ventana": ventana_act,
            "act_pct": pct_label,
            "act_valor": val_act,
            # A
            "a_ventana": ventana_a,
            "a_n_age": n_age_a,
            "a_pct": pct_a_label,
            "a_valor": val_a,
            # B
            "b_age_on": age_on_b,
            "b_n_age": n_age_b,
            "b_pct": pct_b_label,
            "b_valor": val_b,
            # C
            "c_alpha": blend_alpha,
            "c_n_age": n_age_c,
            "c_pct": pct_c_label,
            "c_valor": val_c,
        })

    return resultados


def imprimir_resumen(resultados):
    print(f"\n\n{'=' * 72}")
    print("  RESUMEN COMPARATIVO - AGE FILTER FALLBACK")
    print(f"{'=' * 72}")

    # Cabecera
    print(f"{'Propiedad':<16} {'Anyo':>4} {'Zona':<20} {'n_total':>8} {'n_con_anio':>10}")
    print(f"{'-' * 16} {'-' * 4} {'-' * 20} {'-' * 8} {'-' * 10}")
    for r in resultados:
        print(f"{r['nombre']:<16} {r['anio']:>4} {r['zona']:<20} {r['n_total']:>8} {r['n_con_anio']:>10}")
    print()

    # Tabla PASO 1: Actual
    print(f"{'=' * 72}")
    print("  PASO 1 - DIAGNOSTICO ACTUAL")
    print(f"{'=' * 72}")
    print(f"{'Propiedad':<16} {'Anyo':>4} {'n_total':>8} {'n_con_anio':>10} {'age_filt':>9} {'n_age':>5} {'%ile':>8} {'fallback?':>10} {'valor':>10}")
    print(f"{'-' * 16} {'-' * 4} {'-' * 8} {'-' * 10} {'-' * 9} {'-' * 5} {'-' * 8} {'-' * 10} {'-' * 10}")
    for r in resultados:
        fb = "SI" if not r["act_age_on"] else "NO"
        print(f"{r['nombre']:<16} {r['anio']:>4} {r['n_total']:>8} {r['n_con_anio']:>10} {str(r['act_age_on']):>9} {r['act_n_age']:>5} {r['act_pct']:>8} {fb:>10} ${r['act_valor']:>8.0f}")

    # Tabla PASO 2: Estrategia A
    print(f"\n{'=' * 72}")
    print("  PASO 2 - ESTRATEGIA A (Ventanas progresivas +-10 -> +-15 -> +-20 -> +-30)")
    print(f"{'=' * 72}")
    print(f"{'Propiedad':<16} {'ventana':>10} {'n_age':>5} {'%ile':>8} {'m2_base':>10} {'fallback?':>10}")
    print(f"{'-' * 16} {'-' * 10} {'-' * 5} {'-' * 8} {'-' * 10} {'-' * 10}")
    for r in resultados:
        fb_a = "NO" if r["a_ventana"] != "pool_completo" else "SI"
        print(f"{r['nombre']:<16} {r['a_ventana']:>10} {r['a_n_age']:>5} {r['a_pct']:>8} ${r['a_valor']:>8.0f} {fb_a:>10}")

    # Tabla PASO 3: Estrategia B
    print(f"\n{'=' * 72}")
    print("  PASO 3 - ESTRATEGIA B (Minimo flexible n>=5)")
    print(f"{'=' * 72}")
    print(f"{'Propiedad':<16} {'age_on':>7} {'n_age':>5} {'%ile':>8} {'m2_base':>10} {'nuevo?':>10} {'vs_actual':>10}")
    print(f"{'-' * 16} {'-' * 7} {'-' * 5} {'-' * 8} {'-' * 10} {'-' * 10} {'-' * 10}")
    for r in resultados:
        es_nuevo = "SI" if (r["b_age_on"] and not r["act_age_on"]) else ("=" if r["b_age_on"] == r["act_age_on"] else "?")
        diff_b = r["b_valor"] - r["act_valor"]
        print(f"{r['nombre']:<16} {str(r['b_age_on']):>7} {r['b_n_age']:>5} {r['b_pct']:>8} ${r['b_valor']:>8.0f} {es_nuevo:>10} {diff_b:>+9.0f}")

    # Tabla PASO 4: Estrategia C
    print(f"\n{'=' * 72}")
    print("  PASO 4 - ESTRATEGIA C (Blend con pool completo)")
    print(f"{'=' * 72}")
    print(f"{'Propiedad':<16} {'n_age':>5} {'alpha':>7} {'m2_base':>10} {'tipo':>18}")
    print(f"{'-' * 16} {'-' * 5} {'-' * 7} {'-' * 10} {'-' * 18}")
    for r in resultados:
        if r["c_alpha"] < 1.0 and r["c_n_age"] > 0:
            tipo_c = f"blend a={r['c_alpha']:.2f}"
        elif r["c_n_age"] >= 8:
            tipo_c = f"puro (n={r['c_n_age']})"
        else:
            tipo_c = "pool completo"
        print(f"{r['nombre']:<16} {r['c_n_age']:>5} {r['c_alpha']:>7.2f} ${r['c_valor']:>8.0f} {tipo_c:>18}")

    # Tabla PASO 5: Comparacion final
    print(f"\n{'=' * 72}")
    print("  PASO 5 - COMPARACION FINAL A vs B vs C")
    print(f"{'=' * 72}")
    print(f"{'Propiedad':<16} {'Actual':>10} {'Estr.A':>10} {'Estr.B':>10} {'Estr.C':>10} {'Comentario':>30}")
    print(f"{'-' * 16} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 30}")
    for r in resultados:
        comentarios = []
        if r["b_age_on"] and not r["act_age_on"]:
            comentarios.append("B resuelve!")
        if r["a_ventana"] == "+-10" and not r["act_age_on"]:
            comentarios.append("A gana prec.")
        comentario = "; ".join(comentarios) if comentarios else "similar"
        print(f"{r['nombre']:<16} ${r['act_valor']:>8.0f} ${r['a_valor']:>8.0f} ${r['b_valor']:>8.0f} ${r['c_valor']:>8.0f} {comentario:>30}")

    # Resumen de casos donde falla
    print(f"\n\n{'=' * 72}")
    print("  HALLAZGOS CLAVE")
    print(f"{'=' * 72}")
    fallbacks = [r for r in resultados if not r["act_age_on"]]
    sostenidos = [r for r in resultados if r["act_age_on"]]
    print(f"\n  Age-filter SOSTENIDO: {len(sostenidos)} propiedades")
    for r in sostenidos:
        print(f"    OK {r['nombre']:16}  n={r['act_n_age']:2d}  ventana={r['act_ventana']}  Pct={r['act_pct']}")
    print(f"\n  Age-filter CAIDO (fallback al pool completo): {len(fallbacks)} propiedades")
    for r in fallbacks:
        print(f"    FAIL {r['nombre']:16}  n_con_anio={r['n_con_anio']:2d}  n_age_actual={r['act_n_age']:2d}  (min 8 necesario)")
    print()

    # Vulnerabilidad por zona
    print(f"\n  VULNERABILIDAD POR ZONA/TIPO:")
    for r in resultados:
        riesgo = "ALTO" if not r["act_age_on"] else "BAJO"
        print(f"    {r['nombre']:16}  zona={r['zona']:20}  anyo={r['anio']:4d}  riesgo={riesgo}")


if __name__ == "__main__":
    print("Cargando datos...")
    cache = cargar_cache()
    props = cargar_props()
    print(f"Cache: {len(cache.get('propiedades', []))} propiedades")
    print(f"Propiedades a diagnosticar: {len(props)}")

    fecha_ref = datetime.now().strftime("%Y-%m-%d")
    resultados = diagnosticar(cache, props, fecha_ref=fecha_ref)
    imprimir_resumen(resultados)

    print(f"\n{'=' * 72}")
    print("  DIAGNÓSTICO COMPLETADO")
    print(f"{'=' * 72}")

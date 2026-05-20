"""
Módulo de auditoría técnica para valuaciones AVM.

Genera un log estructurado y persistente por cada valuación,
permitiendo trazabilidad completa de inputs, parámetros y resultados.
"""
import json
import os
from datetime import datetime

AUDIT_LOGS_DIR = "data/history/audit_logs"


def generar_audit_log(propiedad, resultado, f_dict, meta_venta, n_v, m2_base_venta_raw,
                      meta_alq, n_a, es_ventana3, m2_equiv_alquiler, factores_alquiler,
                      m2_base_alquiler, ajuste_nlp, nlp_cap, resolution_metadata, rango_venta,
                      comparables_venta):
    """
    Construye un audit_log estructurado a partir de datos ya calculados.
    NO recalcula nada. Solo reempaqueta valores existentes.
    """
    prop = propiedad
    nombre = prop.get('nombre', prop.get('direccion', 'Desconocida'))

    # Propiedad
    audit_prop = {
        "nombre": nombre,
        "zona": prop.get("zona", ""),
        "tipo_inmueble": prop.get("tipo_inmueble", prop.get("tipo", "")),
        "direccion": prop.get("direccion", ""),
        "lat": prop.get("lat"),
        "lon": prop.get("lon"),
        "anio_construccion": prop.get("anio_construccion"),
        "dormitorios": prop.get("dormitorios"),
        "estado_detalle": prop.get("estado_detalle", ""),
        "calidad_edificio": prop.get("calidad_edificio", ""),
        "piso": prop.get("piso"),
        "total_pisos": prop.get("total_pisos"),
        "ventilacion": prop.get("ventilacion", ""),
        "tipo_balcon": prop.get("tipo_balcon", ""),
        "ubicacion_tipo": prop.get("ubicacion_tipo", ""),
        "vista": prop.get("vista", ""),
        "orientacion": prop.get("orientacion", ""),
        "gas_ok": prop.get("gas_ok", ""),
        "antiguedad": prop.get("antiguedad"),
    }

    # Superficies
    m2_equiv = resultado.get("m2_equivalentes", 0)
    m2_cub = prop.get("m2_cubiertos", 0)
    m2_semi = prop.get("m2_semicubiertos", 0)
    m2_desc_prop = prop.get("m2_descubiertos_propios", prop.get("m2_descubiertos", 0))
    audit_sup = {
        "m2_cubiertos": m2_cub,
        "m2_semicubiertos": m2_semi,
        "m2_descubiertos_propios": m2_desc_prop,
        "m2_descubiertos_comun_exclusivo": prop.get("m2_descubiertos_comun_exclusivo", 0),
        "m2_comunes": prop.get("m2_comunes", 0),
        "m2_equiv": m2_equiv,
    }

    # Cluster venta
    meta = meta_venta or {}
    p33_same = meta.get("p33_same")
    p33_cross = meta.get("p33_cross")
    base_principal = meta.get("base_principal", resultado.get("m2_base_venta"))
    base_conservadora = meta.get("base_conservadora")
    base_mercado = meta.get("base_mercado")
    base_optimista = meta.get("base_optimista")

    audit_cluster = {
        "n_total_cluster": n_v,
        "n_con_anio": meta.get("n_con_anio_alta", 0) + meta.get("n_con_anio_media", 0),
        "pct_con_anio": meta.get("pct_con_anio"),
        "age_filter_applied": meta.get("age_filter_applied", False),
        "n_age_filtered": meta.get("n_age_filtered"),
        "rango_anio_usado": meta.get("rango_anio_usado", ""),
        "percentil_usado": meta.get("percentil_usado", ""),
        "p33_same": p33_same,
        "p33_cross": p33_cross,
        "base_principal": base_principal,
        "base_conservadora": base_conservadora,
        "base_mercado": base_mercado,
        "base_optimista": base_optimista,
        "alpha_principal": meta.get("alpha_principal"),
        "alpha_optimista": meta.get("alpha_optimista"),
        "age_blend_applied": meta.get("age_blend_applied", False),
        "alpha_age_blend": meta.get("alpha_age_blend"),
        "barrier_mode": meta.get("barrier_mode", ""),
        "n_same_side": meta.get("n_same_side"),
        "n_cross_soft": meta.get("n_cross_soft"),
        "radio_usado": meta.get("radio_usado"),
    }

    # Comparables usados (top 20)
    comps = []
    for c in (comparables_venta or [])[:20]:
        comps.append({
            "direccion": c.get("direccion", ""),
            "lat": c.get("lat"),
            "lon": c.get("lon"),
            "precio_m2": c.get("precio_m2", c.get("valor_m2")),
            "anio_estimado": c.get("anio_construccion"),
            "dist_m": c.get("distancia", c.get("dist_m")),
            "grupo": c.get("grupo", ""),
        })
    audit_cluster["comparables_usados"] = comps

    # Factores (solo los que están disponibles en f_dict)
    audit_factores = {
        "estado": f_dict.get("factor_estado"),
        "calidad": f_dict.get("factor_calidad"),
        "depreciacion": f_dict.get("depreciacion"),
        "suma_cruda": f_dict.get("suma_cruda"),
        "suma_cruda_raw": f_dict.get("suma_cruda_raw"),
        "f_estructural": f_dict.get("f_estructural"),
        "f_nlp": resultado.get("nlp_ajuste_pct", 0) / 100.0 + 1.0 if resultado.get("nlp_ajuste_pct") else 1.0,
        "nlp_bruto": ajuste_nlp,
        "nlp_cap_aplicado": nlp_cap,
        "nlp_neto": min(ajuste_nlp, nlp_cap) if ajuste_nlp is not None else 0,
        "es_ventana3": es_ventana3,
    }

    # Venta
    rango = rango_venta or resultado.get("rango_venta", {})
    audit_venta = {
        "valor_conservador": rango.get("min"),
        "valor_mercado": rango.get("mid"),
        "valor_optimista": rango.get("max"),
        "valor_principal": resultado.get("valor_propiedad_usd"),
        "spread_pct": rango.get("spread_pct"),
        "metodo_rango": rango.get("metodo_rango"),
        "margen_error": rango.get("margen_error"),
        "valor_realizable": resultado.get("valor_realizable_usd"),
        "m2_base_venta": resultado.get("m2_base_venta"),
        "m2_base_source": resolution_metadata.get("m2_base_source", ""),
    }

    # Alquiler
    alq_info = resultado.get("cap_rate_info", {})
    audit_alquiler = {
        "metodo_alquiler": resultado.get("metodo_alquiler", ""),
        "cap_rate": resultado.get("cap_rate"),
        "cap_rate_min": alq_info.get("cap_rate_min"),
        "cap_rate_max": alq_info.get("cap_rate_max"),
        "alq_mensual_ars": resultado.get("alquiler_estimado_ars"),
        "alq_rango_min": resultado.get("alquiler_rango", {}).get("min"),
        "alq_rango_max": resultado.get("alquiler_rango", {}).get("max"),
        "size_discount_alquiler": resultado.get("size_discount_alquiler"),
        "es_fallback_alquiler": resultado.get("es_fallback_alquiler"),
        "n_alquiler": alq_info.get("n_alquiler", n_a),
        "alq_m2_base": m2_base_alquiler,
        "m2_equiv_alquiler": m2_equiv_alquiler,
        "factores_alquiler": factores_alquiler,
        "gasto_mantenimiento_mensual": resultado.get("mantenimiento_mensual_ars"),
        "expensas_ars": resultado.get("expensas_ars"),
        "confianza": resultado.get("confianza_alquiler"),
    }

    # Final
    audit_final = {
        "valor_venta": resultado.get("valor_propiedad_usd"),
        "valor_realizable": resultado.get("valor_realizable_usd"),
        "alquiler_mensual_ars": resultado.get("alquiler_estimado_ars"),
        "plusvalia_usd": resultado.get("plusvalia_ciclo_usd"),
        "plusvalia_pct": resultado.get("plusvalia_ciclo_pct"),
        "plusvalia_tipo": resultado.get("plusvalia_tipo"),
        "cap_rate_neto_anual": resultado.get("cap_rate_anual"),
        "cap_rate_bruto_anual": resultado.get("cap_rate_bruto"),
        "dolar_usdt_ars": resultado.get("usdt_ars"),
    }

    return {
        "timestamp": datetime.now().isoformat(),
        "motor_version": "v7.0",
        "nombre": nombre,
        "propiedad": audit_prop,
        "superficies": audit_sup,
        "cluster_venta": audit_cluster,
        "factores": audit_factores,
        "venta": audit_venta,
        "alquiler": audit_alquiler,
        "final": audit_final,
        "resolution_metadata": resolution_metadata,
    }


def guardar_audit_log(audit_log):
    """
    Persiste un audit_log en data/history/audit_logs/.
    Cada propiedad tiene un historial de audit_logs.
    """
    nombre = audit_log.get("nombre", "desconocido").replace(" ", "_")
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs(AUDIT_LOGS_DIR, exist_ok=True)
    filename = f"{ts}__{nombre}.json"
    filepath = os.path.join(AUDIT_LOGS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(audit_log, f, ensure_ascii=False, indent=2, default=str)
    return filepath


def cargar_audit_logs(propiedad=None, limite=20):
    """
    Carga audit_logs desde data/history/audit_logs/.
    Filtra por nombre de propiedad si se especifica.
    Retorna lista ordenada por timestamp descendente.
    """
    if not os.path.exists(AUDIT_LOGS_DIR):
        return []
    logs = []
    for fname in os.listdir(AUDIT_LOGS_DIR):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(AUDIT_LOGS_DIR, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                log = json.load(f)
            if propiedad and log.get("nombre") != propiedad:
                continue
            logs.append((fname, log))
        except (json.JSONDecodeError, OSError):
            continue
    logs.sort(key=lambda x: x[1].get("timestamp", ""), reverse=True)
    return [(fname, log) for fname, log in logs[:limite]]


def obtener_ultimo_audit_log(propiedad):
    """Retorna el audit_log más reciente para una propiedad."""
    logs = cargar_audit_logs(propiedad=propiedad, limite=1)
    return logs[0][1] if logs else None

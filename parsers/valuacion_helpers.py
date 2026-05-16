"""
Helpers para valuar_propiedad_v7. Funciones puras sin dependencias del motor.
Preparación para refactor seguro de valuar_propiedad_v7() (>550 líneas).
"""
import math
from typing import Optional, Dict, Any


ROI_ZONAL = {
    'centro': 0.048, 'martin': 0.048, 'pichincha': 0.050,
    'abasto': 0.052, 'facultades': 0.055, 'sexta': 0.055,
    'sur': 0.060, 'norte': 0.058, 'oeste': 0.060,
}


def calcular_rango_venta(
    m2_equiv: float,
    bases_venta: Dict[str, float],
    factor_total: float,
    ajuste_nlp: float = 0.0,
) -> Dict[str, Any]:
    """
    Calcula los 3 escenarios de venta (conservador, mercado, optimista).
    
    Args:
        m2_equiv: Metros cuadrados equivalentes
        bases_venta: Dict con 'conservadora', 'mercado', 'optimista' (USD/m²)
        factor_total: Factor total de ajuste
        ajuste_nlp: Ajuste por NLP (0.0-0.05)
    
    Returns:
        Dict con 'valor_principal', 'rango_venta' con llaves internas
    """
    base_cons = bases_venta.get('base_conservadora', bases_venta.get('conservadora', 0))
    base_mkt = bases_venta.get('base_mercado', bases_venta.get('mercado', 0))
    base_opt = bases_venta.get('base_optimista', bases_venta.get('optimista', 0))

    if not base_cons or not base_mkt:
        return {'valor_principal': 0, 'rango_venta': {}}

    valor_cons = m2_equiv * base_cons * factor_total * (1 + ajuste_nlp)
    valor_mkt = m2_equiv * base_mkt * factor_total * (1 + ajuste_nlp)
    valor_opt = m2_equiv * base_opt * factor_total * (1 + ajuste_nlp)

    # Asegurar orden conservador <= mercado <= optimista
    valores = sorted([valor_cons, valor_mkt, valor_opt])
    valor_cons, valor_mkt, valor_opt = valores

    # Spread relativo al valor de mercado
    spread_pct = ((valor_opt - valor_cons) / valor_mkt * 100) if valor_mkt > 0 else 0

    p25 = bases_venta.get('p25_cluster', 0)
    p50 = bases_venta.get('p50_cluster', base_mkt)
    p75 = bases_venta.get('p75_cluster', 0)

    rango = {
        'min': round(valor_cons, 0),
        'mid': round(valor_mkt, 0),
        'max': round(valor_opt, 0),
        'spread_pct': round(spread_pct, 1),
        'margen_error': round(spread_pct / 100, 3),
        'p25_cluster': round(p25, 2) if p25 else None,
        'p50_cluster': round(p50, 2) if p50 else None,
        'p75_cluster': round(p75, 2) if p75 else None,
        'metodo_rango': 'valor_estimado_mas_margen_estadistico',
    }

    return {
        'valor_principal': round(valor_mkt, 0),
        'rango_venta': rango,
    }


def procesar_alquiler(
    valor_venta: float,
    m2_equiv: float,
    m2_base_alquiler: float,
    factores_alquiler: float,
    gap_alquiler: float,
    usdt_ars: float,
    zona_txt: str,
    dorms: int,
    size_discount_fn=None,
    size_discount_params: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Procesa el alquiler con Cap Rate data-driven o fallback zonal.
    Aplica size discount si corresponde.
    
    Args:
        valor_venta: Valor de venta estimado (USD)
        m2_equiv: Metros cuadrados equivalentes
        m2_base_alquiler: Precio base de alquiler (ARS/m²)
        factores_alquiler: Factores de ajuste de alquiler
        gap_alquiler: GAP de alquiler (ej: 0.92)
        usdt_ars: Cotización USD/ARS
        zona_txt: Nombre de zona
        dorms: Cantidad de dormitorios
        size_discount_fn: Función de size discount (opcional)
        size_discount_params: Parámetros extra para size_discount_fn
    
    Returns:
        Dict con datos de alquiler
    """
    # Cálculo base de alquiler (fallback)
    alquiler_base_ars = m2_equiv * m2_base_alquiler * factores_alquiler * gap_alquiler

    # Size discount
    size_factor = 1.0
    if size_discount_fn:
        size_factor = size_discount_fn(m2_equiv, **(size_discount_params or {}))
    
    alquiler_ars = alquiler_base_ars * size_factor

    # Cap rate data-driven vs fallback
    cap_info_local = size_discount_params.get('cap_info_local') if size_discount_params else None

    if cap_info_local and not cap_info_local.get('es_fallback', True):
        cap_rate = cap_info_local['cap_rate']
        alq_usd = valor_venta * cap_rate / 12
        alq_ars = alq_usd * usdt_ars

        cap_min = cap_info_local.get('cap_rate_min', cap_rate * 0.90)
        cap_max = cap_info_local.get('cap_rate_max', cap_rate * 1.10)
        alq_min_ars = (valor_venta * cap_min / 12) * usdt_ars * size_factor
        alq_max_ars = (valor_venta * cap_max / 12) * usdt_ars * size_factor

        metodo = 'mercado_local'
        es_fallback = False
        confianza = cap_info_local.get('confianza', 'MEDIA')
    else:
        # Fallback zonal
        zona_key = zona_txt.lower().strip() if zona_txt else 'centro'
        cap_rate = ROI_ZONAL.get(zona_key, 0.052)
        alq_ars = alquiler_ars
        alq_min_ars = alq_ars * 0.85 * size_factor
        alq_max_ars = alq_ars * 1.15 * size_factor
        metodo = 'roi_zonal_fallback'
        es_fallback = True
        confianza = 'BAJA'

    if size_factor < 1.0:
        alq_min_ars *= size_factor
        alq_max_ars *= size_factor

    return {
        'alquiler_estimado_ars': round(alq_ars, 0),
        'alquiler_rango': {
            'min': round(alq_min_ars, 0),
            'max': round(alq_max_ars, 0),
        },
        'cap_rate': round(cap_rate, 4),
        'cap_info': cap_info_local if cap_info_local else {
            'cap_rate': cap_rate, 'metodo': metodo, 'confianza': confianza, 'es_fallback': es_fallback
        },
        'metodo_alquiler': metodo,
        'es_fallback_alquiler': es_fallback,
        'confianza_alquiler': confianza,
        'size_discount': round(1 - size_factor, 3) if size_factor < 1.0 else 0,
    }


def ensamblar_metadata_resolucion(
    meta_venta: Dict[str, Any],
    n_v: int,
    zona_txt: str,
) -> Dict[str, Any]:
    """
    Arma el diccionario 'resolution_metadata' para la UI.
    
    Args:
        meta_venta: Dict con metadata del cluster de venta
        n_v: Cantidad de propiedades en el cluster
        zona_txt: Nombre de zona
    
    Returns:
        Dict 'resolution_metadata' completo
    """
    radio_usado = meta_venta.get('radio_usado')

    if radio_usado:
        resolution = 'GEO'
        if n_v >= 15:
            confidence = 'ALTA'
        elif n_v >= 8:
            confidence = 'MEDIA'
        else:
            confidence = 'BAJA'
    elif n_v > 0:
        resolution = 'ZONAL'
        confidence = 'MEDIA'
    else:
        resolution = 'GLOBAL'
        confidence = 'BAJA'

    return {
        'resolution': resolution,
        'confidence': confidence,
        'method': 'cluster_v2',
        'n_propiedades': n_v,
        'radio_usado': radio_usado,
        'percentil_usado': meta_venta.get('percentil_usado'),
        'zona_resol': meta_venta.get('zona_resolucion'),
        'm2_base_source': meta_venta.get('fuente_rango', ''),
        'n_comparables_total': meta_venta.get('n_comparables_total', 0),
        'n_con_anio_alta': meta_venta.get('n_con_anio_alta', 0),
        'n_con_anio_media': meta_venta.get('n_con_anio_media', 0),
        'pct_con_anio': meta_venta.get('pct_con_anio', 0),
        'age_filter_applied': meta_venta.get('age_filter_applied', False),
        'age_window': meta_venta.get('age_window', ''),
        'n_age_filtered': meta_venta.get('n_age_filtered', 0),
        'rango_anio_usado': meta_venta.get('rango_anio_usado', ''),
        'comparables_reales': meta_venta.get('comparables_reales', []),
    }

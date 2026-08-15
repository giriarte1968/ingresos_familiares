"""
Módulo de Evaluación Financiera, NOI y CAPE Inmobiliario para Valu (TAREA-160).
Cálculo puro e inmutable de métricas de rentabilidad de inversión inmobiliaria.
"""

from typing import Dict, Any

def calcular_evaluacion_financiera(prop: Dict[str, Any], resultado_avm: Dict[str, Any], manual_params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Calcula el NOI (Ingreso Neto Operativo), CAPE Inmobiliario, Price-to-Rent Ratio
    y Retorno Total (TIR: Cap Rate Neto + Plusvalía) para una propiedad.

    Args:
        prop: Diccionario con datos de la propiedad (expensas_ars, etc.)
        resultado_avm: Resultado devuelto por valuar_propiedad_v7
        manual_params: Parámetros opcionales de simulación personalizada

    Returns:
        dict con métricas financieras estructuradas.
    """
    manual_params = manual_params or {}
    
    # 1. Base values (USD & ARS)
    valor_prop_usd = float(manual_params.get('valor_usd') or resultado_avm.get('valor_propiedad_usd', 0) or 0)
    usdt_ars = float(resultado_avm.get('usdt_ars', 1585.0) or 1585.0)
    
    # Alquiler mensual estimado en ARS
    alq_ars_mensual = float(manual_params.get('alquiler_ars') or resultado_avm.get('alquiler_estimado_ars', 0) or 0)
    alq_usd_mensual = alq_ars_mensual / usdt_ars if usdt_ars > 0 else 0.0
    
    alq_bruto_anual_usd = alq_usd_mensual * 12.0
    alq_bruto_anual_ars = alq_ars_mensual * 12.0
    
    # 2. Deducciones Operativas (NOI)
    # A. Vacancia y morosidad (Default: 4.0%)
    pct_vacancia = float(manual_params.get('pct_vacancia', 4.0))
    vacancia_anual_usd = alq_bruto_anual_usd * (pct_vacancia / 100.0)
    
    # B. Fondo de Reserva y Mantenimiento (Default: 0.5% del valor del inmueble/año)
    pct_mantenimiento = float(manual_params.get('pct_mantenimiento', 0.5))
    mantenimiento_anual_usd = valor_prop_usd * (pct_mantenimiento / 100.0)
    
    # C. Expensas a cargo del Propietario / Impuestos Locales
    expensas_ars_mensual = float(prop.get('expensas_ars', 0) or 0)
    # Asumimos que el 25% de las expensas (extraordinarias/fondos) corren por cuenta del propietario si no se desglosa
    expensas_prop_mensual_ars = float(manual_params.get('expensas_prop_ars', expensas_ars_mensual * 0.25))
    expensas_prop_anual_usd = (expensas_prop_mensual_ars * 12.0) / usdt_ars if usdt_ars > 0 else 0.0
    
    # D. Gastos de gestión/administración opcionales (Default: 0%)
    pct_administracion = float(manual_params.get('pct_administracion', 0.0))
    administracion_anual_usd = alq_bruto_anual_usd * (pct_administracion / 100.0)
    
    total_deducciones_anual_usd = (
        vacancia_anual_usd +
        mantenimiento_anual_usd +
        expensas_prop_anual_usd +
        administracion_anual_usd
    )
    
    # 3. NOI (Net Operating Income)
    noi_anual_usd = max(0.0, alq_bruto_anual_usd - total_deducciones_anual_usd)
    noi_anual_ars = noi_anual_usd * usdt_ars
    noi_mensual_usd = noi_anual_usd / 12.0
    noi_mensual_ars = noi_anual_ars / 12.0
    
    # 4. Múltiplos Financieros & Cap Rates
    # CAPE Inmobiliario = Valor Propiedad / NOI Anual
    cape_inmobiliario = (valor_prop_usd / noi_anual_usd) if noi_anual_usd > 0 else 0.0
    
    # Price-to-Rent Bruto = Valor Propiedad / Alquiler Bruto Anual
    price_to_rent_bruto = (valor_prop_usd / alq_bruto_anual_usd) if alq_bruto_anual_usd > 0 else 0.0
    
    # Cap Rate Bruto vs Cap Rate Neto
    cap_rate_bruto = (alq_bruto_anual_usd / valor_prop_usd * 100.0) if valor_prop_usd > 0 else 0.0
    cap_rate_neto = (noi_anual_usd / valor_prop_usd * 100.0) if valor_prop_usd > 0 else 0.0
    
    # 5. Plusvalía y Retorno Total (TIR)
    plusvalia_12m_pct = float(resultado_avm.get('plusvalia_12m_pct', 3.5) or 3.5)
    # Asegurar rango realista de plusvalía (entre 1.0% y 6.0% anual en USD)
    plusvalia_anual_estimada = max(1.0, min(6.0, plusvalia_12m_pct))
    
    retorno_total_tir = cap_rate_neto + plusvalia_anual_estimada
    
    # 6. Rango de Valor por Rentabilidad (Income Approach Valuation)
    # Múltiplos de mercado objetivo: 16.0x (Conservador / 6.25% net), 18.2x (Mercado / 5.50% net), 20.0x (Optimista / 5.00% net)
    valor_income_conservador = round(noi_anual_usd * 16.0, 0)
    valor_income_mercado = round(noi_anual_usd * 18.2, 0)
    valor_income_optimista = round(noi_anual_usd * 20.0, 0)
    
    # 7. Diagnóstico / Termómetro Financiero
    if cape_inmobiliario <= 0:
        diagnostico_cape = "SIN_DATOS"
        etiqueta_diagnostico = "Sin datos suficientes"
        color_diagnostico = "#6c757d"
    elif cape_inmobiliario < 15.0:
        diagnostico_cape = "OPORTUNIDAD"
        etiqueta_diagnostico = "Oportunidad de Alto Rendimiento (Barato en Múltiplo)"
        color_diagnostico = "#198754"
    elif cape_inmobiliario <= 20.0:
        diagnostico_cape = "FAIR_VALUE"
        etiqueta_diagnostico = "Valor Justo de Mercado (Equilibrado)"
        color_diagnostico = "#0d6efd"
    else:
        diagnostico_cape = "PREMIUM"
        etiqueta_diagnostico = "Múltiplo Exigente / Rendimiento Ajustado (Premium)"
        color_diagnostico = "#fd7e14"
        
    return {
        'valor_propiedad_usd': round(valor_prop_usd, 0),
        'usdt_ars': round(usdt_ars, 2),
        # P&L Operativo
        'alquiler_bruto_mensual_ars': round(alq_ars_mensual, 0),
        'alquiler_bruto_anual_usd': round(alq_bruto_anual_usd, 0),
        'vacancia_anual_usd': round(vacancia_anual_usd, 0),
        'mantenimiento_anual_usd': round(mantenimiento_anual_usd, 0),
        'expensas_prop_anual_usd': round(expensas_prop_anual_usd, 0),
        'administracion_anual_usd': round(administracion_anual_usd, 0),
        'total_deducciones_anual_usd': round(total_deducciones_anual_usd, 0),
        'noi_anual_usd': round(noi_anual_usd, 0),
        'noi_anual_ars': round(noi_anual_ars, 0),
        'noi_mensual_usd': round(noi_mensual_usd, 0),
        'noi_mensual_ars': round(noi_mensual_ars, 0),
        # Ratios Financieros
        'cape_inmobiliario': round(cape_inmobiliario, 1),
        'price_to_rent_bruto': round(price_to_rent_bruto, 1),
        'cap_rate_bruto': round(cap_rate_bruto, 2),
        'cap_rate_neto': round(cap_rate_neto, 2),
        'plusvalia_anual_estimada': round(plusvalia_anual_estimada, 2),
        'retorno_total_tir': round(retorno_total_tir, 2),
        # Income Approach Valuation
        'rango_income_approach': {
            'min': int(valor_income_conservador),
            'mid': int(valor_income_mercado),
            'max': int(valor_income_optimista),
        },
        # Diagnóstico
        'diagnostico_cape': diagnostico_cape,
        'etiqueta_diagnostico': etiqueta_diagnostico,
        'color_diagnostico': color_diagnostico,
    }

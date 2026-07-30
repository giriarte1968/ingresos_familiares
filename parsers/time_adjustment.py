"""Ajuste temporal (Ct) compartido entre generador de anclas y valuacion.
Lee configuracion de config/anclas_config.json.
"""
import re
from datetime import datetime

FECHA_REF_DEFAULT = datetime(2026, 6, 1)


def _get_cfg():
    try:
        from parsers.motor_vpp_core import load_anclas_config
        return load_anclas_config()
    except Exception:
        return {}


def get_ct_table():
    cfg = _get_cfg()
    return cfg.get('generator', {}).get('ct_table', [])


def get_ct_factors():
    cfg = _get_cfg()
    return cfg.get('generator', {}).get('ct_factors', {})


def get_natural_window_dias():
    cfg = _get_cfg()
    return cfg.get('generator', {}).get('natural_window_dias', 180)


def interpolar(tabla, x):
    if not tabla:
        return 1.0
    if x <= tabla[0][0]:
        return tabla[0][1]
    if x >= tabla[-1][0]:
        return 1.0
    for i in range(len(tabla) - 1):
        x1, y1 = tabla[i]
        x2, y2 = tabla[i + 1]
        if x1 <= x <= x2:
            return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    return 1.0


def ct_segmento(meses, factor):
    ct_base = interpolar(get_ct_table(), meses)
    return 1.0 + (ct_base - 1.0) * factor


def meses_desde(fecha_str, fecha_ref=None):
    if not fecha_str:
        return None
    if fecha_ref is None:
        fecha_ref = FECHA_REF_DEFAULT
    else:
        try:
            if '-' in str(fecha_ref) and str(fecha_ref).count('-') == 2:
                fecha_ref = datetime.strptime(str(fecha_ref)[:10], '%Y-%m-%d')
            else:
                fecha_ref = datetime.strptime(str(fecha_ref)[:7], '%Y-%m')
        except Exception:
            fecha_ref = FECHA_REF_DEFAULT
    try:
        dt = datetime.strptime(str(fecha_str)[:10], '%Y-%m-%d')
        return max(0, (fecha_ref - dt).days / 30.44)
    except Exception:
        return None


def es_nuevo(prop):
    txt = ('%s %s %s' % (prop.get('direccion', ''), prop.get('tipo', ''), prop.get('zona', ''))).lower()
    return any(k in txt for k in ['a estrenar', 'estrenar', 'pozo', 'obra nueva'])


def get_ct_rate(macrozona_id: str = None) -> float:
    """Retorna la tasa anual de CT para una macrozona desde zonas_depreciacion.json."""
    try:
        import json, os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'zonas_depreciacion.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for mz in data.get('macrozonas', []):
            if mz['id'] == macrozona_id:
                return mz.get('ct_annual_rate', -0.02)
    except Exception:
        pass
    return -0.02

def calcular_ct(meses, es_nuevo_flag=False, macrozona_id=None):
    if meses is None:
        return 1.0
    
    # Prioridad 1: Usar tasa anual de macrozona (Sustituye tabla universal)
    if macrozona_id:
        tasa = get_ct_rate(macrozona_id)
        # Formula: CT = (1 + tasa)^(meses/12)
        ct = (1.0 + tasa) ** (meses / 12.0)
        return ct
    
    # Fallback: Tabla universal original
    factores = get_ct_factors()
    factor = factores.get('nuevo', 0.95) if es_nuevo_flag else factores.get('usado', 1.12)
    return ct_segmento(meses, factor)


def calcular_lista_hoy(valor_m2, fecha_str, es_nuevo_flag=False, fecha_ref=None):
    m = meses_desde(fecha_str, fecha_ref)
    if m is None:
        return valor_m2
    ct = calcular_ct(m, es_nuevo_flag)
    return round(valor_m2 * ct, 2)


def get_ct_alquiler_rate(macrozona_id=None, dormitorios=None):
    """Retorna tasa anual CT alquiler desde zonas_depreciacion.json.
    Si se especifica dormitorios, usa la tasa específica por dormitorio.
    Si no, usa la tasa general de la macrozona."""
    try:
        import json, os
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'zonas_depreciacion.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for mz in data.get('macrozonas', []):
            if mz['id'] == macrozona_id:
                if dormitorios is not None:
                    by_dorm = mz.get('ct_alquiler_by_dormitorios', {})
                    dorm_key = str(int(dormitorios)) if dormitorios else None
                    if dorm_key and dorm_key in by_dorm:
                        return by_dorm[dorm_key]
                return mz.get('ct_alquiler_rate', 0.3014)
    except Exception:
        pass
    return 0.3014  # Default: +30.1% anual (blend scraping + IPEC)


def calcular_ct_alquiler(meses, macrozona_id=None, dormitorios=None):
    """Calcula CT para alquiler: (1 + tasa_alquiler)^(meses/12).
    Usa la tasa específica por dormitorio si está disponible."""
    if meses is None:
        return 1.0
    tasa = get_ct_alquiler_rate(macrozona_id, dormitorios)
    ct = (1.0 + tasa) ** (meses / 12.0)
    return ct

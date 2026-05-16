"""
Funciones helper puras para filtrado y cálculo de cluster.
Preparación para refactor seguro de obtener_mediana_cluster_v2().
Sin dependencias del motor de valuación. Solo cálculos puros.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Callable, Tuple, Any


def filtrar_por_radio(props: List[Dict], lat_ref: float, lon_ref: float,
                      radio_m: float, calcular_distancia_fn: Callable) -> List[Dict]:
    """
    Devuelve propiedades dentro del radio especificado.
    No muta las propiedades originales.
    
    Args:
        props: Lista de propiedades (cada una debe tener 'lat' y 'lon')
        lat_ref: Latitud de referencia
        lon_ref: Longitud de referencia
        radio_m: Radio máximo en metros
        calcular_distancia_fn: Función que calcula distancia en km entre 2 puntos
    
    Returns:
        Propiedades dentro del radio
    """
    resultado = []
    radio_km = radio_m / 1000
    for p in props:
        p_lat = p.get('lat') or p.get('latitud')
        p_lon = p.get('lon') or p.get('longitud')
        if not p_lat or not p_lon:
            continue
        try:
            dist = calcular_distancia_fn(lat_ref, lon_ref, float(p_lat), float(p_lon))
            if dist <= radio_km:
                resultado.append(p)
        except (ValueError, TypeError):
            continue
    return resultado


def filtrar_por_tipo_operacion_dorms(props: List[Dict], tipo: Optional[str] = None,
                                      operacion: Optional[str] = None,
                                      dormitorios: Optional[int] = None,
                                      tolerancia_dorms: int = 1) -> List[Dict]:
    """
    Filtra propiedades por tipo, operación y dormitorios con tolerancia.
    
    Args:
        props: Lista de propiedades
        tipo: Tipo de propiedad (ej: 'departamento', 'casa'). Si None, no filtra.
        operacion: Operación (ej: 'venta', 'alquiler'). Si None, no filtra.
        dormitorios: Cantidad de dormitorios. Si None, no filtra.
        tolerancia_dorms: Tolerancia ± para dormitorios (default: 1)
    
    Returns:
        Propiedades filtradas
    """
    resultado = []
    for p in props:
        if tipo:
            p_tipo = str(p.get('tipo', p.get('tipo_inmueble', '')))
            if not p_tipo or tipo.lower() not in p_tipo.lower():
                continue
        if operacion:
            p_oper = str(p.get('operacion', ''))
            if not p_oper or operacion.lower() not in p_oper.lower():
                continue
        if dormitorios is not None:
            p_dorms = p.get('dormitorios')
            if p_dorms is None:
                continue
            if abs(int(p_dorms) - dormitorios) > tolerancia_dorms:
                continue
        resultado.append(p)
    return resultado


def filtrar_por_fecha(props: List[Dict], fecha_ref: Optional[str] = None,
                      ventana_dias: int = 180) -> List[Dict]:
    """
    Filtra publicaciones dentro de una ventana temporal.
    Si fecha_ref es None, usa datetime.now().
    
    Args:
        props: Lista de propiedades con 'date_updated'
        fecha_ref: Fecha de referencia (formato 'YYYY-MM-DD' o None)
        ventana_dias: Ventana hacia atrás en días (default: 180)
    
    Returns:
        Propiedades dentro de la ventana temporal
    """
    if fecha_ref:
        try:
            fecha_fin = datetime.strptime(fecha_ref, '%Y-%m-%d')
        except ValueError:
            return props
    else:
        fecha_fin = datetime.now()

    fecha_inicio = fecha_fin - timedelta(days=ventana_dias)

    resultado = []
    for p in props:
        fecha_str = p.get('date_updated', '')
        if not fecha_str:
            continue
        try:
            fecha_pub = datetime.fromisoformat(fecha_str.replace('Z', ''))
        except (ValueError, TypeError):
            try:
                fecha_pub = datetime.strptime(fecha_str[:10], '%Y-%m-%d')
            except (ValueError, IndexError):
                continue

        if fecha_inicio <= fecha_pub <= fecha_fin:
            resultado.append(p)

    return resultado


def separar_por_barreras(props: List[Dict], lat_ref: float, lon_ref: float,
                          check_barrier_fn: Callable) -> Dict[str, List[Dict]]:
    """
    Separa propiedades según su cruce de barreras geográficas.
    
    Args:
        props: Lista de propiedades con 'lat' y 'lon'
        lat_ref: Latitud de referencia
        lon_ref: Longitud de referencia
        check_barrier_fn: Función que dado (p1, p2, barriers) retorna False/'soft'/'hard'
    
    Returns:
        Dict con 'same_side', 'cross_soft', 'excluded_hard'
    """
    same_side = []
    cross_soft = []
    excluded_hard = []

    for p in props:
        p_lat = p.get('lat') or p.get('latitud')
        p_lon = p.get('lon') or p.get('longitud')
        if not p_lat or not p_lon:
            same_side.append(p)
            continue
        try:
            cruza = check_barrier_fn(
                (lon_ref, lat_ref),
                (float(p_lon), float(p_lat))
            )
        except Exception:
            same_side.append(p)
            continue

        if cruza == 'hard':
            excluded_hard.append(p)
        elif cruza == 'soft':
            cross_soft.append(p)
        else:
            same_side.append(p)

    return {
        'same_side': same_side,
        'cross_soft': cross_soft,
        'excluded_hard': excluded_hard,
    }


def calcular_percentil(precios: List[float], percentil: int) -> Optional[float]:
    """
    Calcula percentil por metodo discreto/posicional.
    Usa indexacion entera sobre la lista ordenada.
    NO interpola entre comparables.
    
    Args:
        precios: Lista de precios ordenables
        percentil: Percentil a calcular (0-100)
    
    Returns:
        Valor en el percentil, o None si la lista esta vacia
    """
    if not precios:
        return None
    
    s = sorted(precios)
    n = len(s)
    idx = int(n * percentil / 100)
    idx = min(idx, n - 1)
    idx = max(idx, 0)
    return float(s[idx])


def calcular_blend_p33(p33_same: Optional[float], p33_cross: Optional[float],
                       alpha: float = 0.70) -> Optional[float]:
    """
    Calcula blend de P33 same/cross.
    Si falta uno de los dos, retorna el disponible.
    
    Args:
        p33_same: P33 del pool same-side (o None)
        p33_cross: P33 del pool cross-soft (o None)
        alpha: Peso del pool same-side (default: 0.70)
    
    Returns:
        Valor blend, o None si ambos son None
    """
    if p33_same is not None and p33_cross is not None:
        return alpha * p33_same + (1 - alpha) * p33_cross
    elif p33_same is not None:
        return p33_same
    elif p33_cross is not None:
        return p33_cross
    return None


def seleccionar_percentil_por_edad(age_filter_applied: bool,
                                    n_age_filtered: int) -> Tuple[int, str]:
    """
    Selecciona el percentil a usar según el filtro de edad.
    
    Regla actual:
    - Sin filtro de edad → P33
    - n_age >= 20 → P50
    - 10 <= n_age < 20 → P45
    - 8 <= n_age < 10 → P40
    
    Args:
        age_filter_applied: Si el filtro de edad está activo
        n_age_filtered: Cantidad de propiedades post-filtro de edad
    
    Returns:
        (percentil_numero, etiqueta)  ej: (45, 'P45_age')
    """
    if not age_filter_applied:
        return 33, 'P33'

    if n_age_filtered >= 20:
        return 50, 'P50_age'
    elif n_age_filtered >= 10:
        return 45, 'P45_age'
    elif n_age_filtered >= 8:
        return 40, 'P40_age'
    else:
        return 33, 'P33'

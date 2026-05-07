import json
import os
import re
import math
import numpy as np
from datetime import datetime
from parsers.location_engine import cargar_anclas, calcular_precio_m2, estimar_confianza, get_ancla_mas_cercana

DATOS_MERCADO_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'datos_mercado.json'
)

# --- NORMALIZADORES GLOBALES ---
def normalize_float(x):
    """
    Normaliza un valor a float.
    - Convierte strings "41.0" a float
    - Si None/''/NaN -> 0.0
    """
    if x is None or x == '':
        return 0.0
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0

def normalize_year(x):
    """
    Normaliza año de construcción.
    - Acepta int, float, string "1998", string "1998-01-01"
    - Retorna int 4 dígitos si está en rango razonable (1850..año_actual)
    - Si no, None
    """
    if x is None or x == '':
        return None
    
    año_actual = datetime.now().year
    
    try:
        if isinstance(x, str):
            x = x.strip()
            if '-' in x:
                x = x.split('-')[0]
            if not x.isdigit():
                return None
        año = int(float(x))
        
        if 1850 <= año <= año_actual:
            return año
        return None
    except (ValueError, TypeError):
        return None

# --- FUNCIONES AUXILIARES DE DISTANCIA ---
def calcular_distancia_km(lat1, lon1, lat2, lon2):
    """Calcula distancia en km usando fórmula de Haversine."""
    R = 6371  # Radio de la Tierra en km
    
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def filtrar_por_radio(pool, lat, lon, radio_metros):
    """Filtra propiedades dentro del radio especificado."""
    radio_km = radio_metros / 1000
    resultado = []
    
    for p in pool:
        p_lat = p.get('lat') or p.get('latitud')
        p_lon = p.get('lon') or p.get('longitud')
        
        if p_lat is None or p_lon is None:
            continue
        
        try:
            distancia = calcular_distancia_km(lat, lon, p_lat, p_lon)
            
            if distancia <= radio_km:
                p_copy = dict(p)
                p_copy['distancia_km'] = distancia
                resultado.append(p_copy)
        except:
            continue
    
    return resultado

def inferir_zona_por_coordenadas(lat, lon):
    """Infiere la zona basándose en coordenadas."""
    ZONAS_CENTROIDES = {
        "Centro": (-32.9468, -60.6393),
        "Martin": (-32.9541, -60.6316),
        "Abasto": (-32.9445, -60.6319),
        "Sexta": (-32.9520, -60.6330),
        "Pichincha": (-32.9380, -60.6450),
        "Puerto Norte": (-32.9590, -60.6250),
    }
    
    zona_cercana = None
    min_dist = float('inf')
    
    for zona, (z_lat, z_lon) in ZONAS_CENTROIDES.items():
        dist = calcular_distancia_km(lat, lon, z_lat, z_lon)
        if dist < min_dist:
            min_dist = dist
            zona_cercana = zona
    
    return zona_cercana or "Centro"

def normalizar_zona(zona_raw):
    """Normaliza el nombre de zona a su forma canónica."""
    if not zona_raw:
        return "Centro"
    
    import unicodedata
    zona_clean = ''.join(c for c in unicodedata.normalize('NFD', zona_raw) if unicodedata.category(c) != 'Mn')
    zona_lower = zona_clean.lower().strip()
    
    if zona_lower in ('centro', 'microcentro'):
        return "Centro"
    elif zona_lower in ('martin', 'barrio martin'):
        return "Martin"
    elif zona_lower == 'abasto':
        return "Abasto"
    elif zona_lower in ('facultades', 'sexta', 'sexta pellegrini', 'republica', 'republica de la sexta', 'rep de la sexta'):
        return "Sexta"
    elif zona_lower == 'pellegrini':
        return "Pellegrini"
    elif zona_lower == 'pichincha':
        return "Pichincha"
    elif zona_lower in ('echesortu', 'oeste'):
        return "Centro"
    elif zona_lower in ('puerto norte',):
        return "Puerto Norte"
    
    return zona_raw

# === ENTRYPOINT UNIFICADO ===
def valuar_entrada(propiedad, fecha_ref=None):
    """
    Entry point unificado para valuación.
    Retorna breakdown completo para auditar UI vs CLI.
    
    Returns:
        dict con: m2_equiv, m2_base, percentil_usado, n_muestras, factor_final, valor_venta, debug_info
    """
    from parsers.motor_vpp_core import get_binance_usdt_ars
    
    zona = propiedad.get('zona', 'Centro')
    dorms = propiedad.get('dormitorios', 2)
    lat = propiedad.get('lat')
    lon = propiedad.get('lon')
    anio_const = propiedad.get('anio_construccion', 2020)
    
    # 1. m2 equivalentes
    m2_equiv = calcular_m2_equivalentes(propiedad)
    
    # 2. Cluster con v2
    from parsers.mercado_inmobiliario import obtener_mediana_cluster_v2
    valor_cluster, n_muestras, meta_cluster = obtener_mediana_cluster_v2(
        zona, dorms, operacion='venta'
    )
    
    # 3. Base calibrada (usa cluster directamente si hay muestras)
    if n_muestras >= 4:
        m2_base = valor_cluster
        metodo = f"Cluster P33 ({n_muestras} muestras)"
    else:
        # Fallback a ancla
        from parsers.location_engine import get_ancla_mas_cercana
        ancla = get_ancla_mas_cercana(lat, lon, cargar_anclas())
        valor_ancla = ancla.get('usd_m2', 1500) if ancla else 1500
        antiguedad = 2026 - anio_const
        factor_deprec = max(0.5, 1.0 - (antiguedad * 0.006))
        m2_base = valor_ancla * factor_deprec
        metodo = f"Ancla ({n_muestras} muestras)"
    
    # 4. Factores - usar el total directamente (ya incluye todo)
    factores = calcular_factores(propiedad)
    factor_total = factores.get('total', 1.0)
    
    # 5. Valor final (misma fórmula que v7)
    valor_venta = m2_equiv * m2_base * factor_total
    
    return {
        'm2_equiv': m2_equiv,
        'm2_base': m2_base,
        'percentil_usado': meta_cluster.get('percentil_usado', 'P33'),
        'n_muestras': n_muestras,
        'factor_final': factor_total,
        'valor_venta': valor_venta,
        'debug_info': {
            'zona': zona,
            'dorms': dorms,
            'metodo': metodo
        }
    }


# --- PARÁMETROS DE CALIBRACIÓN V10.1 ---
UMBRAL_CONFIANZA_SCRAPING = 8   # Muestras mínimas para confiar en el scraping
NEGOCIACION_ESTANDAR = 0.92    # -8% (Precio lista vs cierre en Rosario 2026)
ZONAS_PREMIUM = ["Martin", "Puerto Norte", "Centro"]  # Menos negociación
NEGOCIACION_PREMIUM = 0.94   # -6% en zonas premium
MAX_BONUS_ATRIBUTOS = 1.30   # Cap +30% para evitar valores locos

# --- CONFIGURACIÓN DE BÚSQUEDA GEOESPACIAL ---
RADIOS_PROGRESIVOS = [300, 500, 800, 1000, 1500]  # metros
MIN_COMPARABLES = 10  # mínimo para considerar cluster válido
MIN_COMPARABLES_FALLBACK = 5  # mínimo para fallback

MAPEO_ZONAS = {
    "Martin": "martin_interno",
    "Martin Río": "martin_rio",
    "Centro": "centro",
    "Pellegrini": "pellegrini_cercano",
    "Facultades": "facultades",
    "República de la Sexta": "republica_sexta",
    "Republica de la Sexta": "republica_sexta",
    "Republica Sexta": "republica_sexta",
    "Macrocentro Sur": "macrocentro_sur",
    "Sexta Pellegrini": "sexta_pellegrini",
    "Republica Sexta Pellegrini": "sexta_pellegrini"
}


def ajustar_microzona(prop, zona_key):
    """
    Ajuste automático de microzona para casos híbridos
    """
    zona_raw = prop.get("zona", "").lower()
    
    if "sexta" in zona_raw and "pellegrini" in zona_raw:
        return "sexta_pellegrini"
    
    return zona_key


def cargar_datos():
    if not os.path.exists(DATOS_MERCADO_FILE):
        raise FileNotFoundError("No existe datos_mercado.json")

    with open(DATOS_MERCADO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def obtener_mediana_cluster(zona, dormitorios, operacion='venta'):
    """
    Obtiene la mediana del cluster desde cache_scraping.json.
    Busca propiedades similares por zona y dormitorios.
    v11.1: Aplica deduplicación + filtro pre-IQR (0.6-1.6x) robusto.
    RETORNO: 2 valores (valor, n_muestras)
    """
    try:
        cache_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'cache_scraping.json'
        )
        if not os.path.exists(cache_path):
            return 0, 0
        
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        # 1) Filtrar por zona, dormitorios y operación
        props = [
            p for p in cache.get('propiedades', [])
            if p.get('zona') == zona 
            and p.get('dormitorios') == dormitorios
            and p.get('operacion') == operacion
            and p.get('valor_m2', 0) > 0
        ]
        
        if not props:
            return 0, 0
        
        # 2) DEDUPLICAR (Consistencia con motor_vpp_core)
        seen = set()
        unicos = []
        for p in props:
            key = (int(p.get('precio', 0)), int(p.get('m2', 0)), p.get('zona', ''))
            if key not in seen:
                seen.add(key)
                unicos.append(p)
        
        precios = [p['valor_m2'] for p in unicos]
        n_raw = len(precios)
        
        if not precios:
            return 0.0, 0
        
        if len(precios) < 3:
            return float(np.median(precios)), len(precios)
        
        # 3) FILTRO PRE-IQR robusto (0.6-1.6x)
        # Usamos np.median para evitar el bug de indexación en listas pares
        mediana_raw = np.median(precios)
        
        lower_robust = mediana_raw * 0.6
        upper_robust = mediana_raw * 1.6
        
        precios_filtrados = [p for p in precios if lower_robust <= p <= upper_robust]
        
        # Si el filtro elimina demasiado, usar IQR tradicional como fallback
        if len(precios_filtrados) < 3:
            precios_ordenados = sorted(precios)
            if len(precios_ordenados) < 3:
                return float(np.median(precios_ordenados)), len(precios_ordenados)
            q1 = np.percentile(precios_ordenados, 25)
            q3 = np.percentile(precios_ordenados, 75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            precios_filtrados = [p for p in precios if lower <= p <= upper]
        
        if not precios_filtrados:
            return float(np.median(precios)), len(precios)
        
        return float(np.median(precios_filtrados)), len(precios_filtrados)
    except Exception:
        return 0, 0


def obtener_mediana_cluster_v2(zona, dormitorios, operacion='venta', lat_ref=None, lon_ref=None, fecha_ref=None):
    """
    Obtiene la mediana del cluster desde cache_scraping.json.
    Versión v2 con metadata extendida Y radios progresivos.
    
    RETORNO: 3 valores (valor, n_muestras, meta_dict)
    
    meta incluye:
    - percentil_usado: "P33" para venta, "P50" para alquiler (según ALGORITMOS.md)
    - n_raw: muestras antes de filtrar
    - n_filtradas: muestras después de filtrar
    - radio_usado: radio en metros usado finalmente
    - fecha_ref: fecha de referencia usada
    - operacion: operación consultada
    - zona_original: zona enviada como input
    - zona_resolucion: zona que devolvió resultados
    """
    try:
        import numpy as np
        
        cache_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'cache_scraping.json'
        )
        if not os.path.exists(cache_path):
            return 0, 0, {'percentil_usado': 'P50' if operacion == 'alquiler' else 'P33', 'n_raw': 0, 'n_filtradas': 0}
        
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        
        # Percentil según operación (ALGORITMOS.md línea 20-23)
        if operacion == 'alquiler':
            percentil_usado = 'P50'
        else:
            percentil_usado = 'P33'
        
        zona_original = zona
        zona_normalizada = normalizar_zona(zona)
        
        RADIOS_PROGRESIVOS = [300, 500, 800, 1000, 1500]
        MIN_COMPARABLES = 10
        MIN_COMPARABLES_FALLBACK = 5
        
        from datetime import datetime, timedelta
        
        def filtrar_por_fecha(props, fecha_ref_str, dias=180):
            """Filtra propiedades por ventana de fecha (días hacia atrás)."""
            if not fecha_ref_str:
                return props
            try:
                fecha_ref_dt = datetime.strptime(fecha_ref_str, '%Y-%m-%d')
                fecha_limite = fecha_ref_dt - timedelta(days=dias)
                props_filtrados = []
                for p in props:
                    date_upd = p.get('date_updated', '')
                    if not date_upd:
                        continue
                    try:
                        dt = datetime.strptime(date_upd[:10], '%Y-%m-%d')
                        if fecha_limite <= dt <= fecha_ref_dt:
                            props_filtrados.append(p)
                    except:
                        continue
                return props_filtrados
            except:
                return props
        
        def buscar_en_zona(zona_buscar, dorms, oper, lat_r=None, lon_r=None, radio=None, fecha_filtro=None):
            """Busca propiedades en una zona, opcionalmente filtradas por radio."""
            props = [
                p for p in cache.get('propiedades', [])
                if (p.get('zona') == zona_buscar or normalizar_zona(p.get('zona', '')) == zona_buscar)
                and p.get('dormitorios') == dorms
                and p.get('operacion') == oper
                and p.get('valor_m2', 0) > 0
            ]

            
            # Filtrar por radio si hay coordenadas
            if lat_r is not None and lon_r is not None and radio is not None:
                props_filtrados = []
                for p in props:
                    p_lat = p.get('lat') or p.get('latitud')
                    p_lon = p.get('lon') or p.get('longitud')
                    if p_lat is None or p_lon is None:
                        continue
                    try:
                        dist = calcular_distancia_km(lat_r, lon_r, p_lat, p_lon)
                        radio_km = radio / 1000
                        if dist <= radio_km:
                            props_filtrados.append(p)
                    except:
                        continue
                return props_filtrados
            
            return props
        
        def aplicar_filtro_fecha(props, fecha_filtro):
            """Aplica ventana móvil de 6 meses (180 días). Si <5 muestras, extiende a 365."""
            if not fecha_filtro:
                return props
            # Primero intentar 180 días
            props_180 = filtrar_por_fecha(props, fecha_filtro, dias=180)
            if len(props_180) >= 5:
                return props_180
            # Extender a 365 días si hay menos de 5
            props_365 = filtrar_por_fecha(props, fecha_filtro, dias=365)
            return props_365
        
        # Estrategia: Radio progresivo + fallback de zona
        mejor_resultado = None
        
        # 1. Intentar búsqueda geográfica primero si hay coordenadas
        if lat_ref is not None and lon_ref is not None:
            for radio in RADIOS_PROGRESIVOS:
                props_geo = []
                for p in cache.get('propiedades', []):
                    p_lat = p.get('lat') or p.get('latitud')
                    p_lon = p.get('lon') or p.get('longitud')
                    if not (p_lat and p_lon): continue
                    
                    dist = calcular_distancia_km(lat_ref, lon_ref, p_lat, p_lon)
                    if dist > radio / 1000: continue
                    
                    if p.get('dormitorios') != dormitorios: continue
                    if p.get('operacion') != operacion: continue
                    if p.get('valor_m2', 0) <= 0: continue
                    
                    props_geo.append(p)
                
                # Aplicar filtro de fecha
                props_geo = aplicar_filtro_fecha(props_geo, fecha_ref)
                
                if len(props_geo) >= MIN_COMPARABLES:
                    mejor_resultado = (props_geo, radio, "busqueda_geografica")
                    break
            else:
                # Fallback: mismo pero sin filtro de radio (1500m)
                for p in cache.get('propiedades', []):
                    p_lat = p.get('lat') or p.get('latitud')
                    p_lon = p.get('lon') or p.get('longitud')
                    if not (p_lat and p_lon): continue
                    dist = calcular_distancia_km(lat_ref, lon_ref, p_lat, p_lon)
                    if dist > 1.5: continue
                    if p.get('dormitorios') != dormitorios: continue
                    if p.get('operacion') != operacion: continue
                    if p.get('valor_m2', 0) <= 0: continue
                    props_geo.append(p)
                
                props_geo = aplicar_filtro_fecha(props_geo, fecha_ref)
                
                if len(props_geo) >= 2:
                    mejor_resultado = (props_geo, 1500, "busqueda_geografica")
        
        # 2. Fallback: zona normalizada + radio progresivo
        if mejor_resultado is None:
            for radio in RADIOS_PROGRESIVOS:
                props = buscar_en_zona(zona_normalizada, dormitorios, operacion, lat_ref, lon_ref, radio, fecha_ref)
                props = aplicar_filtro_fecha(props, fecha_ref)
                if len(props) >= MIN_COMPARABLES:
                    mejor_resultado = (props, radio, zona_normalizada)
                    break
        
        # 3. Último fallback: usar datos disponibles aunque sean mínimos
        if mejor_resultado is None:
            props = buscar_en_zona(zona_normalizada, dormitorios, operacion)
            props = aplicar_filtro_fecha(props, fecha_ref)
            if len(props) >= 2:
                mejor_resultado = (props, None, zona_normalizada)
        
        if mejor_resultado is None:
            if props:
                return 0, 0, {
                    'percentil_usado': percentil_usado, 
                    'n_raw': 0, 
                    'n_filtradas': 0,
                    'radio_usado': None,
                    'fecha_ref': fecha_ref,
                    'operacion': operacion,
                    'zona_original': zona_original,
                    'zona_resolucion': zona_normalizada,
                    'debug': f'Sin datos suficientes ({len(props)} muestras)'
                }
            # Fallback final al ancla
            return 0, 0, {
                'percentil_usado': percentil_usado, 
                'n_raw': 0, 
                'n_filtradas': 0,
                'radio_usado': None,
                'fecha_ref': fecha_ref,
                'operacion': operacion,
                'zona_original': zona_original,
                'zona_resolucion': zona_normalizada
            }
        
        props, radio_usado, zona_resol = mejor_resultado
        
# === APLICAR BARRERAS GEOGRÁFICAS (Rosario) ===
# Blending same-side / cross-soft para evitar contaminación
        same_side = []
        cross_soft = []
        
        if lat_ref and lon_ref and props:
            try:
                from parsers.location_engine import check_barrier_crossing, cargar_barreras
                barreras = cargar_barreras()
                
                props_barrier = []
                for prop in props:
                    p_lat = prop.get('lat') or prop.get('latitud')
                    p_lon = prop.get('lon') or prop.get('longitud')
                    
                    if p_lat and p_lon:
                        cruza = check_barrier_crossing(
                            (lon_ref, lat_ref),
                            (p_lon, p_lat),
                            barreras
                        )
                        if cruza == 'hard':
                            continue  # exclude always
                        elif cruza == 'soft':
                            cross_soft.append(prop)
                            prop['_cross_soft'] = True
                        else:
                            same_side.append(prop)
                            prop['_cross_soft'] = False
                    else:
                        same_side.append(prop)
                        prop['_cross_soft'] = False
                
                props_barrier = same_side + cross_soft
                if len(props_barrier) < len(props):
                    props = props_barrier
            except Exception as e:
                pass  # Si falla, continuar sin barreras
        
        # DEDUPLICAR
        seen = set()
        unicos = []
        for p in props:
            key = (int(p.get('precio', 0)), int(p.get('m2', 0)), p.get('zona', ''))
            if key not in seen:
                seen.add(key)
                unicos.append(p)
        
        precios = [p['valor_m2'] for p in unicos]
        n_raw = len(precios)
        
        if not precios:
            return 0.0, 0, {
                'percentil_usado': percentil_usado,
                'n_raw': 0,
                'n_filtradas': 0,
                'radio_usado': radio_usado,
                'fecha_ref': fecha_ref,
                'operacion': operacion,
                'zona_original': zona_original,
                'zona_resolucion': zona_resol
            }
        
        if len(precios) < 3:
            return float(np.median(precios)), len(precios), {
                'percentil_usado': percentil_usado,
                'n_raw': n_raw,
                'n_filtradas': len(precios),
                'radio_usado': radio_usado,
                'fecha_ref': fecha_ref,
                'operacion': operacion,
                'zona_original': zona_original,
                'zona_resolucion': zona_resol
            }
        
        # FILTRO PRE-IQR robusto
        mediana_raw = np.median(precios)
        lower_robust = mediana_raw * 0.6
        upper_robust = mediana_raw * 1.6
        
        precios_filtrados = [p for p in precios if lower_robust <= p <= upper_robust]
        
        # Fallback IQR si elimina demasiado
        if len(precios_filtrados) < 3:
            precios_ordenados = sorted(precios)
            if len(precios_ordenados) < 3:
                return float(np.median(precios)), len(precios), {
                    'percentil_usado': percentil_usado,
                    'n_raw': n_raw,
                    'n_filtradas': len(precios),
                    'radio_usado': radio_usado,
                    'fecha_ref': fecha_ref,
                    'operacion': operacion,
                    'zona_original': zona_original,
                    'zona_resolucion': zona_resol
                }
            q1 = np.percentile(precios_ordenados, 25)
            q3 = np.percentile(precios_ordenados, 75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            precios_filtrados = [p for p in precios if lower <= p <= upper]
        
        if not precios_filtrados:
            return float(np.median(precios)), len(precios), {
                'percentil_usado': percentil_usado,
                'n_raw': n_raw,
                'n_filtradas': len(precios),
                'radio_usado': radio_usado,
                'fecha_ref': fecha_ref,
                'operacion': operacion,
                'zona_original': zona_original,
                'zona_resolucion': zona_resol
            }
        
        # Calcular percentil CON BLENDING same-side / cross-soft
        # Separar pools
        precios_same = []
        precios_cross = []
        
        for p in unicos:
            val = p.get('valor_m2', 0)
            if val <= 0:
                continue
            if p.get('_cross_soft', False):
                precios_cross.append(val)
            else:
                precios_same.append(val)
        
        def calc_p33(vals):
            if not vals:
                return None
            s = sorted(vals)
            n = len(s)
            idx = int(n * 0.33)
            return s[min(idx, n-1)]
        
        p33_same = calc_p33(precios_same)
        p33_cross = calc_p33(precios_cross)
        
        n_same = len(precios_same)
        if n_same >= 15:
            alpha = 0.70
        elif n_same >= 8:
            alpha = 0.60
        elif n_same >= 5:
            alpha = 0.55
        else:
            alpha = 0.50
        
        # Blending
        if p33_same and p33_cross:
            valor = alpha * p33_same + (1 - alpha) * p33_cross
        elif p33_same:
            valor = p33_same
        else:
            valor = p33_cross if p33_cross else float(np.median(precios_filtrados))
        
        if operacion == 'venta':
            percentil_usado = 'P33'
        else:
            valor = float(np.median(precios_filtrados))
            percentil_usado = 'P50'
        
        n_filtradas = len(precios_filtrados)
        
        meta = {
            'percentil_usado': percentil_usado,
            'n_raw': n_raw,
            'n_filtradas': n_filtradas,
            'radio_usado': radio_usado,
            'fecha_ref': fecha_ref,
            'operacion': operacion,
            'zona_original': zona_original,
            'zona_resolucion': zona_resol,
            'barrier_mode': 'blending',
            'n_same_side': n_same,
            'n_cross_soft': len(precios_cross),
            'alpha': alpha,
            'p33_same': p33_same,
            'p33_cross': p33_cross
        }
        
        return valor, n_filtradas, meta
    except Exception as e:
        return 0, 0, {
            'percentil_usado': 'P50' if operacion == 'alquiler' else 'P33',
            'n_raw': 0,
            'n_filtradas': 0,
            'radio_usado': None,
            'fecha_ref': fecha_ref,
            'operacion': operacion,
            'zona_original': zona_original,
            'zona_resolucion': zona_resol,
            'error': str(e)
        }



def calcular_base_calibrada(valor_ancla, prop_data):
    """
    Fusiona Ancla y Scraping con ponderación dinámica.
    Aplica factor de negociación según zona y factor temporal.
    AHORA USA v2 CON COORDENADAS para mantener consistencia UI-CLI.
    """
    zona = prop_data.get('zona', 'Centro')
    dorms = prop_data.get('dormitorios', 2)
    lat = prop_data.get('lat')
    lon = prop_data.get('lon')
    anio_const = prop_data.get('anio_construccion', 2020)
    anio_tasacion = prop_data.get('anio_tasacion', 2026)
    
    # Usar v2 con coordenadas (IGUAL que valuar_propiedad_v7)
    valor_cluster, muestras, meta = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona),
        dormitorios=dorms,
        operacion='venta',
        lat_ref=lat,
        lon_ref=lon,
        fecha_ref='2026-04'
    )

    # Handle None returns
    if valor_cluster is None or valor_cluster == 0:
        valor_cluster = 0
        muestras = 0
    
    # 2. Depreciar ancla por antigüedad
    antiguedad = 2026 - anio_const
    factor_deprec = max(0.5, 1.0 - (antiguedad * 0.006))
    valor_ancla_ajustado = valor_ancla * factor_deprec
    
    # 3. Ponderación dinámica según cantidad de muestras (UMbral confianza = 15)
    if muestras == 0:
        base = valor_ancla_ajustado
        metodo = "Ancla (sin datos web)"
    elif muestras < 4:
        base = (valor_ancla_ajustado * 0.7) + (valor_cluster * 0.3)
        metodo = f"Hibrido (bajo vol: {muestras} m.)"
    elif muestras < UMBRAL_CONFIANZA_SCRAPING:
        base = (valor_ancla_ajustado * 0.4) + (valor_cluster * 0.6)
        metodo = f"Hibrido (medio: {muestras} m.)"
    else:
        base = valor_cluster
        metodo = f"cluster_v2 (P{meta.get('percentil_usado','33')}, {muestras} props)"
    
    # 4. Factor de negociación según zona
    # El factor de negociación se aplica al final en el valor realizable, 
    # aquí devolvemos la base de mercado pura.
    
    # 5. Factor temporal (ratio) - NEUTRALIZA el índice 2026
    anio_actual = 2026
    datos = cargar_datos()
    indice_data = datos.get('indice_ciudad', {}).get('data', {})
    idx_actual = indice_data.get(str(anio_actual), 1.25)
    idx_destino = indice_data.get(str(anio_tasacion), 1.25)
    factor_temporal = idx_destino / idx_actual  # Si 2026/2026 = 1.0
    
    return base * factor_temporal, metodo


def sanitizar_propiedad(prop):
    """Sanitiza inputs de propiedad - conserva todos los campos."""
    # Primero copiar todas las props
    result = dict(prop)
    
    # Sanitizar solo los campos numéricos importantes
    result['m2'] = max(0, prop.get('m2', 0) or 0)
    result['m2_cubiertos'] = max(0, prop.get('m2_cubiertos', 0) or 0)
    result['m2_semicubiertos'] = max(0, prop.get('m2_semicubiertos', 0) or 0)
    result['m2_descubiertos'] = max(0, prop.get('m2_descubiertos', 0) or 0)
    result['m2_comunes'] = max(0, prop.get('m2_comunes', 0) or 0)
    result['valor_compra_usd'] = max(0, prop.get('valor_compra_usd', 0) or 0)
    result['zona'] = prop.get('zona', 'centro')
    result['fecha_compra'] = prop.get('fecha_compra', '2020-01-01')
    result['uso_exclusivo'] = prop.get('uso_exclusivo', False)
    result['estado_detalle'] = prop.get('estado_detalle', 'bueno')
    # v9.5 Variables Estructurales
    result['vista'] = prop.get('vista', 'frente').lower()
    result['total_pisos'] = int(prop.get('total_pisos', 1))
    result['ubicacion_tipo'] = prop.get('ubicacion_tipo', 'calle').lower()
    result['balcon'] = bool(prop.get('balcon', False))
    result['tipo_balcon'] = prop.get('tipo_balcon', 'ninguno').lower()
    result['gas_ok'] = prop.get('gas_ok', 'si').lower()
    result['constructora'] = str(prop.get('constructora', '')).lower().strip()
    result['seguridad'] = prop.get('seguridad', 'ninguna').lower()
    result['expensas_ars'] = float(prop.get('expensas_ars', 0))
    result['doble_ingreso'] = bool(prop.get('doble_ingreso', False))
    result['lavadero_independiente'] = bool(prop.get('lavadero_independiente', False))
    result['toilet'] = bool(prop.get('toilet', False))
    result['baño_servicio'] = bool(prop.get('baño_servicio', False))
    result['reciclado'] = bool(prop.get('reciclado', False))
    result['reciclado_tipo'] = prop.get('reciclado_tipo', 'ninguno').lower()
    result['anio_reciclado'] = prop.get('anio_reciclado')
    result['ventilacion_bano'] = prop.get('ventilacion_bano', 'natural').lower()
    result['layout_flexible'] = bool(prop.get('layout_flexible', False))
    result['placares_completos'] = bool(prop.get('placares_completos', False))
    result['despensa'] = bool(prop.get('despensa', False))
    result['ascensores_edificio'] = int(prop.get('ascensores_edificio', 2))
    result['calidad_edificio'] = prop.get('calidad_edificio', 'media')
    result['piso'] = prop.get('piso', 0)
    
    return result


def obtener_indice_cercano(indice, año):
    """✅ Fallback seguro - busca año exacto o el más cercano."""
    try:
        años = sorted([int(a) for a in indice.keys()])
        año = int(año)
        
        if str(año) in indice:
            return indice[str(año)]
        
        anteriores = [a for a in años if a <= año]
        if anteriores:
            return indice[str(max(anteriores))]
        
        return indice[str(min(años))]
    except:
        return 1.0


def obtener_base_year(data):
    """✅ Base year explícito - evita drift."""
    return data.get('indice_ciudad', {}).get('base_year', 2026)


def obtener_pesos(ratio):
    """Pesos dinámicos - más agresivos con ratios extremos."""
    if ratio > 1.5:
        return {'comp': 0.90, 'hist': 0.10}
    elif ratio > 1.3:
        return {'comp': 0.80, 'hist': 0.20}
    elif ratio >= 1:
        w_comp = min(0.75, 0.6 + (ratio - 1) * 0.5)
    elif ratio < 0.7:
        return {'comp': 0.85, 'hist': 0.15}
    else:
        w_comp = max(0.65, 0.8 - (1 - ratio) * 0.5)
    return {'comp': w_comp, 'hist': 1 - w_comp}


def calcular_m2_equivalentes(prop):
    """
    Calcula m2 equivalentes con ponderación de mercado real Rosario.
    
    MODO LEGADO: m2_cubiertos, m2_semicubiertos, m2_descubiertos, m2_comunes
    MODO GRANULAR: m2_semi_propios, m2_semi_exclusivos (cuando existen ambos)
    
    Ponderaciones:
    - m2_cubiertos: 100%
    - m2_semicubiertos: 30%/45%/55% (chico/medio/grande)
    - m2_descubiertos: 20% (25% si patio>=20m2)
    - m2_comunes: 12% (15% si exterior=comun)
    
    Clamp: no más de +25% sobre m2_cubiertos (casas +15%)
    """
    # Normalizar todos los campos
    m2_cub = normalize_float(prop.get('m2_cubiertos'))
    
    # Fallback: si m2_cubiertos es 0, usar m2 (para retrocompatibilidad)
    if m2_cub == 0:
        m2_cub = normalize_float(prop.get('m2'))
    
    m2_desc = normalize_float(prop.get('m2_descubiertos'))
    m2_com = normalize_float(prop.get('m2_comunes'))
    
    # Detectar MODO GRANULAR (cuando existen ambos campos)
    m2_semi_propios = prop.get('m2_semi_propios')
    m2_semi_exclusivos = prop.get('m2_semi_exclusivos')
    
    if m2_semi_propios is not None and m2_semi_exclusivos is not None:
        # MODO GRANULAR
        m2_semi = normalize_float(m2_semi_propios) + normalize_float(m2_semi_exclusivos)
        m2_semi_detalle = prop.get('m2_semicubiertos_detalle', 'medio').lower()
        
        # Bonus balcon SOLO sobre m2_semi_exclusivos
        tipo_balcon = prop.get('tipo_balcon', 'ninguno').lower()
        m2_semi_excl = normalize_float(m2_semi_exclusivos)
        bonus_m2 = 0
        if tipo_balcon == 'corrido':
            bonus_m2 = m2_semi_excl * 0.05
        elif tipo_balcon == 'L':
            bonus_m2 = m2_semi_excl * 0.10
    else:
        # MODO LEGADO
        m2_semi = normalize_float(prop.get('m2_semicubiertos'))
        m2_semi_detalle = prop.get('m2_semicubiertos_detalle', 'medio').lower()
        
        # Bonus balcon sobre m2_semi (legacy behavior)
        tipo_balcon = prop.get('tipo_balcon', 'ninguno').lower()
        bonus_m2 = 0
        if tipo_balcon == 'corrido':
            bonus_m2 = m2_semi * 0.05
        elif tipo_balcon == 'L':
            bonus_m2 = m2_semi * 0.10
    
    m2_total_escritura = prop.get('m2_total_escritura')
    
    # Coef según tamaño semicubiertos (solo si NO hay m2 especifico)
    # Si existe m2_semicubiertos > 0, usar coef fijo 0.45
    if m2_semi > 0:
        coef_semi = 0.45
    else:
        coef_semi = {'chico': 0.30, 'medio': 0.45, 'grande': 0.55}.get(m2_semi_detalle, 0.45)
    
    # Si exterior es común, bajar peso
    if prop.get('propiedad_exterior') == 'comun':
        factor_com = 0.15
    else:
        factor_com = 0.12
    
    # --- AJUSTE: Patio Grande (>20m² valorizado a 0.25) ---
    coef_desc = 0.2
    if m2_desc >= 20:
        coef_desc = 0.25
    
    m2_equiv = (
        m2_cub +
        m2_semi * coef_semi +
        m2_desc * coef_desc +
        m2_com * factor_com +
        bonus_m2
    )
    
    # Clamp dinámico v9.3: Casas tienen menos premio por m2 descubierto
    tipo = prop.get('tipo_inmueble', prop.get('tipo', 'departamento')).lower()
    if 'casa' in tipo or 'cochera' in tipo:
        max_ratio = 1.15
    else:
        max_ratio = 1.25
    
    max_m2 = m2_cub * max_ratio
    
    return min(m2_equiv, max_m2)


def calcular_factores(prop, ventana_usada=None):
    """
    Calcula factores de propiedad.
    v8.0: Retorna un diccionario separado para evitar doble conteo de antigüedad.
    
    Args:
        propiedad: dict con datos de la propiedad
        ventana_usada: opcional, ventana temporal a usar (para compatibilidad con UI)
    """
    import json
    import os
    
    # Default ventana si no se spécifiquea
    if ventana_usada is None:
        ventana_usada = "ventana3"
    
    estado = prop.get('estado_detalle', 'bueno').lower().replace(' ', '_')
    calidad = prop.get('calidad_edificio', 'media').lower()
    piso = prop.get('piso', 0)
    
    # FIX BUG 1: Leer anio_construccion con normalización
    anio_const = normalize_year(prop.get('anio_construccion'))
    anio_missing = anio_const is None
    
    if anio_const is None:
        anio_const = 2026 - prop.get('antiguedad', 0)
        anio_const = normalize_year(anio_const)
    
    if anio_const is None:
        anio_const = 2000  # default conservador
    
    antiguedad = 2026 - anio_const
    
    # Depreciación por Antigüedad (Year 0 -> Target)
    # 1. Calcular depreciación lineal normal
    delta_anti_raw = max(-0.60, -(antiguedad * 0.006))
    
    # 2. Atenuación dinámica para propiedades viejas (>30 años)
    UMBRAL_PENALIZACION_SEVERA = -0.18
    FACTOR_ATENUACION = 0.35
    
    if delta_anti_raw < UMBRAL_PENALIZACION_SEVERA:
        # Castigo severo: atenuamos el exceso
        exceso = delta_anti_raw - UMBRAL_PENALIZACION_SEVERA
        delta_anti_efectivo = UMBRAL_PENALIZACION_SEVERA + (exceso * FACTOR_ATENUACION)
    else:
        # Propiedades jóvenes: sin cambios
        delta_anti_efectivo = delta_anti_raw
    
    # Factor anti final
    factor_anti = max(0.40, 1.0 + delta_anti_efectivo)
    
    factor_estado = {
        'a_estrenar': 1.20, 'excelente': 1.10, 'muy_bueno': 1.03,
        'bueno': 1.0, 'regular': 0.85, 'a_refaccionar': 0.7
    }.get(estado, 1.0)
    
    factor_calidad = {
        'premium': 1.2, 'alta': 1.1, 'media': 1.0, 'economica': 0.85, 'baja': 0.85
    }.get(calidad, 1.0)
    
    # 1. Factor Vista v9.5
    vista = prop.get('vista', 'frente').lower()
    factor_vista = {
        'rio': 1.25, 'despejada': 1.12, 'frente': 1.0, 
        'pulmon': 0.95, 'interna': 0.90
    }.get(vista, 1.0)
    
    # 2. Factor Altura v10.0 (Tabla coef: piso alto >70% = +5%)
    total_pisos = max(1, prop.get('total_pisos', 1))
    ratio_altura = piso / total_pisos
    m2_desc = prop.get('m2_descubiertos', 0)
    if piso == 0:
        # --- AJUSTE: Patio Grande compensa planta baja ---
        # Si tiene patio >15m², reducir penalización de -12% a solo -2%
        if m2_desc >= 15:
            factor_piso = 0.98  # -2% (compensa con aire/luz)
        else:
            factor_piso = 0.88  # -12% estándar
    elif ratio_altura >= 0.70:
        factor_piso = 1.05  # piso alto >70%
    else:
        factor_piso = 1.0 + (ratio_altura * 0.10)
    
    # 3. Factor Ubicación v9.5
    u_tipo = prop.get('ubicacion_tipo', 'calle').lower()
    factor_ubica = {
        'avenida': 1.07, 'esquina': 1.03, 'calle': 1.0, 'pasaje': 0.94
    }.get(u_tipo, 1.0)
    
    # 4. Factor Gas v9.5
    gas = prop.get('gas_ok', 'si').lower()
    factor_gas = {'si': 1.0, 'en_proceso': 0.96, 'no': 0.92}.get(gas, 1.0)
    
    # 5. Factor Constructora v9.5 (Carga desde JSON)
    factor_const = 1.0
    try:
        constr_path = "C:/Users/Gustavo/ingresos_familiares_st/constructoras_rosario.json"
        if os.path.exists(constr_path):
            with open(constr_path, "r", encoding="utf-8") as f:
                tiers = json.load(f)
                constr = prop.get('constructora', '').lower()
                if constr:
                    for tier, data in tiers.items():
                        if any(nombre in constr for nombre in data.get('nombres', [])):
                            factor_const = data.get('factor', 1.0)
                            break
    except:
        pass
    
    # 6. Factor Balcón/Terraza v10.0
    # Tabla coef: corrido +2%, L +5%, francesa -2%, terraza +6%
    t_balcon = prop.get('tipo_balcon', 'ninguno').lower()
    factor_balcon = {
        'L': 1.05,          # balcón en L: +5%
        'corrido': 1.02,    # balcón corrido: +2% (AJUSTE 2)
        'frances': 0.98,   # balcón francés: -2%
        'terraza': 1.06,   # balcón terraza: +6%
        'ninguno': 1.0
    }.get(t_balcon, 1.0)
    
    ventilacion = prop.get('ventilacion', 'simple').lower()
    factor_vent = 1.10 if 'cruzada' in ventilacion else 1.0 if 'doble' in ventilacion else 0.90
    
    # 7. Detalles Funcionales v10.0
    f_funcional = 1.0
    if prop.get('doble_ingreso'): f_funcional *= 1.03
    if prop.get('lavadero_independiente'): f_funcional *= 1.015  # AJUSTE 1: 0.02->0.015
    if prop.get('toilet'): f_funcional *= 1.035
    if prop.get('baño_servicio'): f_funcional *= 1.01
    if prop.get('layout_flexible'): f_funcional *= 1.04
    if prop.get('placares_completos'): f_funcional *= 1.015  # AJUSTE 1: 0.02->0.015
    if prop.get('despensa'): f_funcional *= 1.015
    
    # Reciclado v10.0 (parcial +4%, total +8%)
    rec_tipo = prop.get('reciclado_tipo', 'ninguno').lower()
    if rec_tipo == 'parcial':
        f_funcional *= 1.04
    elif rec_tipo == 'total':
        f_funcional *= 1.08
    
    # Ascensores del edificio
    ascensores = prop.get('ascensores_edificio', 2)
    if ascensores > 1:
        f_funcional *= 1.01
    
    # Ventilación baño
    vent_bano = prop.get('ventilacion_bano', 'natural').lower()
    if vent_bano == 'natural':
        f_funcional *= 1.02
    
    # Seguridad Aditiva (v9.6)
    f_seguridad = 1.0
    detalles = prop.get('detalles_categoria', [])
    if not isinstance(detalles, list): detalles = []
    
    seg_weights = {
        'seguridad_24hs': 1.06,
        'seguridad_tag': 1.02,
        'seguridad_camaras': 1.01,
        'seguridad_totem': 1.01
    }
    
    for item in detalles:
        if item in seg_weights:
            f_seguridad *= seg_weights[item]
    
    # Factores estructurales (Sin antigüedad)
    f_estructural = (factor_estado * factor_calidad * factor_piso * factor_vent * 
                     factor_vista * factor_ubica * factor_gas * factor_const * 
                     factor_balcon * f_funcional * f_seguridad)
    
    # Factor Pasillo v9.3 (Castigo SOLO para casas/pasos, NO para deptos)
    tipo = prop.get('tipo_inmueble', prop.get('tipo', '')).lower()
    es_depto = 'departamento' in tipo or 'depto' in tipo or 'ph' in tipo
    
    # Factor estructural BRUTO (sin anti, sin pasillo para deptos)
    f_estructural_raw = f_estructural
    
    # APLICAR FACTOR_PASILLO SOLO PARA NO-DEPTOS
    if es_depto:
        factor_pasillo = 1.0  # Deptos no tienen factor pasillo
    else:
        desc = (prop.get('descripcion_libre', '') + prop.get('nombre', '') + prop.get('direccion', '')).lower()
        es_pasillo = any(x in desc for x in ['pasillo', 'interna', 'interno', 'fondo'])
        factor_pasillo = 0.85 if es_pasillo else 1.0
        f_estructural_raw = f_estructural * factor_pasillo
    
    # FIX BUG 3: FÓRMULA HÍBRIDA ADITIVA CLAMP
    # Convertir producto a suma clamp según DICCIONARIO_DATOS.md
    # SUMA_CRUDA: [-0.40, +0.40], FACTOR: [0.70, 1.35]
    
    # Calcular delta desdes 1.0 por cada factor
    delta_estado = factor_estado - 1.0  # +0.03 para muy_bueno
    delta_calidad = factor_calidad - 1.0
    delta_vent = factor_vent - 1.0
    delta_vista = factor_vista - 1.0
    delta_piso = factor_piso - 1.0
    delta_ubica = factor_ubica - 1.0
    delta_gas = factor_gas - 1.0
    delta_balcon = factor_balcon - 1.0
    delta_funcional = f_funcional - 1.0
    delta_seguridad = f_seguridad - 1.0
    
    # Sumar todos los deltas
    suma_cruda = (delta_estado + delta_calidad + delta_vent + delta_vista + 
                 delta_piso + delta_ubica + delta_gas + delta_balcon + 
                 delta_funcional + delta_seguridad)
    
    # Clamp suma_cruda
    suma_cruda_clamped = max(-0.40, min(0.40, suma_cruda))
    
    # Factor estructural aditivo final con depreciación
    f_estructural_final = max(0.70, min(1.35, 1.0 + suma_cruda_clamped + (factor_anti - 1.0)))
    
    return {
        'total': f_estructural_final,  # Ya incluye anti si clampeado
        'estructural_puro': f_estructural_raw,
        'depreciacion': factor_anti,
        'delta_anti': factor_anti,  # Alias for compatibility
        'factor_estado': factor_estado,
        'factor_calidad': factor_calidad,
        'factor_pasillo': factor_pasillo,
        # Nuevos campos para fórmula híbrida
        'suma_cruda': suma_cruda_clamped,
        'suma_cruda_raw': suma_cruda,
        'f_estructural': f_estructural_final,
        'detalles': {
            'anti': factor_anti,
            'estrato_activo': 'Base',
            'ventana': ventana_usada
        },
        'anti': factor_anti,  # Direct access for compatibility
        'ventana': ventana_usada
    }

def scrapear_m2_argenprop():
    """ Obtenemos la media en venta en la calle de Rosario """
    import requests
    from bs4 import BeautifulSoup
    import re
    url = "https://www.argenprop.com/departamentos/venta/rosario/1-dormitorio"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    tarjetas = soup.find_all("div", class_="listing__item")

    valores_m2 = []
    for tarjeta in tarjetas:
        precio_tag = tarjeta.find("p", class_="card__price")
        if not precio_tag or "USD" not in precio_tag.text:
            continue

        precio_str = re.sub(r'[^\d]', '', precio_tag.text)
        if not precio_str:
            continue
        precio = float(precio_str)

        features = tarjeta.find("ul", class_="card__main-features")
        metros = None
        if features:
            for li in features.find_all("li"):
                if "m²" in li.text and "cub" in li.text:
                    m_str = re.sub(r'[^\d]', '', li.text)
                    if m_str:
                        metros = float(m_str)
                        break

        if precio and metros and metros > 0:
            valor_m2 = precio / metros
            if 800 <= valor_m2 <= 3000:
                valores_m2.append(valor_m2)

    if not valores_m2:
        return None

    return round(sum(valores_m2) / len(valores_m2), 0)

def actualizar_base_ciudad_web():
    """ Scrapea el promedio y lo inyecta en la serie historica y metadata """
    nuevo_valor = scrapear_m2_argenprop()
    if nuevo_valor:
        data = cargar_datos()
        data["metadata"]["base_ciudad_m2_2026"] = nuevo_valor
        anio_actual = datetime.now().year
        serie = data.get("serie_historica_m2_rosario", {}).get("datos", {})
        serie[str(anio_actual)] = nuevo_valor
        if "serie_historica_m2_rosario" not in data:
            data["serie_historica_m2_rosario"] = {"datos": {}}
        data["serie_historica_m2_rosario"]["datos"][str(anio_actual)] = nuevo_valor
        with open(DATOS_MERCADO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return nuevo_valor
    return None


def scrapear_zonaprop():
    """ Obtiene precio m2 promedio de Zonaprop para departamentos en Rosario """
    import requests
    from bs4 import BeautifulSoup
    import re
    url = "https://www.zonaprop.com.ar/departamentos-venta-rosario.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-AR,es;q=0.9"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        valores_m2 = []
        # Zonaprop usa estructura con price y area
        items = soup.find_all("div", {"data-qa": True})
        for item in items:
            price_el = item.find(attrs={"data-qa": "posting-price"})
            area_el = item.find(attrs={"data-qa": "posting-detail-area"})
            if price_el and area_el:
                price_text = price_el.text.replace("USD", "").replace("$", "").replace(".", "").strip()
                area_text = area_el.text.replace("m²", "").replace("m2", "").strip()
                try:
                    precio = float(price_text)
                    area = float(area_text)
                    if area > 0 and precio > 0:
                        m2 = precio / area
                        if 800 <= m2 <= 3000:
                            valores_m2.append(m2)
                except ValueError:
                    continue

        if valores_m2:
            return round(sum(valores_m2) / len(valores_m2), 0)
        return None
    except Exception:
        return None


def scrapear_mercadolibre():
    """ Obtiene precio m2 promedio de MercadoLibre Inmuebles para Rosario """
    import requests
    import re
    # API publica de MercadoLibre para busquedas
    url = "https://api.mercadolibre.com/sites/MLA/search"
    params = {
        "category": "MLA1459",  # Departamentos
        "state": "AR-S",  # Santa Fe
        "city": "Rosario",
        "limit": 50
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        valores_m2 = []
        for result in data.get("results", []):
            precio = result.get("price")
            attributes = result.get("attributes", [])
            area = None
            for attr in attributes:
                if attr.get("id") in ["PROPERTY_TOTAL_AREA", "PROPERTY_AREA"]:
                    area = attr.get("value_number")
                    break
            if precio and area and area > 0:
                m2 = precio / area
                if 800 <= m2 <= 3000:
                    valores_m2.append(m2)

        if valores_m2:
            return round(sum(valores_m2) / len(valores_m2), 0)
        return None
    except Exception:
        return None


def scrapear_rosariogarage():
    """ Obtiene precio m2 promedio de RosarioGarage """
    import requests
    from bs4 import BeautifulSoup
    import re
    url = "https://www.rosariogarage.com/propiedades/departamentos/venta/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        valores_m2 = []
        # Buscar cards de propiedades con precio y superficie
        cards = soup.find_all("div", class_=re.compile(r"card|property|item", re.I))
        for card in cards:
            price_text = ""
            area_text = ""
            # Intentar encontrar precio
            price_el = card.find(class_=re.compile(r"price|precio", re.I))
            if price_el:
                price_text = price_el.text
            area_el = card.find(class_=re.compile(r"area|superficie|m2|metros", re.I))
            if area_el:
                area_text = area_el.text

            if price_text and area_text:
                precio_match = re.search(r'[\d,]+', price_text.replace(".", "").replace(",", ""))
                area_match = re.search(r'[\d,]+', area_text.replace(".", "").replace(",", ""))
                if precio_match and area_match:
                    try:
                        precio = float(precio_match.group().replace(",", ""))
                        area = float(area_match.group().replace(",", ""))
                        if area > 0 and 800 <= precio / area <= 3000:
                            valores_m2.append(precio / area)
                    except ValueError:
                        continue

        if valores_m2:
            return round(sum(valores_m2) / len(valores_m2), 0)
        return None
    except Exception:
        return None


def obtener_promedio_mercado():
    """
    Scrapea TODAS las fuentes y devuelve promedio ponderado.
    Retorna dict con resultados por fuente y promedio general.
    """
    fuentes = {
        "argenprop": scrapear_m2_argenprop,
        "zonaprop": scrapear_zonaprop,
        "mercadolibre": scrapear_mercadolibre,
        "rosariogarage": scrapear_rosariogarage,
    }

    resultados = {}
    valores_validos = []

    for nombre, func in fuentes.items():
        try:
            valor = func()
            resultados[nombre] = valor
            if valor is not None:
                valores_validos.append(valor)
        except Exception as e:
            resultados[nombre] = None

    promedio = round(sum(valores_validos) / len(valores_validos), 0) if valores_validos else None

    return {
        "fuentes": resultados,
        "promedio": promedio,
        "fuentes_exitosas": len(valores_validos),
        "total_fuentes": len(fuentes)
    }


def actualizar_datos_mercado(valor_manual=None):
    """
    Actualiza la serie historica con datos de scraping o valor manual.
    Si valor_manual es provisto, tiene prioridad sobre el scraping.

    Args:
        valor_manual: float opcional, valor ingresado manualmente por el usuario

    Returns:
        dict con resultado de la actualizacion
    """
    data = cargar_datos()
    anio_actual = datetime.now().year
    mes_actual = datetime.now().strftime("%Y-%m")

    if valor_manual is not None and valor_manual > 0:
        # Input manual tiene prioridad maxima
        nuevo_valor = round(valor_manual, 0)
        fuente = "manual"
    else:
        # Usar promedio de scraping
        resultado = obtener_promedio_mercado()
        nuevo_valor = resultado.get("promedio")
        if nuevo_valor is None:
            return {"exito": False, "error": "Ninguna fuente de scraping respondio correctamente"}
        fuente = f"scraping ({resultado['fuentes_exitosas']}/{resultado['total_fuentes']} fuentes)"

    # Actualizar metadata
    data["metadata"]["base_ciudad_m2_2026"] = nuevo_valor

    # Agregar a serie historica (sobreescribe si ya existe el año)
    if "serie_historica_m2_rosario" not in data:
        data["serie_historica_m2_rosario"] = {"datos": {}}

    data["serie_historica_m2_rosario"]["datos"][str(anio_actual)] = nuevo_valor

    # Registrar en metadata cuando fue la ultima actualizacion
    data["metadata"]["ultima_actualizacion"] = mes_actual
    data["metadata"]["fuente_ultima_actualizacion"] = fuente

    with open(DATOS_MERCADO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {
        "exito": True,
        "valor": nuevo_valor,
        "fuente": fuente,
        "fecha": mes_actual
    }


def interpolar_precio_historico(serie_datos, año):
    """
    Interpola linealmente entre puntos reales de la serie historica.
    Si el año existe, devuelve el precio real directamente.
    Si esta fuera de rango, usa el extremo mas cercano.
    """
    años = sorted(int(k) for k in serie_datos.keys())

    año_int = int(año) if año == int(año) else año

    if str(año_int) in serie_datos and año == int(año):
        return serie_datos[str(año_int)]

    for i in range(len(años) - 1):
        a0, a1 = años[i], años[i + 1]
        if a0 <= año_int <= a1:
            if a0 == a1:
                return serie_datos[str(a0)]
            t = (año_int - a0) / (a1 - a0)
            return serie_datos[str(a0)] + t * (serie_datos[str(a1)] - serie_datos[str(a0)])

    if año_int < años[0]:
        return serie_datos[str(años[0])]

    if año_int > años[-1]:
        if len(años) >= 2:
            pendiente = serie_datos[str(años[-1])] - serie_datos[str(años[-2])]
            return serie_datos[str(años[-1])] + pendiente * (año_int - años[-1])

    return serie_datos[str(años[-1])]

def obtener_precio_base_anio(año):
    """
    Obtiene el precio base real del m2 en Rosario para un año dado.
    Usa la serie historica con interpolacion lineal.
    """
    data = cargar_datos()
    serie = data.get("serie_historica_m2_rosario", {}).get("datos", {})
    if not serie:
        return data["metadata"]["base_ciudad_m2_2026"]
    return interpolar_precio_historico(serie, año)

def obtener_factor_barrio(barrio, data):
    barrio_norm = barrio.lower().strip().replace(" ", "_")
    return data.get("factor_barrio", {}).get(barrio_norm, data.get("factor_barrio", {}).get("default", 1.00))

def obtener_factor_piso(piso, data):
    try:
        piso = int(piso)
    except:
        piso = 1
    p_fm = data["factores_propiedad"]["piso"]
    if piso == 0:
        return p_fm.get("pb", 0.95)
    elif piso <= 3:
        return p_fm.get("bajo", 1.00)
    elif piso <= 6:
        return p_fm.get("medio", 1.02)
    else:
        return p_fm.get("alto", 1.04)

def calcular_m2_equivalente(prop_data):
    """
    Calcula los m2 equivalentes considerando superficies diferenciadas.
    
    Factores:
    - cubiertos: 100%
    - semicubiertos: 60%
    - descubiertos (patio/terraza): según propiedad_exterior
      - propio: 25%
      - comun: 18%
    - comunes: 35%
    """
    m2_cub = prop_data.get('m2_cubiertos', 0) or prop_data.get('m2', 0)
    m2_sem = prop_data.get('m2_semicubiertos', 0) or 0
    m2_desc = prop_data.get('m2_descubiertos', 0) or 0
    m2_com = prop_data.get('m2_comunes', 0) or 0
    
    tipo_ext = prop_data.get('tipo_exterior', 'ninguno')
    prop_ext = prop_data.get('propiedad_exterior', 'comun')
    
    factor_desc = 0
    if tipo_ext == 'patio':
        if prop_ext == 'propio':
            factor_desc = 0.25
        else:
            factor_desc = 0.18
    elif tipo_ext == 'balcon':
        factor_desc = 0.50
    elif tipo_ext == 'terraza':
        factor_desc = 0.20
    
    m2_equivalente = (
        m2_cub 
        + m2_sem * 0.6 
        + m2_desc * factor_desc 
        + m2_com * 0.35
    )
    
    return max(m2_equivalente, m2_cub)


def obtener_ajuste_patio(prop_data):
    """
    Calcula el ajuste hedónico por patio en PB.
    
    Ajustes:
    - PB sin patio: -7%
    - PB con patio propio: +12%
    - PB con patio común exclusivo: +8%
    """
    piso = prop_data.get('piso', 0)
    tiene_patio = prop_data.get('tiene_patio', False)
    prop_ext = prop_data.get('propiedad_exterior', 'comun')
    
    if piso == 0:
        if tiene_patio:
            if prop_ext == 'propio':
                return 0.12
            else:
                return 0.08
        else:
            return -0.07
    
    return 0.0


def obtener_descuento_liquidez(prop_data):
    """
    Determina el descuento por liquidez.
    
    - Con patio: 15% (más líquido que depto estándar)
    - Sin patio: 20% (descuento estándar)
    """
    tiene_patio = prop_data.get('tiene_patio', False)
    return 0.15 if tiene_patio else 0.20


def calcular_valor_m2(prop_data, fecha):
    """
    Calcula valor del m2 usando el MODELO DESACOPLADO AVANZADO (v4.0).
    Usa precios historicos REALES del mercado de Rosario como base.
    """
    data = cargar_datos()
    f_p = data["factores_propiedad"]

    if isinstance(fecha, str):
        fecha_dt = datetime.strptime(fecha, "%Y-%m")
    else:
        fecha_dt = fecha

    anio = fecha_dt.year

    # Precio base REAL del mercado para este año
    precio_base = obtener_precio_base_anio(anio)

    # 1. Barrio
    factor_barrio = obtener_factor_barrio(prop_data.get("zona", "default"), data)

    # 2. Estado y Antigüedad
    estado_key = prop_data.get("estado_detalle", "bueno").lower().replace(" ", "_")
    if "estrenar" in estado_key: estado_key = "a_estrenar"
    factor_estado = f_p["estado"].get(estado_key, 1.00)

    antiguedad = prop_data.get("antiguedad", 0)
    try:
        antiguedad = int(antiguedad)
    except:
        antiguedad = 0
    if antiguedad > 10:
        factor_antiguedad = max(1.0 - ((antiguedad - 10) * 0.005), 0.70)
    else:
        factor_antiguedad = 1.0

    # 3. Caracteristicas Constructivas y Funcionales
    factor_calidad = f_p["calidad"].get(prop_data.get("calidad_edificio", "media").lower(), 1.00)
    factor_piso = obtener_factor_piso(prop_data.get("piso", 0), data)

    vent_key = prop_data.get("ventilacion", "simple").lower().strip()
    factor_vent = f_p["ventilacion"].get(vent_key, 1.00)

    suelo_key = prop_data.get("terminaciones_suelo", "estandar").lower().replace(" ", "_")
    factor_suelo = f_p["terminaciones_suelo"].get(suelo_key, 1.00)

    cocina_key = prop_data.get("distribucion_cocina", "integrada").lower().replace(" ", "_")
    factor_cocina = f_p["distribucion_cocina"].get(cocina_key, 1.00)

    carp_key = prop_data.get("carpinteria", "estandar").lower().strip()
    factor_carp = f_p["carpinteria"].get(carp_key, 1.00)

    orient_key = prop_data.get("orientacion", "este").lower().strip()
    factor_orient = f_p["orientacion"].get(orient_key, 1.00)

    detalles = prop_data.get("detalles_categoria", [])
    suma_detalles = 0
    for d in detalles:
        d_key = d.lower().replace(" ", "_")
        suma_detalles += f_p["detalles_categoria"].get(d_key, 0)
    factor_detalles = 1.0 + suma_detalles

    # FORMULA FINAL MULTIPLICATIVA
    valor_m2 = (
        precio_base
        * factor_barrio
        * factor_estado
        * factor_antiguedad
        * factor_calidad
        * factor_piso
        * factor_vent
        * factor_suelo
        * factor_cocina
        * factor_carp
        * factor_orient
        * factor_detalles
    )

    return round(valor_m2, 2)


def construir_serie_historica(propiedad_data, anios=10, fecha_ref=None):
    if fecha_ref is None:
        fecha_tope = datetime.now()
    else:
        if isinstance(fecha_ref, str):
            fecha_tope = datetime.strptime(fecha_ref, "%Y-%m")
        else:
            fecha_tope = fecha_ref

    anio_inicio = fecha_tope.year - anios
    fecha_cursor = datetime(anio_inicio, 1, 1)

    serie = []
    while fecha_cursor <= fecha_tope:
        fecha_str = fecha_cursor.strftime("%Y-%m")
        val = calcular_valor_m2(propiedad_data, fecha_str)
        serie.append({
            "fecha": fecha_str,
            "valor_m2": round(val, 0),
            "fuente": "modelo v4.0 con serie historica real"
        })
        if fecha_cursor.month == 12:
            fecha_cursor = datetime(fecha_cursor.year + 1, 1, 1)
        else:
            fecha_cursor = datetime(fecha_cursor.year, fecha_cursor.month + 1, 1)

    return serie


def calcular_plusvalia_serie(serie, fecha_compra=None):
    if not serie or len(serie) < 2:
        return {'plusvalia_mensual_pct': 0, 'plusvalia_acumulada_pct': 0, 'tendencia': 'neutral'}

    ultimo = serie[-1]['valor_m2']
    penultimo = serie[-2]['valor_m2']
    plusvalia_mensual = ((ultimo / penultimo) - 1) * 100 if penultimo > 0 else 0

    if fecha_compra:
        valor_compra_m2 = None
        for s in serie:
            if s['fecha'] >= fecha_compra:
                valor_compra_m2 = s['valor_m2']
                break
        if valor_compra_m2 and valor_compra_m2 > 0:
            plusvalia_acumulada = ((ultimo / valor_compra_m2) - 1) * 100
        else:
            primer_valor = serie[0]['valor_m2']
            plusvalia_acumulada = ((ultimo / primer_valor) - 1) * 100 if primer_valor > 0 else 0
    else:
        primer_valor = serie[0]['valor_m2']
        plusvalia_acumulada = ((ultimo / primer_valor) - 1) * 100 if primer_valor > 0 else 0

    if len(serie) >= 6:
        ultimos_6 = [s['valor_m2'] for s in serie[-6:]]
        tendencia_valor = sum(ultimos_6) / len(ultimos_6)
        if ultimo > tendencia_valor * 1.02:
            tendencia = 'alcista'
        elif ultimo < tendencia_valor * 0.98:
            tendencia = 'bajista'
        else:
            tendencia = 'neutral'
    else:
        tendencia = 'alcista' if plusvalia_mensual > 0.5 else ('bajista' if plusvalia_mensual < -0.5 else 'neutral')

    return {
        'plusvalia_mensual_pct': round(plusvalia_mensual, 2),
        'plusvalia_acumulada_pct': round(plusvalia_acumulada, 2),
        'tendencia': tendencia,
    }


def valuar_propiedad(propiedad, fecha_ref=None):
    m2_equivalente = calcular_m2_equivalente(propiedad)
    m2_original = propiedad.get("m2", 0)
    fecha_compra = propiedad.get("fecha_compra", None)

    fecha_ref_str = None
    if fecha_ref:
        if isinstance(fecha_ref, str):
            fecha_ref_str = fecha_ref
        elif isinstance(fecha_ref, datetime):
            fecha_ref_str = fecha_ref.strftime("%Y-%m")
    else:
        fecha_ref_str = datetime.now().strftime("%Y-%m")

    valor_m2 = calcular_valor_m2(propiedad, fecha_ref_str)
    ajuste_patio = obtener_ajuste_patio(propiedad)
    valor_m2_ajustado = valor_m2 * (1 + ajuste_patio)
    
    rango_min = valor_m2_ajustado * 0.90
    rango_max = valor_m2_ajustado * 1.10

    serie = construir_serie_historica(propiedad, anios=10, fecha_ref=fecha_ref_str)
    plusvalia = calcular_plusvalia_serie(serie, fecha_compra)

    valor_propiedad = valor_m2_ajustado * m2_equivalente
    descuento_liquidez = obtener_descuento_liquidez(propiedad)
    valor_realizable = valor_propiedad * (1 - descuento_liquidez)

    ajustes_detalle = []
    if ajuste_patio != 0:
        ajustes_detalle.append(f"Ajuste patio: {'+' if ajuste_patio > 0 else ''}{ajuste_patio*100:.0f}%")
    ajustes_detalle.append(f"m² equivalentes: {m2_equivalente:.1f} (vs {m2_original} totales)")
    ajustes_detalle.append(f"Descuento liquidez: -{descuento_liquidez*100:.0f}%")

    justificacion = (
        f"Valuacion v5.0 con superficies diferenciadas al {fecha_ref_str}. "
        f"Basado en serie historica REAL de precios m2 Rosario (2000-2026) "
        f"con m2 equivalentes ({m2_equivalente:.1f}m²), ajuste patio PB ({ajuste_patio*100:+.0f}%) "
        f"y descuento liquidez ({descuento_liquidez*100:.0f}%). "
        f"Rango estimado: USD {rango_min:,.0f} - {rango_max:,.0f}/m2."
    )

    return {
        'valor_m2_actual_usd': round(valor_m2_ajustado, 2),
        'rango_m2': f"USD {rango_min:,.0f} - {rango_max:,.0f}",
        'valor_propiedad_usd': round(valor_propiedad, 0),
        'valor_realizable_usd': round(valor_realizable, 0),
        'm2_equivalentes': m2_equivalente,
        'ajuste_patio_pct': ajuste_patio * 100,
        'descuento_liquidez_pct': descuento_liquidez * 100,
        'serie_mensual_m2': serie,
        'plusvalia_mensual_pct': plusvalia['plusvalia_mensual_pct'],
        'plusvalia_acumulada_pct': plusvalia['plusvalia_acumulada_pct'],
        'tendencia': plusvalia['tendencia'],
        'factores_aplicados': {},
        'nivel_confianza': 'alto',
        'justificacion': justificacion,
        'fecha_valuacion': fecha_ref_str,
    }


def valuar_propiedad_v6(propiedad, fecha_ref=None):
    """
    ✅ Modelo v6.0 - AVM robusto con:
    - Índice histórico de ciudad
    - Microzonas dinámicas
    - Fusión continua
    - Normalización temporal
    - Protección contra edge cases
    """
    prop = sanitizar_propiedad(propiedad)
    
    data = cargar_datos()
    indice = data.get('indice_ciudad', {}).get('data', {})
    base_year = obtener_base_year(data)
    
    if base_year not in indice:
        base_year = max(indice.keys(), key=lambda x: int(x))
    indice_base = indice.get(str(base_year), 1.0)
    
    if indice_base <= 0:
        indice_base = 1.0
    
    fecha_ref_str = None
    if fecha_ref:
        if isinstance(fecha_ref, str):
            fecha_ref_str = fecha_ref[:7] if len(fecha_ref) >= 7 else fecha_ref
        elif isinstance(fecha_ref, datetime):
            fecha_ref_str = fecha_ref.strftime("%Y-%m")
    else:
        fecha_ref_str = datetime.now().strftime("%Y-%m")
    
    año_ref = fecha_ref_str[:4]
    año_compra = prop.get('fecha_compra', '2020-01-01')[:4]
    
    indice_ref = obtener_indice_cercano(indice, año_ref)
    indice_compra = obtener_indice_cercano(indice, año_compra)
    
    valor_hist = prop.get('valor_compra_usd', 0) * (indice_ref / indice_compra) if indice_compra > 0 else 0
    
    zona_key = MAPEO_ZONAS.get(prop.get('zona'), 'centro')
    zona_key = ajustar_microzona(prop, zona_key)
    
    # ===== NUEVO: Location Engine =====
    lat = prop.get('lat')
    lon = prop.get('lon')
    
    if lat is not None and lon is not None:
        try:
            anclas = cargar_anclas()
            m2_base_geo = calcular_precio_m2(lat, lon, anclas)
            confianza_geo = estimar_confianza(lat, lon, anclas)
        except:
            m2_base_geo = None
            confianza_geo = None
    else:
        m2_base_geo = None
        confianza_geo = None
    
    # PRIORIZAR valor geográfico si hay coordenadas
    # (el location engine es más preciso que la zona estática)
    if m2_base_geo:
        m2_base = m2_base_geo
        # Estimar liquidez basada en el m2_base geográfico
        if m2_base >= 1600:
            liquidez_default = 1.10
        elif m2_base >= 1300:
            liquidez_default = 1.00
        elif m2_base >= 1100:
            liquidez_default = 0.95
        else:
            liquidez_default = 0.90
    else:
        zona = data.get('microzonas', {}).get(zona_key, data.get('microzonas', {}).get('centro', {'m2_base': 1650, 'liquidez': 1.10}))
        m2_base = zona.get('m2_base', 1650)
        liquidez_default = zona.get('liquidez', 1.0)
    
    m2_equiv = calcular_m2_equivalentes(prop)
    factores = calcular_factores(prop)
    factor_total = factores.get('total', 1.0)
    valor_comp_actual = m2_equiv * m2_base * factor_total
    
    valor_comp_hist = valor_comp_actual * (indice_ref / indice_base) if indice_base > 0 else valor_comp_actual
    
    # === CAP HISTÓRICO: evitar distorsiones en propiedades antiguas ===
    # Limitar contra valor_comp (el comparable histórico), no contra valor_compra
    if valor_comp_hist > 0:
        valor_hist = min(valor_hist, valor_comp_hist * 1.5)
        valor_hist = max(valor_hist, valor_comp_hist * 0.7)
    
    if valor_hist <= 0:
        pesos = {'comp': 1.0, 'hist': 0.0}
        valor = valor_comp_hist
    else:
        ratio = valor_comp_hist / valor_hist if valor_hist > 0 else 1
        ratio = max(0.5, min(ratio, 2.0))
        pesos = obtener_pesos(ratio)
        valor = valor_comp_hist * pesos['comp'] + valor_hist * pesos['hist']
    
    valor = min(valor, valor_comp_hist * 1.15) if valor_comp_hist > 0 else valor
    valor = max(valor, valor_comp_hist * 0.85) if valor_comp_hist > 0 else valor
    
    # === NUEVO MODELO DE DESCUENTO POR LIQUIDEZ ===
    # Siempre hay descuento base del 6%
    descuento_base = 0.06
    liquidez = liquidez_default
    
    # Ajuste por liquidez de la zona
    if liquidez > 1.0:
        ajuste_liquidez = -0.02   # zonas premium: menos descuento
    elif liquidez < 1.0:
        ajuste_liquidez = 0.03  # zonas menos líquidas: más descuento
    else:
        ajuste_liquidez = 0.0
    
    descuento_total = descuento_base + ajuste_liquidez
    descuento_total = max(0.03, min(descuento_total, 0.12))  # limitar entre 3% y 12%
    
    valor_realizable = valor * (1 - descuento_total)
    
    if valor_hist <= 0 or valor_comp_hist <= 0:
        desviacion = 0
    else:
        desviacion = abs(valor_hist - valor_comp_hist) / valor_comp_hist
    
    confianza = 'alta' if desviacion < 0.15 else 'media' if desviacion < 0.30 else 'baja'
    
    # Calcular tendencia basada en la relación entre comparable e histórico
    if valor_comp_hist > 0 and valor_hist > 0:
        ratio_tendencia = valor_comp_hist / valor_hist
        if ratio_tendencia > 1.10:
            tendencia = 'alcista'
        elif ratio_tendencia < 0.90:
            tendencia = 'bajista'
        else:
            tendencia = 'neutral'
    else:
        tendencia = 'neutral'
    
    justificacion = (
        f"AVM v6.0: Indice ciudad {indice_ref:.2f} vs base {indice_base:.2f}, "
        f"m2_base={m2_base:.0f}, m2_equiv={m2_equiv:.1f}, factores={factor_total:.2f}, "
        f"pesos: hist={pesos['hist']:.2f}/comp={pesos['comp']:.2f}, "
        f"confianza={confianza}, desviacion={desviacion*100:.1f}%"
    )
    
    rango_min = valor * 0.90
    rango_max = valor * 1.10
    
    return {
        'valor_propiedad_usd': round(valor, 0),
        'valor_realizable_usd': round(valor_realizable, 0),
        'valor_m2_actual_usd': round(valor_comp_actual / m2_equiv, 2) if m2_equiv > 0 else 0,
        'valor_historico': round(valor_hist, 0),
        'valor_comparable': round(valor_comp_hist, 0),
        'pesos': pesos,
        'confianza': confianza,
        'desviacion_pct': round(desviacion * 100, 1),
        'liquidez': liquidez_default,
        'm2_equivalentes': m2_equiv,
        'zona_micro': prop.get('zona', 'centro'),
        'tendencia': tendencia,
        'justificacion': justificacion,
        'rango_m2': f"USD {rango_min:,.0f} - {rango_max:,.0f}",
        'plusvalia_acumulada_pct': round(((valor / valor_hist) - 1) * 100, 2) if valor_hist > 0 else 0,
        'serie_mensual_m2': [],
    }

def obtener_nodos_dinamicos(lat, lon, tipo, operacion, dorms=2, fecha_ref=None):
    """
    Obtiene nodos dinámicos para visualización en UI.
    Wrapper que usa la lógica de cluster con radios progresivos.
    """
    if lat is None or lon is None:
        return {"error": "Sin coordenadas"}
    
    # Inferir zona por coordenadas
    zona = inferir_zona_por_coordenadas(lat, lon)
    
    # Usar la función de cluster
    try:
        mediana, n_comparables, meta = obtener_mediana_cluster_v2(
            zona=zona,
            dormitorios=dorms,
            operacion=operacion,
            lat_ref=lat,
            lon_ref=lon,
            fecha_ref=fecha_ref
        )
        
        return {
            "valor_m2": mediana,
            "n_nodos": n_comparables,
            "radio_usado": meta.get("radio_usado"),
            "metodo": meta.get("percentil_usado", "P33"),
            "zona_inferida": zona,
            "n_raw": meta.get("n_raw", 0),
            "n_filtradas": meta.get("n_filtradas", 0)
        }
    except Exception as e:
        return {"error": str(e)}


def valuar_propiedad_v7(propiedad, fecha_ref=None):
    """
    🚀 Modelo v7.0 - Evolución Híbrida PROFESIONAL
    Fusiona el Motor VPP (Clusters/Market) con Factores Físicos (Legacy).
    """
    import os
    import logging
    from datetime import datetime, timedelta
    from parsers.motor_vpp_core import load_cache_cached, cargar_anclas_cached, get_binance_usdt_ars
    
    # Setup logging to file
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log_valuacion')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, f'valuacion_{datetime.now().strftime("%Y%m%d")}.log'), mode='a')
        ]
    )
    logger = logging.getLogger()
    
    # Fecha dinámica por defecto - siempre usa datos recientes
    if fecha_ref is None:
        fecha_ref = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"[FECHA] Usando fecha actual por defecto: {fecha_ref}")
    
    prop = sanitizar_propiedad(propiedad)
    cache = load_cache_cached()
    anclas = cargar_anclas_cached()
    
    # Log de entrada
    logger.info(f"=== VALUACION: {prop.get('nombre', prop.get('direccion', 'Unknown'))} ===")
    logger.info(f"zona: {prop.get('zona')}, dorm: {prop.get('dormitorios')}, m2: {prop.get('m2_cubiertos')}")
    logger.info(f"lat: {prop.get('lat')}, lon: {prop.get('lon')}")
    logger.info(f"estado: {prop.get('estado_detalle')}, anio: {prop.get('anio_construccion')}")
    
    # 1. Obtener Precios Base de Mercado (Venta y Alquiler)
    props_cache = cache.get("propiedades", []) if cache else []
    ventas_cache = [p for p in props_cache if p.get('operacion') == 'venta' or p.get('operacion') is None]
    alquileres_cache = [p for p in props_cache if p.get('operacion') == 'alquiler']
    
    lat = prop.get('lat', -32.9545) # Fallback Ayacucho
    lon = prop.get('lon', -60.6455)
    m2_obj = prop.get('m2', 30)
    zona_txt = prop.get('zona', 'centro')
    
    # 1. Obtener m2 equivalentes y Antigüedad Dinámica
    m2_equiv = calcular_m2_equivalentes(prop)
    
    anio_const = prop.get('anio_construccion', 2026 - prop.get('antiguedad', 0))
    antiguedad_dinamica = 2026 - anio_const
    # Actualizamos el diccionario prop para que calcular_factores use la dinámica
    prop['antiguedad'] = antiguedad_dinamica 
    
    # 1. Valuación VPP Híbrida v10.1 (Calibrada)
    dorms = prop.get('dormitorios', 2)
    anio_const = prop.get('anio_construccion', 2020)
    
    # Encontrar ancla por coordenadas (v11.2) o por zona (fallback)
    valor_ancla_geo = 1500  # default
    ancla_seleccionada = None
    
    prop_lat = prop.get('lat')
    prop_lon = prop.get('lon')
    
    # Si la propiedad tiene coordenadas, usar ancla por cercanía
    if prop_lat and prop_lon:
        try:
            import math
            anclas_list = anclas.get('anclas', list(anclas.values())) if isinstance(anclas, dict) else anclas
            
            min_dist = float('inf')
            for a in anclas_list:
                a_lat = a.get('lat')
                a_lon = a.get('lon')
                if a_lat is None or a_lon is None:
                    continue
                # Haversine
                R = 6371
                lat1, lon1, lat2, lon2 = math.radians(prop_lat), math.radians(prop_lon), math.radians(a_lat), math.radians(a_lon)
                dlat, dlon = lat2 - lat1, lon2 - lon1
                dist = 2 * R * math.asin(math.sqrt(math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2))
                
                if dist < min_dist:
                    min_dist = dist
                    valor_ancla_geo = a.get('usd_m2', 1500)
                    ancla_seleccionada = a.get('id')
        except:
            pass
    
    # Fallback: búsqueda por zona si no hay coordenadas
    if not ancla_seleccionada:
        try:
            if isinstance(anclas, dict):
                anclas_list = anclas.get('anclas', list(anclas.values()))
            else:
                anclas_list = anclas
            
            for a in anclas_list:
                if zona_txt.lower() in str(a.get('id', '')).lower():
                    valor_ancla_geo = a.get('usd_m2', 1500)
                    ancla_seleccionada = a.get('id')
                    break
        except:
            pass
    
    # Usar cluster v2 directamente para m2_base_venta (más preciso)
    m2_base_venta_raw, n_v, meta_venta = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona_txt),
        dormitorios=dorms,
        operacion='venta',
        lat_ref=lat,
        lon_ref=lon,
        fecha_ref=fecha_ref
    )
    
    # Si v2 tiene valor, usarlo; si no, fallback a ancla
    if m2_base_venta_raw > 0:
        m2_base_venta = m2_base_venta_raw
        metodo_origen = f"cluster_v2 (P{meta_venta.get('percentil_usado','33')}, {n_v} props)"
    else:
        # Fallback a ancla
        antiguedad = 2026 - anio_const
        factor_deprec = max(0.5, 1.0 - (antiguedad * 0.006))
        m2_base_venta = valor_ancla_geo * factor_deprec
        metodo_origen = "Ancla (fallback)"
    
    # Metadata REALES de v2
    if meta_venta.get('radio_usado'):
        resolution = 'GEO'
        confidence = 'ALTA' if n_v >= 15 else 'MEDIA' if n_v >= 8 else 'BAJA'
    elif n_v > 0:
        resolution = 'ZONAL'
        confidence = 'MEDIA'
    else:
        resolution = 'GLOBAL'
        confidence = 'BAJA'
    
    resolution_metadata = {
        'resolution': resolution,
        'confidence': confidence,
        'method': 'cluster_v2',
        'n_propiedades': n_v,
        'radio_usado': meta_venta.get('radio_usado'),
        'percentil_usado': meta_venta.get('percentil_usado'),
        'zona_resol': meta_venta.get('zona_resolucion'),
        'm2_base_source': metodo_origen
    }
    
    logger.info(f"--- RESOLUTION ---")
    logger.info(f"resolution: {resolution}, confidence: {confidence}")
    logger.info(f"n_propiedades: {n_v}, radio: {meta_venta.get('radio_usado')}")
    logger.info(f"percentil: {meta_venta.get('percentil_usado')}")
    
    # Alquiler: obtener del cluster o fallback
    # NOTA: El cluster devuelve ARS/m2 directamente (no USD)
    # Usar zona normalizada para mejor match con cache
    zona_alq = normalizar_zona(zona_txt)
    m2_base_alq_raw, n_a, meta_alq = obtener_mediana_cluster_v2(zona=zona_alq, dormitorios=dorms, operacion='alquiler', lat_ref=lat, lon_ref=lon)
    
    # Fallback si no hay datos específicos (en ARS/m²)
    # Ajustar para entrar en rango:
    m2_base_alquiler = m2_base_alq_raw if m2_base_alq_raw > 0 else (11500 if dorms >= 2 else 13500)
    
    # 2. Factores Físicos Propios v10.1 (Con CAP)
    f_dict = calcular_factores(prop)
    factores_base = f_dict['total']
    
    logger.info(f"--- FACTORES ---")
    logger.info(f"factor_estado: {f_dict.get('factor_estado')}, factor_calidad: {f_dict.get('factor_calidad')}")
    logger.info(f"factor_anti (deprec): {f_dict.get('depreciacion')}")
    logger.info(f"f_estructural: {f_dict.get('estructural_puro')}")
    logger.info(f"factores_base (total): {factores_base}")
    
    # CAP de atributos para evitar snowball effect
    if factores_base > MAX_BONUS_ATRIBUTOS:
        excedente = factores_base - MAX_BONUS_ATRIBUTOS
        factores_base = MAX_BONUS_ATRIBUTOS + (excedente * 0.4)
    
    factores_finales = factores_base
    
    # 3. Metros Específicos para Alquiler (Prioriza Cubiertos)
    m2_cub = prop.get('m2_cubiertos', m2_equiv)
    m2_desc = prop.get('m2_descubiertos', 0)
    # En alquiler el patio vale mucho menos que en venta (coef 0.1)
    m2_equiv_alquiler = m2_cub + (m2_desc * 0.1)
    
    # 3. Valores Base (Asking Price / Precio de Lista v9.0)
    # Venta: Impacto Total de Factores
    valor_venta = m2_equiv * m2_base_venta * f_dict['total']
    
    logger.info(f"--- CALCULO ---")
    logger.info(f"m2_equiv: {m2_equiv}, m2_base_venta: {m2_base_venta}")
    logger.info(f"valor_venta (before NLP): {valor_venta}")
    
    # Alquiler: v9.1 Sensibilidad Atenuada de Calidad (Buenas Prácticas)
    f_puros = (0.95 if prop.get('piso') == 0 else 1.0) * (1.10 if 'cruzada' in prop.get('ventilacion','') else 1.0)
    fact_ec = f_dict['factor_estado'] * f_dict['factor_calidad']
    # Aplicamos sensibilidad del 50% al premio por estado/calidad
    factores_alquiler = f_dict['depreciacion'] * f_puros * (1.0 + (fact_ec - 1.0) * 0.50)
    
    # Regional Rental Buffer v9.4: Sinceramiento Periferia (Standard vs Profunda)
    tipo_det = prop.get('tipo_inmueble', prop.get('tipo', '')).lower()
    if 'casa' in tipo_det and any(x in zona_txt.lower() for x in ['oeste', 'sur', 'norte']):
        # Detección de Periferia Profunda (Humble areas)
        direccion = prop.get('direccion', '')
        desc = prop.get('descripcion_libre', '').lower()
        barrios_humildes = ['triangulo', 'godoy', 'moderno', 'ludueña', 'flores', 'empalme', 'industrial']
        
        # Extraer altura de calle si existe
        altura = 0
        match_altura = re.search(r'\d+', direccion)
        if match_altura:
            altura = int(match_altura.group())
        
        es_profunda = altura > 4000 or any(b in desc for b in barrios_humildes) or any(b in direccion.lower() for b in barrios_humildes)
        
        buffer_regional = 0.55 if es_profunda else 0.75
        m2_base_alquiler *= buffer_regional
    
    # GAP_ALQUILER: 0.85 -> 0.92 (post-desregulación Rosario 2024+)
    GAP_ALQUILER = 0.92
    alquiler_mensual_ars = m2_equiv_alquiler * m2_base_alquiler * factores_alquiler * GAP_ALQUILER
    
    # 4. Ajustes Extra (NLP y Moneda)
    usdt_ars = get_binance_usdt_ars()
    from parsers.nlp_inmobiliario import calcular_ajuste_nlp_detallado
    desc = prop.get('descripcion_libre', '')
    ajuste_nlp, detecciones_nlp = calcular_ajuste_nlp_detallado(desc)
    
    # AJUSTE 3: Cap NLP diferenciado por dormitorios
    dorms = prop.get('dormitorios', 2)
    nlp_cap = 0.03 if dorms == 1 else 0.05  # 1 dorm: 3%, 2+: 5%
    ajuste_nlp_capped = min(ajuste_nlp, nlp_cap)
    
    # Aplicar NLP al Precio de Lista
    valor_venta = valor_venta * (1 + ajuste_nlp_capped)
    alquiler_mensual_ars = alquiler_mensual_ars * (1 + ajuste_nlp_capped)
    
    logger.info(f"NLP: {ajuste_nlp}")
    logger.info(f"valor_venta (after NLP): {valor_venta}")
    
    # 5. Valor Realizable (Cierre Real con GAP del 8%)
    GAP_CIERRE = 0.92
    valor_realizable = valor_venta * GAP_CIERRE
    
    logger.info(f"GAP_CIERRE: {GAP_CIERRE}")
    logger.info(f"valor_realizable: {valor_realizable}")
    
    # 5. Cálculo de Rentabilidad NETA (v8.0)
    expensas_ars = prop.get('expensas_ars', 0)
    # Mantenimiento estimado: 0.5% del valor de la propiedad anual
    mantenimiento_mensual_ars = (valor_venta * 0.005 * usdt_ars) / 12
    alquiler_neto_mensual_ars = alquiler_mensual_ars - expensas_ars - mantenimiento_mensual_ars
    
    roi_bruto_anual = (alquiler_mensual_ars * 12 / usdt_ars) / valor_realizable * 100 if valor_realizable > 0 else 0
    cap_rate_neto = (alquiler_neto_mensual_ars * 12 / usdt_ars) / valor_realizable * 100 if valor_realizable > 0 else 0
    
    # 6. Histórico y Plusvalía Segregada
    data_m = cargar_datos()
    indices = data_m.get('indice_ciudad', {}).get('data', {})
    
    fecha_compra_raw = prop.get('fecha_compra', '2024-01-01')
    valor_compra_usd = prop.get('valor_compra_usd', 0)
    
    anio_compra = str(fecha_compra_raw[:4])
    indice_hoy = indices.get("2026", 1.25)
    indice_compra = indices.get(anio_compra, indice_hoy)
    indice_12m = indices.get("2025", 1.18)
    
    # Plusvalía de ciclo
    tipo_plusvalia = "Real (Contable)" if valor_compra_usd > 0 else "Estimada (Mercado)"
    if valor_compra_usd > 0:
        plusvalia_ciclo_usd = valor_venta - valor_compra_usd
        plusvalia_ciclo_pct = (plusvalia_ciclo_usd / valor_compra_usd) * 100
    else:
        valor_mercado_compra = (valor_venta / indice_hoy) * indice_compra
        plusvalia_ciclo_usd = valor_venta - valor_mercado_compra
        plusvalia_ciclo_pct = ((valor_venta / valor_mercado_compra) - 1) * 100 if valor_mercado_compra > 0 else 0
        
    valor_mercado_12m = (valor_venta / indice_hoy) * indice_12m
    plusvalia_12m_usd = valor_venta - valor_mercado_12m
    plusvalia_12m_pct = ((valor_venta / valor_mercado_12m) - 1) * 100 if valor_mercado_12m > 0 else 0

    justificacion = (
        f"VPP v8.0: Modelo Híbrido Dinámico ({n_v} comps). "
        f"Ajuste NLP: {ajuste_nlp*100:+.1f}%. "
        f"Cap Rate Neto: {cap_rate_neto:.2f}% (Cap Bruto: {roi_bruto_anual:.1f}%). "
        f"Plusvalia {tipo_plusvalia}: {plusvalia_ciclo_pct:+.1f}%."
    )
    
    rango_min = valor_venta * 0.90
    rango_max = valor_venta * 1.10
    
    return {
        'valor_propiedad_usd': round(valor_venta, 0),
        'valor_realizable_usd': round(valor_realizable, 0),
        'valor_m2_actual_usd': round(valor_venta / m2_equiv, 2) if m2_equiv > 0 else 0,
        'm2_base_venta': round(m2_base_venta, 2),  # v11.0: m² base del cluster (filtrado + calibrado)
        'alquiler_estimado_ars': round(alquiler_mensual_ars, 0),
        'cap_rate_anual': round(cap_rate_neto, 2), # Devolvemos NETO por defecto
        'cap_rate_bruto': round(roi_bruto_anual, 2),
        'usdt_ars': usdt_ars,
        'fecha_mercado': cache.get("fecha") if cache else "Sin datos",
        'm2_equivalentes': m2_equiv,
        'justificacion': justificacion,
        'rango_m2': f"USD {rango_min:,.0f} - {rango_max:,.0f}",
        'confianza': 'alta' if n_v > 10 else 'media',
        'nlp_detecciones': detecciones_nlp,
        'nlp_ajuste_pct': round(ajuste_nlp * 100, 2),
        'plusvalia_ciclo_usd': round(plusvalia_ciclo_usd, 0),
        'plusvalia_ciclo_pct': round(plusvalia_ciclo_pct, 2),
        'plusvalia_tipo': tipo_plusvalia,
        'plusvalia_12m_usd': round(plusvalia_12m_usd, 0),
        'plusvalia_12m_pct': round(plusvalia_12m_pct, 2),
        'expensas_ars': expensas_ars,
        'mantenimiento_mensual_ars': round(mantenimiento_mensual_ars, 0),
        'serie_mensual_m2': [],
        'resolution_metadata': resolution_metadata,
    }

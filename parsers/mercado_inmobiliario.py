import json
import os
import re
import math
import unicodedata
import logging
from datetime import datetime
from parsers.location_engine import cargar_anclas, calcular_precio_m2, estimar_confianza, get_ancla_mas_cercana
from parsers import cluster_filters
from parsers.cluster_filters import (
    filtrar_por_fecha,
    separar_por_barreras,
    calcular_percentil,
    calcular_blend_p33,
    seleccionar_percentil_por_edad,
    seleccionar_percentil_por_calidad_pool,
    _calcular_cv,
)
from parsers.valuacion_helpers import calcular_rango_venta, ensamblar_metadata_resolucion


def _calcular_mediana(precios):
    """Pure Python median - equivalente a _calcular_mediana()."""
    if not precios:
        return 0.0
    s = sorted(precios)
    n = len(s)
    if n % 2 == 1:
        return float(s[n // 2])
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def _calcular_percentil_linear(precios, q):
    """Pure Python percentile con interpolación lineal - equivalente a _calcular_percentil_linear(..., q)."""
    if not precios:
        return 0.0
    s = sorted(precios)
    n = len(s)
    if n == 1:
        return float(s[0])
    idx = q / 100.0 * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return float(s[-1])
    frac = idx - lo
    return float(s[lo] * (1 - frac) + s[hi] * frac)


logger = logging.getLogger(__name__)
ANIO_ACTUAL = datetime.now().year

# --- Helpers de normalización de direcciones ---
_RE_CITY_NORM = re.compile(
    r'\brosario\s+santa\s+fe\b|\b(rosario|provincia|argentina|arg\.?|capital)\b', re.IGNORECASE)
_RE_DESC_NORM = re.compile(
    r'\b(piso|depto|dpto|departamento|departameto|oficina|local'
    r'|pb|dormitorios?|dorm|balcones?|cochera|living|comedor'
    r'|monoambiente|ph|casa|habitacion|amb|m2|mts|mt2?'
    r'|unidad|patio|terraza|pileta|parrillero|baulera|amenities'
    r'|venta|estrenar|exclusiv[oa]s?|semi|semisubsuelo'
    r'|subsuelo|pasillo|galeria|hall|ingreso'
    r'|frente|fondo|interno|exterior|lateral|trasero'
    r'|condominio|condos|country|barrio|club|torre|edificio'
    r'|dias|meses|ano)\s*\d*', re.IGNORECASE)
_RE_PIPE_NORM = re.compile(r'\s*\|.*$')
_RE_NRO_NORM = re.compile(r'\b(nro|n|num|numero|numero)\b', re.IGNORECASE)
_RE_ORD_NORM = re.compile(r'[\xb0\xba]')  # ordinal chars
_RE_HON_NORM = re.compile(
    r'\b(almirante|general|san|santo|santa|doctor|dra|don|dona'
    r'|padre|profesor|prof|teniente|coronel|comandante'
    r'|capitan|presidente|fray|monsenor|monseñor)\b', re.IGNORECASE)

def normalizar_calle_nombre(nombre):
    """Normaliza nombre de calle: minusculas, sin tildes, sin Av/Bv, sin honorificos."""
    if not isinstance(nombre, str):
        return ''
    s = nombre.lower().strip()
    s = ''.join(c for c in unicodedata.normalize('NFKD', s)
                if not unicodedata.combining(c))
    s = _RE_ORD_NORM.sub(' ', s)
    s = _RE_PIPE_NORM.sub('', s)
    s = re.sub(r'[^\w\s]', ' ', s)
    s = _RE_CITY_NORM.sub('', s)
    s = _RE_DESC_NORM.sub('', s)
    s = _RE_NRO_NORM.sub('', s)
    s = re.sub(r'\b(av|avenida|bv|bulevar|boulevard)\b', '', s)
    # Protect "santa fe" from honorific stripping (compound street name)
    s = re.sub(r'\bsanta\s+fe\b', '__santa_fe__', s)
    s = _RE_HON_NORM.sub('', s)
    s = s.replace('__santa_fe__', 'santa fe')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


_RE_GARBAGE_WORDS = re.compile(
    r'\b(un|una|al|con|para|sobre|por|entre|hasta|de|del|la|las|los|'
    r'subsuelo|pasillo|galeria|hall|ingreso|'
    r'patio|terraza|pileta|parrillero|baulera|amenities|'
    r'venta|estrenar|exclusiv[oa]s?|'
    r'frente|fondo|interno|exterior|lateral|trasero|'
    r'dias|meses|ano|semi|semisubsuelo|'
    r'condominio|condos|country|barrio|club|torre|edificio|'
    r'fisherton|paddock|bis)\b', re.IGNORECASE)

_RE_TRAILING_DIGITS = re.compile(r'\s+\d+$')
_RE_TRAILING_NUM_UNIT = re.compile(r'\s+(0\d|[12]?\d)\s*$')

def _limpiar_calle_post(calle_norm):
    """Limpia tokens basura del FINAL del street name."""
    if not calle_norm:
        return calle_norm
    # Remove trailing unit numbers like "01", "02", "1", "2"
    calle_norm = _RE_TRAILING_NUM_UNIT.sub('', calle_norm)
    # Remove trailing pure digits
    calle_norm = _RE_TRAILING_DIGITS.sub('', calle_norm)
    # Keep removing known garbage words from the end
    changed = True
    while changed:
        changed = False
        m = _RE_GARBAGE_WORDS.search(calle_norm)
        if m and m.end() == len(calle_norm):
            calle_norm = calle_norm[:m.start()].strip()
            changed = True
    return calle_norm.strip()


def _formatear_direccion_limpia(p):
    """Retorna direccion legible: 'calle numero' a partir de calle_limpia/numero_limpio."""
    cl = p.get('calle_limpia', '') or ''
    nl = p.get('numero_limpio', '') or ''
    if cl:
        cl_capitalizada = ' '.join(w.capitalize() if w not in ('de', 'del', 'la', 'los', 'las', 'y', 'al') else w for w in cl.split())
        return f'{cl_capitalizada} {nl}'.strip()
    return (p.get('direccion', '') or '')[:60]


def extraer_calle_numero(direccion):
    """Extrae (calle_normalizada, numero_entero) de una dirección libre."""
    if not isinstance(direccion, str):
        return None, None
    s = direccion.lower().strip()
    s = _RE_ORD_NORM.sub(' ', s)
    s = _RE_PIPE_NORM.sub('', s)
    s = s.replace('|', ' ').replace('/', ' ')
    s = re.sub(r'[^\w\s]', ' ', s)
    s = _RE_CITY_NORM.sub('', s)
    s = _RE_DESC_NORM.sub('', s)
    s = _RE_NRO_NORM.sub('', s)

    # "al 2100"
    m = re.search(r'\bal\s+(\d{1,5})', s)
    if m:
        num = int(m.group(1))
        calle_raw = s[:m.start()] + s[m.end():]
        return _limpiar_calle_post(normalizar_calle_nombre(calle_raw)), num

    # primer numero encontrado
    m = re.search(r'\b(\d{1,5})\b', s)
    if m:
        num = int(m.group(1))
        calle_raw = s[:m.start()] + s[m.end():]
        calle_norm = normalizar_calle_nombre(calle_raw)
        if calle_norm:
            partes = [p for p in calle_norm.split()
                      if not (p.isdigit() and len(p) < 5)
                      and not (len(p) == 1 and p.isalpha())]
            calle_norm = ' '.join(partes).strip()
            calle_norm = _limpiar_calle_post(calle_norm)
        return calle_norm, num

    return _limpiar_calle_post(normalizar_calle_nombre(s)), None

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
        "Puerto Norte": (-32.9280, -60.6608),
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
        antiguedad = ANIO_ACTUAL - anio_const
        factor_deprec = max(0.5, 1.0 - (antiguedad * 0.006))
        m2_base = valor_ancla * factor_deprec
        metodo = f"Ancla ({n_muestras} muestras)"
    
    # 4. Valor final (TAREA-073: sin factores hedónicos)
    valor_venta = m2_equiv * m2_base
    
    return {
        'm2_equiv': m2_equiv,
        'm2_base': m2_base,
        'percentil_usado': meta_cluster.get('percentil_usado', 'P33'),
        'n_muestras': n_muestras,
        'factor_final': 1.0,
        'valor_venta': valor_venta,
        'debug_info': {
            'zona': zona,
            'dorms': dorms,
            'metodo': metodo
        }
    }


# --- PARÁMETROS DE CALIBRACIÓN V10.1 ---
UMBRAL_CONFIANZA_SCRAPING = 8   # Muestras mínimas para confiar en el scraping
MAX_BONUS_ATRIBUTOS = 1.30   # Cap +30% para evitar valores locos

def obtener_caps_factor_por_cluster(meta_venta, n_v):
    radio = meta_venta.get('radio_usado', 999)
    if radio is not None and radio <= 300 and n_v >= 15:
        return 0.85, 1.15
    elif n_v >= 8:
        return 0.78, 1.25
    return 0.70, 1.35

def aplicar_cap_dinamico_factor(f_dict, meta_venta, n_v):
    cap_min, cap_max = obtener_caps_factor_por_cluster(meta_venta, n_v)
    factor_original = f_dict['total']
    factor_final = max(cap_min, min(cap_max, factor_original))
    f_dict['total'] = factor_final
    cluster_conf = 'ALTA' if cap_max == 1.15 else 'MEDIA' if cap_max == 1.25 else 'BAJA'
    f_dict['cap_dinamico'] = {
        'aplicado': factor_original != factor_final,
        'min': cap_min,
        'max': cap_max,
        'cluster_conf': cluster_conf,
        'factor_original': round(factor_original, 4),
        'factor_final': round(factor_final, 4)
    }
    return f_dict

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
            return _calcular_mediana(precios), len(precios)
        
        # 3) FILTRO PRE-IQR robusto (0.6-1.6x)
        # Usamos _calcular_mediana para evitar el bug de indexación en listas pares
        mediana_raw = _calcular_mediana(precios)
        
        lower_robust = mediana_raw * 0.6
        upper_robust = mediana_raw * 1.6
        
        precios_filtrados = [p for p in precios if lower_robust <= p <= upper_robust]
        
        # Si el filtro elimina demasiado, usar IQR tradicional como fallback
        if len(precios_filtrados) < 3:
            precios_ordenados = sorted(precios)
            if len(precios_ordenados) < 3:
                return _calcular_mediana(precios_ordenados), len(precios_ordenados)
            q1 = _calcular_percentil_linear(precios_ordenados, 25)
            q3 = _calcular_percentil_linear(precios_ordenados, 75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            precios_filtrados = [p for p in precios if lower <= p <= upper]
        
        if not precios_filtrados:
            return _calcular_mediana(precios), len(precios)
        
        return _calcular_mediana(precios_filtrados), len(precios_filtrados)
    except Exception:
        return 0, 0


# ─── FASE 1: ENRIQUECIMIENTO DE AÑO DESDE CATASTRO ───

_CATASTRO_CACHE = None
_CATASTRO_INDEX = None  # dict {(calle_norm, num): row} para busqueda exacta
_MAX_DIST_ADDR_MATCH = 200  # distancia maxima para match por direccion exacta

# Street dictionary para enriquecimiento de 3 pasos
_CALLES_ROSARIO = None
_CALLES_DICT_FILTER_CACHE = {}

def cargar_catastro():
    """
    Carga el CSV de Infomapa (rosario_avm_full.csv) con años de construcción.
    Cachea globalmente para no leer disco múltiples veces.
    """
    global _CATASTRO_CACHE, _CATASTRO_INDEX
    if _CATASTRO_CACHE is not None:
        return _CATASTRO_CACHE
    try:
        import pandas as pd
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'rosario_avm_full.csv'
        )
        if not os.path.exists(path):
            logger.error(f"[CATASTRO] Archivo no encontrado: {path}")
            return None
        df = pd.read_csv(path)
        required = ['ph', 'year', 'latitud', 'longitud', 'direccion_nominatim']
        if not all(col in df.columns for col in required):
            logger.error(f"[CATASTRO] Faltan columnas. Tengo: {list(df.columns)}")
            return None
        df = df.dropna(subset=['year', 'latitud', 'longitud'])
        df['year'] = df['year'].astype(int)
        df = df[(df['year'] >= 1900) & (df['year'] <= ANIO_ACTUAL)]

        # Indice de direcciones normalizadas
        idx = {}
        for _, row in df.iterrows():
            cn, num = extraer_calle_numero(str(row.get('direccion_nominatim', '')))
            if cn and num is not None:
                key = (cn, num)
                if key not in idx:
                    idx[key] = row
        _CATASTRO_INDEX = idx

        _CATASTRO_CACHE = df
        logger.info(f"[CATASTRO] Cargado: {len(df)} registros, {len(idx)} direcciones indexadas")
        return df
    except Exception as e:
        logger.error(f"[CATASTRO] Error: {e}")
        return None


# ─── Helpers para enriquecimiento de 3 pasos ───

def _token_contenido(comp_tokens, csv_tokens):
    """True si todos los tokens de comp_tokens aparecen en orden en csv_tokens (prefix OK si >=2 chars)."""
    if not comp_tokens or not csv_tokens:
        return False
    def norm(t):
        """Normaliza token: minuscula + sin acentos."""
        s = t.lower()
        return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    comp_norm = [norm(ct) for ct in comp_tokens if ct]
    csv_norm = [norm(ct) for ct in csv_tokens if ct]
    if not comp_norm or not csv_norm:
        return False
    it = iter(csv_norm)
    for ct in comp_norm:
        found = False
        for csv_t in it:
            if ct == csv_t or (len(ct) >= 2 and len(csv_t) > len(ct) and csv_t.startswith(ct)):
                found = True
                break
        if not found:
            return False
    return True


def _filtrar_calle_diccionario(cn):
    """Filtra tokens de una calle contra el diccionario de calles de Rosario.
    Retorna la mejor subsecuencia que existe en el diccionario, o '' si no hay match."""
    global _CALLES_ROSARIO, _CALLES_DICT_FILTER_CACHE
    if _CALLES_ROSARIO is None:
        _calles_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'calles_rosario.json')
        if os.path.exists(_calles_path):
            with open(_calles_path, encoding='utf-8') as f:
                _CALLES_ROSARIO = json.load(f)
    if not cn or not _CALLES_ROSARIO:
        return ''
    if cn in _CALLES_DICT_FILTER_CACHE:
        return _CALLES_DICT_FILTER_CACHE[cn]
    tokens = cn.split()
    best = None
    best_score = -1
    for longitud in range(len(tokens), 0, -1):
        for inicio in range(len(tokens) - longitud + 1):
            sub = tokens[inicio:inicio + longitud]
            for calle in _CALLES_ROSARIO:
                calle_tokens = calle.split()
                it2 = iter(calle_tokens)
                exact = 0
                prefix = 0
                ok = True
                for st in sub:
                    found = False
                    for ct2 in it2:
                        if st == ct2:
                            exact += 1
                            found = True
                            break
                        elif len(st) >= 2 and len(ct2) > len(st) and ct2.startswith(st):
                            prefix += 1
                            found = True
                            break
                    if not found:
                        ok = False
                        break
                if ok:
                    score = longitud * 1000 + exact * 10 + prefix
                    if score > best_score:
                        best_score = score
                        best = ' '.join(sub)
    if best is None:
        validos = [t for t in tokens if len(t) >= 3 and any(
            t == ct for calle in _CALLES_ROSARIO for ct in calle.split())]
        best = ' '.join(validos)
    _CALLES_DICT_FILTER_CACHE[cn] = best if best else ''
    return _CALLES_DICT_FILTER_CACHE[cn]


def _extraer_interseccion(direccion):
    """Detecta intersecciones (' y ', ' - ', ' esq ', ' esquina ') en RAW.
    Retorna lista de (calle_normalizada, numero) para cada calle de la interseccion.
    Si no hay separador, retorna [(calle, num)] aplicando el diccionario."""
    if not isinstance(direccion, str) or not direccion.strip():
        return []
    s = direccion.lower().strip()
    for sep in [' y ', ' - ', ' e ', ' esq ', ' esq. ', ' esq, ', ' esquina ']:
        if sep in s:
            partes = s.split(sep, 1)
            res = []
            for p in partes:
                p = p.strip()
                if p:
                    cn, num = extraer_calle_numero(p)
                    if cn:
                        cn2 = _filtrar_calle_diccionario(cn)
                        if cn2:
                            res.append((cn2, num))
            return res
    cn, num = extraer_calle_numero(direccion)
    if cn:
        cn2 = _filtrar_calle_diccionario(cn)
        if cn2:
            return [(cn2, num)]
    return []


def enriquecer_anio_comparable(comp, max_dist_m=30, max_dist_exacta=200):
    """
    Asigna año de construcción a un comparable usando catastro.
    PASO 0: match exacto (calle+número) ≤200m → ALTA
    PASO 1: token containment + bloque ≤30m → ALTA
    PASO 2: nearest PH + token + bloque ≤60m → MEDIA
    Sin esquina fallback.
    
    Args:
        comp: dict de comparable (del scraping)
        max_dist_m: distancia máxima en metros para token containment
        max_dist_exacta: distancia máxima para match exacto por dirección
    
    Returns:
        dict con anio_estimado, distancia_match, confianza, o None
    """
    catastro = cargar_catastro()
    if catastro is None:
        return None

    lat = comp.get('lat') or comp.get('latitud')
    lon = comp.get('lon') or comp.get('longitud')
    dir_comp = comp.get('direccion', comp.get('address', ''))

    if not lat or not lon:
        return None

    try:
        lat, lon = float(lat), float(lon)
    except (ValueError, TypeError):
        return None

    # Parsear direccion del comparable (detecta intersecciones en RAW)
    calles = _extraer_interseccion(dir_comp)
    if not calles:
        return None

    # ─── PASO 0: Match exacto por dirección (calle + número) vía _CATASTRO_INDEX ───
    for cn, num in calles:
        if not cn or num is None:
            continue
        key = (cn, num)
        if _CATASTRO_INDEX and key in _CATASTRO_INDEX:
            row = _CATASTRO_INDEX[key]
            d = calcular_distancia_km(lat, lon, row['latitud'], row['longitud']) * 1000
            if d <= max_dist_exacta:
                return {
                    'anio_estimado': int(row['year']),
                    'ph_match': str(row.get('ph', '?')),
                    'distancia_m': round(d, 1),
                    'confianza': 'ALTA',
                    'match_calle': True,
                    'direccion_catastro': str(row.get('direccion_nominatim', ''))
                }

    # Bounding box ±0.001° (~111m) para filtrar catastro
    bbox = 0.001
    cercanos = catastro[
        (catastro['latitud'].between(lat - bbox, lat + bbox)) &
        (catastro['longitud'].between(lon - bbox, lon + bbox))
    ]
    if cercanos.empty:
        return None

    # Pre-normalizar direcciones del bbox (solo ~15-20 filas)
    cercanos_norm = []
    for _, row in cercanos.iterrows():
        cn, num = extraer_calle_numero(str(row.get('direccion_nominatim', '')))
        cn_filt = _filtrar_calle_diccionario(cn) if cn else ''
        cercanos_norm.append({
            'row': row,
            'cn': cn_filt,
            'tokens': cn_filt.split() if cn_filt else []
        })

    # ─── PASO 1: Token containment + bloque ≤30m → ALTA ───
    for cn, num in calles:
        if not cn:
            continue
        comp_tokens = cn.split()
        best_d = float('inf')
        best_row = None
        for entry in cercanos_norm:
            if not entry['tokens']:
                continue
            if _token_contenido(comp_tokens, entry['tokens']):
                r = entry['row']
                # Block validation: skip if PH is on a different block
                if num is not None:
                    _, ph_num = extraer_calle_numero(str(r.get('direccion_nominatim', '')))
                    if ph_num is not None:
                        if (num // 100) * 100 != (ph_num // 100) * 100:
                            continue
                d = calcular_distancia_km(lat, lon, r['latitud'], r['longitud']) * 1000
                if d < best_d:
                    best_d = d
                    best_row = r
        if best_row is not None and best_d <= max_dist_m:
            return {
                'anio_estimado': int(best_row['year']),
                'ph_match': str(best_row.get('ph', '?')),
                'distancia_m': round(best_d, 1),
                'confianza': 'ALTA',
                'match_calle': True,
                'direccion_catastro': str(best_row.get('direccion_nominatim', ''))
            }

    # ─── PASO 2: Nearest PH + token + bloque ≤60m → MEDIA ───
    comp_num = calles[0][1] if calles else None
    PASO2_MAX_DIST = 60
    mejor_dist = float('inf')
    mejor_row = None
    for entry in cercanos_norm:
        r = entry['row']
        if not entry['tokens']:
            continue
        # Token validation: comparable calle must be contained in PH tokens
        if not any(
            _token_contenido(cn.split(), entry['tokens'])
            for cn, _ in calles if cn
        ):
            continue
        # Block validation: skip if PH is on a different block
        if comp_num is not None:
            _, ph_num = extraer_calle_numero(str(r.get('direccion_nominatim', '')))
            if ph_num is not None:
                if (comp_num // 100) * 100 != (ph_num // 100) * 100:
                    continue
        d = calcular_distancia_km(lat, lon, r['latitud'], r['longitud']) * 1000
        if d < mejor_dist:
            mejor_dist = d
            mejor_row = r

    if mejor_row is not None and mejor_dist <= PASO2_MAX_DIST:
        return {
            'anio_estimado': int(mejor_row['year']),
            'ph_match': str(mejor_row.get('ph', '?')),
            'distancia_m': round(mejor_dist, 1),
            'confianza': 'MEDIA',
            'match_calle': True,
            'direccion_catastro': str(mejor_row.get('direccion_nominatim', ''))
        }

    # ─── PASO 3: Nearest PH misma calle_norm por coordenadas ≤60m → MEDIA ───
    PASO3_MAX_DIST = 60
    mejor_dist = float('inf')
    mejor_row = None
    for entry in cercanos_norm:
        r = entry['row']
        if not entry['cn']:
            continue
        if not any(entry['cn'] == cn for cn, _ in calles if cn):
            continue
        d = calcular_distancia_km(lat, lon, r['latitud'], r['longitud']) * 1000
        if d < mejor_dist:
            mejor_dist = d
            mejor_row = r

    if mejor_row is not None and mejor_dist <= PASO3_MAX_DIST:
        return {
            'anio_estimado': int(mejor_row['year']),
            'ph_match': str(mejor_row.get('ph', '?')),
            'distancia_m': round(mejor_dist, 1),
            'confianza': 'MEDIA',
            'match_calle': True,
            'direccion_catastro': str(mejor_row.get('direccion_nominatim', ''))
        }

    return None


def _filtrar_por_ventana_edad(pool, anio_sujeto, ventana=15, min_con_anio=5):
    """
    Filtra comparables por ventana de edad alrededor del año sujeto.

    Reglas:
    - Si no hay anio_sujeto → no aplica filtro.
    - Si hay menos de 5 comparables con año → no aplica filtro.
    - Prueba ±ventana (default 15) años.
    - Si ±ventana tiene >=5 comparables → aplica filtro.
    - Si no, prueba ±30 años.
    - Si ±30 tiene >=5 comparables → aplica filtro.
    - Si ninguna ventana llega a 5 → fallback al pool completo.

    El selector posterior seleccionar_percentil_por_edad() decide:
    - 5-7  → P33_age_blend
    - 8-9  → P40_age
    - 10-19 → P45_age
    - 20+  → P50_age

    Returns:
        (pool_filtrado, age_filter_applied, n_age_filtered, anio_min, anio_max)
    """
    if not anio_sujeto:
        return pool, False, 0, 0, 0

    pool_con_anio = [p for p in pool if p.get('anio_estimado')]

    if len(pool_con_anio) < min_con_anio:
        return pool, False, len(pool_con_anio), 0, 0

    for ventana_actual in [ventana, 30]:
        anio_min = anio_sujeto - ventana_actual
        anio_max = anio_sujeto + ventana_actual

        pool_age_filtered = [
            p for p in pool_con_anio
            if anio_min <= p['anio_estimado'] <= anio_max
        ]

        if len(pool_age_filtered) >= min_con_anio:
            return pool_age_filtered, True, len(pool_age_filtered), anio_min, anio_max

    return pool, False, len(pool_con_anio), 0, 0


def _aplicar_size_adj_a_comparables(pool, subject_m2, macrozona_id=None):
    """
    Aplica size adjustment relativo a cada comparable.
    Normaliza el precio/m² de cada comp al tamaño del sujeto.
    """
    subject_adj = calcular_size_adjustment(subject_m2, macrozona_id=macrozona_id)
    result = []
    for p in pool:
        comp_m2 = p.get('m2', 0) or p.get('m2_cubiertos', 0) or 0
        if comp_m2 <= 0:
            continue
        comp_adj = calcular_size_adjustment(comp_m2, macrozona_id=macrozona_id)
        if comp_adj <= 0:
            continue
        val = p.get('valor_m2', 0) * p.get('_time_adjustment', 1.0)
        if val <= 0:
            continue
        result.append(val * (subject_adj / comp_adj))
    return result


def obtener_mediana_cluster_v2(zona, dormitorios, operacion='venta', lat_ref=None, lon_ref=None, fecha_ref=None, anio_sujeto=None, tipo_inmueble=None, cache_scraping=None, retro_dias=0, flex_dormitorios=None, m2_equiv=None):
    """
    Obtiene la mediana del cluster desde cache_scraping.json.
    Versión v2 con metadata extendida Y radios progresivos.
    
    Args:
        cache_scraping: dict opcional con datos precargados de cache_scraping.json.
                        Si es None, se carga el archivo desde disco.
    
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
        logger.info(f"[DEBUG-ENGINE] obtener_mediana_cluster_v2: zona={zona}, dormitorios={dormitorios}, operacion={operacion}, flex_dormitorios={flex_dormitorios}, retro_dias={retro_dias}")
        
        if cache_scraping is None:
            cache_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'cache_scraping.json'
            )
            if not os.path.exists(cache_path):
                return 0, 0, {'percentil_usado': 'P50' if operacion == 'alquiler' else 'P33', 'n_raw': 0, 'n_filtradas': 0,                 'retro_activo': bool(retro_dias), 'total_dias_ventana': get_natural_window_dias() + retro_dias * 30, 'flex_dormitorios': flex_dormitorios}
            from parsers.profiler import profile_block
            with profile_block("load_cache_scraping"):
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
        else:
            cache = cache_scraping
        
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
        from parsers.time_adjustment import get_natural_window_dias
        window_dias_usado = get_natural_window_dias() + retro_dias * 30
        
        # Puerto Norte: time-expansion en vez de radius-expansion
        TASA_AJUSTE_PN = -0.045
        
        from datetime import datetime, timedelta
        
        def filtrar_por_fecha(props, fecha_ref_str, dias=365):
            """Filtra propiedades por ventana de fecha (días hacia atrás). Usa date_created."""
            if not fecha_ref_str:
                return props
            try:
                if '-' in fecha_ref_str and fecha_ref_str.count('-') == 2:
                    fecha_ref_dt = datetime.strptime(fecha_ref_str, '%Y-%m-%d')
                else:
                    fecha_ref_dt = datetime.strptime(fecha_ref_str, '%Y-%m')
                fecha_limite = fecha_ref_dt - timedelta(days=dias)
                props_filtrados = []
                for p in props:
                    date_cr = p.get('date_created', p.get('date_updated', ''))
                    if not date_cr:
                        # Si no hay fecha, la incluimos por defecto para evitar vaciar el pool
                        props_filtrados.append(p)
                        continue
                    try:
                        dt = datetime.strptime(str(date_cr)[:10], '%Y-%m-%d')
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
                and ((p.get('dormitorios') in flex_dormitorios or p.get('dormitorios') == dorms) if flex_dormitorios else p.get('dormitorios') == dorms)
                and p.get('operacion') == oper
                and p.get('valor_m2', 0) > 0
                and (not tipo_inmueble or tipo_inmueble in str(p.get('tipo', p.get('tipo_inmueble', ''))).lower())
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
        
        def aplicar_filtro_fecha(props, fecha_filtro, dias=None):
            """Aplica ventana móvil. Default desde config (180d) + retro si corresponde."""
            if not fecha_filtro:
                return props
            if dias is None:
                from parsers.time_adjustment import get_natural_window_dias
                dias = get_natural_window_dias() + retro_dias * 30
            return filtrar_por_fecha(props, fecha_filtro, dias=dias)
        
        # Estrategia: Radio progresivo + fallback de zona
        mejor_resultado = None
        
        # 1. Intentar búsqueda geográfica primero si hay coordenadas
        # PN: salta Tier 1 (se contamina con Pichincha), va directo a Tier 2
        if lat_ref is not None and lon_ref is not None and zona_normalizada != 'Puerto Norte':
            for radio in RADIOS_PROGRESIVOS:
                props_geo = cluster_filters.filtrar_por_radio(
                    cache.get('propiedades', []), lat_ref, lon_ref,
                    radio, calcular_distancia_km
                )
                props_geo = cluster_filters.filtrar_por_tipo_operacion_dorms(
                    props_geo, tipo=tipo_inmueble, operacion=operacion, dormitorios=dormitorios,
                    tolerancia_dorms=0
                )
                props_geo = [p for p in props_geo if p.get('valor_m2', 0) > 0]
                
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
                    if flex_dormitorios:
                        if p.get('dormitorios') not in flex_dormitorios and p.get('dormitorios') != dormitorios: continue
                    else:
                        if p.get('dormitorios') != dormitorios: continue
                    if p.get('operacion') != operacion: continue
                    if p.get('valor_m2', 0) <= 0: continue
                    if tipo_inmueble and tipo_inmueble not in str(p.get('tipo', p.get('tipo_inmueble', ''))).lower(): continue
                    props_geo.append(p)
                
                props_geo = aplicar_filtro_fecha(props_geo, fecha_ref)
                
                if len(props_geo) >= 2:
                    mejor_resultado = (props_geo, 1500, "busqueda_geografica")
        
        # 2. Fallback: zona normalizada + radio progresivo (o time-expansion para PN)
        if mejor_resultado is None:
            if zona_normalizada == 'Puerto Norte':
                # PN: No expande radio para no contaminar con Pichincha. 
                # Ventana gobernada 100% por el slider (Suelo Natural: 180d)
                if retro_dias == 0:
                    dias_ventana = get_natural_window_dias()
                else:
                    dias_ventana = get_natural_window_dias() + retro_dias * 30
                
                props = buscar_en_zona(zona_normalizada, dormitorios, operacion, lat_ref, lon_ref, 1500)
                props = filtrar_por_fecha(props, fecha_ref, dias=dias_ventana)
                
                if len(props) >= 2:
                    window_dias_usado = dias_ventana
                    # Aplicar ajuste temporal (-4.5% anual) a comparables > 180 días
                    try:
                        if fecha_ref and fecha_ref.count('-') == 2:
                            ref_dt = datetime.strptime(fecha_ref, '%Y-%m-%d')
                        elif fecha_ref and fecha_ref.count('-') == 1:
                            ref_dt = datetime.strptime(fecha_ref, '%Y-%m')
                        else:
                            ref_dt = datetime.now()
                    except:
                        ref_dt = datetime.now()
                    for p in props:
                        dc = p.get('date_created', '')
                        if dc:
                            try:
                                dt = datetime.strptime(str(dc)[:10], '%Y-%m-%d')
                                anios_desde_ref = max(0, (ref_dt - dt).days / 365.25)
                                if (ref_dt - dt).days > get_natural_window_dias():
                                    p['_time_adjustment'] = 1 + TASA_AJUSTE_PN * anios_desde_ref
                                else:
                                    p['_time_adjustment'] = 1.0
                            except:
                                p['_time_adjustment'] = 1.0
                    mejor_resultado = (props, 1500, 'Puerto Norte')
                else:
                    mejor_resultado = None
            else:
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
            # Aplicar barreras geográficas incluso en fallback para consistencia de precios ajustados
            if lat_ref and lon_ref and props:
                try:
                    from parsers.location_engine import check_barrier_crossing, cargar_barreras
                    barreras = cargar_barreras()
                    barreras_result = separar_por_barreras(
                        props=props, lat_ref=lat_ref, lon_ref=lon_ref,
                        check_barrier_fn=lambda p1, p2: check_barrier_crossing(p1, p2, barreras)
                    )
                    # Marcar penalizaciones en las propiedades
                    for p in props:
                        p['_penalizacion_barrier'] = 1.0
                        if p in barreras_result['cross_soft']:
                            p['_penalizacion_barrier'] = 0.97
                        elif p in barreras_result['excluded_hard']:
                            # En fallback, permitimos hard con penalización
                            p['_penalizacion_barrier'] = 0.97
                except Exception as e:
                    logger.warning(f"Error aplicando barreras en fallback: {e}")

            n_available = len(props) if props else 0
            comparables_reales = [
                {
                    'precio': p.get('precio'),
                    'm2': p.get('m2'),
                    'precio_m2': p.get('valor_m2'),
                    'time_adjustment': round(p.get('_time_adjustment', 1.0), 4),
                    'precio_m2_ajustado': round(p.get('valor_m2', 0) * p.get('_time_adjustment', 1.0), 2),
                    'dormitorios': p.get('dormitorios'),
                    'direccion': (p.get('direccion_limpia') or p.get('direccion', ''))[:60],
                    'direccion_limpia': _formatear_direccion_limpia(p),
                    'lat': p.get('lat'),
                    'lon': p.get('lon'),
                    'zona': p.get('zona'),
                    'tipo': p.get('tipo'),
                    'anio_estimado': p.get('anio_estimado'),
                    'distancia_m': round(calcular_distancia_km(lat_ref, lon_ref, float(p['lat']), float(p['lon'])) * 1000, 0) if lat_ref and lon_ref and p.get('lat') and p.get('lon') else None,
                }
                for p in props
            ] if props else []
            return 0, 0, {
                'percentil_usado': percentil_usado, 
                'n_raw': 0, 
                'n_filtradas': n_available,
                'radio_usado': None,
                'fecha_ref': fecha_ref,
                'operacion': operacion,
                'zona_original': zona_original,
                'zona_resolucion': zona_normalizada,
                'insuficientes_comparables': True,
                'n_comparables': n_available,
                'comparables_reales': comparables_reales,
                'retro_activo': bool(retro_dias),
                'total_dias_ventana': get_natural_window_dias() + retro_dias * 30,
                'debug': f'Solo {n_available} comparables encontrados. '
                          'Se requiere mínimo 2 para valuación automática.'
            }

        
        props, radio_usado, zona_resol = mejor_resultado
        
# === AJUSTE Ct PARA COMPARABLES > VENTANA NATURAL ===
        from parsers.time_adjustment import get_natural_window_dias, calcular_ct, meses_desde, es_nuevo
        natural_dias = get_natural_window_dias()
        for p in props:
            dc = p.get('date_created', '')
            if not dc:
                continue
            try:
                m = meses_desde(dc, fecha_ref)
                if m is not None and m > natural_dias / 30:
                    p['_time_adjustment'] = calcular_ct(m, es_nuevo(p))
            except Exception:
                pass
        
# === APLICAR BARRERAS GEOGRÁFICAS (Rosario) ===
# Blending same-side / cross-soft para evitar contaminación
        same_side = []
        cross_soft = []
        
        if lat_ref and lon_ref and props:
            try:
                from parsers.location_engine import check_barrier_crossing, cargar_barreras
                barreras = cargar_barreras()
                
                barreras_result = separar_por_barreras(
                    props=props,
                    lat_ref=lat_ref,
                    lon_ref=lon_ref,
                    check_barrier_fn=lambda p1, p2: check_barrier_crossing(p1, p2, barreras)
                )
                
                same_side = barreras_result['same_side']
                cross_soft = barreras_result['cross_soft']
                excluded_hard = barreras_result['excluded_hard']
                
                # PASO 1: Convertir excluded_hard → cross_soft para zonas urbanas densas
                ZONAS_BARRERA_BLANDA = ['Puerto Norte', 'Refinería', 'Centro', 'Alberto Olmedo']
                if zona_normalizada in ZONAS_BARRERA_BLANDA and excluded_hard:
                    for comp in excluded_hard:
                        comp['_penalizacion_barrier'] = 0.97
                        cross_soft.append(comp)
                    excluded_hard = []
                    logger.info(f"[BARRERA_BLANDA] {zona_normalizada}: convirtiendo {len(cross_soft)} props (penalización 0.97)")
                
                # PASO 2: Fallback si todas cruzan barrera dura
                if not same_side and not cross_soft and len(excluded_hard) >= 5:
                    for comp in excluded_hard:
                        comp['_penalizacion_barrier'] = 0.97
                        cross_soft.append(comp)
                    excluded_hard = []
                    logger.info(f"[BARRERA_FALLBACK] usando {len(cross_soft)} props vía fallback (penalización 0.97)")
                
                for p in same_side:
                    p['_cross_soft'] = False
                for p in cross_soft:
                    p['_cross_soft'] = True
                
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
        
        # FASE 1: Enriquecer pool con año del catastro (solo informativo)
        n_enriquecidos_alta = 0
        n_enriquecidos_media = 0

        for comp in unicos:
            if comp.get('anio_construccion') or comp.get('anio_estimado'):
                continue
            enriq = enriquecer_anio_comparable(comp)
            if enriq:
                comp['anio_estimado'] = enriq['anio_estimado']
                comp['anio_confianza'] = enriq['confianza']
                comp['anio_ph_match'] = enriq['ph_match']
                comp['anio_distancia_match'] = enriq['distancia_m']

                if enriq['confianza'] == 'ALTA':
                    n_enriquecidos_alta += 1
                elif enriq['confianza'] == 'MEDIA':
                    n_enriquecidos_media += 1

        total_pool = len(unicos)
        n_enriq_total = n_enriquecidos_alta + n_enriquecidos_media
        pct_enriq = (n_enriq_total / total_pool * 100) if total_pool else 0

        # Sin filtro de edad (ML evidence: edad no es factor causal en Rosario)
        pool_final = unicos
        n_age_filtered = 0
        age_filter_applied = False

        # Resolver macrozona para size adjustment
        macrozona_id = None
        try:
            if lat_ref is not None and lon_ref is not None:
                from parsers.zonas_manager import resolver_macrozona
                _pseudo_prop = {'zona': zona or '', 'lat': lat_ref, 'lon': lon_ref}
                _mz_info = resolver_macrozona(_pseudo_prop)
                macrozona_id = _mz_info.get('macrozona_id')
        except Exception:
            pass

        precios = [p['valor_m2'] * p.get('_time_adjustment', 1.0) for p in pool_final]
        n_raw = len(precios)
        
        # Build comparables_reales early so all return paths include them
        comparables_reales = [
            {
                'precio': p.get('precio'),
                'm2': p.get('m2'),
                'precio_m2': p.get('valor_m2'),
                'time_adjustment': round(p.get('_time_adjustment', 1.0), 4),
                'precio_m2_ajustado': round(p.get('valor_m2', 0) * p.get('_time_adjustment', 1.0), 2),
                'dormitorios': p.get('dormitorios'),
                'direccion': (p.get('direccion_limpia') or p.get('direccion', ''))[:60],
                'direccion_limpia': _formatear_direccion_limpia(p),
                'lat': p.get('lat'),
                'lon': p.get('lon'),
                'zona': p.get('zona'),
                'tipo': p.get('tipo'),
                'anio_estimado': p.get('anio_estimado'),
                'distancia_m': round(calcular_distancia_km(lat_ref, lon_ref, float(p['lat']), float(p['lon'])) * 1000, 0) if lat_ref and lon_ref and p.get('lat') and p.get('lon') else None,
            }
            for p in pool_final[:60 if retro_dias > 0 else 30]
        ] if pool_final else []
        
        if not precios:
            return 0.0, 0, {
                'percentil_usado': percentil_usado,
                'n_raw': 0,
                'n_filtradas': 0,
                'radio_usado': radio_usado,
                'fecha_ref': fecha_ref,
                'operacion': operacion,
                'zona_original': zona_original,
                'zona_resolucion': zona_resol,
                'comparables_reales': comparables_reales
            }
        
        if len(precios) < 3:
            logger.info(f"[N<3] Solo {len(precios)} comparables, forzando fallback a ancla")
            return 0.0, len(precios), {
                'percentil_usado': percentil_usado,
                'n_raw': n_raw,
                'n_filtradas': len(precios),
                'radio_usado': radio_usado,
                'fecha_ref': fecha_ref,
                'operacion': operacion,
                'zona_original': zona_original,
                'zona_resolucion': zona_resol,
                'comparables_reales': comparables_reales,
                'n_insuficiente': True,
            }
        
        # FILTRO PRE-IQR robusto
        mediana_raw = _calcular_mediana(precios)
        lower_robust = mediana_raw * 0.6
        upper_robust = mediana_raw * 1.6
        
        precios_filtrados = [p for p in precios if lower_robust <= p <= upper_robust]
        
        # Fallback IQR si elimina demasiado
        if len(precios_filtrados) < 3:
            precios_ordenados = sorted(precios)
            if len(precios_ordenados) < 3:
                return float(_calcular_mediana(precios)), len(precios), {
                    'percentil_usado': percentil_usado,
                    'n_raw': n_raw,
                    'n_filtradas': len(precios),
                    'radio_usado': radio_usado,
                    'fecha_ref': fecha_ref,
                    'operacion': operacion,
                    'zona_original': zona_original,
                    'zona_resolucion': zona_resol,
                    'comparables_reales': comparables_reales
                }
            q1 = _calcular_percentil_linear(precios_ordenados, 25)
            q3 = _calcular_percentil_linear(precios_ordenados, 75)
            iqr = q3 - q1
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            precios_filtrados = [p for p in precios if lower <= p <= upper]
        
        if not precios_filtrados:
            return float(_calcular_mediana(precios)), len(precios), {
                'percentil_usado': percentil_usado,
                'n_raw': n_raw,
                'n_filtradas': len(precios),
                'radio_usado': radio_usado,
                'fecha_ref': fecha_ref,
                'operacion': operacion,
                'zona_original': zona_original,
                'zona_resolucion': zona_resol,
                'comparables_reales': comparables_reales
            }
        
        # Calcular percentil CON BLENDING same-side / cross-soft
        # Separar pools
        precios_same = []
        precios_cross = []
        
        for p in pool_final:
            ta = p.get('_time_adjustment', 1.0)
            val = p.get('valor_m2', 0) * ta
            if val <= 0:
                continue
            if p.get('_cross_soft', False):
                precios_cross.append(val)
            else:
                precios_same.append(val)
        
        # Calcular percentil según operación
        _cv_pool = None
        if operacion == 'alquiler':
            percentil_venta = 50
            percentil_usado = 'P50_alquiler'
        else:
            # Percentil por calidad del pool (CV post-size_adj)
            if m2_equiv and macrozona_id and len(precios) >= 3:
                _size_adj_prices = _aplicar_size_adj_a_comparables(pool_final, m2_equiv, macrozona_id)
                _cv_pool = _calcular_cv(_size_adj_prices) if len(_size_adj_prices) >= 3 else 1.0
            else:
                _cv_pool = _calcular_cv(precios) if len(precios) >= 3 else 1.0
            percentil_venta, percentil_usado = seleccionar_percentil_por_calidad_pool(len(precios), _cv_pool)
            logger.info(f"[CV_POOL] n={len(precios)}, cv={_cv_pool:.4f}, percentil={percentil_venta} ({percentil_usado})")

        pct_same = calcular_percentil(precios_same, percentil_venta)
        pct_cross = calcular_percentil(precios_cross, percentil_venta)
        
        # Calcular percentiles del cluster completo (para dispersión estadística)
        precios_todos = precios_same + precios_cross
        if len(precios_todos) >= 4:
            p25_cluster = float(_calcular_percentil_linear(precios_todos, 25))
            p33_cluster = float(_calcular_percentil_linear(precios_todos, 33))
            p50_cluster = float(_calcular_mediana(precios_todos))
            p75_cluster = float(_calcular_percentil_linear(precios_todos, 75))
        else:
            p25_cluster = p33_cluster = p50_cluster = p75_cluster = None
        
        # VALOR PRINCIPAL: fallback inicial (se recalcula dentro de las ramas)
        valor_principal = pct_same if pct_same else (pct_cross if pct_cross else (p50_cluster if p50_cluster else 0))
        
        n_same = len(precios_same)
        if n_same >= 15:
            alpha = 0.70
        elif n_same >= 8:
            alpha = 0.60
        elif n_same >= 5:
            alpha = 0.55
        else:
            alpha = 0.50
        
# Calcular 3 bases para rango (solo venta)
        ALPHA_CONSERVADOR = 0.70  # FIJO para conservador
        ALPHA_MERCADO = 0.60        # FIJO para mercado
        
        # Combinar dispersión del cluster + alpha blending
        if pct_same is not None and pct_cross is not None:
            # Alpha blending
            blend_cons = calcular_blend_p33(pct_same, pct_cross, alpha=ALPHA_CONSERVADOR)
            blend_mkt = calcular_blend_p33(pct_same, pct_cross, alpha=ALPHA_MERCADO)
            
            # Optimista: alpha dinámico según ratio
            ratio = pct_cross / pct_same if pct_same > 0 else 1.0
            if ratio <= 1.05:
                alpha_opt = 0.70
            elif ratio <= 1.15:
                alpha_opt = 0.60
            else:
                alpha_opt = 0.55
            alpha_opt = max(0.55, min(0.70, alpha_opt))
            blend_opt = calcular_blend_p33(pct_same, pct_cross, alpha=alpha_opt)
            
            # Valor principal: blend puro con alpha 0.70 (SIN min con P25)
            valor_principal = blend_cons  # 0.70 * pct_same + 0.30 * pct_cross
            
            # Rango: estos SÍ usan percentiles
            base_conservadora = p25_cluster if p25_cluster else valor_principal
            base_mercado = p50_cluster if p50_cluster else valor_principal
            base_optimista = p75_cluster if p75_cluster else valor_principal
            
            fuente_rango = 'percentiles+alpha'
            
        elif len(precios_todos) >= 4:
            # Solo percentiles (sin cross-soft) - usar dispersión del cluster
            base_conservadora = p25_cluster
            base_mercado = p50_cluster
            base_optimista = p75_cluster
            alpha_opt = 0.70
            ratio = 1.0
            fuente_rango = 'percentiles'
            # Valor principal = P33 del cluster cuando no hay cross
            valor_principal = p33_cluster if p33_cluster else p50_cluster
            
        else:
            # Datos insuficientes
            base_conservadora = base_mercado = base_optimista = pct_same if pct_same else p50_cluster
            alpha_opt = 0.70
            ratio = 1.0
            fuente_rango = 'p33_unico'
            # Valor principal ya tiene fallback al inicio
        
        # GARANTIZAR ORDEN: conservador <= mercado <= optimista
        # Filtrar Nones antes de ordenar para evitar TypeError
        bases_to_sort = [b for b in [base_conservadora, base_mercado, base_optimista] if b is not None]
        if not bases_to_sort:
            base_conservadora = base_mercado = base_optimista = 0.0
        else:
            bases_sorted = sorted(bases_to_sort)
            # Rellenar con el valor mínimo si faltan bases
            while len(bases_sorted) < 3:
                bases_sorted.insert(0, bases_sorted[0])
            base_conservadora, base_mercado, base_optimista = bases_sorted

        
        # Valor principal = BLEND PURO con alpha 0.70 (para Venta Lista)
        # Las otras bases quedan disponibles para el rango
        
        if operacion == 'venta':
            valor = valor_principal
        else:
            valor = float(_calcular_mediana(precios_filtrados))
            percentil_usado = 'P50_alquiler'
        
        n_filtradas = len(precios_filtrados)

        # M² puro (sin barrera en comparables) para display en header
        m2_puro = valor
        # Barrera del sujeto: ajuste proporcional según ratio de comps que cruzan
        n_cross = len(precios_cross)
        n_total = len(precios_cross) + len(precios_same)
        if n_total > 0 and n_cross > 0:
            barrier_pct = round((n_cross / n_total) * 0.03, 4)
            valor = round(m2_puro * (1 - barrier_pct), 2)
        else:
            barrier_pct = 0.0

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
            'alpha': 0.70,  # conservador siempre
            'pct_same': pct_same,
            'pct_cross': pct_cross,
            # rango de 3 escenarios
            'base_conservadora': round(base_conservadora, 2),
            'base_mercado': round(base_mercado, 2),
            'base_optimista': round(base_optimista, 2),
            'alpha_conservador': ALPHA_CONSERVADOR,
            'alpha_mercado': ALPHA_MERCADO,
            'alpha_optimista': alpha_opt if 'alpha_opt' in dir() else 0.55,
            'ratio_same_cross': round(ratio, 3) if 'ratio' in dir() else 1.0,
            # Percentiles del cluster
            'p25_cluster': round(p25_cluster, 2) if p25_cluster is not None else None,
            'p33_cluster': round(p33_cluster, 2) if p33_cluster is not None else None,
            'p50_cluster': round(p50_cluster, 2) if p50_cluster is not None else None,
            'p75_cluster': round(p75_cluster, 2) if p75_cluster is not None else None,
            # Fuente del rango
            'fuente_rango': fuente_rango,
            # Enriquecimiento Fase 1 (catastro)
            'n_comparables_total': total_pool,
            'n_con_anio_alta': n_enriquecidos_alta,
            'n_con_anio_media': n_enriquecidos_media,
            'pct_con_anio': round(pct_enriq, 1),
            # CV del pool (calidad de comparables)
            'cv_pool': round(_cv_pool, 4) if _cv_pool is not None else None,
            # Comparables reales (muestra de hasta 30/60)
            'comparables_reales': comparables_reales,
            # M² puro sin barrera (para display en header)
            '_m2_puro': round(m2_puro, 2),
            'barrier_pct': barrier_pct,
            # Retro
            'retro_activo': bool(retro_dias),
            'total_dias_ventana': window_dias_usado,
            'flex_dormitorios': flex_dormitorios,
            'sujeto_dormitorios': dormitorios,
        }
        
        return valor, n_filtradas, meta
    except Exception as e:
        import traceback
        logger.error(f"[EXCEPTION] {e}\n{traceback.format_exc()}")
        return 0, 0, {
        'percentil_usado': 'P50' if operacion == 'alquiler' else 'P33',
        'n_raw': 0,
        'n_filtradas': 0,
            'retro_activo': bool(retro_dias),
            'total_dias_ventana': window_dias_usado,
            'flex_dormitorios': flex_dormitorios,
        'sujeto_dormitorios': dormitorios,
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
    anio_tasacion = prop_data.get('anio_tasacion', ANIO_ACTUAL)
    
    from datetime import datetime
    fecha_ref = datetime.now().strftime('%Y-%m-%d')
    # Usar v2 con coordenadas (IGUAL que valuar_propiedad_v7)
    _m2_equiv = calcular_m2_equivalentes(prop_data)
    valor_cluster, muestras, meta = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona),
        dormitorios=dorms,
        operacion='venta',
        lat_ref=lat,
        lon_ref=lon,
        fecha_ref=fecha_ref,
        m2_equiv=_m2_equiv
    )

    # Handle None returns
    if valor_cluster is None or valor_cluster == 0:
        valor_cluster = 0
        muestras = 0
    
    # 2. Depreciar ancla por antigüedad
    antiguedad = ANIO_ACTUAL - anio_const
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
    anio_actual = ANIO_ACTUAL
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
    return data.get('indice_ciudad', {}).get('base_year', ANIO_ACTUAL)


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
    
    MODOS DE CÁLCULO:
    - GRANULAR: m2_descubiertos_propios + m2_descubiertos_comun_exclusivo diferenciados
    - LEGADO: solo m2_descubiertos (sin diferenciar)
    
    Ponderaciones DESCUBIERTOS (nuevo granular):
    - m2_descubiertos_propios: 0.25 (0.30 si >= 20m²)
    - m2_descubiertos_comun_exclusivo: 0.15 (0.20 si >= 20m²)
    
    Ponderaciones legado:
    - m2_descubiertos: 0.20 (0.25 si >= 20m²)
    - m2_cubiertos: 100%
    - m2_semicubiertos: 30%/45%/55% (chico/medio/grande)
    - m2_comunes: 12% (15% si exterior=comun)
    
    Clamp: no más de +25% sobre m2_cubiertos (casas +15%)
    """
    # Normalizar todos los campos
    m2_cub = normalize_float(prop.get('m2_cubiertos'))
    
    # Fallback: si m2_cubiertos es 0, usar m2 (para retrocompatibilidad)
    if m2_cub == 0:
        m2_cub = normalize_float(prop.get('m2'))
    
    m2_com = normalize_float(prop.get('m2_comunes'))
    
    # === SEMICUBIERTOS (granular o legado) ===
    m2_semi_propios = prop.get('m2_semi_propios')
    m2_semi_exclusivos = prop.get('m2_semi_exclusivos')
    
    if m2_semi_propios is not None and m2_semi_exclusivos is not None:
        m2_semi = normalize_float(m2_semi_propios) + normalize_float(m2_semi_exclusivos)
    else:
        m2_semi = normalize_float(prop.get('m2_semicubiertos'))
    
    m2_semi_detalle = prop.get('m2_semicubiertos_detalle', 'medio').lower()
    
    # Coef según tamaño semicubiertos (solo si m2_semi = 0)
    if m2_semi > 0:
        coef_semi = 0.45
    else:
        coef_semi = {'chico': 0.30, 'medio': 0.45, 'grande': 0.55}.get(m2_semi_detalle, 0.45)
    
    # === DESCUBIERTOS: GRANULAR vs LEGADO ===
    m2_desc_propios = prop.get('m2_descubiertos_propios')
    m2_desc_comun_excl = prop.get('m2_descubiertos_comun_exclusivo')
    
    if m2_desc_propios is not None or m2_desc_comun_excl is not None:
        # MODO GRANULAR: diferenciar propio vs común exclusivo
        m2_dp = normalize_float(m2_desc_propios)
        m2_dce = normalize_float(m2_desc_comun_excl)
        
        piso = prop.get('piso', 0)
        
        # Boost para PB (piso=0) con patio comunitario > 10m²
        if piso == 0 and m2_dce > 10:
            coef_desc_comun_excl = 0.40  # 0.40 para patio PB funcional (extensión del living)
        else:
            coef_desc_comun_excl = 0.20 if m2_dce >= 20 else 0.15
        
        coef_desc_propios = 0.30 if m2_dp >= 20 else 0.25
        
        m2_desc_aporte = (m2_dp * coef_desc_propios) + (m2_dce * coef_desc_comun_excl)
    else:
        # MODO LEGADO: un solo campo m2_descubiertos
        m2_desc_raw = normalize_float(prop.get('m2_descubiertos'))
        coef_desc = 0.25 if m2_desc_raw >= 20 else 0.20
        m2_desc_aporte = m2_desc_raw * coef_desc
    
    # Si exterior es común (para m2_comunes)
    if prop.get('propiedad_exterior') == 'comun':
        factor_com = 0.15
    else:
        factor_com = 0.12
    
    m2_equiv = (
        m2_cub +
        m2_semi * coef_semi +
        m2_desc_aporte +
        m2_com * factor_com
    )
    
    # Clamp dinámico v9.3: Casas tienen menos premio por m2 descubierto
    tipo = (prop.get('tipo_inmueble') or prop.get('tipo') or 'departamento').lower()
    if 'casa' in tipo or 'cochera' in tipo:
        max_ratio = 1.15
    else:
        max_ratio = 1.25
    
    max_m2 = m2_cub * max_ratio
    
    return min(m2_equiv, max_m2)


def _interpolar_piecewise(m2, points):
    """Interpolación lineal entre puntos [{"m2": x, "factor": y}, ...]"""
    if not points:
        return 1.0
    if m2 <= points[0]["m2"]:
        return points[0]["factor"]
    if m2 >= points[-1]["m2"]:
        return points[-1]["factor"]
    for i in range(len(points) - 1):
        x1, y1 = points[i]["m2"], points[i]["factor"]
        x2, y2 = points[i + 1]["m2"], points[i + 1]["factor"]
        if x1 <= m2 <= x2:
            if x2 == x1:
                return y1
            return y1 + (y2 - y1) * (m2 - x1) / (x2 - x1)
    return 1.0

def _cargar_size_adjustment_config():
    """Carga la config de size_adjustment desde zonas_depreciacion.json"""
    ruta = os.path.join(os.path.dirname(__file__), "..", "data", "zonas_depreciacion.json")
    ruta = os.path.normpath(ruta)
    if not os.path.exists(ruta):
        return {}
    import json
    with open(ruta) as f:
        cfg = json.load(f)
    result = {}
    for mz in cfg.get("macrozonas", []):
        if "size_adjustment" in mz:
            result[mz["id"]] = mz["size_adjustment"]
    return result

_SIZE_ADJ_CONFIG = None

def calcular_size_adjustment(m2_equiv, macrozona_id=None, ancla_id=None):
    """
    Ajuste por tamaño configurable por macrozona (TAREA-074).
    Lee curvas piecewise desde zonas_depreciacion.json.
    Retorna 1.0 si no hay config (sin ajuste).
    """
    global _SIZE_ADJ_CONFIG
    if _SIZE_ADJ_CONFIG is None:
        _SIZE_ADJ_CONFIG = _cargar_size_adjustment_config()
    
    config = _SIZE_ADJ_CONFIG.get(macrozona_id) if macrozona_id else None
    if not config:
        return 1.0
    
    # Check subzona by anchor_id
    if ancla_id and "subzonas" in config:
        for sub_id, sub in config["subzonas"].items():
            if any(mid in ancla_id for mid in sub.get("match_anchor_ids", [])):
                return _interpolar_piecewise(m2_equiv, sub.get("points", []))
    
    # Default curve for this macrozona
    return _interpolar_piecewise(m2_equiv, config.get("points", []))

def calcular_size_discount_alquiler(m2_equiv):
    """
    Descuento por tamaño para alquiler.
    En el mercado, unidades grandes tienen menor precio/m² de renta.
    
    Curva basada en mercado Rosario 2026:
    - Hasta 45m²: sin descuento (1.00)
    - 45-60m²: descuento suave (1.00 → 0.92)
    - 60-80m²: descuento moderado (0.92 → 0.82)
    - 80-100m²: descuento fuerte (0.82 → 0.75)
    - >100m²: piso (0.75)
    """
    if m2_equiv <= 45:
        return 1.00
    elif m2_equiv <= 60:
        return 1.00 - (m2_equiv - 45) / 15 * 0.08
    elif m2_equiv <= 80:
        return 0.92 - (m2_equiv - 60) / 20 * 0.10
    elif m2_equiv <= 100:
        return 0.82 - (m2_equiv - 80) / 20 * 0.07
    else:
        return 0.75


# === AMENITY WEIGHTS (centralizados) ===
# Criterio conservador: amenities comunes tienen impacto bajo,
# cubierto en gran parte por el cluster.
AMENITY_WEIGHTS = {
    "caldera_central": 0.010,
    "radiadores": 0.010,
    "seguridad_24hs": 0.030,
    "seguridad_tag": 0.008,
    "seguridad_camaras": 0.006,
    "seguridad_totem": 0.006,
    "aberturas_premium": 0.020,
    "balcon_terraza": 0.010,
    "terraza_comun": 0.005,
    "terraza_compartida": 0.005,
    "parrilla": 0.005,       # legacy → tratada como compartida
    "parrilla_propia": 0.020,
    "parrilla_compartida": 0.005,
    "pileta": 0.015,
    "sum": 0.010,
    "gym": 0.005,
    "quincho": 0.020,
    "marinas": 0.020,
    "co_working": 0.010,
}
AMENITY_TOTAL_CAP = 0.06


def calcular_delta_amenities(detalles):
    """
    Calcula delta aditivo de todos los amenities estructurados.
    Normaliza keys legacy y aplica cap total.
    Retorna: (delta_capped, dict_detalle)
    """
    if not isinstance(detalles, list):
        return 0.0, {}
    suma = 0.0
    detalle = {}
    for item in detalles:
        key = item.lower().replace(" ", "_")
        if key == "parrilla":
            key = "parrilla_compartida"
        w = AMENITY_WEIGHTS.get(key, 0)
        if w > 0:
            suma += w
            detalle[key] = w
    capped = min(suma, AMENITY_TOTAL_CAP)
    return capped, detalle


def calcular_valor_activos(prop, m2_base_zona):
    """
    Calcula el valor aditivo de cocheras y bauleras en USD.
    Cocheras: Valor base * CoefTipo * UtilidadDecreciente
    Baulera: Valor fijo editable.
    """
    # 1. Cocheras
    cant = prop.get('cocheras_cantidad', 0)
    tipo = prop.get('cocheras_tipo', 'cubierta')
    
    # El valor base puede venir del formulario o sugerirse por zona (12m2 * base)
    valor_base = prop.get('valor_cochera_base')
    if valor_base is None or valor_base <= 0:
        valor_base = m2_base_zona * 12.0
    
    coef_tipo = {'cubierta': 1.0, 'semicubierta': 0.7, 'descubierta': 0.4}.get(tipo, 1.0)
    
    total_cocheras = 0.0
    for i in range(1, cant + 1):
        factor_utilidad = 1.0 if i == 1 else 0.7 if i == 2 else 0.5
        total_cocheras += (valor_base * coef_tipo * factor_utilidad)
    
    # 2. Baulera
    valor_baulera = prop.get('valor_baulera', 0.0)
    
    return {
        'total': total_cocheras + valor_baulera,
        'cocheras': total_cocheras,
        'baulera': valor_baulera,
        'detalle': f"{cant} cocheras {tipo} (${total_cocheras:,.0f}) + baulera (${valor_baulera:,.0f})" if cant > 0 or valor_baulera > 0 else "Sin activos adicionales"
    }

def calcular_factores(prop, ventana_usada=None):
    """
    Calcula factores de propiedad.
    v13.0 (TAREA-073): Todos los factores hedónicos eliminados por decisión ML.
    La ubicación (m2_microzona) ya captura ~80% de la varianza del precio.
    Retorna factores neutros (1.0) para compatibilidad con callers existentes.
    """
    return {
        'total': 1.0,
        'factor_estado': 1.0,
        'factor_calidad': 1.0,
        'depreciacion': 1.0,
        'anti': 1.0,
        'detalles': {'ventana': ventana_usada},
        'ventana': ventana_usada,
        'tasa_zonal': 0.0,
        'meta_mz': None,
    }


def calcular_factores_display(prop):
    """
    Calcula subfactores para display en UI de Valuación Manual.
    NO modifica el cálculo automático — solo referencia visual.
    Muestra Estado, Calidad, Amenities y NLP como referencia para el analista.
    Depreciación NO se incluye (TAREA-076): análisis ML demostró que la edad
    es confounding effect con ubicación — no existe como factor de mercado en Rosario.

    Retorna dict con valores descriptivos para cada subfactor.
    """
    from parsers.mercado_inmobiliario import calcular_delta_amenities

    estado_raw = (prop.get('estado_detalle') or 'bueno').lower().replace(' ', '_')
    calidad_raw = (prop.get('calidad_edificio') or 'media').lower()
    if estado_raw == 'premium':
        estado_norm = 'excelente'
        calidad_norm = 'premium' if calidad_raw in (None, '', 'media') else calidad_raw
    else:
        estado_norm = estado_raw
        calidad_norm = calidad_raw or 'media'

    factor_estado = {
        'a_estrenar': 1.08, 'excelente': 1.05, 'muy_bueno': 1.03,
        'bueno': 1.0, 'regular': 0.92, 'malo': 0.85, 'a_refaccionar': 0.70
    }.get(estado_norm, 1.0)

    factor_calidad = {
        'premium': 1.08, 'excelente': 1.06, 'alta': 1.04, 'media': 1.0,
        'baja': 0.95, 'economica': 0.90
    }.get(calidad_norm, 1.0)

    amenities_list = prop.get('detalles_categoria', [])
    if not isinstance(amenities_list, list):
        amenities_list = []
    delta_amenities, detalle_amenities = calcular_delta_amenities(amenities_list)

    delta_otros = 0.0
    detalle_otros_parts = []
    if prop.get('terminaciones_cocina') == 'silestone':
        delta_otros += 0.003
        detalle_otros_parts.append('cocina')
    if prop.get('preinstalacion_aa'):
        delta_otros += 0.002
        detalle_otros_parts.append('preinst AA')

    suma_cruda = (factor_estado - 1.0) + (factor_calidad - 1.0) + delta_amenities + delta_otros
    suma_clamped = max(-0.40, min(0.40, suma_cruda))
    total = max(0.70, min(1.35, 1.0 + suma_clamped))

    return {
        'factor_estado': factor_estado,
        'estado_label': estado_norm,
        'factor_calidad': factor_calidad,
        'calidad_label': calidad_norm,
        'delta_amenities': delta_amenities,
        'detalle_amenities': detalle_amenities,
        'delta_otros': delta_otros,
        'detalle_otros': '+'.join(detalle_otros_parts) if detalle_otros_parts else '',
        'suma_cruda': round(suma_cruda, 4),
        'suma_clamped': round(suma_clamped, 4),
        'total': round(total, 4),
    }


def _calcular_factores_rental(prop):
    """Factores para alquiler — mantiene lógica original (TAREA-073).
    Venta ya no usa factores hedónicos, pero alquiler conserva estado/calidad/anti.
    """
    estado_raw = (prop.get('estado_detalle') or 'bueno').lower().replace(' ', '_')
    calidad_raw = (prop.get('calidad_edificio') or 'media').lower()
    if estado_raw == 'premium':
        estado_norm = 'excelente'
        calidad_norm = 'premium' if calidad_raw in (None, '', 'media') else calidad_raw
    else:
        estado_norm = estado_raw
        calidad_norm = calidad_raw or 'media'

    anio_const = normalize_year(prop.get('anio_construccion'))
    if anio_const is None:
        anio_const = normalize_year(ANIO_ACTUAL - prop.get('antiguedad', 0))
    if anio_const is None:
        anio_const = 2000
    antiguedad = ANIO_ACTUAL - anio_const

    try:
        from parsers.zonas_manager import obtener_tasa_depreciacion_macrozona
        _tasa_zonal, _ = obtener_tasa_depreciacion_macrozona(prop)
    except Exception:
        _tasa_zonal = 0.006

    delta_anti_raw = max(-0.60, -(antiguedad * _tasa_zonal))
    UMBRAL_PENALIZACION_SEVERA = -0.18
    FACTOR_ATENUACION = 0.35
    if delta_anti_raw < UMBRAL_PENALIZACION_SEVERA:
        exceso = delta_anti_raw - UMBRAL_PENALIZACION_SEVERA
        delta_anti_efectivo = UMBRAL_PENALIZACION_SEVERA + (exceso * FACTOR_ATENUACION)
    else:
        delta_anti_efectivo = delta_anti_raw

    factor_estado = {
        'a_estrenar': 1.08, 'excelente': 1.05, 'muy_bueno': 1.03,
        'bueno': 1.0, 'regular': 0.92, 'malo': 0.85, 'a_refaccionar': 0.70
    }.get(estado_norm, 1.0)

    factor_calidad = {
        'premium': 1.08, 'excelente': 1.06, 'alta': 1.04, 'media': 1.0,
        'baja': 0.95, 'economica': 0.90
    }.get(calidad_norm, 1.0)

    factor_anti = max(0.40, 1.0 + delta_anti_efectivo)

    return {
        'factor_estado': factor_estado,
        'factor_calidad': factor_calidad,
        'depreciacion': factor_anti,
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
        if d_key == "parrilla":
            d_key = "parrilla_compartida"
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
    valor_comp_actual = m2_equiv * m2_base
    
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
        f"m2_base={m2_base:.0f}, m2_equiv={m2_equiv:.1f}, "
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


def _get_comp_id(c):
    """Genera un ID único y estable para un comparable basado en sus datos."""
    import hashlib
    seed = f"{c.get('precio')}_{c.get('m2')}_{c.get('direccion_limpia') or c.get('direccion')}_{c.get('lat')}_{c.get('lon')}"
    return hashlib.md5(seed.encode()).hexdigest()[:12]

def valuar_propiedad_v7(propiedad, fecha_ref=None, consultar_infomapa=True, retro_dias=0, flex_dormitorios=None, comp_excluded=None):
    """
    🚀 Modelo v7.0 - Evolución Híbrida PROFESIONAL
    Fusiona el Motor VPP (Clusters/Market) con Factores Físicos (Legacy).
    """
    from parsers.profiler import StepLedger
    _ml = StepLedger("entry_motor_v7_ledger", propiedad.get('nombre', '?'))
    _ml.mark("entered_func")
    # ══════════════════════════════════════════════
    # SECCIÓN 1: Datos de entrada y logging
    # ══════════════════════════════════════════════
    import os
    import logging
    from datetime import datetime, timedelta
    from parsers.motor_vpp_core import load_cache_cached, cargar_anclas_cached, get_binance_usdt_ars
    _ml.mark("after_lazy_imports")
    
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
    from parsers.profiler import profile_block
    with profile_block("load_cache_cached"):
        cache = load_cache_cached()
    with profile_block("cargar_anclas"):
        anclas = cargar_anclas_cached()

    # Cargar cache_scraping UNA VEZ y pasar a todos los llamados
    import json as _json
    _cache_scraping_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'cache_scraping.json'
    )
    if os.path.exists(_cache_scraping_path):
        with open(_cache_scraping_path, 'r', encoding='utf-8') as _f:
            cache_scraping_compartido = _json.load(_f)
    else:
        cache_scraping_compartido = None
    _ml.mark("after_cache_scraping_load")
    
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
    
    # ══════════════════════════════════════════════
    # SECCIÓN 2: m2 equivalentes y antigüedad dinámica
    # ══════════════════════════════════════════════
    m2_equiv = calcular_m2_equivalentes(prop)
    
    anio_const = prop.get('anio_construccion', ANIO_ACTUAL - prop.get('antiguedad', 0))
    antiguedad_dinamica = ANIO_ACTUAL - anio_const
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
    with profile_block("cluster_venta", prop):
        m2_base_venta_raw, n_v, meta_venta = obtener_mediana_cluster_v2(
            zona=normalizar_zona(zona_txt),
            dormitorios=dorms,
            operacion='venta',
            lat_ref=lat,
            lon_ref=lon,
            fecha_ref=fecha_ref,
            anio_sujeto=anio_const,
            tipo_inmueble=prop.get('tipo_inmueble') or prop.get('tipo') or 'departamento',
            cache_scraping=cache_scraping_compartido,
            retro_dias=retro_dias,
            flex_dormitorios=flex_dormitorios,
            m2_equiv=m2_equiv
        )

    # Si v2 tiene valor, usarlo; si no, fallback a ancla
    if m2_base_venta_raw > 0:
        m2_base_venta = m2_base_venta_raw
        metodo_origen = f"cluster_v2 (P{meta_venta.get('percentil_usado','33')}, {n_v} props)"
    else:
        if meta_venta.get('insuficientes_comparables'):
            comparables_venta = meta_venta.get('comparables_reales', [])
            mapa_html = _generar_html_mapa(prop, {
                'resolution_metadata': {
                    'radio_usado': 300,
                },
                'comparables_venta': comparables_venta,
                'valor_propiedad_usd': 0,
            })
            return {
                'error': 'insuficientes_comparables',
                'mensaje': 'No se encontraron suficientes comparables (mínimo 2).',
                'n_comps': meta_venta.get('n_comparables', 0),
                'comparables_venta': comparables_venta,
                'mapa_html': mapa_html,
                'resolution_metadata': {
                    'zona_original': meta_venta.get('zona_original'),
                    'zona_resolucion': meta_venta.get('zona_resolucion'),
                    'n_disponibles': meta_venta.get('n_comparables', 0),
                    'metodo': 'insuficiente',
                    'confidence': 'INSUFICIENTE',
                },
                'fuente': 'insuficiente',
            }
        # Fallback a ancla
        antiguedad = ANIO_ACTUAL - anio_const

        factor_deprec = max(0.5, 1.0 - (antiguedad * 0.006))

        m2_base_venta = valor_ancla_geo * factor_deprec
        metodo_origen = "Ancla (fallback)"
    
    # Metadata REALES de v2
    # ══════════════════════════════════════════════
    # SECCIÓN 4: Resolution metadata (DELEGADA a helper)
    # ══════════════════════════════════════════════
    if meta_venta.get('radio_usado'):
        resolution = 'GEO'
        confidence = 'ALTA' if n_v >= 15 else 'MEDIA' if n_v >= 8 else 'BAJA'
    elif n_v > 0:
        resolution = 'ZONAL'
        confidence = 'MEDIA'
    else:
        resolution = 'GLOBAL'
        confidence = 'BAJA'
    
    resolution_metadata = ensamblar_metadata_resolucion(
        meta_venta=meta_venta, n_v=n_v, zona_txt=zona_txt,
        m2_base_source=metodo_origen
    )
    
    # Comparables reales para el mapa y tabla (NO sintéticos)
    comparables_venta = meta_venta.get('comparables_reales', [])
    
    # Filtrar comparables excluidos por el usuario (Sincronización UI -> Motor)
    if comp_excluded:
        comparables_venta = [c for c in comparables_venta if _get_comp_id(c) not in comp_excluded]
        logger.info(f"[FILTER] Excluidos {len(comp_excluded)} comparables")
    
    logger.info(f"--- RESOLUTION ---")
    logger.info(f"resolution: {resolution}, confidence: {confidence}")
    logger.info(f"n_propiedades: {n_v}, radio: {meta_venta.get('radio_usado')}")
    logger.info(f"percentil: {meta_venta.get('percentil_usado')}")
    
    # Alquiler: obtener del cluster o fallback
    # NOTA: El cluster devuelve ARS/m2 directamente (no USD)
    # Usar zona normalizada para mejor match con cache
    zona_alq = normalizar_zona(zona_txt)
    with profile_block("cluster_alquiler", prop):
        m2_base_alq_raw, n_a, meta_alq = obtener_mediana_cluster_v2(zona=zona_alq, dormitorios=dorms, operacion='alquiler', lat_ref=lat, lon_ref=lon, fecha_ref=fecha_ref, tipo_inmueble=prop.get('tipo_inmueble') or prop.get('tipo') or 'departamento', cache_scraping=cache_scraping_compartido, flex_dormitorios=flex_dormitorios)
    
    # Fallback si no hay datos específicos (en ARS/m²)
    # Ajustar para entrar en rango:
    m2_base_alquiler = m2_base_alq_raw if m2_base_alq_raw > 0 else (11500 if dorms >= 2 else 13500)
    
    # 2. Metros Específicos para Alquiler (Prioriza Cubiertos)
    m2_cub = prop.get('m2_cubiertos', m2_equiv)
    m2_desc = prop.get('m2_descubiertos', 0)
    m2_equiv_alquiler = m2_cub + (m2_desc * 0.1)
    
    # 3. Fórmula Base (TAREA-073: sin factores hedónicos)
    # m2_microzona = precio del anchor más cercano (o cluster como fallback)
    m2_microzona = valor_ancla_geo if ancla_seleccionada is not None else m2_base_venta
    from parsers.zonas_manager import resolver_macrozona
    _mz_info = resolver_macrozona(prop)
    _ancla_id = str(ancla_seleccionada) if ancla_seleccionada is not None else None
    size_discount = calcular_size_adjustment(m2_equiv, macrozona_id=_mz_info.get('macrozona_id'), ancla_id=_ancla_id)
    valor_venta = m2_equiv * m2_microzona * size_discount
    
    logger.info(f"--- CALCULO BASE (TAREA-073) ---")
    logger.info(f"m2_equiv: {m2_equiv}, m2_microzona: {m2_microzona}, size_discount: {size_discount}")
    logger.info(f"valor_venta: {valor_venta}")
    
    # === ALQUILER: mantener lógica actual (con NLP y factores) ===
    from parsers.mercado_inmobiliario import _calcular_factores_rental
    f_rental = _calcular_factores_rental(prop)
    f_puros = (0.95 if prop.get('piso') == 0 else 1.0) * (1.10 if 'cruzada' in prop.get('ventilacion','') else 1.0)
    fact_ec = f_rental['factor_estado'] * f_rental['factor_calidad']
    factores_alquiler = f_rental['depreciacion'] * f_puros * (1.0 + (fact_ec - 1.0) * 0.50)
    
    # Regional Rental Buffer v9.4: Sinceramiento Periferia (Standard vs Profunda)
    tipo_det = (prop.get('tipo_inmueble') or prop.get('tipo') or '').lower()
    if 'casa' in tipo_det and any(x in zona_txt.lower() for x in ['oeste', 'sur', 'norte']):
        direccion = prop.get('direccion', '')
        desc = prop.get('descripcion_libre', '').lower()
        barrios_humildes = ['triangulo', 'godoy', 'moderno', 'ludueña', 'flores', 'empalme', 'industrial']
        altura = 0
        match_altura = re.search(r'\d+', direccion)
        if match_altura:
            altura = int(match_altura.group())
        es_profunda = altura > 4000 or any(b in desc for b in barrios_humildes) or any(b in direccion.lower() for b in barrios_humildes)
        buffer_regional = 0.55 if es_profunda else 0.75
        m2_base_alquiler *= buffer_regional
    
    GAP_ALQUILER = 0.92
    alquiler_mensual_ars = m2_equiv_alquiler * m2_base_alquiler * factores_alquiler * GAP_ALQUILER
    
    # NLP para alquiler solamente (TAREA-073: venta sin NLP)
    usdt_ars = get_binance_usdt_ars()
    from parsers.nlp_inmobiliario import calcular_ajuste_nlp_detallado
    desc_nlp = prop.get('descripcion_libre', '')
    amenities_present = prop.get('detalles_categoria', [])
    if not isinstance(amenities_present, list):
        amenities_present = []
    ajuste_nlp, _ = calcular_ajuste_nlp_detallado(desc_nlp, amenities_present=amenities_present)
    dorms = prop.get('dormitorios', 2)
    nlp_cap = 0.03 if dorms == 1 else 0.05
    ajuste_nlp_capped = min(ajuste_nlp, nlp_cap)
    alquiler_mensual_ars = alquiler_mensual_ars * (1 + ajuste_nlp_capped)
    
    # Asset values aditivos (cocheras + baulera)
    valor_activos = calcular_valor_activos(prop, m2_base_venta)
    valor_venta += valor_activos['total']
    
    # === ALQUILER: Cap Rate DATA-DRIVEN (v8.1) ===
    # Obtener lat/lon para Cap Rate (necesario para la función)
    lat_cr = prop.get('lat')
    lon_cr = prop.get('lon')
    
    # Primero: intentar Cap Rate derivado del mercado local
    cap_info = None
    if lat_cr is not None and lon_cr is not None:
        try:
            with profile_block("cap_rate", prop):
                cap_info = calcular_cap_rate_local(
                    lat_ref=lat_cr,
                    lon_ref=lon_cr,
                    dormitorios=dorms,
                    tipo_inmueble='departamento',
                    fecha_ref=fecha_ref,
                    cache_scraping=cache_scraping_compartido
                )
        except:
            pass
    
    # Determinar método y valores
    if cap_info is not None and not cap_info.get('es_fallback', True):
        # MODO DATA-DRIVEN: usar Cap Rate del mercado
        cap_rate = cap_info['cap_rate']
        # alquiler_mensual_usd = valor_realizable * cap_rate / 12
        alquiler_mensual_usd = valor_venta * cap_rate / 12
        alquiler_mensual_ars = alquiler_mensual_usd * usdt_ars
        
        # Rango de alquiler
        cap_rate_min = cap_info.get('cap_rate_min', cap_rate * 0.90)
        cap_rate_max = cap_info.get('cap_rate_max', cap_rate * 1.10)
        alq_min_usd = valor_venta * cap_rate_min / 12
        alq_max_usd = valor_venta * cap_rate_max / 12
        alq_min_ars = alq_min_usd * usdt_ars
        alq_max_ars = alq_max_usd * usdt_ars
        
        metodo_alquiler = 'mercado_local'
        es_fallback = False
        confianza_alq = cap_info.get('confianza', 'MEDIA')
    else:
        # FALLBACK: usar método existente con ROI zonal
        ROI_ZONAL = {
            'centro': 0.048,
            'martin': 0.048,
            'pichincha': 0.050,
            'abasto': 0.052,
            'facultades': 0.055,
            'sexta': 0.055,
            'sur': 0.060,
            'norte': 0.058,
            'oeste': 0.060,
        }
        zona_key = zona_txt.lower().strip() if zona_txt else 'centro'
        cap_rate = ROI_ZONAL.get(zona_key, 0.052)
        
        # No recalcular: mantener el cálculo original
        # (alquiler_mensual_ars ya fue calculado arriba)
        alq_min_ars = alquiler_mensual_ars * 0.85
        alq_max_ars = alquiler_mensual_ars * 1.15
        
        metodo_alquiler = 'roi_zonal_fallback'
        es_fallback = True
        confianza_alq = 'BAJA'
        
        cap_info = {
            'cap_rate': cap_rate,
            'n_venta': n_v,
            'n_alquiler': 0,
            'metodo': 'roi_zonal_fallback',
            'confianza': 'BAJA',
            'es_fallback': True
        }
    
    # === SIZE DISCOUNT para alquiler (unidades grandes) ===
    size_factor = calcular_size_discount_alquiler(m2_equiv)
    if size_factor < 1.0:
        logger.info(f"[SIZE_DISCOUNT] m2_equiv={m2_equiv}, factor={size_factor:.3f}")
        alquiler_mensual_ars = alquiler_mensual_ars * size_factor
        alq_min_ars = alq_min_ars * size_factor
        alq_max_ars = alq_max_ars * size_factor
    
    logger.info(f"NLP: {ajuste_nlp}")
    logger.info(f"valor_venta (TAREA-073 sin NLP): {valor_venta}")
    
    # ══════════════════════════════════════════════
    # SECCIÓN 3: Rango de venta (3 escenarios)
    # FASE 2: Extraído a calcular_rango_venta() en valuacion_helpers.py
    # como única fuente de verdad del rango.
    # ══════════════════════════════════════════════
    # === RANGO 3 ESCENARIOS (solo venta) ===
    p25_c = meta_venta.get('p25_cluster', 0)
    p50_c = meta_venta.get('p50_cluster', m2_base_venta)
    p75_c = meta_venta.get('p75_cluster', 0)
    
    rango_result = calcular_rango_venta(
        valor_estimado=valor_venta,
        p25_cluster=p25_c,
        p50_cluster=p50_c,
        p75_cluster=p75_c,
        n_muestras=n_v,
        radio=meta_venta.get('radio_usado', 999),
        confidence=resolution_metadata.get('confidence', 'MEDIA'),
    )
    
    rango_venta = rango_result['rango_venta']
    margen_error = rango_venta['margen_error']
    spread_pct = rango_venta['spread_pct']
    valor_venta_conservador = rango_venta['min']
    valor_venta_mercado = rango_venta['mid']
    valor_venta_optimista = rango_venta['max']
    
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
        f"Cap Rate Neto: {cap_rate_neto:.2f}% (Cap Bruto: {roi_bruto_anual:.1f}%). "
        f"Plusvalia {tipo_plusvalia}: {plusvalia_ciclo_pct:+.1f}%."
    )
    
    # Generar HTML del mapa (para caching)
    mapa_html = _generar_html_mapa(prop, {
        'resolution_metadata': resolution_metadata,
        'comparables_venta': comparables_venta,
        'valor_propiedad_usd': valor_venta,
    })
    
    # Enriquecer con datos de Infomapa (candidatos + imágenes)
    catastro_detalle = None
    if consultar_infomapa:
        try:
            with profile_block("infomapa", prop):
                from parsers.infomapa_api import enriquecer_con_infomapa
                catastro_raw = enriquecer_con_infomapa(prop)
            if catastro_raw:
                catastro_detalle = {
                    'candidatos': catastro_raw.get('candidatos', []),
                    'imagenes_disponibles': catastro_raw.get('imagenes_disponibles', {}),
                }
                n_cand = len(catastro_raw['candidatos'])
                n_ph_con_img = sum(1 for ph in catastro_raw['imagenes_disponibles'])
                logger.info(f"[INFOMAPA] {n_cand} candidatos, {n_ph_con_img} PHs con imágenes")
        except Exception as e:
            logger.warning(f"[INFOMAPA] Error: {e}")
            catastro_detalle = None
    
    # Macrozona de depreciacion (FASE 7A - solo metadata, no afecta valores)
    try:
        from parsers.zonas_manager import resolver_macrozona
        macrozona_info = resolver_macrozona(prop)
    except Exception:
        macrozona_info = {
            'macrozona_id': 'resto_rosario',
            'macrozona_nombre': 'Resto de Rosario',
            'metodo': 'default',
            'confianza': 'BAJA',
        }

    # ══════════════════════════════════════════════
    # SECCIÓN 5: Generar razonamiento narrativo
    # ══════════════════════════════════════════════
    try:
        razonamiento = generar_razonamiento_valuacion(prop, {
            'valor_propiedad_usd': valor_venta,
            'valor_activos': valor_activos,
            'valor_venta_conservador': valor_venta_conservador,
            'valor_venta_optimista': valor_venta_optimista,
            'valor_realizable': valor_realizable,
            'm2_equivalentes': m2_equiv,
            'm2_base_venta': m2_base_venta,
            'cap_rate': cap_rate,
            'alquiler_estimado_ars': alquiler_mensual_ars,
            'usdt_ars': usdt_ars,
            'rango_venta': rango_venta,
            'f_dict': calcular_factores(prop),
            'nlp_detecciones': [],
            'nlp_ajuste_pct': 0.0,
            'n_comps': n_v,
            'meta_venta': meta_venta,
            'macrozona_info': macrozona_info,
            'plusvalia_ciclo_usd': plusvalia_ciclo_usd,
            'plusvalia_ciclo_pct': plusvalia_ciclo_pct,
            'plusvalia_tipo': tipo_plusvalia,
            'plusvalia_12m_usd': plusvalia_12m_usd,
            'plusvalia_12m_pct': plusvalia_12m_pct,
            'expensas_ars': expensas_ars,
            'mantenimiento_mensual_ars': mantenimiento_mensual_ars,
            'fecha_mercado': cache.get("fecha") if cache else "Sin datos",
            'cap_rate_info': cap_info,
            'confianza_alquiler': confianza_alq,
            'alquiler_rango': {'min': round(alq_min_ars), 'mid': round(alquiler_mensual_ars), 'max': round(alq_max_ars)},
            'size_discount_alquiler': round(size_factor, 3),
            'es_fallback_alquiler': es_fallback,
            'cap_rate_anual': round(cap_rate_neto, 2),
            'cap_rate_bruto': round(roi_bruto_anual, 2),
            'metodo_alquiler': metodo_alquiler,
            'depreciacion_zonificada': {
                'macrozona': macrozona_info.get('macrozona_nombre', 'Resto de Rosario'),
                'macrozona_id': macrozona_info.get('macrozona_id', 'resto_rosario'),
                'tasa_anual': 0.0,
                'metodo_match': macrozona_info.get('metodo_match', 'default'),
                'confianza': macrozona_info.get('confianza_macrozona', 'BAJA'),
            },
        }, resolution_metadata)
    except Exception as e:
        razonamiento = f"Error generando razonamiento: {str(e)}"
        import traceback
        traceback.print_exc()
    
    # ══════════════════════════════════════════════
    # SECCIÓN 6: Return con resultado completo
    # ══════════════════════════════════════════════
    
    resultado = {
        'valor_propiedad_usd': round(valor_venta, 0),
        '_comp_excluded': comp_excluded or [],
        '_comp_exclusion_applied': False,
        'valor_realizable_usd': round(valor_realizable, 0),
        'valor_m2_actual_usd': round(valor_venta / m2_equiv, 2) if m2_equiv > 0 else 0,
        'm2_base_venta': round(m2_base_venta, 2),
        # Rango 3 escenarios
        'valor_venta_conservador': int(rango_venta['min']),
        'valor_venta_mercado': int(rango_venta['mid']),
        'valor_venta_optimista': int(rango_venta['max']),
        'valor_cierre_conservador': int(rango_venta['min'] * GAP_CIERRE),
        'valor_cierre_mercado': int(rango_venta['mid'] * GAP_CIERRE),
        'valor_cierre_optimista': int(rango_venta['max'] * GAP_CIERRE),
        'rango_venta': rango_venta,
        'alquiler_estimado_ars': round(alquiler_mensual_ars, 0),
        'alquiler_rango': {
            'min': round(alq_min_ars),
            'mid': round(alquiler_mensual_ars),
            'max': round(alq_max_ars),
        },
        'cap_rate': round(cap_rate, 4),
        'cap_rate_info': cap_info,
        'metodo_alquiler': metodo_alquiler,
        'es_fallback_alquiler': es_fallback,
        'confianza_alquiler': confianza_alq,
        'size_discount_alquiler': round(size_factor, 3),
        'cap_rate_anual': round(cap_rate_neto, 2), # Devolvemos NETO por defecto
        'cap_rate_bruto': round(roi_bruto_anual, 2),
        'usdt_ars': usdt_ars,
        'fecha_mercado': cache.get("fecha") if cache else "Sin datos",
        'm2_equivalentes': m2_equiv,
        'justificacion': justificacion,
        'rango_m2': f"USD {rango_venta['min']:,} - {rango_venta['max']:,}",
        'confianza': 'alta' if n_v > 10 else 'media',
        'nlp_detecciones': [],
        'nlp_ajuste_pct': 0.0,
        'plusvalia_ciclo_usd': round(plusvalia_ciclo_usd, 0),
        'plusvalia_ciclo_pct': round(plusvalia_ciclo_pct, 2),
        'plusvalia_tipo': tipo_plusvalia,
        'plusvalia_12m_usd': round(plusvalia_12m_usd, 0),
        'plusvalia_12m_pct': round(plusvalia_12m_pct, 2),
        'expensas_ars': expensas_ars,
'mantenimiento_mensual_ars': round(mantenimiento_mensual_ars, 0),
        'serie_mensual_m2': [],
        'resolution_metadata': resolution_metadata,
        'comparables_venta': comparables_venta,
        'retro_activo': meta_venta.get('retro_activo', False),
        'total_dias_ventana': meta_venta.get('total_dias_ventana', 180),
        'flex_dormitorios': meta_venta.get('flex_dormitorios', None),
        'sujeto_dormitorios': meta_venta.get('sujeto_dormitorios', None),
        'mapa_html': mapa_html,
        'razonamiento': razonamiento,
        'catastro_detalle': catastro_detalle,
        'macrozona_depreciacion': macrozona_info,
        # FASE 7B: depreciacion zonificada aplicada
        'depreciacion_zonificada': {
            'macrozona': macrozona_info.get('macrozona_nombre', 'Resto de Rosario'),
            'macrozona_id': macrozona_info.get('macrozona_id', 'resto_rosario'),
            'tasa_anual': 0.0,
            'metodo_match': macrozona_info.get('metodo_match', 'default'),
            'confianza': macrozona_info.get('confianza_macrozona', 'BAJA'),
        },
        'f_dict': calcular_factores(prop),
        'n_comps': n_v,
        'valor_activos': valor_activos,
        'tiene_barreras': bool(meta_venta.get('n_same_side', 0) > 0 and meta_venta.get('n_cross_soft', 0) > 0),
        'meta_venta': {
            'n_same_side': meta_venta.get('n_same_side', 0),
            'n_cross_soft': meta_venta.get('n_cross_soft', 0),
        },
    }
    from parsers.audit_logger import generar_audit_log, guardar_audit_log
    audit_log = generar_audit_log(
        propiedad=prop, resultado=resultado,
        f_dict=calcular_factores(prop), meta_venta=meta_venta, n_v=n_v,
        m2_base_venta_raw=m2_base_venta_raw,
        meta_alq=meta_alq, n_a=n_a, es_ventana3=False,
        m2_equiv_alquiler=m2_equiv_alquiler,
        factores_alquiler=factores_alquiler,
        m2_base_alquiler=m2_base_alquiler,
        ajuste_nlp=0.0, nlp_cap=0.0,
        resolution_metadata=resolution_metadata,
        rango_venta=rango_venta,
        comparables_venta=comparables_venta,
    )
    resultado['audit_log'] = audit_log
    try:
        guardar_audit_log(audit_log)
    except Exception:
        pass
    _ml.mark("before_return")
    _ml.close()
    return resultado



def calcular_cap_rate_local(lat_ref, lon_ref, dormitorios=2, tipo_inmueble='departamento', fecha_ref='2026-04', cache_scraping=None):
    """
    Deriva Cap Rate del mercado local usando clusters reales de venta y alquiler.
    Retorna dict con cap_rate y metadata de confianza.
    
    Args:
        lat_ref, lon_ref: coordenadas de referencia
        dormitorios: cantidad de dormitorios
        tipo_inmueble: tipo de inmueble
        fecha_ref: fecha de referencia para el cluster
        cache_scraping: dict opcional con datos precargados para evitar re-lectura
    
    Returns:
        dict con cap_rate, cap_rate_min, cap_rate_max, n_venta, n_alquiler,
        venta_m2_base, alq_m2_base, metodo, confianza, es_fallback
    """
    from datetime import datetime, timedelta
    
    try:
        zona = None
        
        # Cluster de VENTA (P33)
        venta_m2, n_venta, meta_venta = obtener_mediana_cluster_v2(
            zona=zona,
            dormitorios=dormitorios,
            operacion='venta',
            lat_ref=lat_ref,
            lon_ref=lon_ref,
            fecha_ref=fecha_ref,
            tipo_inmueble=tipo_inmueble,
            cache_scraping=cache_scraping
        )
        
        # Cluster de ALQUILER (P50)
        alq_m2, n_alq, meta_alq = obtener_mediana_cluster_v2(
            zona=zona,
            dormitorios=dormitorios,
            operacion='alquiler',
            lat_ref=lat_ref,
            lon_ref=lon_ref,
            fecha_ref=fecha_ref,
            tipo_inmueble=tipo_inmueble,
            cache_scraping=cache_scraping
        )
        
        # Extraer valores base
        if isinstance(venta_m2, dict):
            venta_base = venta_m2.get('mercado') or venta_m2.get('conservadora') or venta_m2.get('p50') or 0
        else:
            venta_base = venta_m2 or 0
        
        if isinstance(alq_m2, dict):
            alq_base = alq_m2.get('mercado') or alq_m2.get('p50') or alq_m2.get('conservadora') or 0
        else:
            alq_base = alq_m2 or 0
        
        # Validar datos suficientes
        if not venta_base or venta_base <= 0:
            return None
        if not alq_base or alq_base <= 0:
            return None
        if n_alq < 5:
            return None
        
        # Obtener USD rate
        try:
            from parsers.motor_vpp_core import get_binance_usdt_ars
            dolar = get_binance_usdt_ars()
        except:
            dolar = 1500  # fallback
        
        if not dolar or dolar <= 0:
            return None
        
        # Convertir alquiler ARS/m² a USD/m² anual
        alq_mensual_usd = alq_base / dolar
        alq_anual_usd = alq_mensual_usd * 12
        
        # Cap Rate = alquiler anual / valor venta
        cap_rate = alq_anual_usd / venta_base
        
        # Rango según confianza
        if n_alq >= 15:
            confianza = 'ALTA'
            margen = 0.08
        elif n_alq >= 8:
            confianza = 'MEDIA'
            margen = 0.12
        else:
            confianza = 'BAJA'
            margen = 0.15
        
        cap_rate_min = cap_rate * (1 - margen)
        cap_rate_max = cap_rate * (1 + margen)
        
        return {
            'cap_rate': round(cap_rate, 4),
            'cap_rate_min': round(cap_rate_min, 4),
            'cap_rate_max': round(cap_rate_max, 4),
            'n_venta': n_venta,
            'n_alquiler': n_alq,
            'venta_m2_base': round(venta_base, 2),
            'alq_m2_base': round(alq_base, 2),
            'metodo': 'mercado_local',
            'confianza': confianza,
            'es_fallback': False
        }
        
    except Exception as e:
        return None


def calcular_cap_rate_fallback(zona_normalizada=None):
    """
    Fallback: ROI zonal cuando no hay datos suficientes de alquiler.
    """
    ROI_ZONAL = {
        'centro': 0.048,
        'martin': 0.048,
        'pichincha': 0.050,
        'abasto': 0.052,
        'facultades': 0.055,
        'sexta': 0.055,
        'barrio': 0.055,
        'sur': 0.060,
        'norte': 0.058,
        'oeste': 0.060,
    }
    
    zona_key = zona_normalizada.lower().strip() if zona_normalizada else 'centro'
    cap_rate = ROI_ZONAL.get(zona_key, 0.052)
    
    return {
        'cap_rate': cap_rate,
        'cap_rate_min': round(cap_rate * 0.85, 4),
        'cap_rate_max': round(cap_rate * 1.15, 4),
        'n_venta': 0,
        'n_alquiler': 0,
        'metodo': 'roi_zonal_fallback',
        'confianza': 'BAJA',
        'es_fallback': True
    }


def _generar_html_mapa(prop, resultado):
    """Genera HTML del mapa UNA sola vez para caching."""
    try:
        import folium
        lat = prop.get('lat')
        lon = prop.get('lon')
        if not lat or not lon:
            return None
        
        radio = resultado.get('resolution_metadata', {}).get('radio_usado', 300)
        comparables = resultado.get('comparables_venta', [])
        valor = resultado.get('valor_propiedad_usd', 0)

        # Zoom calibrado segun el radio de busqueda (ANTES de crear el mapa)
        if radio <= 300:
            zoom_level = 15
        elif radio <= 500:
            zoom_level = 14
        elif radio <= 800:
            zoom_level = 13
        else:
            zoom_level = 12

        # location y zoom_start van en el CONSTRUCTOR para que surtan efecto
        m = folium.Map(
            location=[float(lat), float(lon)],
            zoom_start=zoom_level,
            tiles='cartodbpositron'
        )

        folium.Marker(
            [lat, lon],
            popup=f"📍 Propiedad - ${valor:,.0f}",
            icon=folium.Icon(color='red', icon='home')
        ).add_to(m)

        folium.Circle(
            [lat, lon],
            radius=radio,
            color='gray',
            fill=False,
            dash_array='5'
        ).add_to(m)

        for comp in comparables:
            if comp.get('lat') and comp.get('lon'):
                folium.CircleMarker(
                    [comp['lat'], comp['lon']],
                    radius=4,
                    color='blue',
                    fill=True,
                    fill_opacity=0.6,
                    popup=f"${comp.get('precio_m2', 0):,.0f}/m²"
                ).add_to(m)
        
        return m._repr_html_()
    except Exception as e:
        return None


def _calcular_sub_factors_breakdown(prop):
    """
    Desglose del factor hedonico para VIEW MODE.
    Usa calcular_factores_display() para valores reales de estado,calidad,amenities,otros.
    Depreciación no se incluye (TAREA-076): análisis ML demostró que la edad
    es confounding effect con ubicación — no existe como factor de mercado en Rosario.
    """
    from parsers.mercado_inmobiliario import calcular_factores_display
    fd = calcular_factores_display(prop)

    d_estado = fd['factor_estado'] - 1.0
    d_calidad = fd['factor_calidad'] - 1.0
    delta_edif = d_estado + d_calidad

    delta_amenities = fd.get('delta_amenities', 0.0)
    delta_otros = fd.get('delta_otros', 0.0)

    suma_cruda = delta_edif + delta_amenities + delta_otros
    suma_clamped = max(-0.40, min(0.40, suma_cruda))
    total = max(0.70, min(1.35, 1.0 + suma_clamped))

    return {
        'delta_edificacion': round(delta_edif, 4),
        'delta_amenities': round(delta_amenities, 4),
        'delta_otros': round(delta_otros, 4),
        'suma_cruda': round(suma_cruda, 4),
        'suma_clamped': round(suma_clamped, 4),
        'total': round(total, 4),
        'detalle_amenities': fd.get('detalle_amenities', ''),
        'detalle_otros': fd.get('detalle_otros', ''),
    }

def generar_resultado_manual(prop, manual_params):
    """
    Genera resultado de valuacion completo a partir de parametros manuales.
    Estructura compatible con valuar_propiedad_v7() para UI.
    """
    from parsers.motor_vpp_core import get_binance_usdt_ars
    usdt_ars = get_binance_usdt_ars()

    m2_equiv = calcular_m2_equivalentes(prop)
    usd_m2 = manual_params.get('usd_m2', 0)
    fh_raw = manual_params.get('factor_hedonico', 1.0)
    factor_hedonico = fh_raw if fh_raw != 0 else 1.0
    incertidumbre_pct = manual_params.get('incertidumbre_pct', 10.0)

    # Size adjustment por macrozona (TAREA-077)
    size_adj = 1.0
    mz_nombre = ""
    try:
        from parsers.zonas_manager import resolver_macrozona
        _mz_info = resolver_macrozona(prop)
        mz_nombre = _mz_info.get('macrozona', '')
        if manual_params.get('incluir_size_adj', True):
            ancla_id_input = manual_params.get('ancla_id', None)
            size_adj = calcular_size_adjustment(
                m2_equiv,
                macrozona_id=_mz_info.get('macrozona_id'),
                ancla_id=ancla_id_input,
            )
    except:
        pass

    # Factor constructora desde JSON
    factor_const = 1.0
    pct_const = 0
    constr_nombre = prop.get('constructora', '')
    try:
        constr_path = "C:/Users/Gustavo/ingresos_familiares_st/constructoras_rosario.json"
        if os.path.exists(constr_path):
            with open(constr_path, "r", encoding="utf-8") as f:
                constr_list = json.load(f)
                constr = constr_nombre.lower().strip()
                if constr and isinstance(constr_list, list):
                    for entry in constr_list:
                        if constr == entry.get('descripcion', '').lower().strip():
                            pct_const = entry.get('porcentaje', 0)
                            if manual_params.get('incluir_prima_const', True):
                                factor_const = 1.0 + pct_const / 100.0
                            break
    except:
        pass

    valor_activos = calcular_valor_activos(prop, usd_m2)

    ajuste_pct = manual_params.get('ajuste_pct', 0.0)
    subtotal = (m2_equiv * usd_m2 * size_adj * factor_hedonico * factor_const) + valor_activos['total']
    valor_venta = subtotal * (1 + ajuste_pct / 100.0)

    v_cons = valor_venta * (1 - incertidumbre_pct / 100.0)
    v_opt = valor_venta * (1 + incertidumbre_pct / 100.0)
    spread_pct = ((v_opt - v_cons) / v_cons) * 100 if v_cons > 0 else 0

    rango_venta = {
        'min': round(v_cons),
        'mid': round(valor_venta),
        'max': round(v_opt),
        'spread_pct': round(spread_pct, 1),
    }

    GAP_CIERRE = 0.92
    cap_rate = 0.05
    alquiler_mensual_usd = valor_venta * cap_rate / 12
    alquiler_mensual_ars = alquiler_mensual_usd * usdt_ars

    result = {
        'valor_propiedad_usd': round(valor_venta, 0),
        'valor_realizable_usd': round(valor_venta * GAP_CIERRE, 0),
        'valor_m2_actual_usd': round(valor_venta / m2_equiv, 2) if m2_equiv > 0 else 0,
        'm2_base_venta': round(usd_m2, 2),
        'valor_activos': valor_activos,
        'valor_venta_conservador': int(v_cons),
        'valor_venta_mercado': int(valor_venta),
        'valor_venta_optimista': int(v_opt),
        'valor_cierre_conservador': int(v_cons * GAP_CIERRE),
        'valor_cierre_mercado': int(valor_venta * GAP_CIERRE),
        'valor_cierre_optimista': int(v_opt * GAP_CIERRE),
        'rango_venta': rango_venta,
        'alquiler_estimado_ars': round(alquiler_mensual_ars, 0),
        'alquiler_rango': {
            'min': round(alquiler_mensual_ars * 0.9),
            'mid': round(alquiler_mensual_ars),
            'max': round(alquiler_mensual_ars * 1.1),
        },
        'cap_rate': cap_rate,
        'usdt_ars': usdt_ars,
        'm2_equivalentes': m2_equiv,
        'rango_m2': f"USD {int(v_cons):,} - {int(v_opt):,}",
        'confianza': 'media',
        'justificacion': 'Valuacion manual — parametros especificados por el analista.',
        'razonamiento': 'Valuacion manual — parametros especificados por el analista.',
        'comparables_venta': [],
        'mapa_html': None,
        'catastro_detalle': None,
        'fuente': 'manual',
        'manual_params': manual_params,
        'resolution_metadata': {
            'n_propiedades': 0,
            'fuente': 'manual',
            'zona': prop.get('zona', ''),
        },
        'size_adjustment': round(size_adj, 4),
        'macrozona_nombre': mz_nombre,
        'factor_total': factor_hedonico * factor_const,
        'factor_hedonico_efectivo': factor_hedonico,
        'factor_const': factor_const,
        'constructora': constr_nombre,
        'delta_anti': 1.0,
        'nlp_ajuste': 0,
        'sub_factors_breakdown': _calcular_sub_factors_breakdown(prop),
    }
    return result


def generar_razonamiento_valuacion(prop, resultado, meta):
    """
    Genera un texto narrativo profesional que justifica la valuacion.
    Versión cualitativa: explica los drivers de valor en lenguaje natural,
    sin porcentajes ni términos técnicos, como lo haría un tasador.
    """
    nombre = prop.get('nombre', 'La propiedad')
    zona = prop.get('zona', '')
    tipo = prop.get('tipo_inmueble') or prop.get('tipo') or 'departamento'
    m2_equiv = resultado.get('m2_equivalentes', 0)
    m2_cub = prop.get('m2_cubiertos', 0)
    dorms = prop.get('dormitorios', 0)
    anio = prop.get('anio_construccion', 0)
    anio = int(anio) if anio else 0
    piso = prop.get('piso', 0)
    total_pisos = prop.get('total_pisos', 0)
    antiguedad = (ANIO_ACTUAL - anio) if anio else 0

    valor_usd = resultado.get('valor_propiedad_usd', 0)
    vc = resultado.get('valor_venta_conservador', 0)
    vo = resultado.get('valor_venta_optimista', 0)
    vr = resultado.get('valor_realizable', 0)
    rango = resultado.get('rango_venta', {}) or {}
    spread = rango.get('spread_pct', 0)
    dolar = resultado.get('usdt_ars', 1480)
    alq_ars = resultado.get('alquiler_estimado_ars', 0)
    cap_rate = resultado.get('cap_rate', 0)
    f_dict = resultado.get('f_dict', {}) or {}

    lineas = []

    # ─── PÁRRAFO 1: Identificación ───
    tipo_inm_lower = tipo.lower()
    if tipo_inm_lower.startswith('departamento') or tipo_inm_lower.startswith('depto') or tipo_inm_lower.startswith('ph'):
        tipo_inm = 'departamento'
        art = 'un'
    elif tipo.startswith('casa'):
        tipo_inm = 'casa'
        art = 'una'
    else:
        tipo_inm = 'propiedad'
        art = 'una'

    if dorms <= 1:
        texto_dorms = 'un dormitorio'
    else:
        texto_dorms = f'{dorms} dormitorios'

    if piso == 0:
        texto_piso = 'en planta baja'
        m2_desc = prop.get('m2_descubiertos', 0) or prop.get('m2_descubiertos_propios', 0) or prop.get('m2_descubiertos_comun_exclusivo', 0) or 0
        if m2_desc >= 10:
            texto_piso = 'en planta baja con patio'
    elif total_pisos > 3 and piso >= total_pisos * 0.75:
        texto_piso = f'en un piso alto ({piso} de {total_pisos})'
    else:
        texto_piso = f'en el piso {piso} de {total_pisos}'

    orientacion = prop.get('orientacion', '').lower()
    texto_orientacion = ''
    if orientacion in ('norte',):
        texto_orientacion = ' con orientación norte, que favorece la luminosidad durante todo el día'
    elif orientacion in ('noreste',):
        texto_orientacion = ' con orientación noreste, muy valorada por su buena luz'
    elif orientacion in ('sur',):
        texto_orientacion = ' con orientación sur, que limita la entrada de luz natural'

    amb = prop.get('ambientes', 0)
    texto_amb = f" de {amb} ambientes" if amb and amb > dorms else ""
    lineas.append(
        f"{nombre} es {art} {tipo_inm}{texto_amb} de {texto_dorms} ubicado en {zona}, Rosario, "
        f"{texto_piso}{texto_orientacion}. "
        f"Con {m2_cub:.0f} m2 cubiertos, fue construido en {anio}"
        f"{' y tiene ' + str(antiguedad) + ' años de antigüedad' if antiguedad > 0 else ''}."
    )

    # ─── PÁRRAFO 2: Contexto de mercado ───
    n_comps = resultado.get('n_comps', meta.get('n_propiedades', 0))
    radio = meta.get('radio_usado', 300)

    if n_comps >= 25:
        texto_mercado = (
            "La zona cuenta con una oferta abundante de propiedades en el mercado, "
            "lo que permite establecer una referencia de precios sólida y confiable."
        )
    elif n_comps >= 12:
        texto_mercado = (
            f"La zona presenta una oferta moderada de propiedades en el mercado, "
            f"suficiente para establecer una referencia de precios."
        )
    elif n_comps >= 5:
        texto_mercado = (
            "La oferta de propiedades comparables en la zona es limitada, "
            "lo que introduce un grado de incertidumbre mayor en la estimación."
        )
    else:
        texto_mercado = (
            "La oferta de propiedades comparables en la zona es muy reducida, "
            "por lo que el valor estimado debe tomarse con mayor precaución."
        )

    meta_v = resultado.get('meta_venta', {}) or {}
    barreras = meta_v.get('n_same_side', 0) > 0 and meta_v.get('n_cross_soft', 0) > 0
    if barreras and radio > 0:
        texto_mercado += (
            " Se identificaron propiedades al otro lado de barreras geográficas "
            "(vías del ferrocarril o avenidas principales) que fueron tratadas "
            "por separado para evitar distorsiones en el análisis."
        )
    elif radio <= 500:
        texto_mercado += (
            " Las propiedades consideradas se encuentran dentro de un radio "
            "acotado, lo que garantiza que pertenecen al mismo entorno urbano."
        )

    lineas.append(texto_mercado)

    # ─── PÁRRAFO 3: Factores estructurales (cualitativo) ───
    factores_pos = []
    factores_neg = []
    factores_neutros = []

    # Vista
    vista = prop.get('vista', 'frente').lower()
    if vista == 'rio':
        factores_pos.append("la vista al río es un atributo excepcional y escaso, que marca una diferencia fundamental en el mercado")
    elif vista == 'despejada':
        factores_pos.append("la vista despejada aporta luminosidad y sensación de amplitud")
    elif vista == 'interna':
        factores_neg.append("la vista interna reduce el atractivo de la unidad al no tener una vista exterior directa")
    elif vista == 'pulmon':
        factores_neg.append("la vista a pulmón de manzana es menos valorada que una vista frontal")

    # Calidad
    calidad = (prop.get('calidad_edificio') or 'media').lower().replace(' ', '_')
    if calidad in ('premium',):
        factores_pos.append("la calidad constructiva premium es un factor distintivo que la posiciona por encima del estándar de la zona")
    elif calidad in ('excelente',):
        factores_pos.append("la calidad de construcción es excelente, superior al promedio del mercado")
    elif calidad in ('alta',):
        factores_pos.append("la calidad constructiva es alta, notablemente por encima del estándar")
    elif calidad in ('baja',):
        factores_neg.append("la calidad constructiva es básica, por debajo del estándar de la zona")
    elif calidad in ('economica',):
        factores_neg.append("la calidad constructiva es económica, lo que modera su valor frente a otras propiedades")

    # Estado
    estado = (prop.get('estado_detalle') or 'bueno').lower().replace(' ', '_')
    if estado in ('a_estrenar',):
        factores_pos.append("se encuentra a estrenar, lo que representa un diferencial importante en el mercado")
    elif estado in ('excelente',):
        factores_pos.append("se encuentra en excelente estado de conservación")
    elif estado in ('muy_bueno',):
        factores_pos.append("presenta un muy buen estado general")
    elif estado in ('regular',):
        factores_neg.append("su estado regular implica que requiere algunas mejoras y mantenimiento")
    elif estado in ('malo',):
        factores_neg.append("el estado general es desfavorable, con necesidad de refacciones")
    elif estado in ('a_refaccionar',):
        factores_neg.append("requiere refacciones integrales, lo que desvía el valor de propiedades en buen estado")

    # Ventilación
    ventilacion = prop.get('ventilacion', 'simple').lower()
    if 'cruzada' in ventilacion:
        factores_pos.append("la ventilación cruzada es muy valorada en Rosario porque mantiene los ambientes frescos sin necesidad de aire acondicionado")
    elif 'doble' in ventilacion:
        factores_pos.append("la doble ventilación permite una buena circulación de aire en la unidad")

    # Piso (factores adicionales)
    if piso > 0 and total_pisos > 3:
        if piso >= total_pisos * 0.75:
            factores_pos.append("la ubicación en un piso alto ofrece mejor vista y mayor luminosidad")
        elif piso == 1:
            pass  # neutro

    # Ubicación
    u_tipo = prop.get('ubicacion_tipo', 'calle').lower()
    if u_tipo == 'pasaje':
        factores_neg.append("la ubicación en pasaje, si bien es más tranquila, tiene menor exposición y es menos cotizada que una calle o avenida")
    elif u_tipo == 'avenida':
        factores_pos.append("la ubicación sobre avenida ofrece buena conectividad y exposición")

    # Gas
    gas = prop.get('gas_ok', 'si').lower()
    if gas == 'no':
        factores_neg.append("no dispone de gas natural, un aspecto relevante en Rosario donde la calefacción a gas es el sistema predominante")
    elif gas == 'en_proceso':
        factores_neutros.append("tiene gas natural en proceso de conexión")

    # Disposición (TAREA-028)
    disp = prop.get('disposicion', '')
    if disp == 'interna':
        factores_neg.append("la disposición interna limita la exposición y ventilación natural")
    elif disp == 'contrafrente':
        factores_neg.append("la disposición al contrafrente reduce la luminosidad respecto a una unidad al frente")
    elif disp == 'pasante':
        factores_pos.append("al ser pasante, goza de ventilación cruzada y luz en ambos frentes")

    # Balcón
    t_balcon = prop.get('tipo_balcon', 'ninguno').lower()
    if t_balcon in ('terraza',):
        factores_pos.append("la terraza exclusiva funciona como una extensión del living y es un diferencial importante")
    elif t_balcon in ('L',):
        factores_pos.append("el balcón en L ofrece un espacio exterior de mayor aprovechamiento")
    elif t_balcon in ('corrido',):
        factores_pos.append("el balcón corrido es un atributo valorado como espacio exterior habitable")
    elif t_balcon in ('frances', 'frances'):
        factores_neutros.append("el balcón francés permite ventilación pero no ofrece espacio habitable")

    # Funcionales
    funcionales = []
    if prop.get('doble_ingreso'):
        funcionales.append('doble ingreso')
    if prop.get('lavadero_independiente'):
        funcionales.append('lavadero independiente')
    if prop.get('toilet'):
        funcionales.append('toilet de recepción')
    if prop.get('baño_servicio'):
        funcionales.append('baño de servicio')
    if prop.get('layout_flexible'):
        funcionales.append('distribución flexible')
    if prop.get('placares_completos'):
        funcionales.append('placares completos')
    if prop.get('despensa'):
        funcionales.append('despensa')

    rec_tipo = prop.get('reciclado_tipo', 'ninguno').lower()
    if rec_tipo == 'parcial':
        funcionales.append('reciclada parcialmente')
    elif rec_tipo == 'total':
        funcionales.append('reciclada totalmente, como a nuevo')

    if funcionales:
        if len(funcionales) == 1:
            factores_pos.append(f"cuenta con {funcionales[0]}, un detalle funcional apreciado en el mercado")
        else:
            ultimo = funcionales.pop()
            texto_func = ", ".join(funcionales) + " y " + ultimo
            factores_pos.append(f"cuenta con {texto_func}, detalles funcionales que suman atractivo")

    # Seguridad
    detalles_seg = prop.get('detalles_categoria', [])
    if not isinstance(detalles_seg, list):
        detalles_seg = []
    if 'seguridad_24hs' in detalles_seg:
        factores_pos.append("el edificio cuenta con seguridad 24 horas, un servicio muy valorado")
    if 'seguridad_camaras' in detalles_seg and 'seguridad_24hs' not in detalles_seg:
        factores_pos.append("el edificio cuenta con cámaras de seguridad")

    # Ascensores
    asc = prop.get('ascensores_edificio')
    if asc is not None and total_pisos > 3 and asc <= 1 and piso > 2:
        factores_neg.append("el edificio tiene un solo ascensor, lo que puede generar demoras en horas pico")

    # Armar párrafo de factores
    if factores_pos or factores_neg:
        parrafos_fact = []

        if factores_pos:
            if len(factores_pos) == 1:
                parrafos_fact.append(f"Entre los atributos que contribuyen positivamente al valor se destaca que {factores_pos[0]}.")
            else:
                parrafos_fact.append(
                    "Entre los atributos que contribuyen positivamente al valor se destaca que "
                    + ", ".join(factores_pos[:-1]) + " y " + factores_pos[-1] + "."
                )

        if factores_neg:
            if len(factores_neg) == 1:
                parrafos_fact.append(f"Por otro lado, {factores_neg[0]}.")
            else:
                parrafos_fact.append(
                    "Por otro lado, " +
                    ", ".join(factores_neg[:-1]) + " y " + factores_neg[-1] + "."
                )

        if factores_neutros and not factores_neg:
            for n in factores_neutros:
                parrafos_fact.append(f"Además, {n}.")

        if not factores_pos and not factores_neg and not factores_neutros:
            parrafos_fact.append("La propiedad presenta características constructivas estándar para la zona, sin atributos que se desvíen significativamente del promedio del mercado.")

        lineas.append(" ".join(parrafos_fact))
    else:
        lineas.append("La propiedad presenta características estándar para la zona, sin atributos que se desvíen significativamente del promedio del mercado.")

    # ─── PÁRRAFO 4: Antigüedad y depreciación ───
    if antiguedad > 0:
        if antiguedad <= 5:
            texto_anti = (
                "Con pocos años de antigüedad, el desgaste por edad es mínimo "
                "y la propiedad se encuentra en su etapa óptima de valor."
            )
        elif antiguedad <= 15:
            texto_anti = (
                f"Con {antiguedad} años de antigüedad, la propiedad está en una etapa "
                f"donde el desgaste es moderado y no requiere intervenciones significativas."
            )
        elif antiguedad <= 30:
            texto_anti = (
                f"Con {antiguedad} años de antigüedad, el desgaste acumulado comienza a ser "
                f"notable y se refleja en el valor frente a propiedades más nuevas."
            )
        elif antiguedad <= 50:
            texto_anti = (
                f"La antigüedad de {antiguedad} años implica un desgaste considerable "
                f"que Impacta en el valor, aunque la propiedad puede mantener "
                f"atractivo si ha recibido mantenimiento."
            )
        else:
            texto_anti = (
                f"Con {antiguedad} años de antigüedad, la depreciación es significativa "
                f"y el valor se ve moderado sustancialmente por la edad."
            )

        lineas.append(texto_anti)

    # NLP detections
    nlp_det = resultado.get('nlp_detecciones', [])
    if nlp_det:
        keywords_nlp = [d[0] for d in nlp_det]
        textos_nlp = {
            'vista al río': 'vista al río',
            'vista franca al río': 'vista franca al río',
            'frente al río': 'frente al río',
            'primera línea río': 'primera línea de río',
            'a estrenar': 'a estrenar',
            'reciclado': 'reciclada',
            'reciclado a nuevo': 'reciclada a nuevo',
            'refaccionado': 'refaccionada',
            'muy luminoso': 'muy luminoso',
            'luminoso': 'luminoso',
            'orientación norte': 'orientación norte',
            'premium': 'premium',
            'alta gama': 'alta gama',
            'excelentes terminaciones': 'excelentes terminaciones',
            'balcón terraza': 'balcón terraza',
            'terraza exclusiva': 'terraza exclusiva',
            'patio': 'patio',
            'quincho': 'quincho',
            'parrillero': 'parrillero',
            'pileta': 'pileta',
            'piscina': 'piscina',
            'sum': 'SUM',
            'gimnasio': 'gimnasio',
            'seguridad 24 horas': 'seguridad 24 horas',
            'vigilancia': 'vigilancia',
            'cerca del río': 'cerca del río',
            'zona río': 'zona de río',
            'zona facultades': 'zona facultades',
            'a refaccionar': 'a refaccionar',
            'para reciclar': 'para reciclar',
            'estado original': 'estado original',
            'interno': 'interno',
            'muy interno': 'muy interno',
            'oscuro': 'oscuro',
            'planta baja': 'planta baja',
            'sin ascensor': 'sin ascensor',
            'zona insegura': 'zona insegura',
            'ruidoso': 'ruidoso',
        }
        textos_encontrados = []
        for kw in keywords_nlp:
            t = textos_nlp.get(kw, kw)
            textos_encontrados.append(f'"{t}"')
        if len(textos_encontrados) <= 2:
            texto_nlp = ', '.join(textos_encontrados)
        else:
            texto_nlp = ', '.join(textos_encontrados[:-1]) + ' y ' + textos_encontrados[-1]
        lineas.append(
            f"La descripción de la propiedad destaca términos como {texto_nlp}, "
            f"que reflejan una percepción {'favorable' if all(d[1] >= 0 for d in nlp_det) else 'variada'} "
            f"en el mercado y fueron considerados en la estimación."
        )

    # ─── PÁRRAFO 5: Valor y rango ───
    if spread < 12:
        texto_rango = (
            "El valor de publicación estimado es de " +
            f"USD {valor_usd:,.0f}. "
            "El rango de mercado es acotado, lo que refleja un mercado homogéneo "
            "donde los precios entre propiedades similares tienen poca dispersión. "
        )
    elif spread < 18:
        texto_rango = (
            "El valor de publicación estimado es de " +
            f"USD {valor_usd:,.0f}. "
            "El rango de mercado se sitúa entre un escenario conservador "
            f"(USD {vc:,.0f}) y uno optimista (USD {vo:,.0f}), "
            "con una dispersión moderada propia de una zona heterogénea. "
        )
    else:
        texto_rango = (
            "El valor de publicación estimado es de " +
            f"USD {valor_usd:,.0f}. "
            "El rango de mercado es amplio, reflejando la heterogeneidad de la oferta "
            f"en la zona: desde USD {vc:,.0f} en un escenario conservador "
            f"hasta USD {vo:,.0f} en uno optimista. "
        )

    if vr > 0:
        texto_rango += (
            f"Para una venta rápida, considerando los gastos de cierre habituales, "
            f"el valor realizable se ubica en USD {vr:,.0f}."
        )

    # Mention asset values (cocheras, baulera) if present
    val_act = resultado.get('valor_activos', {}) or {}
    if val_act.get('total', 0) > 0:
        texto_rango += (
            f" Se consideraron activos adicionales por "
            f"USD {val_act['total']:,.0f} ({val_act.get('detalle', '')})."
        )

    lineas.append(texto_rango)

    # ─── PÁRRAFO 6: Rendimiento por alquiler ───
    if cap_rate > 0 and alq_ars > 0:
        alq_usd = alq_ars / dolar if dolar else 0
        es_fallback = resultado.get('es_fallback_alquiler', False)
        confianza_alq = resultado.get('confianza_alquiler', 'MEDIA')

        if cap_rate >= 0.055:
            texto_renta = "un rendimiento atractivo para inversores, por encima del promedio de la ciudad"
        elif cap_rate >= 0.045:
            texto_renta = "un rendimiento alineado con el promedio del mercado de Rosario"
        else:
            texto_renta = "un rendimiento moderado, reflejando que el valor de venta es elevado en relación al alquiler"

        texto_renta_base = (
            f"En términos de renta, la propiedad genera un alquiler estimado de "
            f"ARS {alq_ars:,.0f} mensuales (USD {alq_usd:,.0f}), "
            f"lo que representa {texto_renta}."
        )

        cap_info = resultado.get('cap_rate_info', {}) or {}
        n_alq_comps = cap_info.get('n_alquiler', 0)
        if not es_fallback and n_alq_comps >= 5:
            texto_renta_base += (
                " El análisis de alquiler se realizó sobre datos directos del mercado "
                "de la zona, lo que otorga confianza en la estimación."
            )
        elif es_fallback:
            texto_renta_base += (
                " La estimación de alquiler se realizó por referencia indirecta "
                "debido a la escasez de propiedades en alquiler comparables en la zona."
            )

        lineas.append(texto_renta_base)

    # ─── PÁRRAFO 7: Plusvalía ───
    precio_compra = prop.get('valor_compra_usd', 0)
    fecha_compra = prop.get('fecha_compra', '')
    if precio_compra and precio_compra > 0 and fecha_compra:
        ganancia = valor_usd - precio_compra
        pct_ganancia = (ganancia / precio_compra) * 100
        if ganancia > 0:
            if pct_ganancia > 50:
                texto_plusv = "un crecimiento excepcional"
            elif pct_ganancia > 20:
                texto_plusv = "un crecimiento significativo"
            elif pct_ganancia > 5:
                texto_plusv = "un crecimiento moderado"
            else:
                texto_plusv = "una ligera apreciación"

            lineas.append(
                f"Desde su adquisición en {fecha_compra}, la propiedad registra "
                f"{texto_plusv} en su valor, reflejando la evolución del "
                f"mercado inmobiliario de {zona}."
            )

    return "\n\n".join(lineas)

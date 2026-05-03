"""
Utilidades y Helpers para Scraping Inmobiliario
================================================
Funciones auxiliares para procesamiento de datos, logging y helpers.
"""

import re
import json
import random
import time
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Union
from urllib.parse import urljoin, urlparse, urlunparse, quote
from functools import wraps
import unicodedata

from config import SCRAPING_CONFIG, LOGGING_CONFIG


# =============================================================================
# CONFIGURACIÓN DE LOGGING
# =============================================================================

def setup_logger(name: str = "scraper") -> logging.Logger:
    """Configura y retorna un logger con formato personalizado."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, LOGGING_CONFIG["level"]))
    
    formatter = logging.Formatter(LOGGING_CONFIG["format"])
    
    # Handler para archivo
    file_handler = logging.FileHandler(LOGGING_CONFIG["file"], encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Handler para consola
    if LOGGING_CONFIG["console"]:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()


# =============================================================================
# DECORADORES
# =============================================================================

def retry_on_exception(max_retries: int = None, delay: float = None, 
                       exceptions: tuple = (Exception,)):
    """
    Decorador para reintentar funciones que fallan.
    
    Args:
        max_retries: Máximo número de reintentos
        delay: Segundos de espera entre reintentos
        exceptions: Tupla de excepciones a capturar
    """
    if max_retries is None:
        max_retries = SCRAPING_CONFIG["max_retries"]
    if delay is None:
        delay = SCRAPING_CONFIG["retry_delay"]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Intento {attempt + 1}/{max_retries} falló: {e}. "
                            f"Reintentando en {wait_time}s..."
                        )
                        time.sleep(wait_time)
            raise last_exception
        return wrapper
    return decorator


def timing(func):
    """Decorador para medir tiempo de ejecución."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} ejecutado en {elapsed:.2f} segundos")
        return result
    return wrapper


# =============================================================================
# UTILIDADES DE RED Y HEADERS
# =============================================================================

def get_random_user_agent() -> str:
    """Retorna un User-Agent aleatorio de la lista configurada."""
    return random.choice(SCRAPING_CONFIG["user_agents"])


def get_random_headers(base_url: str = None) -> Dict[str, str]:
    """
    Genera headers HTTP aleatorios y realistas.
    
    Args:
        base_url: URL base para el header Referer
    
    Returns:
        Diccionario con headers HTTP
    """
    headers = SCRAPING_CONFIG["headers"].copy()
    headers["User-Agent"] = get_random_user_agent()
    
    if base_url:
        parsed = urlparse(base_url)
        headers["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"
        headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
    
    # Agregar variabilidad aleatoria
    if random.random() > 0.5:
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    
    return headers


def random_delay(min_sec: float = None, max_sec: float = None) -> None:
    """
    Espera un tiempo aleatorio para parecer comportamiento humano.
    
    Args:
        min_sec: Tiempo mínimo de espera
        max_sec: Tiempo máximo de espera
    """
    if min_sec is None:
        min_sec = SCRAPING_CONFIG["min_delay"]
    if max_sec is None:
        max_sec = SCRAPING_CONFIG["max_delay"]
    
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"Esperando {delay:.2f} segundos...")
    time.sleep(delay)


def build_url(base: str, path: str = "", params: Dict = None) -> str:
    """
    Construye una URL completa con parámetros.
    
    Args:
        base: URL base
        path: Ruta adicional
        params: Parámetros de query string
    
    Returns:
        URL completa
    """
    # Normalizar base
    base = base.rstrip('/')
    
    # Agregar path
    if path:
        path = path.lstrip('/')
        url = f"{base}/{path}"
    else:
        url = base
    
    # Agregar parámetros
    if params:
        query = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
        url = f"{url}?{query}"
    
    return url


def normalize_url(url: str, base: str = None) -> str:
    """
    Normaliza y completa URLs relativas.
    
    Args:
        url: URL a normalizar
        base: URL base para URLs relativas
    
    Returns:
        URL normalizada
    """
    if not url:
        return ""
    
    # Si es relativa y hay base
    if not url.startswith(('http://', 'https://')) and base:
        url = urljoin(base, url)
    
    # Normalizar
    parsed = urlparse(url)
    return urlunparse(parsed)


# =============================================================================
# UTILIDADES DE TEXTO Y DATOS
# =============================================================================

def clean_text(text: str) -> str:
    """
    Limpia y normaliza texto.
    
    Args:
        text: Texto a limpiar
    
    Returns:
        Texto limpio
    """
    if not text:
        return ""
    
    # Normalizar unicode
    text = unicodedata.normalize('NFKC', text)
    
    # Eliminar caracteres extraños
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Normalizar espacios
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def extract_number(text: str) -> Optional[float]:
    """
    Extrae un número de un texto.
    
    Args:
        text: Texto con número
    
    Returns:
        Número como float o None
    """
    if not text:
        return None
    
    # Limpiar texto
    text = clean_text(text)
    
    # Buscar patrón numérico
    match = re.search(r'[\d.,]+', text)
    if match:
        # Normalizar separador decimal
        num_str = match.group().replace('.', '').replace(',', '.')
        try:
            return float(num_str)
        except ValueError:
            pass
    
    return None


def extract_price(text: str) -> Dict[str, Any]:
    """
    Extrae precio y moneda de un texto.
    
    Args:
        text: Texto con precio
    
    Returns:
        Dict con precio y moneda
    """
    result = {"precio": None, "moneda": None, "precio_original": text}
    
    if not text:
        return result
    
    text = clean_text(text.upper())
    
    # Detectar moneda
    if 'USD' in text or 'U$S' in text or 'DOLAR' in text or 'DÓLAR' in text:
        result["moneda"] = "USD"
    elif '$' in text or 'PESO' in text or 'ARS' in text:
        result["moneda"] = "ARS"
    
    # Extraer número
    result["precio"] = extract_number(text)
    
    return result


def extract_surface(text: str) -> Dict[str, Any]:
    """
    Extrae superficie de un texto.
    
    Args:
        text: Texto con superficie
    
    Returns:
        Dict con superficie_total y superficie_cubierta
    """
    result = {"superficie_total": None, "superficie_cubierta": None}
    
    if not text:
        return result
    
    text = clean_text(text.lower())
    
    # Buscar superficie total
    match_total = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]?(?:\s*(?:totales?|total))?', text)
    if match_total:
        result["superficie_total"] = extract_number(match_total.group(1))
    
    # Buscar superficie cubierta
    match_cubierta = re.search(r'(\d+(?:[.,]\d+)?)\s*m[²2]?\s*(?:cubiert[oa]s?|cubiert[oa])', text)
    if match_cubierta:
        result["superficie_cubierta"] = extract_number(match_cubierta.group(1))
    
    return result


def extract_rooms(text: str) -> Dict[str, Any]:
    """
    Extrae cantidad de ambientes y dormitorios de un texto.
    
    Args:
        text: Texto con información de ambientes
    
    Returns:
        Dict con ambientes y dormitorios
    """
    result = {"ambientes": None, "dormitorios": None}
    
    if not text:
        return result
    
    text = clean_text(text.lower())
    
    # Monoambiente
    if 'monoambiente' in text or 'mono ambiente' in text:
        result["ambientes"] = 1
        result["dormitorios"] = 0
        return result
    
    # Ambientes
    match_amb = re.search(r'(\d+)\s*(?:ambientes?|amb\.?)', text)
    if match_amb:
        result["ambientes"] = int(match_amb.group(1))
    
    # Dormitorios
    match_dorm = re.search(r'(\d+)\s*(?:dormitorios?|dorm\.?)', text)
    if match_dorm:
        result["dormitorios"] = int(match_dorm.group(1))
    
    return result


def extract_bathrooms(text: str) -> Optional[int]:
    """
    Extrae cantidad de baños de un texto.
    
    Args:
        text: Texto con información de baños
    
    Returns:
        Cantidad de baños o None
    """
    if not text:
        return None
    
    text = clean_text(text.lower())
    
    match = re.search(r'(\d+)\s*(?:baños?|bañ\.?)', text)
    if match:
        return int(match.group(1))
    
    return None


def extract_antiquity(text: str) -> Optional[int]:
    """
    Extrae antigüedad en años de un texto.
    
    Args:
        text: Texto con información de antigüedad
    
    Returns:
        Años de antigüedad o None
    """
    if not text:
        return None
    
    text = clean_text(text.lower())
    
    # A estrenar
    if 'a estrenar' in text or 'nuevo' in text or '0 años' in text:
        return 0
    
    # Años específicos
    match = re.search(r'(\d+)\s*años?', text)
    if match:
        return int(match.group(1))
    
    return None


def extract_amenities(text: str) -> List[str]:
    """
    Extrae lista de amenities de un texto.
    
    Args:
        text: Texto descriptivo
    
    Returns:
        Lista de amenities encontradas
    """
    if not text:
        return []
    
    text = clean_text(text.lower())
    
    amenities_keywords = {
        "pileta": ["pileta", "piscina", "natatorio"],
        "gimnasio": ["gimnasio", "gym", "gimnasio equipado"],
        "quincho": ["quincho", "parrillero", "asador"],
        "jardin": ["jardín", "jardin", "patio", "parque"],
        "terraza": ["terraza", "balcón", "balcon", "solarium"],
        "laundry": ["laundry", "lavadero"],
        "sum": ["sum", "salón de usos múltiples", "salon de usos multiples"],
        "seguridad": ["seguridad", "vigilancia", "portería", "porteria", "encargado"],
        "cochera": ["cochera", "garage", "cocheras"],
        "ascensor": ["ascensor", "elevador"],
        "aire_acondicionado": ["aire acondicionado", "aa", "a/a", "climatizado"],
        "calefaccion": ["calefacción", "calefaccion", "losa radiante", "radiadores"],
        "wifi": ["wifi", "internet", "conexión"],
        "amueblado": ["amueblado", "totalmente equipado", "mobiliario"]
    }
    
    found = []
    for amenity, keywords in amenities_keywords.items():
        if any(kw in text for kw in keywords):
            found.append(amenity)
    
    return found


def detect_property_type(text: str) -> Optional[str]:
    """
    Detecta el tipo de propiedad de un texto.
    
    Args:
        text: Texto descriptivo
    
    Returns:
        Tipo de propiedad o None
    """
    if not text:
        return None
    
    text = clean_text(text.lower())
    
    tipos = {
        "departamento": ["departamento", "depto", "dpto", "piso"],
        "casa": ["casa", "vivienda", "hogar"],
        "ph": ["ph", "propiedad horizontal", "casa en altura"],
        "townhouse": ["townhouse", "casa en propiedad horizontal"],
        "local": ["local", "local comercial"],
        "oficina": ["oficina", "consultorio"],
        "terreno": ["terreno", "lote", "parcela", "tierra"],
        "cochera": ["cochera", "garage", "box"],
        "deposito": ["depósito", "deposito", "galpón", "galpon"],
        "campo": ["campo", "estancia", "chacra", "quinta"]
    }
    
    for tipo, keywords in tipos.items():
        if any(kw in text for kw in keywords):
            return tipo
    
    return None


def detect_neighborhood(text: str, ciudad: str = "Rosario") -> Optional[str]:
    """
    Detecta el barrio de un texto.
    
    Args:
        text: Texto descriptivo
        ciudad: Nombre de la ciudad
    
    Returns:
        Nombre del barrio o None
    """
    if not text:
        return None
    
    text = clean_text(text.lower())
    
    # Barrios de Rosario
    barrios_rosario = [
        "centro", "macrocentro", "microcentro",
        "pichincha", "barrio jardín", "barrio jardin",
        "fisherton", "funes", "roldán", "roldan",
        "alberdi", "sargento cabral",
        "echesortu", "lomas de alberdi",
        "parque alem", "parque alemania",
        "refinería", "refineria",
        "arroyito", "la tablada",
        "saladillo", "belgrano",
        "fontanina", "basural",
        "newbery", "ludueña", "luduena",
        "almagro", "hipster",
        "barrio blanco", "barrio negro",
        "puede crecer", "abasto",
        "romo", "tiro suizo",
        "barrio cristóbal colón", "barrio cristobal colon",
        "zona sur", "zona norte",
        "puerto norte", "puerto",
        "fontanarrosa", "san lorenzo"
    ]
    
    for barrio in barrios_rosario:
        if barrio in text:
            return barrio.title()
    
    return None


# =============================================================================
# UTILIDADES DE ARCHIVOS
# =============================================================================

def ensure_dir(path: str) -> Path:
    """
    Asegura que un directorio existe.
    
    Args:
        path: Ruta del directorio
    
    Returns:
        Objeto Path del directorio
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def save_json(data: Any, filename: str, directory: str = None) -> str:
    """
    Guarda datos en archivo JSON.
    
    Args:
        data: Datos a guardar
        filename: Nombre del archivo
        directory: Directorio de destino
    
    Returns:
        Ruta del archivo guardado
    """
    if directory is None:
        directory = SCRAPING_CONFIG["output_dir"]
    
    ensure_dir(directory)
    
    filepath = Path(directory) / filename
    
    with open(filepath, 'w', encoding=SCRAPING_CONFIG["encoding"]) as f:
        json.dump(data, f, indent=SCRAPING_CONFIG["json_indent"], 
                  ensure_ascii=False, default=str)
    
    logger.info(f"Datos guardados en: {filepath}")
    return str(filepath)


def load_json(filepath: str) -> Any:
    """
    Carga datos de archivo JSON.
    
    Args:
        filepath: Ruta del archivo
    
    Returns:
        Datos cargados
    """
    with open(filepath, 'r', encoding=SCRAPING_CONFIG["encoding"]) as f:
        return json.load(f)


def generate_filename(prefix: str, extension: str = "json") -> str:
    """
    Genera un nombre de archivo único con timestamp.
    
    Args:
        prefix: Prefijo del nombre
        extension: Extensión del archivo
    
    Returns:
        Nombre de archivo
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{timestamp}.{extension}"


def get_file_hash(filepath: str) -> str:
    """
    Calcula hash MD5 de un archivo.
    
    Args:
        filepath: Ruta del archivo
    
    Returns:
        Hash MD5 en hexadecimal
    """
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# =============================================================================
# UTILIDADES DE ESTADÍSTICAS
# =============================================================================

class ScrapingStats:
    """Clase para mantener estadísticas del scraping."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reinicia todas las estadísticas."""
        self.start_time = datetime.now()
        self.pages_scraped = 0
        self.properties_found = 0
        self.properties_saved = 0
        self.errors = []
        self.inmobiliarias_processed = []
    
    def add_page(self):
        """Incrementa contador de páginas."""
        self.pages_scraped += 1
    
    def add_property(self):
        """Incrementa contador de propiedades encontradas."""
        self.properties_found += 1
    
    def save_property(self):
        """Incrementa contador de propiedades guardadas."""
        self.properties_saved += 1
    
    def add_error(self, error: str, source: str = None):
        """Registra un error."""
        self.errors.append({
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "source": source
        })
    
    def add_inmobiliaria(self, nombre: str, status: str = "ok"):
        """Registra procesamiento de inmobiliaria."""
        self.inmobiliarias_processed.append({
            "nombre": nombre,
            "status": status,
            "timestamp": datetime.now().isoformat()
        })
    
    @property
    def elapsed_time(self) -> float:
        """Tiempo transcurrido en segundos."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict:
        """Convierte estadísticas a diccionario."""
        return {
            "start_time": self.start_time.isoformat(),
            "elapsed_seconds": round(self.elapsed_time, 2),
            "pages_scraped": self.pages_scraped,
            "properties_found": self.properties_found,
            "properties_saved": self.properties_saved,
            "errors_count": len(self.errors),
            "errors": self.errors,
            "inmobiliarias_processed": self.inmobiliarias_processed
        }
    
    def summary(self) -> str:
        """Retorna resumen de estadísticas."""
        return (
            f"\n{'='*50}\n"
            f"RESUMEN DE SCRAPING\n"
            f"{'='*50}\n"
            f"Tiempo total: {self.elapsed_time:.2f} segundos\n"
            f"Páginas procesadas: {self.pages_scraped}\n"
            f"Propiedades encontradas: {self.properties_found}\n"
            f"Propiedades guardadas: {self.properties_saved}\n"
            f"Errores: {len(self.errors)}\n"
            f"Inmobiliarias procesadas: {len(self.inmobiliarias_processed)}\n"
            f"{'='*50}"
        )


# Instancia global de estadísticas
stats = ScrapingStats()

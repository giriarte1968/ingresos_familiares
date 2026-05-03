"""
Motor de Scraping Inmobiliario - Técnicas Avanzadas
====================================================
Implementa scraping con múltiples técnicas:
- Requests con sesiones y rotación de headers
- Selenium para sitios con JavaScript
- Async scraping con aiohttp
- Anti-bot evasion
- Manejo de reintentos con exponential backoff
"""

import re
import json
import time
import random
import asyncio
import aiohttp
from typing import Optional, Dict, List, Any, Generator
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# Selenium imports (con manejo de errores)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        TimeoutException, 
        NoSuchElementException,
        WebDriverException
    )
    # Undetected chromedriver para evitar detección
    try:
        import undetected_chromedriver as uc
        HAS_UNDETECTED = True
    except ImportError:
        HAS_UNDETECTED = False
    
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    HAS_UNDETECTED = False

# lxml para parsing rápido
try:
    import lxml
    HAS_LXML = True
except ImportError:
    HAS_LXML = False

from config import (
    SCRAPING_CONFIG, SELECTORES_COMUNES, PATRONES_REGEX,
    CARACTERISTICAS, INMOBILIARIAS
)
from utils import (
    logger, retry_on_exception, timing, random_delay,
    get_random_headers, get_random_user_agent, build_url, normalize_url,
    clean_text, extract_number, extract_price, extract_surface,
    extract_rooms, extract_bathrooms, extract_antiquity, extract_amenities,
    detect_property_type, detect_neighborhood, 
    stats, ScrapingStats
)


# =============================================================================
# CLASE BASE DE SCRAPING
# =============================================================================

class BaseScraper:
    """Clase base para todos los scrapers."""
    
    def __init__(self, config: Dict = None):
        self.config = config or SCRAPING_CONFIG
        self.session = None
        self.driver = None
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        
    def close(self):
        """Cierra conexiones y recursos."""
        if self.session:
            self.session.close()
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


# =============================================================================
# SCRAPER CON REQUESTS (Para sitios estáticos)
# =============================================================================

class RequestsScraper(BaseScraper):
    """
    Scraper usando requests con técnicas avanzadas:
    - Sesiones persistentes
    - Rotación de User-Agents
    - Reintentos con exponential backoff
    - Rate limiting inteligente
    """
    
    def __init__(self, config: Dict = None):
        super().__init__(config)
        self._setup_session()
    
    def _setup_session(self):
        """Configura sesión HTTP con reintentos y adapters."""
        self.session = requests.Session()
        
        # Configurar reintentos
        retry_strategy = Retry(
            total=self.config["max_retries"],
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=self.config["max_concurrent"]
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    @retry_on_exception(exceptions=(requests.RequestException,))
    def fetch_page(self, url: str, params: Dict = None, 
                   method: str = "GET", data: Dict = None) -> Optional[str]:
        """
        Obtiene el HTML de una página.
        
        Args:
            url: URL de la página
            params: Parámetros de query string
            method: Método HTTP (GET o POST)
            data: Datos para POST
        
        Returns:
            HTML de la página o None si falla
        """
        headers = get_random_headers(url)
        
        logger.info(f"Obteniendo: {url}")
        
        try:
            if method.upper() == "POST":
                response = self.session.post(
                    url, 
                    headers=headers,
                    data=data,
                    params=params,
                    timeout=self.config["timeout"],
                    allow_redirects=True
                )
            else:
                response = self.session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.config["timeout"],
                    allow_redirects=True
                )
            
            response.raise_for_status()
            
            # Verificar si hay contenido
            if not response.content:
                logger.warning(f"Respuesta vacía de {url}")
                return None
            
            # Rate limiting
            random_delay()
            
            stats.add_page()
            return response.text
            
        except requests.HTTPError as e:
            logger.error(f"Error HTTP {e.response.status_code} en {url}")
            if e.response.status_code == 429:
                # Rate limited - esperar más tiempo
                retry_after = int(e.response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Esperando {retry_after} segundos...")
                time.sleep(retry_after)
                raise
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error de conexión en {url}: {e}")
            raise
    
    def parse_html(self, html: str, parser: str = None) -> BeautifulSoup:
        """
        Parsea HTML con BeautifulSoup.
        
        Args:
            html: HTML a parsear
            parser: Parser a usar ('html.parser', 'lxml', 'html5lib')
        
        Returns:
            Objeto BeautifulSoup
        """
        if parser is None:
            parser = "lxml" if HAS_LXML else "html.parser"
        
        return BeautifulSoup(html, parser)
    
    def extract_links(self, soup: BeautifulSoup, base_url: str,
                      patterns: List[str] = None) -> List[str]:
        """
        Extrae todos los links de una página.
        
        Args:
            soup: Objeto BeautifulSoup
            base_url: URL base para resolver links relativos
            patterns: Patrones regex para filtrar links
        
        Returns:
            Lista de URLs
        """
        links = []
        
        for tag in soup.find_all('a', href=True):
            href = tag['href']
            url = normalize_url(href, base_url)
            
            if url and url.startswith(('http://', 'https://')):
                # Filtrar por patrones si se especifican
                if patterns:
                    if any(re.search(p, url, re.IGNORECASE) for p in patterns):
                        links.append(url)
                else:
                    links.append(url)
        
        return list(set(links))


# =============================================================================
# SCRAPER CON SELENIUM (Para sitios dinámicos)
# =============================================================================

class SeleniumScraper(BaseScraper):
    """
    Scraper usando Selenium con técnicas anti-detección:
    - Undetected ChromeDriver
    - Rotación de fingerprints
    - Manejo de JavaScript
    - Evitación de detección de bots
    """
    
    def __init__(self, config: Dict = None, headless: bool = True):
        super().__init__(config)
        self.headless = headless
        self._setup_driver()
    
    def _setup_driver(self):
        """Configura el driver de Selenium con opciones anti-detección."""
        if not HAS_SELENIUM:
            raise ImportError("Selenium no está instalado. Instala con: pip install selenium")
        
        options = Options()
        
        # Configurar opciones de Chrome
        if self.headless:
            options.add_argument('--headless=new')
        
        # Opciones anti-detección
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        
        # Configurar ventana
        options.add_argument(f'--window-size={self.config["selenium"]["window_size"][0]},{self.config["selenium"]["window_size"][1]}')
        
        # Deshabilitar imágenes para más velocidad
        if self.config["selenium"]["disable_images"]:
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
        
        # User agent aleatorio
        options.add_argument(f'--user-agent={get_random_user_agent()}')
        
        # Excluir switches de automatización
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            if HAS_UNDETECTED:
                # Usar undetected-chromedriver
                self.driver = uc.Chrome(options=options)
            else:
                # Fallback a selenium normal
                self.driver = webdriver.Chrome(options=options)
                
                # Aplicar scripts anti-detección
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        })
                    '''
                })
            
            self.driver.set_page_load_timeout(self.config["selenium"]["page_load_timeout"])
            logger.info("Driver de Selenium inicializado correctamente")
            
        except WebDriverException as e:
            logger.error(f"Error inicializando Selenium: {e}")
            raise
    
    def fetch_page(self, url: str, wait_for: str = None, 
                   timeout: int = None) -> Optional[str]:
        """
        Obtiene el HTML de una página con Selenium.
        
        Args:
            url: URL de la página
            wait_for: Selector CSS para esperar a que cargue
            timeout: Timeout en segundos
        
        Returns:
            HTML de la página o None
        """
        if timeout is None:
            timeout = self.config["timeout"]
        
        logger.info(f"Obteniendo con Selenium: {url}")
        
        try:
            self.driver.get(url)
            
            # Esperar a que cargue un elemento específico
            if wait_for:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                )
            else:
                # Esperar genérica
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
            
            # Scroll para cargar contenido lazy
            self._scroll_page()
            
            html = self.driver.page_source
            stats.add_page()
            
            random_delay()
            return html
            
        except TimeoutException:
            logger.error(f"Timeout cargando {url}")
            return None
        except Exception as e:
            logger.error(f"Error con Selenium en {url}: {e}")
            return None
    
    def _scroll_page(self, pause_time: float = 0.5):
        """Hace scroll en la página para cargar contenido lazy."""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for _ in range(3):  # Hacer scroll 3 veces
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
    
    def click_element(self, selector: str, timeout: int = 10) -> bool:
        """
        Hace clic en un elemento.
        
        Args:
            selector: Selector CSS del elemento
            timeout: Timeout en segundos
        
        Returns:
            True si tuvo éxito
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
            )
            element.click()
            return True
        except Exception as e:
            logger.error(f"Error haciendo clic en {selector}: {e}")
            return False
    
    def execute_script(self, script: str) -> Any:
        """Ejecuta JavaScript en la página."""
        return self.driver.execute_script(script)
    
    def get_cookies(self) -> List[Dict]:
        """Obtiene las cookies de la sesión actual."""
        return self.driver.get_cookies()
    
    def add_cookies(self, cookies: List[Dict]):
        """Agrega cookies a la sesión."""
        for cookie in cookies:
            self.driver.add_cookie(cookie)


# =============================================================================
# SCRAPER ASÍNCRONO (Para alto rendimiento)
# =============================================================================

class AsyncScraper:
    """
    Scraper asíncrono con aiohttp para alto rendimiento.
    Ideal para scraping masivo de múltiples páginas.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or SCRAPING_CONFIG
        self.semaphore = asyncio.Semaphore(self.config["max_concurrent"])
    
    async def fetch_page(self, session: aiohttp.ClientSession, 
                         url: str) -> Optional[str]:
        """
        Obtiene una página de forma asíncrona.
        
        Args:
            session: Sesión de aiohttp
            url: URL a obtener
        
        Returns:
            HTML de la página o None
        """
        async with self.semaphore:
            headers = get_random_headers(url)
            
            try:
                async with session.get(
                    url, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config["timeout"])
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        stats.add_page()
                        
                        # Rate limiting
                        await asyncio.sleep(random.uniform(
                            self.config["min_delay"],
                            self.config["max_delay"]
                        ))
                        
                        return html
                    else:
                        logger.warning(f"Status {response.status} en {url}")
                        return None
                        
            except asyncio.TimeoutError:
                logger.error(f"Timeout en {url}")
                return None
            except Exception as e:
                logger.error(f"Error en {url}: {e}")
                return None
    
    async def fetch_multiple(self, urls: List[str]) -> Dict[str, str]:
        """
        Obtiene múltiples páginas concurrentemente.
        
        Args:
            urls: Lista de URLs
        
        Returns:
            Diccionario URL -> HTML
        """
        connector = aiohttp.TCPConnector(
            limit=self.config["max_concurrent"],
            enable_cleanup_closed=True
        )
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [self.fetch_page(session, url) for url in urls]
            results = await asyncio.gather(*tasks)
            
            return dict(zip(urls, results))


# =============================================================================
# EXTRACTOR DE PROPIEDADES
# =============================================================================

class PropertyExtractor:
    """
    Extrae características de propiedades de HTML.
    Soporta múltiples estructuras de sitios inmobiliarios.
    """
    
    def __init__(self):
        self.selectors = SELECTORES_COMUNES
        self.patterns = PATRONES_REGEX
    
    def extract_from_page(self, soup: BeautifulSoup, url: str,
                          custom_selectors: Dict = None) -> Dict[str, Any]:
        """
        Extrae datos de una página de propiedad individual.
        
        Args:
            soup: BeautifulSoup de la página
            url: URL de la propiedad
            custom_selectors: Selectores personalizados para el sitio
        
        Returns:
            Diccionario con datos de la propiedad
        """
        property_data = {
            "url_propiedad": url,
            "fecha_extraccion": datetime.now().isoformat(),
            "fuente": urlparse(url).netloc
        }
        
        selectors = custom_selectors or self.selectors
        
        # Extraer título
        property_data["titulo"] = self._extract_by_selectors(
            soup, selectors.get("titulo", [])
        )
        
        # Extraer precio
        price_text = self._extract_by_selectors(
            soup, selectors.get("precio", [])
        )
        price_data = extract_price(price_text)
        property_data.update(price_data)
        
        # Extraer ubicación
        property_data["ubicacion"] = self._extract_by_selectors(
            soup, selectors.get("ubicacion", [])
        )
        property_data["barrio"] = detect_neighborhood(
            property_data.get("ubicacion", "") + " " + 
            property_data.get("titulo", "")
        )
        
        # Extraer superficie
        surface_text = self._extract_by_selectors(
            soup, selectors.get("superficie", [])
        )
        surface_data = extract_surface(surface_text)
        property_data.update(surface_data)
        
        # Extraer ambientes
        rooms_text = self._extract_by_selectors(
            soup, selectors.get("ambientes", [])
        )
        rooms_data = extract_rooms(rooms_text)
        property_data.update(rooms_data)
        
        # Extraer descripción completa
        descripcion = self._extract_by_selectors(
            soup, selectors.get("descripcion", [])
        )
        property_data["descripcion"] = descripcion
        
        # Extraer información adicional de la descripción
        if descripcion:
            # Si no se encontraron ambientes, buscar en descripción
            if not property_data.get("ambientes"):
                rooms_from_desc = extract_rooms(descripcion)
                property_data.update(rooms_from_desc)
            
            # Buscar baños
            if not property_data.get("banos"):
                property_data["banos"] = extract_bathrooms(descripcion)
            
            # Buscar antigüedad
            if not property_data.get("antiguedad"):
                property_data["antiguedad"] = extract_antiquity(descripcion)
            
            # Buscar amenities
            property_data["amenities"] = extract_amenities(descripcion)
            
            # Detectar tipo de propiedad
            if not property_data.get("tipo_propiedad"):
                property_data["tipo_propiedad"] = detect_property_type(
                    descripcion + " " + property_data.get("titulo", "")
                )
        
        # Extraer imagen principal
        property_data["imagen_principal"] = self._extract_image(soup, selectors)
        
        # Extraer datos con regex del HTML completo
        html_text = str(soup)
        property_data.update(self._extract_with_regex(html_text))
        
        return property_data
    
    def extract_from_listing(self, soup: BeautifulSoup, base_url: str,
                             custom_selectors: Dict = None) -> List[Dict]:
        """
        Extrae propiedades de una página de listado.
        
        Args:
            soup: BeautifulSoup de la página
            base_url: URL base para resolver links
            custom_selectors: Selectores personalizados
        
        Returns:
            Lista de diccionarios con datos básicos de propiedades
        """
        properties = []
        selectors = custom_selectors or self.selectors
        
        # Encontrar contenedores de propiedades
        containers = self._find_containers(soup, selectors)
        
        for container in containers:
            try:
                prop_data = self._extract_from_container(container, base_url, selectors)
                if prop_data:
                    properties.append(prop_data)
            except Exception as e:
                logger.debug(f"Error extrayendo propiedad: {e}")
                continue
        
        return properties
    
    def _find_containers(self, soup: BeautifulSoup, 
                         selectors: Dict) -> List[BeautifulSoup]:
        """Encuentra contenedores de propiedades."""
        container_selectors = selectors.get("contenedor_propiedades", [])
        
        for selector in container_selectors:
            containers = soup.select(selector)
            if containers:
                logger.debug(f"Encontrados {len(containers)} contenedores con '{selector}'")
                return containers
        
        return []
    
    def _extract_from_container(self, container: BeautifulSoup,
                                base_url: str, selectors: Dict) -> Optional[Dict]:
        """Extrae datos de un contenedor individual."""
        prop_data = {}
        
        # Extraer link
        link = self._extract_link(container, base_url, selectors)
        if link:
            prop_data["url_propiedad"] = link
        else:
            return None  # Sin link, no es una propiedad válida
        
        # Extraer precio
        price_text = self._extract_by_selectors(container, selectors.get("precio", []))
        if not price_text:
            price_text = self._extract_by_heuristics(container, "precio")
        prop_data.update(extract_price(price_text))
        
        # Extraer ubicación
        prop_data["ubicacion"] = self._extract_by_selectors(
            container, selectors.get("ubicacion", [])
        )
        
        # Extraer superficie
        surface_text = self._extract_by_selectors(
            container, selectors.get("superficie", [])
        )
        if not surface_text:
            surface_text = self._extract_by_heuristics(container, "superficie")
        prop_data.update(extract_surface(surface_text))
        
        # Extraer ambientes
        rooms_text = self._extract_by_selectors(
            container, selectors.get("ambientes", [])
        )
        if not rooms_text:
            rooms_text = self._extract_by_heuristics(container, "ambientes")
        prop_data.update(extract_rooms(rooms_text))
        
        # Extraer imagen
        prop_data["imagen_principal"] = self._extract_image(container, selectors)
        
        prop_data["fecha_extraccion"] = datetime.now().isoformat()
        prop_data["fuente"] = urlparse(base_url).netloc
        
        return prop_data
    
    def _extract_by_selectors(self, element: BeautifulSoup, 
                              selectors: List[str]) -> str:
        """Extrae texto usando múltiples selectores."""
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found:
                    return clean_text(found.get_text())
            except:
                continue
        
        # Intentar con atributos data-*
        for selector in selectors:
            if selector.startswith('[data-'):
                try:
                    found = element.select_one(selector)
                    if found:
                        return clean_text(found.get(selector[1:-1]))
                except:
                    continue
        
        return ""
    
    def _extract_link(self, container: BeautifulSoup, base_url: str,
                      selectors: Dict) -> Optional[str]:
        """Extrae link a la propiedad."""
        link_selectors = selectors.get("link", ["a[href]"])
        
        for selector in link_selectors:
            try:
                link_elem = container.select_one(selector)
                if link_elem and link_elem.get('href'):
                    return normalize_url(link_elem['href'], base_url)
            except:
                continue
        
        return None
    
    def _extract_image(self, element: BeautifulSoup, 
                       selectors: Dict) -> Optional[str]:
        """Extrae URL de imagen principal."""
        img_selectors = selectors.get("imagen", ["img"])
        
        for selector in img_selectors:
            try:
                img = element.select_one(selector)
                if img:
                    # Priorizar srcset > data-src > src
                    src = (
                        img.get('srcset', '').split()[0] if img.get('srcset') else
                        img.get('data-src') or
                        img.get('data-lazy-src') or
                        img.get('src')
                    )
                    if src and not src.startswith('data:'):
                        return src
            except:
                continue
        
        return None
    
    def _extract_with_regex(self, html: str) -> Dict[str, Any]:
        """Extrae datos usando patrones regex."""
        results = {}
        
        # Extraer superficies adicionales
        for pattern in self.patterns.get("superficie", []):
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                results.setdefault("superficie_total", extract_number(match.group()))
        
        # Extraer ambientes adicionales
        for pattern in self.patterns.get("ambientes", []):
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                results.setdefault("ambientes", extract_number(match.group()))
        
        # Extraer baños
        for pattern in self.patterns.get("banos", []):
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                results.setdefault("banos", extract_number(match.group()))
        
        # Extraer cochera
        for pattern in self.patterns.get("cochera", []):
            if re.search(pattern, html, re.IGNORECASE):
                results["tiene_cochera"] = True
                break
        
        # Extraer antigüedad
        for pattern in self.patterns.get("antiguedad", []):
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                results.setdefault("antiguedad", extract_number(match.group()))
        
        return results

    def _extract_by_heuristics(self, element: BeautifulSoup, campo: str) -> str:
        """Extrae datos buscando patrones en todo el texto del elemento."""
        text = element.get_text(" ", strip=True)
        
        if campo == "precio":
            # Buscar patrones de moneda: USD 100.000, $ 50.000, 100.000 USD
            patterns = [
                r'(?:USD|U\$D|\$)\s*[\d\.,]+',
                r'[\d\.,]+\s*(?:USD|U\$D|\$|dólares|pesos)'
            ]
            for p in patterns:
                match = re.search(p, text, re.IGNORECASE)
                if match:
                    return match.group()
        
        elif campo == "superficie":
            # Buscar patrones de m2: 100 m2, 100m2, 100 mts
            patterns = [
                r'[\d\.,]+\s*(?:m2|mts2|metros|mts)',
            ]
            for p in patterns:
                match = re.search(p, text, re.IGNORECASE)
                if match:
                    return match.group()

        elif campo == "ambientes":
            # Buscar n dorm, n amb
            patterns = [
                r'\d+\s*(?:dormitorios|dorm|ambientes|amb|habitaciones|hab)',
            ]
            for p in patterns:
                match = re.search(p, text, re.IGNORECASE)
                if match:
                    return match.group()
        
        return ""


# =============================================================================
# SCRAPER PRINCIPAL DE INMOBILIARIA
# =============================================================================

class InmobiliariaScraper:
    """
    Scraper completo para una inmobiliaria específica.
    Combina todas las técnicas según sea necesario.
    """
    
    def __init__(self, inmobiliaria: Dict, config: Dict = None):
        """
        Inicializa el scraper para una inmobiliaria.
        
        Args:
            inmobiliaria: Dict con datos de la inmobiliaria
            config: Configuración de scraping
        """
        self.inmobiliaria = inmobiliaria
        self.config = config or SCRAPING_CONFIG
        self.extractor = PropertyExtractor()
        
        # Inicializar scrapers según necesidad
        self.requests_scraper = RequestsScraper(config)
        self.selenium_scraper = None  # Lazy loading
        self.async_scraper = AsyncScraper(config)
    
    @timing
    def scrape(self, max_pages: int = 10, use_selenium: bool = False) -> List[Dict]:
        """
        Ejecuta el scraping completo de la inmobiliaria.
        
        Args:
            max_pages: Máximo de páginas a scrapear
            use_selenium: Si usar Selenium para JavaScript
        
        Returns:
            Lista de propiedades encontradas
        """
        if not self.inmobiliaria.get("activo", True):
            logger.info(f"Inmobiliaria {self.inmobiliaria['nombre']} está inactiva")
            return []
        
        logger.info(f"\n{'='*50}")
        logger.info(f"Iniciando scraping: {self.inmobiliaria['nombre']}")
        logger.info(f"{'='*50}")
        
        properties = []
        
        try:
            if use_selenium:
                properties = self._scrape_with_selenium(max_pages)
            else:
                properties = self._scrape_with_requests(max_pages)
            
            stats.add_inmobiliaria(self.inmobiliaria['nombre'], "ok")
            
        except Exception as e:
            logger.error(f"Error en scraping de {self.inmobiliaria['nombre']}: {e}")
            stats.add_error(str(e), self.inmobiliaria['nombre'])
            stats.add_inmobiliaria(self.inmobiliaria['nombre'], "error")
        
        logger.info(f"Propiedades encontradas: {len(properties)}")
        return properties
    
    def _scrape_with_requests(self, max_pages: int) -> List[Dict]:
        """Scraping usando requests."""
        properties = []
        base_url = self.inmobiliaria['url']
        search_path = self.inmobiliaria.get('busqueda', '')
        
        # Obtener primera página
        url = build_url(base_url, search_path)
        html = self.requests_scraper.fetch_page(url)
        
        if not html:
            return properties
        
        soup = self.requests_scraper.parse_html(html)
        
        # Extraer propiedades del listado
        found = self.extractor.extract_from_listing(soup, base_url)
        properties.extend(found)
        
        # Buscar paginación y más páginas
        pagination_links = self._find_pagination(soup, base_url)
        
        for i, page_url in enumerate(pagination_links[:max_pages - 1]):
            if i >= max_pages - 1:
                break
            
            random_delay()
            html = self.requests_scraper.fetch_page(page_url)
            
            if html:
                soup = self.requests_scraper.parse_html(html)
                found = self.extractor.extract_from_listing(soup, base_url)
                properties.extend(found)
        
        return properties
    
    def _scrape_with_selenium(self, max_pages: int) -> List[Dict]:
        """Scraping usando Selenium."""
        if not HAS_SELENIUM:
            logger.warning("Selenium no disponible, usando requests")
            return self._scrape_with_requests(max_pages)
        
        # Lazy loading de Selenium
        if not self.selenium_scraper:
            self.selenium_scraper = SeleniumScraper(self.config)
        
        properties = []
        base_url = self.inmobiliaria['url']
        search_path = self.inmobiliaria.get('busqueda', '')
        
        url = build_url(base_url, search_path)
        html = self.selenium_scraper.fetch_page(url)
        
        if not html:
            return properties
        
        soup = BeautifulSoup(html, "lxml" if HAS_LXML else "html.parser")
        found = self.extractor.extract_from_listing(soup, base_url)
        properties.extend(found)
        
        # Buscar más páginas
        for page in range(2, max_pages + 1):
            # Buscar botón de siguiente página
            next_selectors = [
                f"a[href*='page={page}']",
                f"a[href*='pagina={page}']",
                ".pagination .next a",
                "a.siguiente",
                "a.next"
            ]
            
            clicked = False
            for selector in next_selectors:
                if self.selenium_scraper.click_element(selector):
                    clicked = True
                    break
            
            if not clicked:
                break
            
            random_delay()
            html = self.selenium_scraper.driver.page_source
            soup = BeautifulSoup(html, "lxml" if HAS_LXML else "html.parser")
            found = self.extractor.extract_from_listing(soup, base_url)
            properties.extend(found)
        
        return properties
    
    def _find_pagination(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Encuentra links de paginación."""
        pagination_urls = []
        
        pagination_selectors = [
            ".pagination a",
            ".pager a",
            "nav[aria-label*='pagin'] a",
            "a[href*='page=']",
            "a[href*='pagina=']",
            ".page-link"
        ]
        
        for selector in pagination_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = normalize_url(href, base_url)
                    if full_url not in pagination_urls:
                        pagination_urls.append(full_url)
        
        return pagination_urls
    
    def close(self):
        """Cierra todos los scrapers."""
        if self.requests_scraper:
            self.requests_scraper.close()
        if self.selenium_scraper:
            self.selenium_scraper.close()

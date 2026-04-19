import requests
from bs4 import BeautifulSoup
import re
import math
import json
import time
import random
import os
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor

# Rutas y Configuración
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, "cache_scraping.json")
ANCLAS_FILE = os.path.join(BASE_DIR, "anclas_rosario.json")
CACHE_TTL_MINUTES = 60

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
]

# --- UTILITARIOS ---

def get_random_ua():
    return random.choice(USER_AGENTS)

def get_binance_usdt_ars():
    """
    Obtiene cotización representativa de USDT/ARS en Binance P2P vía CriptoYa.
    Prioriza el precio de mercado real para conversión de rentabilidad ARS->USD.
    """
    try:
        # Probamos primero el endpoint específico de Binance que suele promediar P2P
        r = requests.get('https://criptoya.com/api/binance/usdt/ars/1', timeout=5)
        if r.status_code == 200:
            data = r.json()
            # Usamos el 'totalAsk' que incluye comisiones bancarias promedio, 
            # o el 'ask' si no está disponible, que es lo que pagaríamos para pasar de ARS a USD.
            return data.get('totalAsk') or data.get('ask') or 1450.0
    except Exception as e:
        print(f"Error CriptoYa (Binance): {e}")

    try:
        # Fallback 1: Promedio del mercado (CriptoYa tiene un endpoint 'p2p' que promedia varios)
        r = requests.get('https://criptoya.com/api/usdt/ars/1', timeout=5)
        if r.status_code == 200:
            return r.json().get('binancep2p', {}).get('ask', 1450.0)
    except:
        pass
        
    return 1450.0

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except:
            pass
    return None

def save_cache(propiedades, status="completado", inicio=0):
    data = {
        "fecha": datetime.now().isoformat(),
        "status": status,
        "propiedades": propiedades,
        "inicio": inicio
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def cargar_anclas():
    if not os.path.exists(ANCLAS_FILE):
        return {}
    with open(ANCLAS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        anclas_list = data.get("anclas", data) if isinstance(data, dict) else data
        return {a["id"]: a for a in anclas_list}

def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def normalizar_zona(texto):
    texto = texto.lower()
    mapping = {
        "martin": "Martin", "centro": "Centro", "pellegrini": "Pellegrini",
        "sexta": "Sexta", "abasto": "Abasto", "facultades": "Facultades",
        "pichincha": "Pichincha", "puerto norte": "Puerto Norte"
    }
    for k, v in mapping.items():
        if k in texto: return v
    return "Otro"

# --- SCRAPERS ---

def deduplicar_propiedades(props):
    """
    Elimina propiedades duplicadas basandose en precio+m2+zona
    v11.1: Nueva función para evitar duplicados en cache
    """
    seen = set()
    unicas = []
    for p in props:
        key = (int(p.get('precio', 0)), int(p.get('m2', 0)), p.get('zona', ''))
        if key not in seen:
            seen.add(key)
            unicas.append(p)
    return unicas


def scrapear_argenprop(operacion="venta", max_pages=3):
    """
    Scraper para Argenprop con paginacion y deteccion de fin
    """
    import logging
    logger = logging.getLogger("motor_vpp")
    props = []
    
    # URLs base por tipo de dormitorio
    base_urls = [
        "monoambiente", "1-dormitorio", "2-dormitorios", "3-dormitorios", "4-dormitorios"
    ]
    
    headers = {"User-Agent": get_random_ua()}
    
    for tipo in base_urls:
        url_base = f"https://www.argenprop.com/departamentos/{operacion}/rosario/{tipo}"
        
        for page in range(1, max_pages + 1):
            if page == 1:
                url = url_base
            else:
                url = f"{url_base}?pagina={page}"
            
            try:
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code != 200:
                    break
                    
                soup = BeautifulSoup(r.text, 'html.parser')
                items = soup.find_all("div", class_="listing__item")
                
                # Detectar fin: si no hay items, salir
                if not items:
                    logger.debug(f"[Argenprop] No mas resultados en pagina {page} para {tipo}")
                    break
                
                logger.debug(f"[Argenprop] Pagina {page} - {len(items)} items para {tipo}")
                
                for t in items:
                    try:
                        price_text = t.find("p", class_="card__price")
                        if not price_text:
                            continue
                        price_text = price_text.text
                        
                        px_match = re.search(r'([\d.]+)', price_text.replace(",", "."))
                        if not px_match:
                            continue
                        precio = float(px_match.group(1).replace(".", ""))
                        if operacion == "venta" and "USD" not in price_text:
                            continue
                        
                        m2 = dorms = None
                        features = t.find("ul", class_="card__main-features")
                        if features:
                            text = features.text.lower()
                            m_match = re.search(r'(\d+)\s*m²', text)
                            if m_match:
                                m2 = float(m_match.group(1))
                            else:
                                m_match2 = re.search(r'(\d+)m', text)
                                if m_match2:
                                    m2 = float(m_match2.group(1))
                            
                            d_match = re.search(r'(\d+)\s*dorm', text)
                            if d_match:
                                dorms = int(d_match.group(1))
                        
                        if operacion == "alquiler" and (not m2 or m2 <= 0):
                            desc = t.get_text(" ").lower()
                            m_match = re.search(r'(\d+)\s*(?:m2|m²)', desc)
                            if m_match:
                                m2 = float(m_match.group(1))
                        
                        if precio and m2 and m2 > 0 and m2 < 500:
                            props.append({
                                "precio": precio,
                                "m2": m2,
                                "dormitorios": dorms or 1,
                                "valor_m2": precio / m2,
                                "direccion": t.find("h2").text.strip() if t.find("h2") else "",
                                "fuente": "argenprop",
                                "operacion": operacion,
                                "zona": normalizar_zona(t.text)
                            })
                    except:
                        continue
            
            except Exception as e:
                logger.debug(f"[Argenprop] Error en {tipo} pagina {page}: {e}")
                break
        
    logger.info(f"[Argenprop] Completado: {len(props)} propiedades")
    return props


def scrapear_ttl(operacion="venta"):
    """Scraper para TTL Propiedades - Version con anti-deteccion"""
    import logging
    import random
    logger = logging.getLogger("motor_vpp")
    props = []
    
    logger.info(f"[TTL] Iniciando scraper para {operacion}...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--no-sandbox",
            ]
        )
        context = browser.new_context(user_agent=get_random_ua())
        page = context.new_page()
        page.set_extra_http_headers({
            "Accept-Language": "es-AR,es;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        })
        
        op_str = "Alquiler" if operacion == "alquiler" else "Venta"
        urls_ttl = [
            f"https://www.ttlpropiedades.com/{op_str}?tipopropiedad=departamento&ambientes=1",
            f"https://www.ttlpropiedades.com/{op_str}?tipopropiedad=departamento&ambientes=2",
            f"https://www.ttlpropiedades.com/{op_str}",
        ]
        
        for ttl_url in urls_ttl:
            logger.debug(f"[TTL] Visitando: {ttl_url}")
            try:
                page.goto(ttl_url, timeout=30000)
                
                # Anti-deteccion: scroll erratico
                for _ in range(2):
                    page.evaluate("window.scrollBy(0, 300)")
                    page.wait_for_timeout(800)
                
                page.wait_for_timeout(2000)
                items = page.query_selector_all("ul#propiedades > li")
                logger.debug(f"[TTL] Encontrados {len(items)} items en {ttl_url}")
                
                for item in items:
                    try:
                        precio_el = item.query_selector("[class*='valor']")
                        if not precio_el:
                            continue
                        precio_text = precio_el.inner_text()
                        
                        if operacion == "venta":
                            precio_match = re.search(r"USD([\d.,]+)", precio_text)
                        else:
                            precio_match = re.search(r"\$([\d.,]+)", precio_text)
                        
                        if not precio_match:
                            continue
                        precio = float(precio_match.group(1).replace(",", "").replace(".", ""))
                        if operacion == "venta" and precio < 1000:
                            precio *= 1000
                        
                        m2_el = item.query_selector(".prop-data")
                        metros = dorms = None
                        if m2_el:
                            m2_text = m2_el.inner_text()
                            m_match = re.search(r"([\d.,]+)\s*m", m2_text)
                            if m_match:
                                metros = float(m_match.group(1).replace(",", "."))
                            d_match = re.search(r"(\d+)\s*dorm", m2_text, re.I)
                            if d_match:
                                dorms = int(d_match.group(1))
                        
                        link = item.query_selector("a[href]")
                        direccion = ""
                        if link:
                            href = link.get_attribute("href")
                            direccion = href.split("/")[-1] if href else ""
                            direccion = direccion.replace("-", " ")[:50]
                        
                        if precio and metros and 20 < metros < 250:
                            valor_m2 = precio / metros
                            zona = normalizar_zona(direccion)
                            valido = False
                            
                            if operacion == "venta" and 400 <= valor_m2 <= 4000 and precio > 10000:
                                valido = True
                            elif operacion == "alquiler" and 40000 <= precio <= 800000:
                                valido = True
                            
                            if valido:
                                props.append({
                                    "precio": precio,
                                    "m2": metros,
                                    "dormitorios": dorms,
                                    "valor_m2": valor_m2,
                                    "direccion": direccion,
                                    "fuente": "ttl",
                                    "operacion": operacion,
                                    "zona": zona
                                })
                    except:
                        continue
            except Exception as e:
                logger.warning(f"[TTL] Error en {ttl_url}: {e}")
                continue
        
        browser.close()
        logger.info(f"[TTL] Completado: {len(props)} propiedades")
    
    return props


def scrapear_lacapital(operacion="venta"):
    """
    Scraper para La Capital Inmuebles
    """
    import logging
    logger = logging.getLogger("motor_vpp")
    props = []
    
    logger.info("[LC] Iniciando scraper para La Capital...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(user_agent=get_random_ua())
        page = context.new_page()
        
        url = f"https://inmuebles.lacapital.com.ar/buscar-propiedades/?inmueble_hidden=Departamento&localidad=487&operacion_hidden={operacion.capitalize()}"
        
        try:
            page.goto(url, timeout=30000)
            page.wait_for_load_state("domcontentloaded", timeout=20000)
            
            for _ in range(2):
                page.evaluate("window.scrollBy(0, 400)")
                page.wait_for_timeout(1000)
            
            page.wait_for_timeout(3000)
            
            items = page.query_selector_all(".avisodestacado")
            logger.debug(f"[LC] Encontrados {len(items)} items")
            
            for item in items:
                try:
                    texto = item.inner_text()
                    
                    m_match = re.search(r"(\d+)\s*M", texto)
                    if not m_match:
                        continue
                    metros = int(m_match.group(1))
                    if not (20 < metros < 250):
                        continue
                    
                    precio_match = re.search(r"--\s*(\d+)", texto)
                    if not precio_match:
                        continue
                    precio = int(precio_match.group(1))
                    if precio < 10000:
                        precio *= 1000
                    
                    d_match = re.search(r"(\d+)\s*dorm", texto, re.I)
                    dorms = int(d_match.group(1)) if d_match else None
                    
                    dir_el = item.query_selector(".dir")
                    direccion = dir_el.inner_text() if dir_el else ""
                    direccion = direccion.replace("Departamento en Venta", "").replace("-", " ").strip()[:50]
                    
                    if precio and metros:
                        valor_m2 = precio / metros
                        zona = normalizar_zona(direccion)
                        valido = False
                        
                        if operacion == "venta" and 400 <= valor_m2 <= 4000:
                            valido = True
                        elif operacion == "alquiler" and 50000 <= precio <= 800000:
                            valido = True
                        
                        if valido:
                            props.append({
                                "operacion": operacion,
                                "precio": precio,
                                "m2": metros,
                                "dormitorios": dorms,
                                "valor_m2": valor_m2,
                                "direccion": direccion,
                                "zona": zona,
                                "fuente": "lacapital"
                            })
                except:
                    continue
        except Exception as e:
            logger.warning(f"[LC] Error: {e}")
        
        browser.close()
        logger.info(f"[LC] Completado: {len(props)} propiedades")
    
    return props


def scrapear_zonaprop():
    """
    Scraper para Zonaprop via API con anti-bloqueo
    """
    import logging
    import random
    logger = logging.getLogger("motor_vpp")
    props = []
    
    logger.info("[ZP] Iniciando scraper Zonaprop...")
    
    # Intentar con requests primero (más rápido)
    try:
        api_url = "https://www.zonaprop.com.ar/api-gateway/inmuebles/v1/search"
        params = {
            "operatingRegion": "rosario",
            "tipoInmueble": "departamento",
            "operacion": "venta",
            "estado": "todos",
        }
        headers = {
            "User-Agent": get_random_ua(),
            "Accept": "application/json",
            "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
            "Referer": "https://www.zonaprop.com.ar/",
            "Origin": "https://www.zonaprop.com.ar",
        }
        
        logger.debug("[ZP] Haciendo request a API...")
        response = requests.get(api_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            items_encontrados = data.get("results", [])[:30]
            logger.debug(f"[ZP] Encontrados {len(items_encontrados)} items")
            
            for item in items_encontrados:
                try:
                    precio = item.get("price", {}).get("amount", 0)
                    metros = item.get("superficie", {}).get("total", 0)
                    dorms = item.get("ambientes", {}).get("dormitorios")
                    titulo = item.get("title", "Sin titulo")
                    
                    if precio and metros and metros > 0:
                        valor_m2 = precio / metros
                        if 400 <= valor_m2 <= 3500:
                            zona = normalizar_zona(titulo)
                            props.append({
                                "precio": precio,
                                "m2": metros,
                                "dormitorios": dorms,
                                "valor_m2": valor_m2,
                                "direccion": titulo[:50],
                                "zona": zona,
                                "fuente": "zonaprop",
                                "operacion": "venta"
                            })
                except Exception as e:
                    logger.debug(f"[ZP] Error procesando item: {e}")
                    continue
            
            logger.info(f"[ZP] Completado via API: {len(props)} propiedades")
            return props
            
    except Exception as e:
        logger.warning(f"[ZP] Error con API, intentando con Playwright: {e}")
    
    # Fallback: intentar con Playwright (anti-detección)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ]
            )
            context = browser.new_context(
                user_agent=get_random_ua(),
                viewport={'width': random.randint(1200, 1920), 'height': random.randint(800, 1080)}
            )
            page = context.new_page()
            
            # Ir a la página principal primero para evitar bloqueos
            page.goto("https://www.zonaprop.com.ar/", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            
            # Después ir a la búsqueda
            search_url = "https://www.zonaprop.com.ar/departamentos/rosario/venta"
            page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            
            # Anti-deteccion: scroll basico (original)
            for _ in range(2):
                page.evaluate("window.scrollBy(0, 300)")
                page.wait_for_timeout(600)
            
            page.wait_for_timeout(2000)
            
            # Obtener HTML y buscar propiedades
            html = page.content()
            
            # Verificar si hay bloqueo
            if "Just a moment" in html or "Cloudflare" in html[:500]:
                logger.warning("[ZP] Detectado Cloudflare")
                browser.close()
                return props
            
            # Parsear con BeautifulSoup
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Buscar cards de propiedades (selector genérico)
            cards = soup.find_all("div", class_=lambda x: x and "card" in str(x).lower() if x else False)
            
            for card in cards[:30]:
                try:
                    texto = card.get_text(" ")
                    # Buscar precio
                    precio_match = re.search(r'USD\s*([\d,]+)', texto)
                    if not precio_match:
                        continue
                    precio = float(precio_match.group(1).replace(",", ""))
                    
                    # Buscar metros
                    m_match = re.search(r'(\d+)\s*m', texto)
                    if not m_match:
                        continue
                    metros = float(m_match.group(1))
                    
                    # Buscar dormitorios
                    d_match = re.search(r'(\d+)\s*dorm', texto, re.I)
                    dorms = int(d_match.group(1)) if d_match else None
                    
                    if precio and metros and 20 < metros < 300:
                        valor_m2 = precio / metros
                        if 400 <= valor_m2 <= 3500:
                            zona = normalizar_zona(texto)
                            props.append({
                                "precio": precio,
                                "m2": metros,
                                "dormitorios": dorms,
                                "valor_m2": valor_m2,
                                "direccion": "Propiedad ZP",
                                "zona": zona,
                                "fuente": "zonaprop",
                                "operacion": "venta"
                            })
                except Exception as e:
                    continue
            
            browser.close()
            logger.info(f"[ZP] Completado via Playwright: {len(props)} propiedades")
    
    except Exception as e:
        logger.error(f"[ZP] Error en fallback Playwright: {e}")
    
    return props


def scrapear_todoprop(operacion="venta"):
    """Scraper para TodoProps"""
    import logging
    logger = logging.getLogger("motor_vpp")
    props = []
    
    url = "https://www.todoprop.com.ar/inmuebles/rosario/venta/departamentos"
    headers = {"User-Agent": get_random_ua()}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning("[TP] Error fetching URL")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        cards = soup.find_all("div", class_="inmueble-item")
        logger.debug(f"[TP] Encontrados {len(cards)} cards")
        
        for card in cards:
            try:
                precio_el = card.find(class_="precio")
                if not precio_el:
                    continue
                precio_text = precio_el.get_text()
                precio_match = re.search(r'USD\s*([\d.,]+)', precio_text.replace(".", "").replace(",", ""))
                if not precio_match:
                    continue
                precio = float(precio_match.group(1).replace(",", "."))
                
                m2_el = card.find(class_="metros")
                metros = None
                if m2_el:
                    m_match = re.search(r'(\d+)', m2_el.get_text())
                    if m_match:
                        metros = float(m_match.group(1))
                
                if not metros or metros < 20:
                    continue
                
                titulo_el = card.find("h3") or card.find(class_="titulo")
                titulo = titulo_el.get_text() if titulo_el else "Sin titulo"
                
                if precio and metros:
                    valor_m2 = precio / metros
                    if 400 <= valor_m2 <= 3500:
                        zona = normalizar_zona(titulo)
                        props.append({
                            "precio": precio,
                            "m2": metros,
                            "dormitorios": None,
                            "valor_m2": valor_m2,
                            "direccion": titulo[:50],
                            "zona": zona,
                            "fuente": "todoprop",
                            "operacion": operacion
                        })
            except:
                continue
    except Exception as e:
        logger.warning(f"[TP] Error: {e}")
    
    logger.info(f"[TP] Completado: {len(props)} propiedades")
    return props


def scrapear_giuliani(operacion="venta"):
    """Scraper para Giuliani (inmobiliaria local)"""
    import logging
    logger = logging.getLogger("motor_vpp")
    props = []
    
    urls = [
        "https://www.giuliani.com.ar/propiedades/venta/rosario",
    ]
    
    for url in urls:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                page.goto(url, timeout=30000)
                page.wait_for_timeout(3000)
                
                html = page.content()
                if "No se encontraron" in html or len(html) < 5000:
                    browser.close()
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                cards = soup.find_all("div", class_=lambda x: x and "inmueble" in str(x).lower() if x else False)
                logger.debug(f"[GIU] Encontrados {len(cards)} cards")
                
                for card in cards:
                    try:
                        precio_el = card.find(class_=lambda x: x and "precio" in str(x).lower() if x else False)
                        if not precio_el:
                            continue
                        precio = re.sub(r'[^\d]', '', precio_el.get_text())
                        if not precio:
                            continue
                        precio = float(precio)
                        
                        m2_el = card.find(class_=lambda x: x and ("metro" in str(x).lower() or "superficie" in str(x).lower()) if x else False)
                        metros = None
                        if m2_el:
                            m_match = re.search(r'(\d+)', m2_el.get_text())
                            if m_match:
                                metros = float(m_match.group(1))
                        
                        titulo_el = card.find("h2") or card.find("h3")
                        titulo = titulo_el.get_text() if titulo_el else "Sin titulo"
                        
                        if precio and metros and metros > 20:
                            valor_m2 = precio / metros
                            if 400 <= valor_m2 <= 3500:
                                zona = normalizar_zona(titulo)
                                props.append({
                                    "precio": precio,
                                    "m2": metros,
                                    "dormitorios": None,
                                    "valor_m2": valor_m2,
                                    "direccion": titulo[:50],
                                    "zona": zona,
                                    "fuente": "giuliani",
                                    "operacion": operacion
                                })
                    except:
                        continue
                
                browser.close()
                if props:
                    break
        except Exception as e:
            logger.warning(f"[GIU] Error: {e}")
            continue
    
    logger.info(f"[GIU] Completado: {len(props)} propiedades")
    return props


# --- LOGICA DE CLUSTERING ---

def filtrar_similares(propiedades, lat_obj, lon_obj, m2_obj, anclas, radio_km=1.5, antiguedad_obj=None, dormitorios_obj=None):
    # v10.0: Filtrar por dormitorios también
    filtradas = _ejecutar_filtro(propiedades, lat_obj, lon_obj, m2_obj, anclas, radio_km, antiguedad_obj, rango_edad=10, dormitorios_obj=dormitorios_obj)
    
    # Si la muestra es demasiado pobre (< 10), abrir rango de edad
    if len(filtradas) < 10 and antiguedad_obj is not None:
        filtradas = _ejecutar_filtro(propiedades, lat_obj, lon_obj, m2_obj, anclas, radio_km, antiguedad_obj, rango_edad=20, dormitorios_obj=dormitorios_obj)
        
    return filtradas

def _ejecutar_filtro(propiedades, lat_obj, lon_obj, m2_obj, anclas, radio_km, antiguedad_obj, rango_edad, dormitorios_obj=None):
    filtradas = []
    for p in propiedades:
        # Filtro m2 (rango 0.7-1.3 mas estricto)
        m2_p = p.get("m2", 0)
        if not (m2_obj * 0.7 <= m2_p <= m2_obj * 1.3): continue
        
        # Filtro dormitorios (clave - maximo 1 de diferencia)
        if dormitorios_obj is not None:
            dorm_p = p.get("dormitorios", 1)
            if abs(dorm_p - dormitorios_obj) > 1: continue
        
        # Filtro Antigüedad Adaptativo
        if antiguedad_obj is not None:
            p_ant = p.get("antiguedad")
            if p_ant is not None:
                 if abs(p_ant - antiguedad_obj) > rango_edad: continue

        # Filtro Distancia
        dist = 999
        if p.get("lat") and p.get("lon"):
            dist = calcular_distancia(lat_obj, lon_obj, p["lat"], p["lon"])
        else:
            zona = p.get("zona", "Otro")
            ancla_p = next((a for a in anclas.values() if zona.lower() in a["id"].lower()), None)
            if ancla_p:
                dist = calcular_distancia(lat_obj, lon_obj, ancla_p["lat"], ancla_p["lon"])
        
        if dist <= radio_km:
            p["distancia_estimada"] = dist
            filtradas.append(p)
    return filtradas

def calculate_iqr_cluster(propiedades, es_alquiler=False):
    """
    v10.1: Clustering robusto con filtro pre-IQR y detección de dispersión.
    Para alquiler no aplica el filtro pre-IQR (valores muy diferentes a venta).
    """
    if len(propiedades) < 3: return propiedades
    
    # DEDUPLICAR antes de clustering (v11.1)
    seen = set()
    unicas = []
    for p in propiedades:
        key = (int(p.get('precio', 0)), int(p.get('m2', 0)), p.get('zona', ''))
        if key not in seen:
            seen.add(key)
            unicas.append(p)
    
    props_dedup = unicas
    if len(props_dedup) < 3:
        return propiedades  # No hay suficientes datos
    
    vals = sorted([p["valor_m2"] for p in props_dedup])
    mediana = vals[len(vals)//2]
    
    # A) Filtro PRE-IQR robusto SOLO para VENTA
    # Alquiler usa IQR tradicional porque tiene menos datos y valores distintos
    if es_alquiler:
        # Alquiler: solo IQR simple
        q1 = vals[int(len(vals) * 0.25)]
        q3 = vals[int(len(vals) * 0.75)]
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        return [p for p in props_dedup if lower <= p["valor_m2"] <= upper]
    
    # Venta: filtro pre-IQR robusto
    lower_robust = mediana * 0.6
    upper_robust = mediana * 1.6
    cluster_robust = [p for p in props_dedup if lower_robust <= p["valor_m2"] <= upper_robust]
    
    # Si el filtro elimina demasiado, usar los valores originales
    if len(cluster_robust) >= 3:
        cluster = cluster_robust
    else:
        # Fallback: usar IQR tradicional
        q1 = vals[int(len(vals) * 0.25)]
        q3 = vals[int(len(vals) * 0.75)]
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        cluster = [p for p in props_dedup if lower <= p["valor_m2"] <= upper]
    
    return cluster


def calcular_dispersion(propiedades):
    """Detecta si el cluster tiene alta dispersión (problema estructural)"""
    if len(propiedades) < 5:
        return 0.5  # default usable
    
    vals = sorted([p["valor_m2"] for p in propiedades])
    idx_p10 = int(len(vals) * 0.10)
    idx_p90 = int(len(vals) * 0.90)
    p10 = vals[idx_p10]
    p90 = vals[idx_p90]
    mediana = vals[len(vals) // 2]
    
    if mediana <= 0:
        return 0.5
    
    dispersion = (p90 - p10) / mediana
    return dispersion

def calcular_valor_vpp(propiedades, lat_obj, lon_obj, m2_obj, zona_name, anclas, usar_ancla=True, antiguedad=None, dormitorios=None):
    # 1. Filtrar similares (v10.0 incluye dormitorios)
    similares = filtrar_similares(propiedades, lat_obj, lon_obj, m2_obj, anclas, radio_km=1.5, antiguedad_obj=antiguedad, dormitorios_obj=dormitorios)
    if not similares: similares = propiedades
    
    # 2. Clustering con limpieza de outliers
    cluster = calculate_iqr_cluster(similares, es_alquiler=(not usar_ancla))
    if not cluster:
        # Fallback: si no hay cluster, usar los datos originales (sin filtro)
        cluster = similares if similares else propiedades
    if not cluster: return 0, 0, 0, 0
    
    # Calcular mediana del cluster
    vals = sorted([p["valor_m2"] for p in cluster])
    cluster_mediana = vals[len(vals)//2]
    
    # 3. Ancla
    if usar_ancla:
        ancla_key = next((k for k,v in anclas.items() if zona_name.lower() in v["id"].lower()), None)
        ancla_val_raw = anclas[ancla_key]["usd_m2"] if ancla_key else 1500
        ancla_val = ancla_val_raw
            
        # C) Detección de dispersión
        dispersion = calcular_dispersion(similares)
        
        # D)GAP de cierre (-15% al cluster SOLO para VENTA, NO para alquiler)
        if usar_ancla:
            cluster_con_gap = cluster_mediana * 0.85
        else:
            cluster_con_gap = cluster_mediana  # Alquiler sin gap
        
        # 4. Blending Dinámico v10.1 (con dispersión)
        n = len(cluster)
        
        if dispersion > 0.7:
            # Cluster muy disperso - reducir peso
            if n >= 15:
                w_cluster = 0.5
            elif n >= 8:
                w_cluster = 0.35
            elif n >= 4:
                w_cluster = 0.2
            else:
                w_cluster = 0.0
        else:
            # ClusterOK - pesos normales
            if n >= 15:
                w_cluster = 1.0
            elif n >= 8:
                w_cluster = 0.7
            elif n >= 4:
                w_cluster = 0.4
            else:
                w_cluster = 0.0
        
        if w_cluster == 0:
            precio_final = ancla_val
        else:
            precio_final = cluster_con_gap * w_cluster + ancla_val * (1 - w_cluster)
        
        return precio_final, cluster_mediana, ancla_val, n
    else:
        # Alquiler: Mercado puro
        return cluster_mediana, cluster_mediana, 0, len(cluster)

# --- PROCESO ASINCRONICO ---

def actualizar_mercado_vpp_full():
    """Función para correr en segundo plano con progreso - Version mejorada con mas fuentes"""
    import logging
    import os
    os.environ['STRIPRINT_PROGRESS'] = '1'
    
    # Configurar logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    logger = logging.getLogger("motor_vpp")
    
    print("INICIANDO Scraping Masivo VPP (v11.0 - Multi-fuentes)...")
    
    # Backup automatico antes de scrapear
    try:
        if os.path.exists(CACHE_FILE):
            import shutil
            backup_path = CACHE_FILE + ".bak"
            shutil.copy2(CACHE_FILE, backup_path)
            logger.info(f"Backup creado: {backup_path}")
    except Exception as e:
        logger.warning(f"No se pudo crear backup: {e}")
    
    try:
        # Scraping Venta - todas las fuentes
        print("[1/7] Argenprop Venta (mono + 1-4 dorms)...")
        ventas_argen = scrapear_argenprop("venta")
        print(f"   => {len(ventas_argen)} propiedades")
        
        print("[2/7] TTL Venta...")
        ventas_ttl = scrapear_ttl("venta")
        print(f"   => {len(ventas_ttl)} propiedades")
        
        print("[3/7] La Capital Venta...")
        ventas_lacapital = scrapear_lacapital("venta")
        print(f"   => {len(ventas_lacapital)} propiedades")
        
        print("[4/7] Zonaprop Venta...")
        ventas_zp = scrapear_zonaprop()
        print(f"   => {len(ventas_zp)} propiedades")
        
        print("[5/7] TodoProps + Giuliani Venta...")
        ventas_todoprop = scrapear_todoprop("venta")
        ventas_giuliani = scrapear_giuliani("venta")
        print(f"   => {len(ventas_todoprop) + len(ventas_giuliani)} propiedades")
        
        # Omitir agencias (no implementado)
        ventas_age = []
        
        ventas = deduplicar_propiedades(ventas_argen + deduplicar_propiedades(ventas_ttl) + deduplicar_propiedades(ventas_lacapital) + ventas_zp + ventas_todoprop + ventas_giuliani + ventas_age)
        
        # Scraping Alquiler
        print("[6/7] Argenprop Alquiler...")
        alquiler_argen = scrapear_argenprop("alquiler")
        print(f"   => {len(alquiler_argen)} propiedades")
        
        print("[7/7] TTL + La Capital Alquiler...")
        alquiler_ttl = scrapear_ttl("alquiler")
        alquiler_lac = scrapear_lacapital("alquiler")
        print(f"   => {len(alquiler_ttl) + len(alquiler_lac)} propiedades")
        
        alquileres = deduplicar_propiedades(alquiler_argen + deduplicar_propiedades(alquiler_ttl) + deduplicar_propiedades(alquiler_lac))
        
        total = ventas + alquileres
        
        # Resumen por fuente
        fuentes = {}
        for p in total:
            f = p.get("fuente", "unknown")
            fuentes[f] = fuentes.get(f, 0) + 1
        
        save_cache(total, status="completado")
        print(f"Scraping FINALIZADO: {len(total)} propiedades total.")
        print(f"   - Ventas: {len(ventas)}")
        print(f"   - Alquileres: {len(alquileres)}")
        print(f"   Fuentes: {fuentes}")
        
        # ALERTA: Verificar minima cantidad de datos
        if len(total) < 50:
            logger.warning(f"ALERTA: Solo se extrajeron {len(total)} propiedades. Revisar scrapers!")
        
        return True
    except Exception as e:
        print(f"ERROR en scraping: {e}")
        import traceback
        traceback.print_exc()
        return False
        return False

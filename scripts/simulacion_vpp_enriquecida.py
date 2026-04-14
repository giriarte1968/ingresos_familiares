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
from playwright_stealth import stealth as stealth_page
from concurrent.futures import ThreadPoolExecutor

CACHE_FILE = "C:/Users/Gustavo/ingresos_familiares_st/cache_scraping.json"
CACHE_TTL_MINUTES = 30

def get_binance_usdt_ars():
    """Obtiene cotización Binance USDT->ARS vía CriptoYa"""
    try:
        r = requests.get('https://criptoya.com/api/binance/usdt/ars/1', timeout=5)
        if r.status_code == 200:
            return r.json().get('ask', 1050.0)
    except Exception as e:
        print(f"Error CryptoYa API: {e}")
    return 1050.0

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                data = json.load(f)
                fecha = datetime.fromisoformat(data.get("fecha", "2000-01-01"))
                if datetime.now() - fecha < timedelta(minutes=CACHE_TTL_MINUTES):
                    return data.get("propiedades", [])
        except:
            pass
    return None

def save_cache(propiedades):
    data = {
        "fecha": datetime.now().isoformat(),
        "propiedades": propiedades
    }
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f)

def geocode_osm(direccion):
    """Geocodifica usando Nominatim (gratuito)"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{direccion}, Rosario, Santa Fe, Argentina",
            "format": "json",
            "limit": 1,
            "accept-language": "es"
        }
        headers = {"User-Agent": "IngresosFamiliares/1.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        if resp.status_code == 200 and resp.json():
            result = resp.json()[0]
            return float(result["lat"]), float(result["lon"])
    except Exception as e:
        print(f"OSM error: {e}")
    return None, None

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0",
]

def get_random_ua():
    return random.choice(USER_AGENTS)

RADIO_KM = 1.5
AYACUCHO = {
    "nombre": "Ayacucho",
    "direccion": "Ayacucho 1518",
    "lat": -32.9545,
    "lon": -60.6455,
    "m2": 27.0,
    "m2_cubiertos": 27.0,
    "zona": "Sexta Pellegrini",
    "piso": 1,
    "estado": "muy bueno",
    "antiguedad": 15,
    "dormitorios": 1,
    "banos": 1
}

def cargar_anclas(path=None):
    if path is None:
        path = "C:/Users/Gustavo/ingresos_familiares_st/anclas_rosario.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return {a["id"]: a for a in data.get("anclas", data)}

def distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def geocodificar(direccion):
    """Convierte dirección a lat/lon usando Nominatim"""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{direccion}, Rosario, Santa Fe, Argentina",
            "format": "json",
            "limit": 1
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except:
        pass
    return None, None

def normalizar_zona(direccion):
    """Extrae zona de la dirección"""
    direccion = direccion.lower()
    zonas = {
        "pellegrini": "Pellegrini",
        "sexta": "Sexta",
        "pichincha": "Pichincha",
        "centro": "Centro",
        "martin": "Martin",
        "abasto": "Abasto",
        "facultades": "Facultades"
    }
    for key, zona in zonas.items():
        if key in direccion:
            return zona
    return "Otro"

def detectar_ancla_por_zona(zona, anclas):
    """Detecta la ancla correspondiente a una zona"""
    zona_norm = zona.lower()
    
    mapeo = {
        "pellegrini": "pellegrini_necochea",
        "sexta": "sexta_pellegrini",
        "pichincha": "pichincha_centro",
        "centro": "centro_rio",
        "martin": "rio_bv_oroño",
        "abasto": "abasto_norte",
        "facultades": "facultades_centro"
    }
    
    ancla_id = mapeo.get(zona_norm)
    if ancla_id and ancla_id in anclas:
        return anclas[ancla_id]
    
    return None

def filtrar_por_distancia(propiedades, objetivo, anclas, radio_km=1.0):
    """Filtra propiedades dentro del radio usando anclas o coordenadas directas"""
    lat_obj = objetivo["lat"]
    lon_obj = objetivo["lon"]
    
    filtradas = []
    for p in propiedades:
        ancla = detectar_ancla_por_zona(p.get("zona", ""), anclas)
        
        if ancla:
            d = distancia(lat_obj, lon_obj, ancla["lat"], ancla["lon"])
            p["distancia_km"] = round(d, 2)
            p["ancla_id"] = ancla["id"]
            
            if d <= radio_km:
                filtradas.append(p)
        elif p.get("lat") and p.get("lon"):
            d = distancia(lat_obj, lon_obj, p["lat"], p["lon"])
            p["distancia_km"] = round(d, 2)
            p["ancla_id"] = "osm"
            if d <= radio_km:
                filtradas.append(p)
        else:
            p["distancia_km"] = None
            p["ancla_id"] = None
    
    if not filtradas:
        for p in propiedades:
            ancla = detectar_ancla_por_zona(p.get("zona", ""), anclas)
            if ancla:
                p["distancia_km"] = round(distancia(lat_obj, lon_obj, ancla["lat"], ancla["lon"]), 2)
                p["ancla_id"] = ancla["id"]
                filtradas.append(p)
            else:
                p["distancia_km"] = 999
                p["ancla_id"] = "desconocida"
                filtradas.append(p)
    
    return filtradas

def scrapear_argenprop(operacion="venta"):
    propiedades = []
    headers = {"User-Agent": get_random_ua()}
    
    time.sleep(random.uniform(1, 3))
    
    urls_busqueda = []
    if operacion == "venta":
        urls_busqueda = [
            "https://www.argenprop.com/departamentos/venta/rosario/monoambiente",
            "https://www.argenprop.com/departamentos/venta/rosario/1-dormitorio",
            "https://www.argenprop.com/departamentos/venta/rosario",
        ]
    else:
        urls_busqueda = [
            "https://www.argenprop.com/departamentos/alquiler/rosario/monoambiente",
            "https://www.argenprop.com/departamentos/alquiler/rosario/1-dormitorio",
            "https://www.argenprop.com/departamentos/alquiler/rosario",
        ]
    
    for base_url in urls_busqueda:
        if len(propiedades) >= 20:
            break
        for intento in range(2):
            if propiedades:
                break
            
            for pagina in range(1, 4):
                url = base_url if pagina == 1 else f"{base_url}/pagina-{pagina}"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                break
        except:
            break
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        tarjetas = soup.find_all("div", class_="listing__item")
        if not tarjetas:
            break
        
        for t in tarjetas:
            try:
                price_tag = t.find("p", class_="card__price")
                if not price_tag:
                    continue
                precio = re.sub(r"[^\d]", "", price_tag.text)
                if not precio:
                    continue
                precio = float(precio)
                
                features = t.find("ul", class_="card__main-features")
                metros = dorms = banos = None
                if features:
                    for li in features.find_all("li"):
                        text = li.text
                        if "m²" in text:
                            m = re.sub(r"[^\d]", "", text)
                            if m:
                                metros = float(m)
                        elif "dorm" in text.lower():
                            d = re.sub(r"[^\d]", "", text)
                            if d:
                                dorms = int(d)
                        elif "baño" in text.lower():
                            b = re.sub(r"[^\d]", "", text)
                            if b:
                                banos = int(b)
                
                direccion_el = t.find("h2") or t.find("h3")
                direccion = direccion_el.text if direccion_el else ""
                
                if precio and metros and metros > 0:
                    valor_m2 = precio / metros
                    zona = normalizar_zona(direccion)
                    valido = False
                    
                    if operacion == "venta":
                        if 500 <= valor_m2 <= 3500 and precio > 10000:
                            valido = True
                    elif operacion == "alquiler":
                        if 50000 <= precio <= 800000:  # Alquileres en pesos suelen estar en este rango
                            valido = True
                            
                    if valido:
                        propiedades.append({
                            "precio": precio,
                            "m2": metros,
                            "dormitorios": dorms,
                            "banos": banos,
                            "valor_m2": valor_m2,
                            "direccion": direccion,
                            "zona": zona,
                            "lat": None,
                            "lon": None,
                            "fuente": "argenprop",
                            "operacion": operacion
                        })
            except:
                continue
    
    return propiedades

def scrapear_ttl(operacion="venta"):
    propiedades = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(user_agent=f"Mozilla/5.0 ({get_random_ua()})")
        page = context.new_page()
        # Anti-deteccion manual via headers y args del browser
        page.set_extra_http_headers({"Accept-Language": "es-AR,es;q=0.9", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"})
        
        # Filtrar por departamentos pequeños (monoambiente / 1 dorm)
        op_str = "Alquiler" if operacion == "alquiler" else "Venta"
        urls_ttl = [
            f"https://www.ttlpropiedades.com/{op_str}?tipopropiedad=departamento&ambientes=1",
            f"https://www.ttlpropiedades.com/{op_str}?tipopropiedad=departamento&ambientes=2",
            f"https://www.ttlpropiedades.com/{op_str}",
        ]
        
        for ttl_url in urls_ttl:
            page.goto(ttl_url, timeout=30000)
        
        for _ in range(2):
            page.evaluate("window.scrollBy(0, 300)")
            page.wait_for_timeout(800)
        
        page.wait_for_timeout(2000)
        
        items = page.query_selector_all("ul#propiedades > li")
        
        for item in items:
            try:
                precio_el = item.query_selector("[class*='valor']")
                if not precio_el:
                    continue
                precio_text = precio_el.inner_text()
                if operacion == "venta":
                    precio_match = re.search(r"USD([\d.,]+)", precio_text)
                else:
                    precio_match = re.search(r"\$([\d.,]+)", precio_text) # ARS
                if not precio_match:
                    continue
                precio = float(precio_match.group(1).replace(",", "").replace(".", ""))
                if operacion == "venta" and precio < 1000:
                    precio *= 1000
                
                m2_el = item.query_selector(".prop-data")
                metros = dorms = banos = None
                if m2_el:
                    m2_text = m2_el.inner_text()
                    m_match = re.search(r"([\d.,]+)\s*m", m2_text)
                    if m_match:
                        metros = float(m_match.group(1).replace(",", "."))
                    d_match = re.search(r"(\d+)\s*dorm", m2_text, re.I)
                    if d_match:
                        dorms = int(d_match.group(1))
                    b_match = re.search(r"(\d+)\s*baño", m2_text, re.I)
                    if b_match:
                        banos = int(b_match.group(1))
                
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
                        propiedades.append({
                            "precio": precio,
                            "m2": metros,
                            "dormitorios": dorms,
                            "banos": banos,
                            "valor_m2": valor_m2,
                            "direccion": direccion,
                            "zona": zona,
                            "lat": None,
                            "lon": None,
                            "fuente": "ttl",
                            "operacion": operacion
                        })
            except:
                continue
        
        browser.close()
    
    return propiedades

def scrapear_lacapital(operacion="venta"):
    propiedades = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(user_agent=f"Mozilla/5.0 ({get_random_ua()})")
        page = context.new_page()
        
        url = f"https://inmuebles.lacapital.com.ar/buscar-propiedades/?inmueble_hidden=Departamento&localidad=487&operacion_hidden={operacion.capitalize()}"
        page.goto(url, timeout=30000)
        
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        
        for _ in range(2):
            page.evaluate("window.scrollBy(0, 400)")
            page.wait_for_timeout(1000)
        
        page.wait_for_timeout(3000)
        
        items = page.query_selector_all(".avisodestacado")
        
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
                
                b_match = re.search(r"(\d+)\s*baño", texto, re.I)
                banos = int(b_match.group(1)) if b_match else None
                
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
                        propiedades.append({
                            "operacion": operacion,
                            "precio": precio,
                            "m2": metros,
                            "dormitorios": dorms,
                            "banos": banos,
                            "valor_m2": valor_m2,
                            "direccion": direccion,
                            "zona": zona,
                            "lat": None,
                            "lon": None,
                            "fuente": "lacapital"
                        })
            except:
                continue
        
        browser.close()
    
    return propiedades

def scrapear_zonaprop():
    propiedades = []
    
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
            "Accept-Language": "es-AR,es;q=0.9",
        }
        
        response = requests.get(api_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get("results", [])[:30]:
                precio = item.get("price", {}).get("amount", 0)
                metros = item.get("superficie", {}).get("total", 0)
                dorms = item.get("ambientes", {}).get("dormitorios")
                titulo = item.get("title", "Sin titulo")
                
                if precio and metros and metros > 0:
                    valor_m2 = precio / metros
                    if 400 <= valor_m2 <= 3500:
                        zona = normalizar_zona(titulo)
                        propiedades.append({
                            "precio": precio,
                            "m2": metros,
                            "dormitorios": dorms,
                            "banos": None,
                            "valor_m2": valor_m2,
                            "direccion": titulo[:50],
                            "zona": zona,
                            "lat": None,
                            "lon": None,
                            "fuente": "zonaprop"
                        })
            
            if propiedades:
                return propiedades
                
    except:
        pass
    
    urls = [
        "https://www.zonaprop.com.ar/departamentos-venta-en-rosario-santa-fe.html",
    ]
    
    cards = []
    html_content = ""
    
    for url_intento, url in enumerate(urls):
        try:
            with sync_playwright() as p:
                browser = p.firefox.launch(
                    headless=True,
                )
                page = browser.new_page()
                
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(15000)
                
                for _ in range(4):
                    page.evaluate("window.scrollBy(0, 300)")
                    page.wait_for_timeout(600)
                
                html_content = page.content()
                
                if "Just a moment" in html_content[:500]:
                    browser.close()
                    continue
                
                soup = BeautifulSoup(html_content, 'html.parser')
                cards = soup.find_all("div", {"data-posting-type": "PROPERTY"})
                
                if cards:
                    break
                    
        except:
            continue
    
    if not cards:
        return []
        
        for card in cards:
            try:
                posting_type = card.get("data-posting-type")
                if posting_type != "PROPERTY":
                    continue
                
                precio = None
                metros = None
                dorms = banos = None
                titulo = ""
                
                precio_el = card.find("p", attrs={"data-qa": "POSTING_CARD_PRICE"})
                if precio_el:
                    precio_text = precio_el.get_text()
                    precio_match = re.search(r'USD\s*([\d.,]+)', precio_text.replace(".", "").replace(",", ""))
                    if precio_match:
                        precio = float(precio_match.group(1).replace(",", "."))
                
                area_el = card.find("ul", attrs={"data-qa": "POSTING_CARD_FEATURES"})
                if area_el:
                    area_text = area_el.get_text()
                    m_match = re.search(r'(\d+)\s*m', area_text)
                    if m_match:
                        metros = float(m_match.group(1))
                    d_match = re.search(r'(\d+)\s*dorm', area_text, re.I)
                    if d_match:
                        dorms = int(d_match.group(1))
                    b_match = re.search(r'(\d+)\s*baño', area_text, re.I)
                    if b_match:
                        banos = int(b_match.group(1))
                
                titulo_el = card.find("h2") or card.find("h3")
                if titulo_el:
                    titulo = titulo_el.get_text()
                
                if not titulo:
                    titulo = "Sin titulo"
                
                if precio and metros and metros > 0:
                    valor_m2 = precio / metros
                    if 400 <= valor_m2 <= 3500:
                        zona = normalizar_zona(titulo)
                        propiedades.append({
                            "precio": precio,
                            "m2": metros,
                            "dormitorios": dorms,
                            "banos": banos,
                            "valor_m2": valor_m2,
                            "direccion": titulo[:50],
                            "zona": zona,
                            "lat": None,
                            "lon": None,
                            "fuente": "zonaprop"
                        })
            except:
                continue
        
        browser.close()
    
    return propiedades

def scrapear_todoprops():
    """Scraper para TodoProps (otro portal inmobiliario)"""
    propiedades = []
    
    url = "https://www.todoprop.com.ar/inmuebles/rosario/venta/departamentos"
    headers = {"User-Agent": get_random_ua()}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        cards = soup.find_all("div", class_="inmueble-item")
        
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
                        propiedades.append({
                            "precio": precio,
                            "m2": metros,
                            "dormitorios": None,
                            "banos": None,
                            "valor_m2": valor_m2,
                            "direccion": titulo[:50],
                            "zona": zona,
                            "lat": None,
                            "lon": None,
                            "fuente": "todoprop"
                        })
            except:
                continue
                
    except:
        pass
    
    return propiedades

def scrapear_giuliani():
    """Scraper para Giuliani (inmobiliaria local) con Playwright"""
    propiedades = []
    
    urls = [
        "https://www.giuliani.com.ar/propiedades/venta/rosario",
        "https://www.giuliani.com.ar/venta/departamentos-rosario",
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
                        
                        titulo_el = card.find("h2") or card.find("h3") or card.find(class_=lambda x: x and "titulo" in str(x).lower() if x else False)
                        titulo = titulo_el.get_text() if titulo_el else "Sin titulo"
                        
                        if precio and metros and metros > 20:
                            valor_m2 = precio / metros
                            if 400 <= valor_m2 <= 3500:
                                zona = normalizar_zona(titulo)
                                propiedades.append({
                                    "precio": precio,
                                    "m2": metros,
                                    "dormitorios": None,
                                    "banos": None,
                                    "valor_m2": valor_m2,
                                    "direccion": titulo[:50],
                                    "zona": zona,
                                    "lat": None,
                                    "lon": None,
                                    "fuente": "giuliani"
                                })
                    except:
                        continue
                
                browser.close()
                if propiedades:
                    break
                    
        except:
            continue
    
    return propiedades

def scrapear_sabatini():
    """Scraper para Sabatini Propiedades con Playwright"""
    propiedades = []
    
    url = "https://www.sabatiniprop.com.ar/buscar/?operacion=venta&tipo=departamento"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)
            
            html = page.content()
            if "No se encontraron" in html or len(html) < 5000:
                browser.close()
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            cards = soup.find_all("div", class_=lambda x: x and "inmueble" in str(x).lower() if x else False)
            
            for card in cards:
                try:
                    precio_el = card.find(class_=lambda x: x and "precio" in str(x).lower() if x else False)
                    if not precio_el:
                        continue
                    precio = re.sub(r'[^\d]', '', precio_el.get_text())
                    if not precio:
                        continue
                    precio = float(precio)
                    
                    m2_el = card.find(class_=lambda x: x and "metro" in str(x).lower() if x else False)
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
                            propiedades.append({
                                "precio": precio,
                                "m2": metros,
                                "dormitorios": None,
                                "banos": None,
                                "valor_m2": valor_m2,
                                "direccion": titulo[:50],
                                "zona": zona,
                                "lat": None,
                                "lon": None,
                                "fuente": "sabatini"
                            })
                except:
                    continue
            
            browser.close()
    except:
        pass
    
    return propiedades

def scrapear_cassina():
    """Scraper para Cassina Inmobiliaria con Playwright"""
    propiedades = []
    
    url = "https://www.cassina.com.ar/buscar/venta/departamentos"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)
            
            html = page.content()
            if "No se encontraron" in html or len(html) < 5000:
                browser.close()
                return []
            
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.find_all("div", class_=lambda x: x and "inmueble" in str(x).lower() if x else False)
            
            for item in items:
                try:
                    precio_el = item.find(class_=lambda x: x and "precio" in str(x).lower() if x else False)
                    if not precio_el:
                        continue
                    precio = re.sub(r'[^\d]', '', precio_el.get_text())
                    if not precio:
                        continue
                    precio = float(precio)
                    
                    m2_el = item.find(class_=lambda x: x and "metro" in str(x).lower() if x else False)
                    metros = None
                    if m2_el:
                        m_match = re.search(r'(\d+)', m2_el.get_text())
                        if m_match:
                            metros = float(m_match.group(1))
                    
                    titulo_el = item.find("h2") or item.find("h3")
                    titulo = titulo_el.get_text() if titulo_el else "Sin titulo"
                    
                    if precio and metros and metros > 20:
                        valor_m2 = precio / metros
                        if 400 <= valor_m2 <= 3500:
                            zona = normalizar_zona(titulo)
                            propiedades.append({
                                "precio": precio,
                                "m2": metros,
                                "dormitorios": None,
                                "banos": None,
                                "valor_m2": valor_m2,
                                "direccion": titulo[:50],
                                "zona": zona,
                                "lat": None,
                                "lon": None,
                                "fuente": "cassina"
                            })
                except:
                    continue
            
            browser.close()
    except:
        pass
    
    return propiedades

def extract_single_agency(args):
    nombre, url, operacion = args
    props_locales = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            context = browser.new_context(
                user_agent=get_random_ua(),
                viewport={'width': random.randint(1200, 1920), 'height': random.randint(800, 1080)}
            )
            page = context.new_page()
            # Anti-deteccion manual - stealth no funciona en threads
            page.set_extra_http_headers({"Accept-Language": "es-AR,es;q=0.9", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
            
            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                
                # Evadir detección inicial
                page.wait_for_timeout(random.uniform(4000, 6000))
                
                # Desplazarse erráticamente
                for _ in range(random.randint(2, 4)):
                    scroll_offset = random.randint(300, 800)
                    page.evaluate(f"window.scrollBy(0, {scroll_offset})")
                    page.wait_for_timeout(random.uniform(800, 2000))
                
                html = page.content()
            except Exception as e:
                browser.close()
                return props_locales
            
            # Anti-bot detection simple
            if len(html) < 2000 or "Just a moment" in html or "Cloudflare" in html[:300]:
                browser.close()
                return props_locales
            
            soup = BeautifulSoup(html, 'html.parser')
            
            cards = soup.find_all("div", class_=lambda x: x and any(y in str(x).lower() for y in ["inmueble", "property", "card", "item", "listado", "aviso"]) if x else False)
            if not cards:
                cards = soup.find_all("article")
            if not cards:
                cards = soup.find_all("li", class_=lambda x: x and "item" in str(x).lower() if x else False)
            
            count = 0
            for card in cards[:20]:
                try:
                    texto = card.get_text(separator=' ')
                    m_match = re.search(r'(\d+)\s*m[²2]?', texto)
                    if not m_match:
                        continue
                    metros = float(m_match.group(1))
                    
                    if metros < 20 or metros > 300:
                        continue
                    
                    valido = False
                    if operacion == "venta":
                        precio_match = re.search(r'USD\s*([\d.,]+)|U?\$S?\s*([\d.,]+)', texto.replace(".", "").replace(",", ""))
                        if precio_match:
                            precio = float((precio_match.group(1) or precio_match.group(2) or "").replace(",", ""))
                            valor_m2 = precio / metros
                            if 400 <= valor_m2 <= 4000 and 10000 <= precio <= 1000000:
                                valido = True
                    else:
                        precio_match = re.search(r'\$\s*([\d.,]+)|ARS\s*([\d.,]+)', texto.replace(".", "").replace(",", ""))
                        if precio_match:
                            precio = float((precio_match.group(1) or precio_match.group(2) or "").replace(",", ""))
                            if 50000 <= precio <= 800000:
                                valor_m2 = precio / metros
                                valido = True
                                
                    if not valido:
                        continue
                    
                    zona = normalizar_zona(texto)
                    cln_text = re.sub(r'[\r\n\t]', ' ', texto)
                    
                    props_locales.append({
                        "operacion": operacion,
                        "precio": precio,
                        "m2": metros,
                        "dormitorios": None,
                        "banos": None,
                        "valor_m2": valor_m2,
                        "direccion": f"{nombre}: {cln_text[:40].strip()}",
                        "zona": zona,
                        "lat": None,
                        "lon": None,
                        "fuente": nombre
                    })
                    count += 1
                except:
                    continue
                    
            browser.close()
            if count > 0:
                print(f"    {nombre}: Obtenidas {count} props")
    except Exception as e:
        print(f"    {nombre}: ERROR - {str(e)[:50]}")
        pass
        
    return props_locales

def scrapear_valerio_dedicado():
    """Scraper dedicado para Rubén Valerio - la que más rinde - con filtro 1 dorm"""
    propiedades = []
    urls = [
        "https://www.rubenvalerio.com.ar/buscar/operacion-venta-tipo-departamento-ambientes-1-id_ciudad-rosario",
        "https://www.rubenvalerio.com.ar/buscar/operacion-venta-tipo-departamento-id_ciudad-rosario",
    ]
    
    for url in urls:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
                context = browser.new_context(user_agent=get_random_ua())
                page = context.new_page()
                page.set_extra_http_headers({"Accept-Language": "es-AR,es;q=0.9"})
                page.goto(url, timeout=25000, wait_until="domcontentloaded")
                page.wait_for_timeout(4000)
                for _ in range(3):
                    page.evaluate("window.scrollBy(0, 500)")
                    page.wait_for_timeout(800)
                html = page.content()
                browser.close()
                
                soup = BeautifulSoup(html, 'html.parser')
                # Selectores específicos de Valerio
                cards = (soup.find_all("div", class_=lambda x: x and any(k in str(x).lower() for k in ["prop","inmueble","listing","card","item","aviso"]) if x else False)
                         or soup.find_all("article"))
                
                count = 0
                for card in cards[:25]:
                    try:
                        texto = card.get_text(separator=" ")
                        m_match = re.search(r'(\d+)\s*m[²2s]', texto, re.I)
                        if not m_match: continue
                        metros = float(m_match.group(1))
                        if not (15 <= metros <= 50): continue  # Solo pequeños
                        
                        precio_match = re.search(r'USD\s*([\d.,]+)|U\$S\s*([\d.,]+)|\$\s*([\d.,]+)', texto)
                        if not precio_match: continue
                        raw = precio_match.group(1) or precio_match.group(2) or precio_match.group(3) or ""
                        precio = float(raw.replace(".","").replace(",",""))
                        if precio < 10000 or precio > 500000: continue
                        
                        valor_m2 = precio / metros
                        if not (400 <= valor_m2 <= 4000): continue
                        
                        cln = re.sub(r'[\r\n\t]+', ' ', texto)
                        propiedades.append({
                            "precio": precio, "m2": metros, "dormitorios": 1,
                            "banos": None, "valor_m2": valor_m2,
                            "direccion": f"valerio: {cln[:40].strip()}",
                            "zona": normalizar_zona(cln),
                            "lat": None, "lon": None, "fuente": "valerio"
                        })
                        count += 1
                    except: continue
                
                if count > 0:
                    print(f"    valerio_dedicado: {count} props (1 dorm, <= 50m2)")
                    break
        except Exception as e:
            print(f"    valerio_dedicado ERROR: {str(e)[:60]}")
    
    return propiedades

def scrapear_top20_inmobiliarias(operacion="venta"):
    """Scraper para las top 20 inmobiliarias"""
    propiedades = []
    
    # URLs apuntando a búsquedas de departamentos pequeños donde est posible
    inmobiliarias = [
        ("vanzini",          "https://vanzini.com.ar/buscar/?tipo=departamento&operacion=venta"),
        ("bassini",          "https://www.bassiniinmobiliaria.com/resultados/?operacion=venta&tipo=departamento"),
        ("guillermo_rod",    "https://guillermorodriguez.com.ar/propiedades/venta/departamento"),
        ("ducler",           "https://www.ducler.com.ar/propiedades/venta/departamento"),
        ("giaganti",         "https://giaganti.com.ar/propiedades/venta/departamentos"),
        ("dunod",            "https://www.dunod.com.ar/propiedades?operacion=venta&tipo=departamento"),
        ("ferreyra",         "https://diegoferreyra.com.ar/propiedades/departamentos/venta"),
        ("telleria",         "https://www.telleriainmuebles.com.ar/buscar/?operacion=venta&tipo=departamento"),
        ("uno",              "https://uno-propiedades.com.ar/filtros?operacion=Venta&tipo=Departamento&localidad=Rosario"),
        ("pereyra",          "https://norapereyra.com.ar/propiedades/venta/departamento"),
        ("berbari",          "https://berbariprop.com.ar/search-results/?type=departamento&status=venta&location=rosario"),
        ("fransa",           "https://fransapropiedades.com.ar/listado/?operacion=venta&tipo=departamento"),
        ("imperia",          "https://imperiapropiedades.com/propiedades/venta/departamentos"),
        ("escala",           "https://escalapropiedades.com.ar/propiedades/venta/departamento"),
        ("crestale",         "https://crestalepropiedades.com.ar/departamentos/venta"),
        ("bled",             "https://bledpropiedades.com.ar/propiedades/venta/departamentos"),
        ("acc",              "https://www.accpropiedades.com.ar/properties?operacion=venta&tipo=departamento"),
        ("acec",             "https://www.acecpropiedades.com/buscar/?operacion=venta&tipo=departamento"),
        ("torrepotosi",      "http://www.torrepotosi.com.ar/"),
        ("duolegal",         "https://www.duolegal.com.ar/propiedades/venta/departamento"),
        ("farina",           "https://farinainmobiliaria.com.ar/propiedades/venta/departamentos"),
        ("domum",            "https://www.domumpropiedades.com.ar/Venta"),
        ("deluxe",           "https://www.deluxepropiedades.com.ar/propiedades/venta/departamento"),
        ("fw",               "https://fwpropiedades.com.ar/web2/"),
        ("fidentia",         "https://www.fidentia.com.ar/propiedades/venta/departamentos"),
        ("bottai",           "https://www.bottai.com.ar/propiedades/venta/departamento"),
        ("brettmarta",       "https://www.martabrett.com.ar/site/properties/sale"),
    ]
    
    inmobiliarias = [(n, u.replace("venta", operacion).replace("Venta", operacion.capitalize()), operacion) for n, u in inmobiliarias]
    with ThreadPoolExecutor(max_workers=3) as executor:
        resultados = list(executor.map(extract_single_agency, inmobiliarias))
    
    for res in resultados:
        propiedades.extend(res)
    
    print(f"    Top20 total obtenido: {len(propiedades)} props")
    return propiedades

def filtrar_similares(propiedades, objetivo, tolerancia_m2=0.40):
    """Filtra propiedades similares al objetivo y aplica coeficientes de normalización"""
    m2_obj = objetivo["m2"]
    m2_min = m2_obj * (1 - tolerancia_m2)
    m2_max = m2_obj * (1 + tolerancia_m2)
    dorms_obj = objetivo.get("dormitorios", 1)
    antiguedad_obj = objetivo.get("antiguedad", 15)
    
    filtradas = []
    for p in propiedades:
        if not (m2_min <= p["m2"] <= m2_max):
            continue
            
        p_dorm = p.get("dormitorios")
        texto_busqueda = p.get("direccion", "").lower() + " " + p.get("descripcion", "").lower()
        if p_dorm is None:
            if "monoambiente" in texto_busqueda or "ambiente unico" in texto_busqueda:
                p_dorm = 0
            else:
                p_dorm = 1 # Por defecto 1 dorm para tamaño pequeño
        p["dormitorios"] = p_dorm
        
        ajuste_tipologia = 1.0
        if dorms_obj == 1 and p_dorm == 0:
            ajuste_tipologia = 1.15  # Monoambiente -> sumar 15% para igualarlo a 1 Dorm
        elif dorms_obj == 0 and p_dorm == 1:
            ajuste_tipologia = 0.85  # 1 Dorm -> restar 15% para igualarlo a Monoambiente
        
        p["ajuste_tipologia"] = ajuste_tipologia
        
        # Ajuste de Antigüedad
        p_antig = p.get("antiguedad")
        if p_antig is None:
            if "a estrenar" in texto_busqueda or "pozo" in texto_busqueda or "nuevo" in texto_busqueda:
                p_antig = 0
            elif "excelente" in texto_busqueda:
                p_antig = 5
            elif "reciclar" in texto_busqueda:
                p_antig = 40
            else:
                p_antig = 15 # Usado estándar
        p["antiguedad"] = p_antig
        
        # Depreciación lineal simple: 1% por año de diferencia
        diff_anios = p_antig - antiguedad_obj
        ajuste_antiguedad = 1.0 + (diff_anios * 0.01)
        if ajuste_antiguedad > 1.30: ajuste_antiguedad = 1.30
        if ajuste_antiguedad < 0.70: ajuste_antiguedad = 0.70
        p["ajuste_antiguedad"] = ajuste_antiguedad
        
        if "valor_m2_original" not in p:
            p["valor_m2_original"] = p["valor_m2"]
            
        p["valor_m2"] = p["valor_m2_original"] * ajuste_tipologia * ajuste_antiguedad
        
        filtradas.append(p)
    
    return filtradas

def geocodificar_lote(propiedades, limite=10):
    """Geocodifica las primeras N propiedades"""
    geocodificadas = 0
    for p in propiedades[:limite]:
        if p.get("lat") is None:
            lat, lon = geocodificar(p["direccion"])
            if lat:
                p["lat"] = lat
                p["lon"] = lon
                geocodificadas += 1
                time.sleep(1.1)
    return geocodificadas

import math

def obtener_percentil(data, p):
    data_sorted = sorted(data)
    i = (len(data_sorted) - 1) * p / 100.0
    f = int(i)
    c = math.ceil(i)
    if f == c: return data_sorted[f]
    return data_sorted[f] * (c - i) + data_sorted[c] * (i - f)

def filtrar_cluster_m2(propiedades):
    if not propiedades: return []
    valores_m2 = [p["valor_m2"] for p in propiedades]
    n = len(valores_m2)
    
    if n >= 25:
        p_low, p_high = 25, 75
    elif n >= 10:
        p_low, p_high = 20, 80
    elif n >= 4:
        p_low, p_high = 15, 85
    else:
        return propiedades # Too few to mathematically cluster safely
        
    val_low = obtener_percentil(valores_m2, p_low)
    val_high = obtener_percentil(valores_m2, p_high)
    
    return [p for p in propiedades if val_low <= p["valor_m2"] <= val_high]

def calcular_precio_blended_idw(propiedades, lat_obj, lon_obj):
    if not propiedades: return 0
    tiene_coords = any(p.get("lat") for p in propiedades)
    if tiene_coords:
        valores, pesos = [], []
        for p in propiedades:
            if p.get("lat"):
                d = distancia(lat_obj, lon_obj, p["lat"], p["lon"])
                peso = 1 / (d**2 + 0.1) if d > 0 else 10
                valores.append(p["valor_m2"] * peso)
                pesos.append(peso)
        return sum(valores) / sum(pesos) if valores else 0
    return sum(p["valor_m2"] for p in propiedades) / len(propiedades)

def calcular_precio_blended(propiedades, lat_obj, lon_obj, zona_ancla_usd=None):
    """Modelo Analítico con Cluster de Precio y Ponderación Estructural de Ancla"""
    if not propiedades:
        return 0, 0, 0, 0, 0, []
        
    cluster_puro = filtrar_cluster_m2(propiedades)
    precio_cluster = calcular_precio_blended_idw(cluster_puro, lat_obj, lon_obj)
    
    n = len(propiedades)
    
    # Si tenemos Ancla para Venta (USD), aplicamos modelo híbrido
    if zona_ancla_usd:
        if n >= 20:   # Alta confiabilidad local
            peso_cluster = 0.50
            peso_ancla = 0.50
        elif n >= 10: # Media
            peso_cluster = 0.30
            peso_ancla = 0.70
        else:         # Baja (domina el ancla estructural)
            peso_cluster = 0.10
            peso_ancla = 0.90
            
        precio_final = (precio_cluster * peso_cluster) + (zona_ancla_usd * peso_ancla)
    else:
        # Modo Alquileres o sin Ancla: 100% Cluster
        peso_cluster = 1.0
        peso_ancla = 0.0
        precio_final = precio_cluster
        zona_ancla_usd = 0
        
    return precio_final, precio_cluster, zona_ancla_usd, peso_cluster, peso_ancla, cluster_puro

def main():
    print("="*70)
    print("SIMULACIÓN VPP ENRIQUECIDA - AYACUCHO")
    print("="*70)
    
    print(f"\n[OBJETIVO] PROPIEDAD:")
    print(f"   Dirección: {AYACUCHO['direccion']}")
    print(f"   Coordenadas: {AYACUCHO['lat']}, {AYACUCHO['lon']}")
    print(f"   Superficie: {AYACUCHO['m2']} m2")
    print(f"   Dormitorios: {AYACUCHO['dormitorios']}")
    print(f"   Baños: {AYACUCHO['banos']}")
    print(f"   Zona: {AYACUCHO['zona']}")
    print(f"   Estado: {AYACUCHO['estado']} (Antigüedad estimada: {AYACUCHO['antiguedad']} años)")
    
    print("\n" + "-"*70)
    print("SCRAPING DE PORTALES...")
    print("-"*70)
    
    cached = load_cache()
    if cached:
        todas = cached
        print(f"    [CACHE] {len(todas)} propiedades")
    else:
        print("\n[1] Argenprop...")
        try:
            argenprop = scrapear_argenprop("venta") + scrapear_argenprop("alquiler")
            print(f"    + {len(argenprop)} propiedades")
        except Exception as e:
            argenprop = []
        
        print("\n[2] TTL Propiedades...")
        try:
            ttl = scrapear_ttl("venta") + scrapear_ttl("alquiler")
            print(f"    -> {len(ttl)} propiedades")
        except:
            ttl = []
            
        print("\n[3] La Capital...")
        try:
            lacapital = scrapear_lacapital("venta") + scrapear_lacapital("alquiler")
            print(f"    -> {len(lacapital)} propiedades")
        except:
            lacapital = []
            
        todoprop = []
        valerio = []
        
        print("\n[6] Top Inmobiliarias...")
        try:
            top20 = scrapear_top20_inmobiliarias("venta") + scrapear_top20_inmobiliarias("alquiler")
            print(f"    -> {len(top20)} propiedades")
        except:
            top20 = []
        
        print("\n[7] Zonaprop...")
        try:
            zonaprop = scrapear_zonaprop()
            print(f"    -> {len(zonaprop)} propiedades")
        except:
            zonaprop = []
        
        todas = argenprop + ttl + lacapital + todoprop + valerio + top20 + zonaprop
        print(f"\n    [MERGE] argenprop:{len(argenprop)} ttl:{len(ttl)} lacapital:{len(lacapital)} todo:{len(todoprop)} valerio:{len(valerio)} top20:{len(top20)} zonaprop:{len(zonaprop)} = {len(todas)} total")
        
        if todas:
            save_cache(todas)
            print(f"    [CACHE GUARDADO] {len(todas)} propiedades")
            
    # Split fuera del bloque if/else
    ventas = [p for p in todas if p.get('operacion') == 'venta' or p.get('operacion') is None]
    alquileres = [p for p in todas if p.get('operacion') == 'alquiler']
    
    print(f"\n[TOTAL] TOTAL: {len(todas)} propiedades scraped (Ventas: {len(ventas)}, Alquileres: {len(alquileres)})")

    print("\n" + "-"*70)
    print("GEOCODIFICANDO (OSM)...")
    print("-"*70)
    
    geocodificadas = 0
    for p in todas[:15]:
        if p.get("lat") is None and p.get("direccion"):
            lat, lon = geocode_osm(p["direccion"])
            if lat:
                p["lat"] = lat
                p["lon"] = lon
                geocodificadas += 1
                time.sleep(1.1)
    
    print(f"   -> {geocodificadas} propiedades geocodificadas")

    print("\n" + "-"*70)
    print("CARGANDO ANCLAS...")
    print("-"*70)
    anclas = cargar_anclas()
    print(f"   -> {len(anclas)} anclas cargadas")

    print("\n" + "-"*70)
    print("FILTRO POR DISTANCIA")
    print("-"*70)
    
    por_zona = filtrar_por_distancia(ventas, AYACUCHO, anclas, RADIO_KM)
    print(f"   Dentro de {RADIO_KM}km: {len(por_zona)} propiedades")
    
    if por_zona:
        print(f"\n   Propiedades dentro del radio (sin filtrar):")
        for i, p in enumerate(por_zona[:5]):
            dorm = p.get("dormitorios") or "?"
            dist = p.get("distancia_km") or "?"
            ancla = p.get("ancla_id", "")
            print(f"   {i+1:2}. {p['direccion'][:30]:30} | {p['m2']:5.0f}m2 | {dorm}d | {dist}km | ${p['valor_m2']:.0f}/m2 | {ancla}")
    
    # Aplicar el filtro real (0.55 cubre hasta 41m2 partiendo de 27m2)
    similares_zona = filtrar_similares(por_zona, AYACUCHO, tolerancia_m2=0.55)
    print(f"\n   -> Filtradas por similitud (m2/dorm) en la zona: {len(similares_zona)} propiedades")
    
    if similares_zona:
        similares = similares_zona
    else:
        print("   ⚠️ No hay similares en la zona. Usando similares de toda la ciudad...")
        similares = filtrar_similares(ventas, AYACUCHO, tolerancia_m2=0.55)
        print(f"   -> Filtradas por similitud en toda la ciudad: {len(similares)} propiedades")
        if not similares:
            print("   ⚠️ Fallo total de filtros. Usando todo en la zona como fallback.")
            similares = por_zona

    if similares:
        print(f"\n   Comparables EXACTOS a usar para VPP (valores normalizados a 1Dorm/{AYACUCHO['antiguedad']}Años):")
        for i, p in enumerate(similares[:10]):
            dorm = p.get("dormitorios")
            dorm_str = "Mono" if dorm == 0 else "1D"
            dist = p.get("distancia_km", "?")
            ancla = p.get("ancla_id", "")
            antig = p.get("antiguedad", 15)
            precio_norm = p['valor_m2']
            precio_orig = p.get('valor_m2_original', precio_norm)
            print(f"   {i+1:2}. {p['direccion'][:29]:29} | {p['m2']:4.0f}m2 | {dorm_str} | Ant:{antig:2}a | {dist}km | ${precio_norm:.0f}/m2 (orig:${precio_orig:.0f}) | {ancla}")
    
    print("\n" + "-"*70)
    print("CALCULO VPP")
    print("-"*70)
    
    anclas_dict = {a["id"]: a for a in anclas.values()}
    # Intentamos encontrar el USD Ancla para la zona de Ayacucho (ej. "sexta_pellegrini")
    ancla_obj = detectar_ancla_por_zona(AYACUCHO["zona"], anclas)
    ancla_usd = ancla_obj["usd_m2"] if ancla_obj and "usd_m2" in ancla_obj else 1500
    
    precio_m2, pr_cluster, pr_ancla, w_cluster, w_ancla, cluster_v = calcular_precio_blended(similares, AYACUCHO["lat"], AYACUCHO["lon"], ancla_usd)
    print(f"\n   [MODELO DUAL] ANALÍTICA DE PRECIO BASE:")
    print(f"      Señal Local (Cluster de {len(cluster_v)} props IQR): ${pr_cluster:.0f}/m2 (Peso: {w_cluster*100:.0f}%)")
    print(f"      Control Estructural (Ancla {ancla_obj['id'] if ancla_obj else 'Default'}): ${pr_ancla:.0f}/m2 (Peso: {w_ancla*100:.0f}%)")
    print(f"   => PRECIO BASE/m2 SINTETIZADO: ${precio_m2:.0f}")
    
    valor_base = AYACUCHO["m2"] * precio_m2
    
    estado_map = {
        "a_estrenar": 1.20,
        "excelente": 1.15,
        "muy bueno": 1.10,
        "muy_bueno": 1.10,
        "muy_bueno": 1.10,
        "bueno": 1.00,
        "regular": 0.85
    }
    factor_estado = estado_map.get(AYACUCHO["estado"], 1.0)
    
    factor_piso = 0.90 if AYACUCHO["piso"] == 0 else (1.0 if AYACUCHO["piso"] <= 3 else 1.05)
    
    valor_ajustado = valor_base * factor_estado * factor_piso
    
    descuento_liquidez = 0.08
    valor_realizable = valor_ajustado * (1 - descuento_liquidez)
    
    print(f"\n   [CALC] CÁLCULOS:")
    print(f"      m2: {AYACUCHO['m2']}")
    print(f"      Precio/m2: ${precio_m2:.0f}")
    print(f"      Valor base: ${valor_base:,.0f}")
    print(f"      Ajuste estado ({AYACUCHO['estado']}): x{factor_estado}")
    print(f"      Ajuste piso: x{factor_piso}")
    print(f"      Valor ajustado: ${valor_ajustado:,.0f}")
    print(f"      Descuento liquidez: -{descuento_liquidez*100:.0f}%")
    print(f"\n   [RESULTADO] VALOR REALIZABLE: ${valor_realizable:,.0f}")
    print("-"*70)
    print("CÁLCULO ALQUILER (ARS) & RENTABILIDAD")
    print("-"*70)
    
    por_zona_alq = filtrar_por_distancia(alquileres, AYACUCHO, anclas, RADIO_KM)
    similares_alq = filtrar_similares(por_zona_alq, AYACUCHO, tolerancia_m2=0.55)
    
    if not similares_alq:
        similares_alq = filtrar_similares(alquileres, AYACUCHO, tolerancia_m2=0.55)
    
    if similares_alq:
        print(f"   Comparables Alquiler EXACTOS (normalizados a 1Dorm/{AYACUCHO['antiguedad']}Años):")
        for i, p in enumerate(similares_alq[:5]):
            dorm_str = "Mono" if p.get("dormitorios") == 0 else "1D"
            print(f"   {i+1:2}. {p['direccion'][:29]:29} | {p['m2']:4.0f}m2 | {dorm_str} | ${p['precio']:,.0f} ARS")
            
        # Calcular Cluster Puro de Alquileres (Sin Ancla)
        precio_alq_m2, pr_c_alq, _, _, _, cl_alq = calcular_precio_blended(similares_alq, AYACUCHO["lat"], AYACUCHO["lon"], None)
        
        usdt_ars = get_binance_usdt_ars()
        
        renta_cluster_mensual_ars = AYACUCHO["m2"] * pr_c_alq
        alquiler_mensual_estimado = renta_cluster_mensual_ars
        
        ingreso_anual_ars = alquiler_mensual_estimado * 12
        usdt_ars = get_binance_usdt_ars()
        ingreso_anual_usd = ingreso_anual_ars / usdt_ars
        
        print(f"\n   [MODELO MERCADO] ANALÍTICA DE ALQUILER (Dólar: {usdt_ars:,.1f}):")
        print(f"      Señal Local Alquiler (Cluster {len(cl_alq)} props IQR): ${renta_cluster_mensual_ars:,.0f} ARS (Peso: 100%)")
        
        roi_bruto = (ingreso_anual_usd / valor_realizable) * 100
        
        print(f"\n   [ALQUILER] Estimado Mensual: ${alquiler_mensual_estimado:,.0f} ARS")
        print(f"   [ROI] Dólar Crypto Binance: ${usdt_ars:.2f} ARS/USD")
        print(f"   [ROI] Renta Anual Estimada: ${ingreso_anual_usd:,.0f} USD")
        print(f"   [ROI] Cap Rate Bruto: {roi_bruto:.2f}% Anual")
    else:
        print("   ⚠️ No se encontraron comparables de alquiler en la zona y rango m2 especificado.")
        
    print("="*70)

if __name__ == "__main__":
    main()
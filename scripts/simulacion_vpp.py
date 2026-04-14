from playwright.sync_api import sync_playwright
import requests
from bs4 import BeautifulSoup
import re
import math

# Importar funciones de distancia
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
try:
    from parsers.location_engine import distancia
except:
    # Define distancia locally if import fails
    def distancia(lat1, lon1, lat2, lon2):
        import math
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

# ===== CONFIGURACIÓN =====
RADIO_KM = 1.0  # Radio de búsqueda en km
AYACUCHO_LAT = -32.9545
AYACUCHO_LON = -60.6455

# ===== ARGENPROP =====
def scrapear_argenprop():
    propiedades = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    for pagina in range(1, 6):
        url = "https://www.argenprop.com/departamentos/venta/rosario" if pagina == 1 else f"https://www.argenprop.com/departamentos/venta/rosario/pagina-{pagina}"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                break
        except:
            break
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tarjetas = soup.find_all('div', class_='listing__item')
        if not tarjetas:
            break
        
        for t in tarjetas:
            price_tag = t.find("p", class_="card__price")
            if not price_tag:
                continue
            precio = re.sub(r'[^\d]', '', price_tag.text)
            if not precio:
                continue
            try:
                precio = float(precio)
            except:
                continue
            
            features = t.find("ul", class_="card__main-features")
            metros = None
            if features:
                for li in features.find_all("li"):
                    text = li.text
                    if "m²" in text:
                        m_str = re.sub(r'[^\d]', '', text)
                        if m_str:
                            try:
                                metros = float(m_str)
                            except:
                                pass
                            break
            
            # NO TENEMOS COORDENADAS EN ARGENPROP - solo filtramos por zona
            # Para este ejemplo, usamos los datos disponibles directamente
            
            if precio and metros and metros > 0:
                valor_m2 = precio / metros
                if 500 <= valor_m2 <= 3500:
                    propiedades.append({
                        "precio": precio,
                        "m2": metros,
                        "valor_m2": valor_m2,
                        "fuente": "argenprop",
                        "titulo": str(t.find("h2"))[:50] if t.find("h2") else "",
                        "lat": None,  # No disponible
                        "lon": None
                    })
    
    return propiedades

# ===== ZONAPROP =====
def scrapear_zonaprop():
    propiedades = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        
        page.goto("https://www.zonaprop.com.ar/departamentos-venta-rosario.html", timeout=60000)
        page.wait_for_timeout(20000)
        
        if "Just a moment" in page.content()[:500]:
            browser.close()
            return []
        
        cards = page.query_selector_all(".postingCardLayout-module__posting-card-layout")
        
        for card in cards:
            try:
                if card.get_attribute("data-posting-type") != "PROPERTY":
                    continue
                
                precio_el = card.query_selector("[data-qa='POSTING_CARD_PRICE']")
                if not precio_el:
                    continue
                
                precio_text = precio_el.inner_text()
                precio_match = re.search(r'USD\s*([\d.,]+)', precio_text.replace(".", "").replace(",", ""))
                if not precio_match:
                    continue
                try:
                    precio = float(precio_match.group(1).replace(",", "."))
                except:
                    continue
                
                area_el = card.query_selector("[data-qa='POSTING_CARD_FEATURES']")
                metros = None
                if area_el:
                    area_text = area_el.inner_text()
                    m_match = re.search(r'(\d+)\s*m', area_text)
                    if m_match:
                        try:
                            metros = float(m_match.group(1))
                        except:
                            pass
                
                if not metros:
                    continue
                
                titulo_el = card.query_selector("h2, h3")
                titulo = titulo_el.inner_text() if titulo_el else ""
                
                valor_m2 = precio / metros
                if 400 <= valor_m2 <= 3500:
                    propiedades.append({
                        "precio": precio,
                        "m2": metros,
                        "valor_m2": valor_m2,
                        "fuente": "zonaprop",
                        "titulo": titulo[:50],
                        "lat": None,
                        "lon": None
                    })
            except:
                continue
        
        browser.close()
    
    return propiedades

# ===== TTL =====
def scrapear_ttl():
    propiedades = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto("https://www.ttlpropiedades.com/Venta", timeout=30000)
        page.wait_for_timeout(3000)
        
        propiedades = page.query_selector_all("ul#propiedades > li")
        
        props = []
        
        for prop in propiedades:
            try:
                precio_el = prop.query_selector("[class*='valor']")
                if not precio_el:
                    continue
                
                precio_text = precio_el.inner_text()
                precio_match = re.search(r'USD([\d.,]+)', precio_text)
                if not precio_match:
                    continue
                
                precio_str = precio_match.group(1)
                precio = float(precio_str.replace(",", ""))
                
                if precio < 1000:
                    precio = precio * 1000
                
                m2_el = prop.query_selector(".prop-data")
                if not m2_el:
                    continue
                
                m2_text = m2_el.inner_text()
                m2_match = re.search(r'([\d.,]+)\s*m', m2_text)
                if not m2_match:
                    continue
                
                metros = float(m2_match.group(1).replace(",", "."))
                
                if not (20 < metros < 250):
                    continue
                
                link = prop.query_selector("a[href]")
                titulo = ""
                if link:
                    href = link.get_attribute("href")
                    titulo = href.split("/")[-1] if href else ""
                    titulo = titulo.replace("-", " ")[:50]
                
                valor_m2 = precio / metros
                if 400 <= valor_m2 <= 4000:
                    props.append({
                        "precio": precio,
                        "m2": metros,
                        "valor_m2": valor_m2,
                        "fuente": "ttl",
                        "titulo": titulo,
                        "lat": None,
                        "lon": None
                    })
            except:
                continue
        
        browser.close()
    
    return props

# ===== LA CAPITAL =====
def scrapear_lacapital():
    propiedades = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://inmuebles.lacapital.com.ar/buscar-propiedades/?inmueble_hidden=Departamento&localidad=487&operacion_hidden=Venta"
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        
        props_divs = page.query_selector_all(".avisodestacado")
        
        for div in props_divs:
            try:
                texto = div.inner_text()
                
                m2_match = re.search(r"(\d+)\s*M", texto)
                if not m2_match:
                    continue
                
                try:
                    metros = int(m2_match.group(1))
                except:
                    continue
                
                if not (20 < metros < 250):
                    continue
                
                precio_match = re.search(r"--\s*(\d+)", texto)
                if not precio_match:
                    continue
                
                try:
                    precio = int(precio_match.group(1))
                    if precio < 10000:
                        precio = precio * 1000
                except:
                    continue
                
                dir_el = div.query_selector(".dir")
                titulo = dir_el.inner_text() if dir_el else ""
                titulo = titulo.replace("Departamento en Venta", "").replace("-", " ").strip()[:50]
                
                valor_m2 = precio / metros
                if 400 <= valor_m2 <= 4000:
                    propiedades.append({
                        "precio": precio,
                        "m2": metros,
                        "valor_m2": valor_m2,
                        "fuente": "lacapital",
                        "titulo": titulo,
                        "lat": None,
                        "lon": None
                    })
            except:
                continue
        
        browser.close()
    
    return propiedades

def filtrar_por_distancia(propiedades, lat_objetivo, lon_objetivo, radio_km=1.0):
    """
    Filtra propiedades dentro del radio usando Haversine.
    Si las propiedades no tienen coordenadas, usa TODAS (compatibilidad hacia atrás).
    """
    if not propiedades:
        return []
    
    # Verificar si tenemos coordenadas
    tiene_coords = any(p.get('lat') is not None and p.get('lon') is not None for p in propiedades)
    
    if not tiene_coords:
        # Si no hay coordenadas, devolver todas (funcionamiento actual)
        print("  [Sin coords] Propiedades sin coordenadas - usando todas")
        return propiedades
    
    # Filtrar por distancia
    filtradas = []
    for p in propiedades:
        if p.get('lat') is None or p.get('lon') is None:
            continue
        
        d = distancia(lat_objetivo, lon_objetivo, p['lat'], p['lon'])
        if d <= radio_km:
            filtradas.append(p)
    
    return filtradas

def calcular_precio_blended(propiedades):
    """Calcula precio promedio con ponderación por distancia."""
    if not propiedades:
        return 0
    
    # Verificar si tenemos coordenadas para IDW
    tiene_coords = any(p.get('lat') is not None and p.get('lon') is not None for p in propiedades)
    
    if tiene_coords:
        # IDW ponderado
        valores = []
        pesos = []
        
        for p in propiedades:
            d = distancia(AYACUCHO_LAT, AYACUCHO_LON, p['lat'], p['lon'])
            peso = 1 / (d**2 + 0.1) if d > 0 else 10
            valores.append(p['valor_m2'] * peso)
            pesos.append(peso)
        
        return sum(valores) / sum(pesos) if valores else 0
    else:
        # Promedio simple
        return sum(p['valor_m2'] for p in propiedades) / len(propiedades)

def main():
    print("="*70)
    print(f"SIMULACIÓN VPP CON FILTRO DE DISTANCIA ({RADIO_KM} km)")
    print("="*70)
    
    ayacucho = {
        "nombre": "Ayacucho",
        "lat": AYACUCHO_LAT,
        "lon": AYACUCHO_LON,
        "m2": 27.0,
        "zona": "Sexta Pellegrini",
        "piso": 1,
        "estado": "muy bueno"
    }
    
    print(f"\nOBJETIVO: {ayacucho['nombre']} ({ayacucho['lat']}, {ayacucho['lon']})")
    print(f"RADIO DE BÚSQUEDA: {RADIO_KM} km")
    
    # Scraping
    print("\n--- ARGENPROP ---")
    argenprop_props = scrapear_argenprop()
    print(f"  Encontradas: {len(argenprop_props)}")
    
    print("\n--- ZONAPROP ---")
    zonaprop_props = scrapear_zonaprop()
    print(f"  Encontradas: {len(zonaprop_props)}")
    
    print("\n--- TTL ---")
    ttl_props = scrapear_ttl()
    print(f"  Encontradas: {len(ttl_props)}")
    
    print("\n--- LA CAPITAL ---")
    lacapital_props = scrapear_lacapital()
    print(f"  Encontradas: {len(lacapital_props)}")
    
    # Combinar
    todas = argenprop_props + zonaprop_props + ttl_props + lacapital_props
    
    print(f"\n--- TOTALES ---")
    print(f"  Total propiedades: {len(todas)}")
    
    # Filtrar por distancia (solo si hay coordenadas)
    filtradas = filtrar_por_distancia(todas, AYACUCHO_LAT, AYACUCHO_LON, RADIO_KM)
    
    if len(filtradas) < len(todas):
        print(f"  Dentro de {RADIO_KM}km: {len(filtradas)}")
    
    # Calcular precio blended
    precio_m2 = calcular_precio_blended(filtradas if filtradas else todas)
    
    print(f"\n  PRECIO BASE/m2: ${precio_m2:.0f}")
    
    # Cálculo VPP
    valor_base = ayacucho['m2'] * precio_m2
    factor_estado = 1.10 if ayacucho['estado'] == "muy bueno" else 1.0
    factor_piso = 0.95 if ayacucho['piso'] == 0 else 1.0
    
    valor_ajustado = valor_base * factor_estado * factor_piso
    descuento_liquidez = 0.08
    valor_realizable = valor_ajustado * (1 - descuento_liquidez)
    
    print(f"\n--- VALUACIÓN ---")
    print(f"  Valor VPP: ${valor_ajustado:,.0f}")
    print(f"  Valor Neto: ${valor_realizable:,.0f}")

if __name__ == "__main__":
    main()
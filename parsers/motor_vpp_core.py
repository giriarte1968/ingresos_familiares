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

def save_cache(propiedades, status="completado"):
    data = {
        "fecha": datetime.now().isoformat(),
        "status": status,
        "propiedades": propiedades
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

def scrapear_argenprop(operacion="venta"):
    props = []
    base_urls = [
        f"https://www.argenprop.com/departamentos/{operacion}/rosario/monoambiente",
        f"https://www.argenprop.com/departamentos/{operacion}/rosario/1-dormitorio"
    ]
    headers = {"User-Agent": get_random_ua()}
    for url in base_urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            for t in soup.find_all("div", class_="listing__item"):
                try:
                    price_text = t.find("p", class_="card__price").text
                    px_match = re.search(r'([\d.]+)', price_text.replace(",", "."))
                    if not px_match: continue
                    precio = float(px_match.group(1).replace(".", ""))
                    if operacion == "venta" and "USD" not in price_text: continue
                    
                    m2 = dorms = None
                    features = t.find("ul", class_="card__main-features")
                    if features:
                        text = features.text.lower()
                        m_match = re.search(r'(\d+)\s*m²', text)
                        if m_match: m2 = float(m_match.group(1))
                        d_match = re.search(r'(\d+)\s*dorm', text)
                        if d_match: dorms = int(d_match.group(1))
                    
                    if precio and m2 and m2 > 0:
                        props.append({
                            "precio": precio, "m2": m2, "dormitorios": dorms or 1,
                            "valor_m2": precio / m2, "direccion": t.find("h2").text.strip() if t.find("h2") else "",
                            "fuente": "argenprop", "operacion": operacion, "zona": normalizar_zona(t.text)
                        })
                except: continue
        except: continue
    return props

def scrapear_ttl(operacion="venta"):
    props = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=get_random_ua())
            op_label = "Venta" if operacion == "venta" else "Alquiler"
            page.goto(f"https://www.ttlpropiedades.com/{op_label}?tipopropiedad=departamento", timeout=20000)
            page.wait_for_timeout(2000)
            items = page.query_selector_all("ul#propiedades > li")
            for item in items:
                try:
                    text = item.inner_text()
                    px_match = re.search(r'USD\s*([\d.,]+)' if operacion == "venta" else r'\$\s*([\d.,]+)', text.replace(".", ""))
                    if not px_match: continue
                    precio = float(px_match.group(1))
                    m_match = re.search(r'(\d+)\s*m', text)
                    m2 = float(m_match.group(1)) if m_match else 0
                    if precio and m2 > 10:
                        # Limpieza de seguridad para evitar concatenación de dígitos
                        if precio > 50000000 and operacion == "venta": # Nadie vende por 50M USD en Rosario (salvo hoteles)
                             precio = float(str(int(precio))[:6]) # Truncar
                        
                        props.append({
                            "precio": precio, "m2": m2, "valor_m2": precio / m2,
                            "fuente": "ttl", "operacion": operacion, "zona": normalizar_zona(text)
                        })
                except: continue
            browser.close()
    except: pass
    return props

def scrapear_agencias_batch(operacion="venta"):
    agencias = [
        ("giaganti", f"https://giaganti.com.ar/propiedades/{operacion}/departamentos"),
        ("dunod", f"https://www.dunod.com.ar/propiedades?operacion={operacion}&tipo=departamento"),
        ("ferreyra", f"https://diegoferreyra.com.ar/propiedades/departamentos/{operacion}")
    ]
    props = []
    def scrape_one(info):
        name, url = info
        try:
            r = requests.get(url, headers={"User-Agent": get_random_ua()}, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            found = []
            for card in soup.find_all(["div", "article"], class_=re.compile(r"prop|card|item", re.I))[:10]:
                txt = card.text.replace(".", "").replace(",", "")
                px_m = re.search(r'(?:USD|\$)\s*([\d.]+)', txt)
                m_m = re.search(r'(\d+)\s*m', txt)
                if px_m and m_m:
                    p_str = px_m.group(1).replace(".", "")
                    p, m = float(p_str), float(m_m.group(1))
                    if m > 0: found.append({"precio":p, "m2":m, "valor_m2":p/m, "fuente":name, "operacion":operacion, "zona":normalizar_zona(txt)})
            return found
        except: return []

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = pool.map(scrape_one, agencias)
        for r in results: props.extend(r)
    return props

# --- LOGICA DE CLUSTERING ---

def filtrar_similares(propiedades, lat_obj, lon_obj, m2_obj, anclas, radio_km=1.5, antiguedad_obj=None):
    # Intentar con radio de edad estricto (+/- 10 años)
    filtradas = _ejecutar_filtro(propiedades, lat_obj, lon_obj, m2_obj, anclas, radio_km, antiguedad_obj, rango_edad=10)
    
    # Si la muestra es demasiado pobre (< 10), abrimos el rango de edad para ganar masa crítica (Adaptive Age Filter)
    if len(filtradas) < 10 and antiguedad_obj is not None:
        filtradas = _ejecutar_filtro(propiedades, lat_obj, lon_obj, m2_obj, anclas, radio_km, antiguedad_obj, rango_edad=20)
        
    return filtradas

def _ejecutar_filtro(propiedades, lat_obj, lon_obj, m2_obj, anclas, radio_km, antiguedad_obj, rango_edad):
    filtradas = []
    for p in propiedades:
        # Filtro m2
        if not (m2_obj * 0.5 <= p["m2"] <= m2_obj * 1.5): continue
        
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

def calculate_iqr_cluster(propiedades):
    if len(propiedades) < 3: return propiedades
    vals = sorted([p["valor_m2"] for p in propiedades])
    q1 = vals[int(len(vals) * 0.25)]
    q3 = vals[int(len(vals) * 0.75)]
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return [p for p in propiedades if lower <= p["valor_m2"] <= upper]

def calcular_valor_vpp(propiedades, lat_obj, lon_obj, m2_obj, zona_name, anclas, usar_ancla=True, antiguedad=None):
    # 1. Filtrar similares con lógica adaptativa
    similares = filtrar_similares(propiedades, lat_obj, lon_obj, m2_obj, anclas, antiguedad_obj=antiguedad)
    if not similares: similares = propiedades # Fallback ciudad
    
    # 2. Clustering
    cluster = calculate_iqr_cluster(similares)
    if not cluster: return 0, 0, 0, 0
    
    precio_cluster = sum(p["valor_m2"] for p in cluster) / len(cluster)
    
    # 3. Ancla Estructural (Solo para Venta/USD)
    if usar_ancla:
        ancla_key = next((k for k,v in anclas.items() if zona_name.lower() in v["id"].lower()), None)
        ancla_val_raw = anclas[ancla_key]["usd_m2"] if ancla_key else 1500
        
        # v8.4: Re-ajustar ancla institucional por antigüedad antes del blending
        if antiguedad is not None:
            f_dep_ancla = max(0.4, 1.0 - (antiguedad * 0.006))
            ancla_val = ancla_val_raw * f_dep_ancla
        else:
            ancla_val = ancla_val_raw
            
        # 4. Blending Dinámico v8.0 (Ponderación por Calidad de Muestra)
        n = len(cluster)
        if n >= 20: 
            w_c = 0.50 
        elif n >= 10: 
            w_c = 0.40 
        else: 
            w_c = 0.25 
        
        precio_final = (precio_cluster * w_c) + (ancla_val * (1 - w_c))
        return precio_final, precio_cluster, ancla_val, n
    else:
        # Alquiler: Mercado puro 100%
        return precio_cluster, precio_cluster, 0, len(cluster)

# --- PROCESO ASINCRONICO ---

def actualizar_mercado_vpp_full():
    """Función para correr en segundo plano"""
    print("Iniciando Scraping Masivo VPP...")
    try:
        ventas = scrapear_argenprop("venta") + scrapear_ttl("venta") + scrapear_agencias_batch("venta")
        alquileres = scrapear_argenprop("alquiler") + scrapear_ttl("alquiler") + scrapear_agencias_batch("alquiler")
        total = ventas + alquileres
        save_cache(total, status="completado")
        print(f"Scraping finalizado: {len(total)} propiedades.")
        return True
    except Exception as e:
        print(f"Error en scraping asíncrono: {e}")
        return False

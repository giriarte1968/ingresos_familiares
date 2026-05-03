import requests
import json
import urllib.parse
import time
import random
import math
import os
from bs4 import BeautifulSoup
import re
from concurrent.futures import ThreadPoolExecutor

CACHE_FILE = "cache_scraping.json"

def extract_info_from_text(text):
    """
    Extrae año de construcción y estado de la propiedad del texto.
    """
    if not text:
        return None, None
    text = text.lower()
    
    # --- 1. EXTRACCIÓN DE AÑO ---
    year = None
    # Buscamos años entre 1900 y 2026
    years = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', text)
    keywords_year = ['construido', 'construccion', 'año', 'anio', 'edificio', 'estrenar', 'antigüedad']
    for kw in keywords_year:
        if kw in text:
            # Buscamos el año más cercano a la palabra clave
            match = re.search(rf'{kw}.*?\b(19\d{2}|20[0-2]\d)\b', text)
            if match:
                year = int(match.group(1))
                break
    if not year and years:
        year = int(years[0])
    
    # Fallback antigüedad relativa (ej: "10 años")
    if not year:
        age_match = re.search(r'(\d+)\s*año', text)
        if age_match:
            year = 2026 - int(age_match.group(1))
    
    if 'estrenar' in text or 'a estrenar' in text:
        year = 2026
        
    # --- 2. EXTRACCIÓN DE ESTADO ---
    estado = "usado" # default
    if any(x in text for x in ['estrenar', 'a estrenar', 'nuevo', 'moderno']):
        estado = "nuevo"
    elif any(x in text for x in ['refaccionar', 'reciclar', 'estado regular', 'a refaccionar', 'estado malo']):
        estado = "refaccionar"
    elif any(x in text for x in ['pozo', 'en construcción', 'proyecto', 'preventa']):
        estado = "pozo"
    elif any(x in text for x in ['excelente', 'impecable', 'como nuevo']):
        estado = "excelente"
        
    return year, estado

def scrape_detail(url):
    """Visita la URL y extrae info."""
    if not url:
        return None
    try:
        time.sleep(random.uniform(0.5, 1.5))
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text(" ")
        return extract_info_from_text(text)
    except:
        return None

def get_dist(lat1, lon1, lat2, lon2):
    R = 6371
    try:
        dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
    except:
        return 999

def main():
    # Coordenadas prioridad (Mabel y Ayacucho)
    targets = [
        {"nombre": "Mabel", "lat": -32.9541101, "lon": -60.6316406},
        {"nombre": "Ayacucho", "lat": -32.960323, "lon": -60.6299652}
    ]
    radius_km = 1.5
    
    # Cargar Cache
    if not os.path.exists(CACHE_FILE):
        print("No cache file found.")
        return
    
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    props = data.get('propiedades', [])
    print(f"[SISTEMA] Total propiedades en cache: {len(props)}")
    
    # Identificar propiedades prioritarias
    priority_props = []
    for p in props:
        p_lat, p_lon = p.get('lat'), p.get('lon')
        if not p_lat or not p_lon: continue
        
        for target in targets:
            if get_dist(target['lat'], target['lon'], p_lat, p_lon) <= radius_km:
                priority_props.append(p)
                break
    
    print(f"[SISTEMA] Propiedades en radio de prioridad: {len(priority_props)}")
    
    # Filtrar solo las que necesitan enriquecer (sin año o estado)
    to_enrich = [p for p in priority_props if p.get('anio_construccion') is None]
    print(f"[SISTEMA] Propiedades para enriquecer: {len(to_enrich)}")
    
    # Deep Scrape
    updated_count = 0
    for i, p in enumerate(to_enrich):
        url = p.get('url')
        if not url: continue
        
        print(f"[{i+1}/{len(to_enrich)}] Procesando: {url[:50]}...")
        res = scrape_detail(url)
        if res:
            year, estado = res
            p['anio_construccion'] = year
            p['estado_propiedad'] = estado
            updated_count += 1
            print(f"  -> Encontrado: Año={year}, Estado={estado}")
        else:
            print(f"  -> No se pudo extraer info")
            
    # Guardar cambios
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n[FINAL] Proceso completado. {updated_count} propiedades actualizadas.")

if __name__ == "__main__":
    main()
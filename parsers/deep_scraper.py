
import requests
from bs4 import BeautifulSoup
import re
import json
import os
import time
import random
import math
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
]

def get_random_ua():
    return random.choice(USER_AGENTS)

def extract_year_from_text(text):
    """
    Busca patrones de año de construcción en el texto.
    Ej: 'Año de construcción: 2000', 'Construido en 1995', 'Antigüedad: 10 años'
    """
    if not text: return None
    text = text.lower()
    
    # 1. Búsqueda de año explícito (4 dígitos entre 1900 y 2026)
    years = re.findall(r'\b(19\d{2}|20[0-2]\d)\b', text)
    # Priorizamos años que estén cerca de palabras clave
    keywords = ['construido', 'construccion', 'año', 'anio', 'edificio', 'estrenar']
    
    # Si hay palabras clave, buscamos el año más cercano a ellas
    for kw in keywords:
        if kw in text:
            # Buscar el primer año que aparezca después de la palabra clave
            match = re.search(rf'{kw}.*?\b(19\d{2}|20[0-2]\d)\b', text)
            if match:
                return int(match.group(1))
    
    if years:
        # Retornamos el primero encontrado si no hay palabras clave
        return int(years[0])
        
    # 2. Búsqueda de antigüedad relativa (ej: "10 años")
    age_match = re.search(r'(\d+)\s*año', text)
    if age_match:
        age = int(age_match.group(1))
        return 2026 - age
        
    if 'estrenar' in text:
        return 2026
        
    return None

def scrape_property_detail(prop):
    """Visita la URL de una propiedad y extrae el año de construcción."""
    url = prop.get('url')
    if not url: return prop
    
    try:
        headers = {"User-Agent": get_random_ua()}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200: 
            print(f"HTTP {r.status_code} for {url}")
            return prop
        
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text(" ")
        
        year = extract_year_from_text(text)
        if year:
            print(f"Found year {year} for {url}")
            prop['anio_construccion'] = year
        else:
            print(f"No year found in {url}")
            
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        pass
    
    return prop


def enrich_cache_targeted(lat=None, lon=None, radius=1.0):
    """Enriquece solo las propiedades en un radio específico para pruebas rápidas."""
    cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache_scraping.json')
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    props = data.get('propiedades', [])
    
    def get_dist(l1, o1, l2, o2):
        R = 6371
        try:
            dlat, dlon = math.radians(l2-l1), math.radians(o2-o1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(l1))*math.cos(math.radians(l2))*math.sin(dlon/2)**2
            return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))
        except:
            return 999
    
    # Si no hay coordenadas, enriquecer todas las que tengan URL
    if lat is None or lon is None:
        to_enrich = [p for p in props if p.get('url') and ('anio_construccion' not in p or p['anio_construccion'] is None)]
        print(f"Full enrichment: {len(to_enrich)} properties to process.")
    else:
        to_enrich = []
        for p in props:
            p_lat, p_lon = p.get('lat'), p.get('lon')
            if not p_lat or not p_lon: continue
            if get_dist(lat, lon, p_lat, p_lon) <= radius:
                if 'anio_construccion' not in p or p['anio_construccion'] is None:
                    to_enrich.append(p)
        print(f"Targeted enrichment: {len(to_enrich)} properties found near target.")
    
    if not to_enrich:
        print("No properties to enrich.")
        return
    
    # Limitar a 50 para evitar bloqueos
    to_enrich = to_enrich[:50]
    print(f"Processing {len(to_enrich)} properties...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(scrape_property_detail, to_enrich))
    
    updated = 0
    for p_new in results:
        url = p_new.get('url')
        if url and p_new.get('anio_construccion'):
            for p_old in props:
                if p_old.get('url') == url:
                    p_old['anio_construccion'] = p_new.get('anio_construccion')
                    updated += 1
                    break
    
    data['propiedades'] = props
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Enrichment completed. {updated} properties updated.")

if __name__ == "__main__":
    enrich_cache_targeted()

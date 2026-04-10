import requests
from bs4 import BeautifulSoup
import re
import json
import os
from datetime import datetime

DATOS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'datos.json'
)


def obtener_precio_oro_forex():
    """API exchangerate.host - precio XAU/USD"""
    try:
        url = "https://api.exchangerate.host/latest?base=XAU&symbols=USD"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if data and 'rates' in data:
            usd_per_oz = data['rates'].get('USD')
            if usd_per_oz:
                return round(usd_per_oz / 31.1035, 2)
    except:
        pass
    return None


def obtener_precio_oro_oxr():
    """Open Exchange Rates API alternativa"""
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"}
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if data.get('rates') and 'XAU' in data['rates']:
            usd_per_oz = data['rates']['XAU']
            return round(usd_per_oz / 31.1035, 2)
    except:
        pass
    return None


def obtener_precio_oro_metal():
    """API metals.dev"""
    try:
        url = "https://api.metal.dev/api/v1/spot?api_key=demo&symbol=XAU&currency=USD"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data and 'price' in data:
            return round(float(data['price']) / 31.1035, 2)
    except:
        pass
    return None


def obtener_precio_oro_goldapi():
    """API goldapi.io"""
    try:
        url = "https://www.goldapi.io/api/XAU/USD"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'price' in data:
                return round(data['price'] / 31.1035, 2)
    except:
        pass
    return None


def obtener_precio_oro_ml():
    """Scraping de Mercado Libre Argentina - oro lingotes"""
    try:
        url = "https://api.mercadolibre.com/sites/MLA/search?q=oro+lingote+24k&category=MLA403399"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        precios = []
        for item in data.get('results', [])[:10]:
            price = item.get('price', 0)
            if price and 5000 < price < 500000:
                # Asumiendo 1 onza = 31.1g, precio en ARS -> USD
                usdt_ars = 1500
                usd_per_gram = (price / usdt_ars) / 31.1
                if 40 < usd_per_gram < 150:
                    precios.append(usd_per_gram)
        
        if precios:
            return round(sum(precios) / len(precios), 2)
    except:
        pass
    return None


def obtener_precio_oro_cotizacionoro():
    """Scraping cotizacionoro.com.ar"""
    try:
        url = "https://www.cotizacionoro.com.ar/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-ES,es;q=0.9"
        }
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buscar tabla de precios
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    texto = cells[0].get_text().lower()
                    if 'gramo' in texto or '24k' in texto or 'onza' in texto:
                        precio_texto = cells[1].get_text()
                        match = re.search(r'[\d.]+', precio_texto.replace(',', '.'))
                        if match:
                            valor = float(match.group())
                            if 'onza' in texto:
                                return round(valor / 31.1035, 2)
                            return round(valor, 2)
    except:
        pass
    return None


def obtener_precio_oro_scraper():
    """Scraping genérico de precio del oro"""
    urls = [
        "https://www.preciodeloro.com/",
        "https://www.cotizacionoro.com/",
    ]
    
    for url in urls:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar patrones comunes
            textos = soup.get_text()
            matches = re.findall(r'(\d+\.?\d*)\s*(?:USD|usd)\s*/\s*(?:gramo|g|oz|onza)', textos, re.I)
            for match in matches:
                valor = float(match)
                if 50 < valor < 150:
                    return round(valor, 2) if 'gramo' in textos.lower() or 'g ' in textos.lower() else round(valor / 31.1, 2)
        except:
            continue
    return None


def obtener_precio_oro():
    """
    Obtiene precio del gramo de oro en USD.
    Intenta múltiples fuentes y retorna el promedio.
    """
    fuentes = [
        ("forex", obtener_precio_oro_forex),
        ("oxr", obtener_precio_oro_oxr),
        ("metal", obtener_precio_oro_metal),
        ("ml", obtener_precio_oro_ml),
    ]
    
    valores = []
    fuentes_exitosas = []
    
    for nombre, func in fuentes:
        try:
            valor = func()
            if valor and 50 < valor < 150:
                valores.append(valor)
                fuentes_exitosas.append(nombre)
        except:
            pass
    
    if valores:
        return round(sum(valores) / len(valores), 2)
    
    # Fallback: precio aproximado del oro
    return round(2650 / 31.1035, 2)  # ~85.20 USD/gramo


def actualizar_precio_oro():
    """Actualiza el precio del oro en datos.json"""
    precio = obtener_precio_oro()
    if precio is None:
        return None
    
    datos = json.load(open(DATOS_FILE, 'r', encoding='utf-8'))
    
    datos.setdefault('metadata', {})['precio_oro_gramo_usd'] = precio
    datos['metadata']['precio_oro_fecha'] = datetime.now().strftime('%Y-%m-%d')
    
    mes_actual = datetime.now().strftime('%Y-%m')
    datos.setdefault('metadata', {}).setdefault('oro_mes_anterior', {})[mes_actual] = precio
    
    with open(DATOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    
    return precio


def get_precio_oro():
    """Retorna el precio actual del oro desde metadata"""
    try:
        datos = json.load(open(DATOS_FILE, 'r', encoding='utf-8'))
        return datos.get('metadata', {}).get('precio_oro_gramo_usd')
    except:
        return None
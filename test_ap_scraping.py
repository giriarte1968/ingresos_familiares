import requests
from bs4 import BeautifulSoup
import re

def scrapear_m2_argenprop():
    url = "https://www.argenprop.com/departamentos/venta/rosario/1-dormitorio"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9"
    }
    
    try:
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
            
        promedio_m2 = sum(valores_m2) / len(valores_m2)
        return round(promedio_m2, 2)
    except Exception as e:
        print(f"Error scraping: {e}")
        return None

if __name__ == "__main__":
    v = scrapear_m2_argenprop()
    print("Promedio AP:", v)

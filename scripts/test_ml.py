import requests
from bs4 import BeautifulSoup
import re

url = "https://inmuebles.mercadolibre.com.ar/MLA-1459-departamentos_Logged"
params = {"estado": "AR-S", "provincia": "Santa-Fe"}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

response = requests.get(url, params=params, headers=headers, timeout=20)
print(f"Status: {response.status_code}")
print(f"URL: {response.url}")

soup = BeautifulSoup(response.text, 'html.parser')

items = soup.find_all("li", class_="ui-search-layout__item")
print(f"Items encontrados: {len(items)}")

props = []
for i, item in enumerate(items[:10]):
    titulo = item.find("h2", class_="ui-search-item__title")
    titulo = titulo.text if titulo else ""
    
    precio = item.find("span", class_="price-tag-fraction")
    if precio:
        precio = precio.text.replace(".", "")
        try:
            precio = float(precio)
        except:
            precio = None
    
    area = item.find("ul", class_="ui-search-card-attributes__attribute")
    metros = None
    
    print(f"{i+1}. {titulo[:40]} | {precio}")
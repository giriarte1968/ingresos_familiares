import requests
from bs4 import BeautifulSoup
import re

url = "https://www.argenprop.com/departamentos/venta/rosario"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers, timeout=20)
print(f"Status: {response.status_code}")
soup = BeautifulSoup(response.text, 'html.parser')

tarjetas = soup.find_all('div', class_='listing__item')
print(f"Encontradas {len(tarjetas)} tarjetas listing__item")

if not tarjetas:
    print("Buscando otras clases...")
    todas = soup.find_all('div')
    print(f"Total divs: {len(todas)}")
    for d in todas[:10]:
        cls = d.get('class', [])
        if cls:
            print(f"Clase: {cls}")

props = []
for t in tarjetas:
    price_tag = t.find("p", class_="card__price")
    if not price_tag:
        continue
    
    price_str = price_tag.text
    precio = re.sub(r'[^\d]', '', price_str)
    if not precio:
        continue
    precio = float(precio)
    
    features = t.find("ul", class_="card__main-features")
    metros = None
    if features:
        for li in features.find_all("li"):
            text = li.text
            if "m²" in text or "m2" in text.lower():
                m_str = re.sub(r'[^\d]', '', text)
                if m_str:
                    metros = float(m_str)
                    break
    
    direccion = t.find("h2") or t.find("h3")
    direccion = direccion.text if direccion else "N/A"
    
    if precio and metros and metros > 0:
        valor_m2 = precio / metros
        if 500 <= valor_m2 <= 3500:
            props.append({
                "precio": precio,
                "m2": metros,
                "valor_m2": valor_m2,
                "direccion": direccion
            })

print(f"\nPropiedades válidas: {len(props)}")
for i, p in enumerate(props[:10]):
    print(f"{i+1}. {p['direccion'][:40]} - {p['m2']}m2 - USD {p['precio']:,.0f} - USD/m2 {p['valor_m2']:.0f}")
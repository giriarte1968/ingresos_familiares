import requests
from bs4 import BeautifulSoup
import re

url = "https://www.ttlpropiedades.com/Venta"
headers = {"User-Agent": "Mozilla/5.0"}

r = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(r.text, "html.parser")

# Analizar la estructura - buscar el contenedor principal
print("Buscando estructura...")

# Método 1: buscar el listado
listado = soup.find(class_="resultados-list")
print(f"resultados-list: {listado is not None}")

# Método 2: buscar todos los prop-data
prop_data = soup.find_all(class_=re.compile(r"prop-data"))
print(f"prop-data: {len(prop_data)}")

# Analizar primer prop-data
if prop_data:
    first = prop_data[0]
    print(f"\n--- Primer prop-data ---")
    print(first.get_text()[:500])
    print(f"\n--- HTML ---")
    print(first)

# Si no hay prop-data, buscar otras clases
if not prop_data:
    # Buscar por estructura más genérica
    all_divs = soup.find_all("div")
    for div in all_divs[:20]:
        cls = div.get("class")
        if cls:
            print(f"Div class: {cls}")
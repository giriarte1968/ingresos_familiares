import requests
from bs4 import BeautifulSoup
import re

headers = {"User-Agent": "Mozilla/5.0"}

# Visitar una propiedad de prueba
link = "https://www.bienesrosario.com/index.php?action=carro/showProduct&itmId=2122361&rbrId=119"
r = requests.get(link, headers=headers, timeout=15)
soup = BeautifulSoup(r.text, "html.parser")

# Buscar todos los elementos con precio
print("Buscando precios...")
precios = soup.find_all(class_=re.compile(r"precio", re.I))
print(f"Elementos con clase precio: {len(precios)}")

for i, p in enumerate(precios):
    print(f"  {i}: {p.get_text(strip=True)[:50]}")

# Buscar por texto
all_text = soup.get_text()
import re
matches = re.findall(r'U?\$S?\s*([\d.,]+)', all_text)
print(f"\nPrecios en texto: {matches}")

# Buscar estructura general
print(f"\n--- HTML preview de la zona de precio ---")
for tag in soup.find_all(class_=re.compile(r"precio"))[:3]:
    print(tag)
    print("---")
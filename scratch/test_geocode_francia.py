import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(BASE_DIR, 'cache_scraping.json')

with open(CACHE_PATH, 'r', encoding='utf-8') as f:
    cache = json.load(f)

propiedades = cache.get('propiedades', [])
print(f"Total properties in cache: {len(propiedades)}")

# Find properties matching addresses: Cabrera, Suarez, Marc, Balcarce, Callao
matching_comps = []
for p in propiedades:
    addr = p.get('direccion', '').lower()
    # Check if this matches one of the comparables
    if any(k in addr for k in ['cabrera', 'suarez', 'marc', 'balcarce 50', 'callao 55']):
        matching_comps.append(p)

print(f"\nFound {len(matching_comps)} matches in cache:")
for mc in matching_comps[:15]:
    print(f"Direccion: {mc.get('direccion')} | Lat/Lon: {mc.get('lat')}, {mc.get('lon')} | Valor m2: {mc.get('valor_m2')} | Precio: {mc.get('precio')} | Operacion: {mc.get('operacion')}")

# Let's search Nominatim for Callao 5575, Rosario
import requests
def query_nominatim(address):
    params = {"q": address, "format": "jsonv2", "limit": 1}
    r = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers={"User-Agent": "test"})
    if r.status_code == 200 and r.json():
        res = r.json()[0]
        print(f"\nNominatim [{address}]: {res.get('display_name')} -> {res.get('lat')}, {res.get('lon')}")
    else:
        print(f"\nNominatim [{address}]: Not found")

query_nominatim("Callao 5575, Rosario")
query_nominatim("Balcarce 5090, Rosario")
query_nominatim("Francia 250 bis, Rosario")

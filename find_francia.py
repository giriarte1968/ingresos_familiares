import json
base = r'C:\Users\Gustavo\ingresos_familiares_st'
with open(base + r'\cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)
for p in cache.get('propiedades', []):
    name = p.get('nombre', '')
    if 'Francia' in name:
        print(f"Name: {name} | Zona: {p.get('zona')} | Lat: {p.get('lat')} | Lon: {p.get('lon')}")

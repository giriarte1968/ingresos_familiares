import json

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

props = data.get('propiedades', [])
print(f"Total: {len(props)}")
print("-" * 60)
for p in props[:50]:
    print(f"Dir: {p.get('direccion', 'N/A')[:40]:<40} | Lat: {p.get('lat')} | Lon: {p.get('lon')}")

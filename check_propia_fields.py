import requests
import json

# Test what fields are available in Propia API
r = requests.get("https://admin.propia.com.ar/items/properties?limit=1&fields=*", timeout=30)
if r.status_code == 200:
    data = r.json()
    items = data.get('data', [])
    if items:
        item = items[0]
        print("Campos disponibles en la API:")
        for key in sorted(item.keys()):
            print(f"  - {key}")
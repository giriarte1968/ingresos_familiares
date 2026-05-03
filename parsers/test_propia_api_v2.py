# Direct API test for Propia with proper filters
import requests
import json
import urllib.parse

BASE_API = "https://admin.propia.com.ar/items/properties"

def test_propia_api_v2():
    print("[PROPIA] Probando API directa v2...")
    
    # Let's explore the available fields and operations
    print("\n[PROPIA] Obteniendo tipos de operación...")
    r_ops = requests.get("https://admin.propia.com.ar/items/operations?fields=id,name&limit=-1", timeout=30)
    if r_ops.status_code == 200:
        ops = r_ops.json()
        print("[PROPIA] Operaciones:")
        for o in ops.get('data', []):
            print(f"  {o}")
    
    print("\n[PROPIA] Obteniendo tipos de propiedad...")
    r_types = requests.get("https://admin.propia.com.ar/items/property_types?fields=id,name&limit=-1", timeout=30)
    if r_types.status_code == 200:
        types = r_types.json()
        print("[PROPIA] Tipos:")
        for t in types.get('data', []):
            print(f"  {t}")
    
    # Now try a simple query without filters first
    print("\n[PROPIA] Solicitando properties sin filtros...")
    params = {
        "limit": 5,
        "fields": "id,title,slug,price,area,bedrooms,address,latitude,longitude",
    }
    
    r = requests.get(BASE_API, params=params, timeout=30)
    print(f"[PROPIA] Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"[PROPIA] Properties: {len(data.get('data', []))}")
        
        # Save sample
        with open("propia_api_test.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        for item in data.get('data', [])[:3]:
            print(f"\n[PROPIA] Property:")
            print(f"  Title: {item.get('title')}")
            print(f"  Price: {item.get('price')}")
            print(f"  Area: {item.get('area')} m2")
            print(f"  Bedrooms: {item.get('bedrooms')}")
            print(f"  Address: {item.get('address')}")
            print(f"  Lat/Lon: {item.get('latitude')}, {item.get('longitude')}")
            slug = item.get('slug', '')
            print(f"  URL: https://propia.com.ar/propiedad/{slug}")

if __name__ == "__main__":
    test_propia_api_v2()
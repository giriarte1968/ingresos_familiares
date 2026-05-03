# Direct API test for Propia
import requests
import json
import urllib.parse

BASE_API = "https://admin.propia.com.ar/items/properties"

def test_propia_api():
    print("[PROPIA] Probando API directa...")
    
    # Parameters for Rosario (city=1), venta (operation_id=1), departamento (type_id=2)
    # First, let's get the cities to confirm Rosario
    r = requests.get("https://admin.propia.com.ar/items/location_cities?fields=id,name&limit=-1", timeout=30)
    if r.status_code == 200:
        cities = r.json()
        print("[PROPIA] Ciudades disponibles:")
        for c in cities.get('data', [])[:10]:
            print(f"  ID: {c.get('id')} - {c.get('name')}")
    
    # Now get properties in Rosario
    # Filter: status=published, city_id=1 (Rosario)
    filter_json = json.dumps({
        "status": "published",
        "location_city_id": {"_eq": 1}
    })
    
    params = {
        "limit": 10,
        "page": 1,
        "fields": "id,title,slug,price,area,bedrooms,address,latitude,longitude",
        "filter": urllib.parse.quote(filter_json)
    }
    
    print(f"\n[PROPIA] Solicitando propiedades...")
    r = requests.get(BASE_API, params=params, timeout=30)
    print(f"[PROPIA] Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"[PROPIA] Total properties: {data.get('meta', {}).get('total_count', 'N/A')}")
        
        items = data.get('data', [])
        print(f"[PROPIA] Properties returned: {len(items)}")
        
        # Save sample
        with open("propia_api_test.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Print sample
        for item in items[:3]:
            print(f"\n[PROPIA] Property:")
            print(f"  Title: {item.get('title')}")
            print(f"  Price: {item.get('price')}")
            print(f"  Area: {item.get('area')} m2")
            print(f"  Bedrooms: {item.get('bedrooms')}")
            print(f"  Address: {item.get('address')}")
            print(f"  Lat/Lon: {item.get('latitude')}, {item.get('longitude')}")
            slug = item.get('slug', '')
            print(f"  URL: https://propia.com.ar/propiedad/{slug}")
    
    # Try with more filters (venta = operation_id 1)
    print("\n[PROPIA] Probando con operación=venta...")
    filter_venta = json.dumps({
        "status": "published",
        "location_city_id": {"_eq": 1},
        "operation_id": {"_eq": 1},
    })
    
    params2 = {
        "limit": 5,
        "page": 1,
        "fields": "id,title,slug,price,area,bedrooms,address,latitude,longitude",
        "filter": urllib.parse.quote(filter_venta)
    }
    
    r2 = requests.get(BASE_API, params=params2, timeout=30)
    if r2.status_code == 200:
        data2 = r2.json()
        print(f"[PROPIA] Properties for sale: {data2.get('meta', {}).get('total_count', 'N/A')}")
        
        with open("propia_api_venta.json", "w", encoding="utf-8") as f:
            json.dump(data2, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    test_propia_api()
import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
headers = {"User-Agent": "rosario_avm_geocoder_test"}

def query(q):
    print(f"\nQuerying: {q}")
    params = {
        "q": q,
        "format": "jsonv2",
        "limit": 3
    }
    r = requests.get(NOMINATIM_URL, params=params, headers=headers)
    if r.status_code == 200:
        results = r.json()
        if not results:
            print("  -> No results found")
        for idx, item in enumerate(results):
            print(f"[{idx}] display_name: {item.get('display_name')}")
            print(f"    lat/lon: {item.get('lat')}, {item.get('lon')}")
            print(f"    type: {item.get('type')}, class: {item.get('class')}")
    else:
        print(f"  -> Error status: {r.status_code}")

query("Francia 250 bis, Puerto Norte, Rosario")
query("Francia bis 250, Puerto Norte, Rosario")
query("Francia 200 bis, Puerto Norte, Rosario")
query("Francia 250, Puerto Norte, Rosario")
query("Francia, Puerto Norte, Rosario")
query("Francia bis, Puerto Norte, Rosario")

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
headers = {"User-Agent": "rosario_avm_geocoder_test"}

def query_freeform(direccion, zona):
    zona_osm = zona
    if zona.lower() == "sexta pellegrini":
        zona_osm = "República de la Sexta"
    elif zona.lower() == "facultades":
        zona_osm = "Rosario Centro"
        
    q = f"{direccion}, {zona_osm}, Rosario, Santa Fe, Argentina"
    print(f"\nQuerying: {q}")
    params = {
        "q": q,
        "format": "jsonv2",
        "limit": 1
    }
    r = requests.get(NOMINATIM_URL, params=params, headers=headers)
    if r.status_code == 200:
        results = r.json()
        if results:
            item = results[0]
            print(f"  FOUND: {item.get('display_name')}")
            print(f"  lat/lon: {item.get('lat')}, {item.get('lon')}")
            return item.get('lat'), item.get('lon')
        else:
            print("  -> NOT FOUND")
    else:
        print(f"  -> Error status: {r.status_code}")
    return None

query_freeform("3 de Febrero 520", "Martin")
query_freeform("Ayacucho 1805", "Sexta Pellegrini")
query_freeform("Vera Mujica 912", "Facultades")
query_freeform("Pellegrini 1200", "Centro")
query_freeform("Entre Ríos 400", "Centro")
query_freeform("Brown 2700", "Centro")

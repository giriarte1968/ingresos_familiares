import json, time, requests

d = json.load(open("propiedades.json", encoding="utf-8"))
prop = [p for p in d["propiedades"] if p.get("id") == 10][0]

address = "Cochabamba 45, Rosario, Santa Fe, Argentina"
try:
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": address, "format": "json", "limit": 1},
        headers={"User-Agent": "valu"},
        timeout=10,
    )
    if r.ok and r.json():
        lat = float(r.json()[0]["lat"])
        lon = float(r.json()[0]["lon"])
        print(f"Address: {address}")
        print(f"Coordinates: ({lat}, {lon})")
        prop["lat"] = lat
        prop["lon"] = lon
        json.dump(d, open("propiedades.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("Saved!")
    else:
        print(f"NOT FOUND: {address}")
except Exception as e:
    print(f"ERROR: {e}")

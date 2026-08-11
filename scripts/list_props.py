import json
d = json.load(open("propiedades.json", "r", encoding="utf-8"))
for p in d["propiedades"]:
    print(f'id={p.get("id")}, name={p.get("nombre","?")}, addr={p.get("address","?")}, lat={p.get("lat")}, lon={p.get("lon")}')

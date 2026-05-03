import json
m = [p for p in json.load(open('propiedades.json'))['propiedades'] if p.get('nombre') == 'Mabel'][0]
print(f"ancla: {m.get('ancla_mas_cercana')}")
print(f"ancla_usd: {m.get('ancla_usd_m2')}")
print(f"lat: {m.get('lat')}")
print(f"lon: {m.get('lon')}")
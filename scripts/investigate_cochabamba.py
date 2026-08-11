import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.geocoder import haversine_distance as haversine

cache_data = json.load(open("cache_scraping.json", "r", encoding="utf-8"))
cache = cache_data.get("propiedades", [])
d = json.load(open("propiedades.json", encoding="utf-8"))
prop = [p for p in d["propiedades"] if p.get("nombre") == "Cochabamba 45"][0]

lat, lon = prop["lat"], prop["lon"]
anio = prop.get("anio_construccion", 0)
dorms = prop.get("dormitorios", 0)
tipo = prop.get("tipo_inmueble", "departamento")

print(f"Subject: year={anio}, dorms={dorms}, tipo={tipo}, lat={lat}, lon={lon}")
print(f"Age window: {anio-10} to {anio+10}")
print()

# Find all venta props within 1000m
matches = []
for p in cache:
    plat = p.get("lat")
    plon = p.get("lon")
    if plat is None or plon is None:
        continue
    if p.get("operacion") != "venta":
        continue
    if (p.get("tipo") or "").lower() != tipo.lower():
        continue
    dist = haversine(lat, lon, plat, plon)
    if dist > 1000:
        continue
    
    pdorms = p.get("dormitorios", 0)
    panio = p.get("antiquity", 0) or 0
    
    # Convert antiquity to year if needed
    if panio > 2000 and panio < 2030:
        pass  # already year
    elif panio > 0 and panio < 100:
        panio = 2026 - panio  # convert antiquity to year
    
    in_age_window = abs(panio - anio) <= 10 if panio > 0 else False
    matches.append({
        "address": p.get("direccion", "?")[:50],
        "dorms": pdorms,
        "year": panio,
        "m2": p.get("m2", 0),
        "dist_m": round(dist),
        "m2_price": p.get("valor_m2", 0),
        "same_dorm": pdorms == dorms,
        "in_age_window": in_age_window,
    })

print(f"Total depto venta within 1000m: {len([m for m in matches if True])}")
print(f"4-dorm within 1000m: {len([m for m in matches if m['same_dorm']])}")
print()

# Show all 4-dorm with their years
four_dorm = [m for m in matches if m["same_dorm"]]
four_dorm.sort(key=lambda x: x["dist_m"])
print("=== 4-DORM COMPARABLES ===")
for m in four_dorm:
    age_flag = "IN_WINDOW" if m["in_age_window"] else "EXCLUDED"
    print(f"  {m['dist_m']}m | {m['address'][:40]:40} | year={m['year']} | m2={m['m2']:.0f} | ${m['m2_price']:.0f}/m2 | {age_flag}")

print()
print(f"4-dorm in age window (1956-1976): {len([m for m in four_dorm if m['in_age_window']])}")

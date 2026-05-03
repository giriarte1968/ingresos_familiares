import json
with open("cache_scraping.json", encoding="utf-8") as f:
    data = json.load(f)

props = data.get("propiedades", [])
with_year = [p for p in props if p.get("anio_construccion")]
print(f"Properties with year: {len(with_year)}")
print(f"---First 10 with year---")
for p in with_year[:10]:
    yr = p.get("anio_construccion")
    addr = p.get("direccion", "")[:40]
    url = p.get("url", "")[:30]
    print(f"  {yr} | {addr} | {url}...")
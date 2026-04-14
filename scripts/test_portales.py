import requests

urls = [
    "https://www.unopropiedades.com.ar",
    "https://www.zeballosinmobiliaria.com",
    "https://properati.com.ar",
    "https://www.urbania.com.ar"
]

for url in urls:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        print(f"{url[:40]}: {r.status_code}")
    except Exception as e:
        print(f"{url[:40]}: Error")
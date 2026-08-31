# -*- coding: utf-8 -*-
"""
scrape_vanzini_ph.py
====================
Extrae los PHs / Casas de Pasillo en venta del sitio Vanzini Propiedades
(https://www.vanzini.com.ar/feed/p.h) y los deja listos para inyectar en
el cache de comparables de Valu (cache_scraping.json).

Fuente:
  - __NEXT_DATA__ embebido en el HTML del feed (contiene: _id, titulo,
    geoLocation[lat,lon], secondSubDivision[barrio], totalSurfaceMax,
    address, addressSlug, propertyType).
  - Precio USD renderizado como "U$D xxx.xxx" en las tarjetas (1:1 con items).

Salida:
  - Lista de dicts con el esquema del cache de comparables de Valu
    (precio, m2, m2_cubiertos, dormitorios, tipo, operacion, moneda,
     direccion, url, valor_m2, fuente, id_propia, lat, lon, zona,
     date_created, date_updated, calle_limpia, numero_limpio,
     antiquity, es_barrio_cerrado, m2_semicubiertos).

Modo de uso:
  python scripts/scrape_vanzini_ph.py [--json salida.json]
  (por defecto imprime en consola; --json escribe a archivo)
"""

import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

FEED_BASE = "https://www.vanzini.com.ar/feed/p.h?orden={orden}&moneda=USD"
ORDENES = ["venta-mayor-precio", "venta-menor-precio", "fecha-actualizacion"]

# Mapeo barrio (secondSubDivision Vanzi) -> zona canónica de Rosario
ZONA_MAP = {
    "centro": "Centro",
    "nuestra señora de lourdes": "Lourdes / Parque Independencia",
    "lourdes": "Lourdes / Parque Independencia",
    "pichincha": "Pichincha",
    "luis agote": "Luis Agote",
    "martin": "Barrio Martin",
    "arroyito": "Arroyito",
    "abasto": "Abasto",
    "refinerias": "Puerto Norte / Refinería",
    "refinería": "Puerto Norte / Refinería",
}


def fetch_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_feed(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  html, re.S)
    if not m:
        return [], []
    data = json.loads(m.group(1))
    items = data["props"]["pageProps"]["initialProperties"]
    prices = re.findall(r'U\$D\s*([\d\.]+)', html)
    return items, prices


def canonical_zone(second_sub):
    key = (second_sub or "").lower().strip()
    for k, v in ZONA_MAP.items():
        if k in key:
            return v
    return second_sub or ""


def scrape_vanzini_ph():
    seen = {}
    for orden in ORDENES:
        try:
            html = fetch_html(FEED_BASE.format(orden=orden))
            items, prices = parse_feed(html)
        except Exception as e:
            print(f"[WARN] orden '{orden}' falló: {e}", file=sys.stderr)
            continue
        for i, it in enumerate(items):
            pid = it.get("_id")
            if not pid:
                continue
            price = prices[i] if i < len(prices) else None
            seen[pid] = (it, price)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    registros = []
    for pid, (it, price) in seen.items():
        try:
            precio = float(price.replace(".", "")) if price else 0.0
        except Exception:
            precio = 0.0
        if precio <= 0:
            print(f"[WARN] item {pid} sin precio; se omite", file=sys.stderr)
            continue

        total = it.get("totalSurfaceMax")
        try:
            m2_total = round(float(total), 2)
        except Exception:
            m2_total = 0.0

        geo = it.get("geoLocation") or {}
        coords = geo.get("coordinates") or []
        lat = coords[0] if len(coords) > 0 else None
        lon = coords[1] if len(coords) > 1 else None

        direccion = str(it.get("address") or "")
        calle_limpia = direccion.split(" ")[0].lower().rstrip(".,") if direccion else ""

        zona = canonical_zone(it.get("secondSubDivision"))

        registro = {
            "precio": precio,
            "m2": m2_total,
            "m2_cubiertos": m2_total,
            "m2_semicubiertos": 0.0,
            "dormitorios": 0,
            "tipo": "Casa de Pasillo",
            "operacion": "venta",
            "moneda": "USD",
            "direccion": direccion,
            "url": f"https://www.vanzini.com.ar/feed/{it.get('addressSlug') or 'p.h'}",
            "valor_m2": round(precio / m2_total, 2) if m2_total else 0.0,
            "fuente": "vanzini_scraping_ph",
            "id_propia": f"vanzini_{pid}",
            "lat": lat,
            "lon": lon,
            "zona": zona or "Rosario",
            "barrio": it.get("secondSubDivision"),
            "ciudad": it.get("firstSubDivision"),
            "es_barrio_cerrado": False,
            "titulo": it.get("publicationTitle"),
            "date_created": now,
            "date_updated": now,
            "calle_limpia": calle_limpia,
            "numero_limpio": None,
            "antiquity": -1,
        }
        registros.append(registro)

    return registros


def main():
    out_path = None
    args = sys.argv[1:]
    if "--json" in args:
        out_path = args[args.index("--json") + 1]

    registros = scrape_vanzini_ph()
    print("=" * 72)
    print(f"VANZINI PH: {len(registros)} pasillos extraídos")
    print("=" * 72)
    for r in registros:
        print(f"  [{r['id_propia']}] {r['barrio']} | {r['m2']:>6}m2 | "
              f"USD {r['precio']:>9,.0f} | {r['direccion'][:45]}")
        print(f"      lat={r['lat']}, lon={r['lon']} | zona='{r['zona']}'")

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(registros, f, ensure_ascii=False, indent=2)
        print(f"\nGuardado en: {out_path}")
    else:
        print("\n--- JSON ---")
        print(json.dumps(registros, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Scraping incremental de Propia.com.ar
- Usa id como proxy de recencia (id > max_id del cache = nueva)
- Dedup por URL y por id_propia
- Guarda en cache_scraping_nuevo.json (NUNCA toca cache_scraping.json)
- Normaliza campos: lat/lon, tipo (inferido del título)
"""

import requests
import json
import time
import os
import re

# ── Config ──
CACHE_EXISTENTE = "cache_scraping.json"
CACHE_NUEVO = "cache_scraping_nuevo.json"
API_BASE = "https://admin.propia.com.ar/items/properties"

PRECIO_MINIMO_VENTA_USD = 5000
PRECIO_MINIMO_ALQUILER_USD = 200
PRECIO_MINIMO_ALQUILER_ARS = 30000
VALOR_M2_MINIMO_VENTA = 300
VALOR_M2_MINIMO_ALQUILER = 2

API_FIELDS = (
    "id,title,slug,price,area,bedrooms,bathrooms,"
    "address,latitude,longitude,operation_id,"
    "antiquity,delivery_year,currency_id,"
    "hide_price,published_on_portal,"
    "date_created"
)


def inferir_tipo(title):
    """Inferir tipo de propiedad desde el título."""
    t = title.lower()
    if "ph" in t.split():
        return "PH"
    if "casa" in t:
        return "Casa"
    if "oficina" in t:
        return "Oficina"
    if "local" in t:
        return "Local Comercial"
    if "terreno" in t or "lote" in t:
        return "Terreno"
    if "departamento" in t or "dpto" in t or "monoambiente" in t:
        return "Departamento"
    return "Departamento"


def cargar_cache_existente():
    """Lee cache existente, retorna (max_id, urls, ids_propia, total)."""
    max_id = 0
    urls = set()
    ids_propia = set()
    total = 0
    if os.path.exists(CACHE_EXISTENTE):
        try:
            with open(CACHE_EXISTENTE, "r", encoding="utf-8") as f:
                data = json.load(f)
            props = data.get("propiedades", [])
            total = len(props)
            for p in props:
                pid = p.get("id_propia")
                if pid and isinstance(pid, (int, float)):
                    pid = int(pid)
                    ids_propia.add(pid)
                    if pid > max_id:
                        max_id = pid
                url = p.get("url", "")
                if url:
                    urls.add(url)
        except Exception as e:
            print("[WARN] Error leyendo cache: %s" % e)
    return max_id, urls, ids_propia, total


def scrapear_propia(max_id, existing_urls, existing_ids, max_pages=30, limit_per_page=50):
    """Llama API Propia, filtra solo nuevas por id > max_id."""
    props = []
    seen_urls = set()
    seen_ids = set()
    pages_fetched = 0
    consecutive_old = 0

    for page in range(1, max_pages + 1):
        params = {
            "limit": limit_per_page,
            "page": page,
            "fields": API_FIELDS,
            "filter": json.dumps({"location_city_id": {"_eq": 1}}),
            "sort": "-id",
        }

        try:
            r = requests.get(API_BASE, params=params, timeout=30)
            if r.status_code != 200:
                params.pop("filter", None)
                r = requests.get(API_BASE, params=params, timeout=30)
                if r.status_code != 200:
                    print("[PROPIA] Error %d en pagina %d, abortando." % (r.status_code, page))
                    break

            data = r.json()
            items = data.get("data", [])
            if not items:
                break

            pages_fetched += 1
            new_in_page = 0

            for item in items:
                item_id = item.get("id")
                if not item_id:
                    continue

                # ── Corte temprano: si el id es menor al max_id, la API no tiene más nuevas ──
                if max_id > 0 and item_id <= max_id:
                    consecutive_old += 1
                    if consecutive_old >= limit_per_page:
                        print("[PROPIA] Pagina %d: corte temprano (%d items viejos seguidos)" % (page, consecutive_old))
                        break
                    continue
                else:
                    consecutive_old = 0

                # ── Dedup por id_propia ──
                if item_id in existing_ids or item_id in seen_ids:
                    continue

                # ── Filtros de calidad ──
                if item.get("hide_price", False):
                    continue
                if not item.get("published_on_portal", False):
                    continue

                slug = item.get("slug", "")
                url = "https://propia.com.ar/propiedad/%s" % slug if slug else ""
                if not url:
                    continue
                if url in existing_urls or url in seen_urls:
                    continue
                seen_urls.add(url)
                seen_ids.add(item_id)

                # ── Precio ──
                price_raw = item.get("price", 0)
                if isinstance(price_raw, str):
                    try:
                        price = float(price_raw.replace(",", ""))
                    except (ValueError, AttributeError):
                        continue
                else:
                    price = float(price_raw or 0)

                area = float(item.get("area", 0) or 0)
                if not price or not area or area <= 0:
                    continue
                if area < 15 or area > 500:
                    continue

                currency_id = item.get("currency_id", 1)
                op_id = item.get("operation_id", {})
                es_venta = op_id == 1

                if es_venta:
                    if currency_id == 1:
                        if price < PRECIO_MINIMO_VENTA_USD:
                            continue
                        precio_usd = price
                    elif currency_id == 2:
                        precio_usd = round(price / 1200, 2)
                        if precio_usd < PRECIO_MINIMO_VENTA_USD:
                            continue
                    else:
                        continue
                else:
                    if currency_id == 1:
                        if price < PRECIO_MINIMO_ALQUILER_USD:
                            continue
                        precio_usd = price
                    elif currency_id == 2:
                        if price < PRECIO_MINIMO_ALQUILER_ARS:
                            continue
                        precio_usd = round(price / 1200, 2)
                    else:
                        continue

                valor_m2 = round(precio_usd / area, 2)
                if es_venta and valor_m2 < VALOR_M2_MINIMO_VENTA:
                    continue
                if not es_venta and valor_m2 < VALOR_M2_MINIMO_ALQUILER:
                    continue

                title = item.get("title", "")
                tipo = inferir_tipo(title)
                operacion = "venta" if es_venta else "alquiler"

                props.append({
                    "precio": precio_usd,
                    "m2": area,
                    "dormitorios": item.get("bedrooms") or 1,
                    "valor_m2": valor_m2,
                    "direccion": item.get("address_to_show") or item.get("address") or title,
                    "fuente": "propia",
                    "operacion": operacion,
                    "zona": "Rosario",
                    "url": url,
                    "lat": item.get("latitude"),
                    "lon": item.get("longitude"),
                    "tipo": tipo,
                    "id_propia": item_id,
                    "moneda": "USD",
                    "antiquity": item.get("antiquity"),
                    "delivery_year": item.get("delivery_year"),
                    "date_created": item.get("date_created"),
                })
                new_in_page += 1

            if consecutive_old >= limit_per_page:
                break

            if new_in_page > 0:
                print("[PROPIA] Pagina %d: %d items, %d nuevas" % (page, len(items), new_in_page))
            time.sleep(0.3)

        except Exception as e:
            print("[PROPIA] Error en pagina %d: %s" % (page, e))
            break

    print("[PROPIA] Total nuevas: %d en %d paginas" % (len(props), pages_fetched))
    return props


def guardar_nuevas(props_nuevas, max_id_existente, total_existente, output_file):
    """Guarda propiedades nuevas en archivo separado."""
    from datetime import datetime
    data = {
        "fecha": datetime.now().isoformat(),
        "status": "incremental_propia",
        "source_file": CACHE_EXISTENTE,
        "source_max_id": max_id_existente,
        "source_total": total_existente,
        "total_nuevas": len(props_nuevas),
        "propiedades": props_nuevas,
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Scraping incremental de Propia.com.ar")
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--output", default=CACHE_NUEVO)
    args = parser.parse_args()

    print("=" * 60)
    print("PROPIA SCRAPER INCREMENTAL")
    print("=" * 60)

    max_id, existing_urls, existing_ids, total = cargar_cache_existente()
    print("Cache actual: %d propiedades" % total)
    print("Max id_propia: %d" % max_id)
    print("URLs existentes: %d" % len(existing_urls))
    print()

    nuevas = scrapear_propia(max_id, existing_urls, existing_ids, max_pages=args.max_pages)

    if not nuevas:
        print("\nNo hay propiedades nuevas.")
        return

    guardar_nuevas(nuevas, max_id, total, args.output)

    print()
    print("=" * 60)
    print("RESULTADO:")
    print("  Nuevas: %d" % len(nuevas))
    print("  Guardadas en: %s" % args.output)
    print("  NO se modifico: %s" % CACHE_EXISTENTE)
    print("=" * 60)

    ventas = sum(1 for p in nuevas if p["operacion"] == "venta")
    alquileres = len(nuevas) - ventas
    print("  Venta: %d" % ventas)
    print("  Alquiler: %d" % alquileres)

    tipos = {}
    for p in nuevas:
        t = p.get("tipo", "?")
        tipos[t] = tipos.get(t, 0) + 1
    print("  Por tipo:")
    for t, c in sorted(tipos.items(), key=lambda x: -x[1]):
        print("    %s: %d" % (t, c))


if __name__ == "__main__":
    main()

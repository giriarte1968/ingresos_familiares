#!/usr/bin/env python3
"""
TAREA-1: Genera nombres legibles para las 386 anclas de Valu.
Usa Nominatim (OSM) para resolver coordenadas a intersecciones de calles.
Rate limit: 1 request/segundo (politica Nominatim).
"""
import json
import time
import requests
import os

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"
HEADERS = {"User-Agent": "ValuApp/1.0 (proyecto valuacion inmobiliaria)"}
DELAY = 1.1


def get_street_from_coords(lat, lon):
    """Obtiene el nombre de la calle mas cercana a unas coordenadas."""
    params = {
        "lat": lat, "lon": lon,
        "format": "json", "zoom": 18, "addressdetails": 1,
    }
    try:
        r = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        if r.status_code == 429:
            time.sleep(5)
            return get_street_from_coords(lat, lon)
        if r.status_code == 200:
            data = r.json()
            addr = data.get("address", {})
            for key in ["road", "pedestrian", "residential", "tertiary",
                        "secondary", "primary", "unclassified"]:
                if key in addr:
                    return addr[key]
    except Exception as e:
        print(f"  Error: {e}")
    return None


def find_cross_street(lat, lon, main_street):
    """Busca la calle cruzada con 1 offset."""
    # Offset ~100m en diagonal para encontrar la otra calle
    street = get_street_from_coords(lat + 0.0007, lon + 0.0007)
    if street and street.lower() != main_street.lower():
        return street
    # Intentar otro offset
    time.sleep(DELAY)
    street = get_street_from_coords(lat - 0.0007, lon - 0.0007)
    if street and street.lower() != main_street.lower():
        return street
    return None


def normalize_street(name):
    """Normaliza nombre de calle para display."""
    if not name:
        return ""
    return " ".join(w.capitalize() for w in name.split())


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    anchors_path = os.path.join(base, "data", "anclas_v7_20260727_164600.json")

    print(f"Leyendo anclas de: {anchors_path}")
    with open(anchors_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    anclas = data["anclas"]
    total = len(anclas)
    print(f"Total anclas: {total}")
    print(f"Tiempo estimado: ~{total * 3 * DELAY / 60:.0f} minutos")
    print("---")

    processed = 0
    for i, a in enumerate(anclas):
        if "nombre_legible" in a:
            processed += 1
            continue

        lat = a["lat"]
        lon = a["lon"]
        main_street = a.get("calle_principal", "")

        print(f"[{i+1}/{total}] {a['id']}: ", end="", flush=True)

        if not main_street:
            a["nombre_legible"] = a["id"].replace("_", " ").title()
            print(f"sin calle -> {a['nombre_legible']}")
            processed += 1
            continue

        # Buscar calle cruzada
        time.sleep(DELAY)
        cross = find_cross_street(lat, lon, main_street)
        main_norm = normalize_street(main_street)

        if cross:
            cross_norm = normalize_street(cross)
            nombre = f"{main_norm} y {cross_norm}"
        else:
            nombre = main_norm

        a["nombre_legible"] = nombre
        print(f"{nombre}")
        processed += 1

        # Guardar progreso cada 50 anclas
        if processed % 50 == 0:
            with open(anchors_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  [Guardado: {processed}/{total}]")

    # Guardar resultado final
    with open(anchors_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("---")
    print(f"Completado: {processed} anclas")
    with_inter = sum(1 for a in anclas if " y " in a.get("nombre_legible", ""))
    print(f"Con interseccion: {with_inter}/{total}")
    print(f"Sin interseccion: {total - with_inter}/{total}")


if __name__ == "__main__":
    main()

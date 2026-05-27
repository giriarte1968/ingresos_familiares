"""
Script batch: valida coordenadas de propiedades en cache contra geocoding textual.
Corrige automáticamente aquellas con discrepancia > MAX_DISCREPANCIA_M.
Ejecución recomendada: después de cada scraping, o bajo demanda.
"""

import json
import os
import sys
import time

# Asegurar que el proyecto está en el path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from parsers.geocoder import validar_coordenadas_contra_direccion

CACHE_FILE = os.path.join(BASE_DIR, "cache_scraping.json")
MAX_DISCREPANCIA_M = 500
SLEEP_INTERVAL = 1.0  # Nominatim rate limit


def validar_cache():
    if not os.path.exists(CACHE_FILE):
        print(f"ERROR: cache no encontrado: {CACHE_FILE}")
        return {"exito": False, "error": "Archivo no encontrado"}

    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        cache = json.load(f)

    propiedades = cache.get('propiedades', [])
    revisados = 0
    corregidos = 0
    errores = 0
    detalles = []

    for p in propiedades:
        direccion = p.get('direccion', '').strip()
        lat = p.get('lat')
        lon = p.get('lon')

        if not direccion or lat is None or lon is None:
            continue

        lat_corregida, lon_corregida, diff_m, accion = validar_coordenadas_contra_direccion(
            direccion, lat, lon, MAX_DISCREPANCIA_M
        )

        revisados += 1

        if accion == "error":
            errores += 1
        elif accion == "corregido":
            p['lat'] = lat_corregida
            p['lon'] = lon_corregida
            corregidos += 1
            detalles.append({
                "direccion": direccion,
                "lat_original": lat,
                "lon_original": lon,
                "lat_corregida": lat_corregida,
                "lon_corregida": lon_corregida,
                "diferencia_m": diff_m
            })
            print(f"CORREGIDO [{corregidos}] {direccion}: {lat},{lon} -> {lat_corregida},{lon_corregida} ({diff_m}m)")

        # Rate limiting para no abusar de Nominatim
        time.sleep(SLEEP_INTERVAL)

    # Guardar cambios
    if corregidos > 0:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    return {
        "exito": True,
        "revisados": revisados,
        "corregidos": corregidos,
        "errores": errores,
        "detalles": detalles
    }


if __name__ == "__main__":
    print("=== Validación de coordenadas contra dirección textual ===")
    print(f"Umbral de discrepancia: {MAX_DISCREPANCIA_M}m")
    print()
    resultado = validar_cache()
    print()
    print(f"Revisados: {resultado['revisados']}")
    print(f"Corregidos: {resultado['corregidos']}")
    print(f"Errores: {resultado['errores']}")
    if resultado['corregidos'] > 0:
        print(f"Ver detalles arriba. Cache actualizado.")
    else:
        print("No se encontraron discrepancias significativas.")

"""
Infomapa Rosario API - Integración con datos catastrales oficiales.

Flujo:
1. Cargar CSV de PHs (rosario_avm_full.csv)
2. Buscar candidato por DIRECCIÓN (calle + número más cercano) — SIEMPRE incluido
3. Buscar top 2 por COORDENADAS como alternativas
4. Obtener imágenes + nomenclatura de la API para cada candidato
5. El analista selecciona manualmente el PH correcto en la UI
"""

import os
import csv
import re
import requests
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

BASE = "https://infomapa.rosario.gov.ar"
API_URL = f"{BASE}/emapa/planos/mensura/buscarPorCarpeta.htm"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CSV_PATH = os.path.join(DATA_DIR, 'rosario_avm_full.csv')


def _extraer_calle_numero(direccion: str):
    """Extrae (calle, numero) de una dirección tipo 'Ayacucho 1805'."""
    if not direccion:
        return None, None
    m = re.search(r'([A-Za-z0-9\u00C0-\u024F\s.]+?)\s+(\d+)$', direccion.strip())
    if m:
        return m.group(1).strip().lower(), int(m.group(2))
    return None, None


def obtener_datos_ph(ph) -> dict:
    """
    Consulta API de Infomapa y retorna imágenes + nomenclatura catastral.
    
    Returns:
        {
            "imagenes": [{"ruta": "...", "url": "..."}, ...],
            "seccion": "9",
            "manzana": "48", 
            "grafico": "11",
        }
        Dict vacío si hay error.
    """
    if not ph:
        return {}
    try:
        resp = requests.post(
            API_URL,
            data={"nroCarpeta": str(ph)},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                entry = data[0]
                imagenes = [
                    {"ruta": img.get("ruta", ""), "url": BASE + img.get("ruta", "")}
                    for img in entry.get("imagenes", []) if img.get("ruta")
                ]
                cat = entry.get("catastrales", [{}])[0] if entry.get("catastrales") else {}
                return {
                    "imagenes": imagenes,
                    "seccion": cat.get("seccion", ""),
                    "manzana": cat.get("manzana", ""),
                    "grafico": cat.get("grafico", ""),
                }
    except Exception as e:
        logger.error(f"[INFOMAPA] Error PH {ph}: {e}")
    return {}


def _cargar_csv() -> list:
    """Carga el CSV de PHs. Retorna lista vacía si no existe."""
    if not os.path.exists(CSV_PATH):
        logger.warning(f"CSV no encontrado: {CSV_PATH}")
        return []
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except Exception as e:
        logger.error(f"Error leyendo CSV: {e}")
        return []


def _match_coordenadas(filas: list, lat: float, lon: float, tol: float = 0.0005) -> list:
    """
    Retorna TODAS las filas del CSV dentro de tolerancia, ordenadas por distancia.
    Cada fila incluye campo extra 'distancia' en grados decimales.
    """
    matches = []
    for row in filas:
        try:
            dl = (lat - float(row.get('latitud', 0))) ** 2
            dn = (lon - float(row.get('longitud', 0))) ** 2
            d = (dl + dn) ** 0.5
            if d <= tol:
                row['distancia'] = d
                matches.append(row)
        except (ValueError, TypeError):
            continue
    matches.sort(key=lambda x: x['distancia'])
    return matches


def _match_por_direccion(filas: list, calle: str, numero: int) -> Optional[Dict]:
    """
    Busca en TODAS las filas del CSV la misma calle + número más cercano.
    No depende de coordenadas, busca por texto de dirección.
    
    Returns:
        La fila con diff num mínima (máx 10 de diferencia) o None.
    """
    mejores = []
    for row in filas:
        csv_calle, csv_num = _extraer_calle_numero(row.get('direccion_nominatim', ''))
        if not csv_calle or not csv_num:
            continue
        if csv_calle != calle and calle not in csv_calle and csv_calle not in calle:
            continue
        diff = abs(csv_num - numero)
        if diff <= 10:
            mejores.append((diff, row))
    if not mejores:
        return None
    mejores.sort(key=lambda x: x[0])
    return mejores[0][1]


def enriquecer_con_infomapa(prop: Dict) -> Optional[Dict]:
    """
    Busca candidatos: 1 por dirección (prioritario) + 2 por coordenadas.
    Luego obtiene imágenes + nomenclatura de la API.
    
    Returns:
        {
            "candidatos": [
                {"ph": "17817", "year": "2010", "direccion_nominatim": "Ayacucho 1805",
                 "seccion": "1", "manzana": "211", "grafico": "22",
                 "distancia": 0.000369, "recomendado": True},
                ...
            ],
            "imagenes_disponibles": {"17817": [{"ruta": "...", "url": "..."}, ...]}
        }
        None si no hay datos.
    """
    lat, lon = prop.get('lat'), prop.get('lon')
    if not lat or not lon:
        logger.info(f"[INFOMAPA] Sin coordenadas para {prop.get('nombre', '?')}")
        return None

    filas = _cargar_csv()
    if not filas:
        return None

    # PASO 1: Top 2 por coordenadas
    coord_candidates = _match_coordenadas(filas, float(lat), float(lon), tol=0.0006)[:2]

    # PASO 2: Candidato por dirección (sobre TODAS las filas del CSV)
    calle, numero = _extraer_calle_numero(prop.get('direccion', ''))
    dir_candidate = None
    if calle and numero:
        dir_candidate = _match_por_direccion(filas, calle, numero)

    # PASO 3: Combinar (máximo 3, sin duplicados)
    candidatos = []
    phs_vistos = set()

    if dir_candidate:
        dir_candidate['recomendado'] = True
        candidatos.append(dir_candidate)
        phs_vistos.add(dir_candidate['ph'])

    for c in coord_candidates:
        if c['ph'] not in phs_vistos and len(candidatos) < 3:
            c['recomendado'] = False
            candidatos.append(c)
            phs_vistos.add(c['ph'])

    if not candidatos:
        logger.info(f"[INFOMAPA] Sin candidatos para ({lat}, {lon})")
        return None

    # PASO 4: Llamar API para imágenes + nomenclatura
    imagenes = {}
    for c in candidatos:
        datos_api = obtener_datos_ph(c['ph'])
        if datos_api.get('imagenes'):
            imagenes[c['ph']] = datos_api['imagenes']
        if not c.get('seccion') and datos_api.get('seccion'):
            c['seccion'] = datos_api['seccion']
        if not c.get('manzana') and datos_api.get('manzana'):
            c['manzana'] = datos_api['manzana']
        if not c.get('grafico') and datos_api.get('grafico'):
            c['grafico'] = datos_api['grafico']

    return {
        "candidatos": candidatos,
        "imagenes_disponibles": imagenes,
    }

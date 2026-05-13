"""
Infomapa Rosario API - Integración con datos catastrales oficiales.

Flujo:
1. Buscar candidatos PH en CSV (rosario_avm_full.csv) por coordenadas
2. Obtener imágenes disponibles de la API para cada PH candidato
3. El analista selecciona manualmente el PH correcto en la UI
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
    m = re.search(r'([A-Za-z\u00C0-\u024F\s.]+?)\s+(\d+)$', direccion.strip())
    if m:
        return m.group(1).strip().lower(), int(m.group(2))
    return None, None


def obtener_url_plano(ph) -> list:
    """
    Consulta API de Infomapa y retorna lista de imágenes disponibles.
    
    Returns:
        [{"ruta": "/emapa/...", "url": "https://infomapa..."}, ...]
        Lista vacía si hay error o no hay imágenes.
    """
    if not ph:
        return []
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
                return [
                    {"ruta": img.get("ruta", ""), "url": BASE + img.get("ruta", "")}
                    for img in data[0].get("imagenes", []) if img.get("ruta")
                ]
    except Exception as e:
        logger.error(f"[INFOMAPA] Error PH {ph}: {e}")
    return []


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


def enriquecer_con_infomapa(prop: Dict) -> Optional[Dict]:
    """
    Busca candidatos PH en CSV por coordenadas, obtiene imágenes de la API.
    
    Returns:
        {
            "candidatos": [
                {"ph": "17817", "year": "2010", "direccion_nominatim": "Ayacucho 1805",
                 "seccion": "1", "manzana": "211", "grafico": "22",
                 "distancia": 0.000369, "recomendado": True},
                ...
            ],
            "imagenes_disponibles": {
                "17817": [{"ruta": "...", "url": "..."}, ...],
                ...
            }
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

    candidatos = _match_coordenadas(filas, float(lat), float(lon), tol=0.0006)
    if not candidatos:
        logger.info(f"[INFOMAPA] Sin candidatos para ({lat}, {lon})")
        return None

    candidatos = candidatos[:3]

    # Determinar recomendado por dirección
    calle, numero = _extraer_calle_numero(prop.get('direccion', ''))
    for c in candidatos:
        c_csv, n_csv = _extraer_calle_numero(c.get('direccion_nominatim', ''))
        c['recomendado'] = (
            c_csv and calle
            and (c_csv == calle or c_csv in calle or calle in c_csv)
            and n_csv and numero
            and abs(n_csv - numero) <= 5
        ) if (calle and numero and c_csv) else False

    phs = [c['ph'] for c in candidatos]
    imagenes = {}
    for ph in phs:
        imgs = obtener_url_plano(ph)
        if imgs:
            imagenes[ph] = imgs

    return {
        "candidatos": candidatos,
        "imagenes_disponibles": imagenes,
    }

"""
Infomapa Rosario API - Integración con datos catastrales oficiales.

Flujo:
1. Buscar PH en CSV local (rosario_avm_full.csv) por coordenadas
2. Llamar a API real de Infomapa con ese PH para obtener URL del plano PDF
"""

import os
import csv
import requests
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

BASE = "https://infomapa.rosario.gov.ar"
API_URL = f"{BASE}/emapa/planos/mensura/buscarPorCarpeta.htm"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CSV_PATH = os.path.join(DATA_DIR, 'rosario_avm_full.csv')


def obtener_url_plano(ph) -> Optional[str]:
    """
    Consulta API de Infomapa y devuelve URL completa del PDF.
    Retorna None si hay error o no existe.
    """
    if not ph:
        return None
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
                imagenes = data[0].get("imagenes", [])
                if imagenes and len(imagenes) > 0:
                    ruta = imagenes[0].get("ruta")
                    if ruta:
                        return BASE + ruta
    except Exception as e:
        logger.error(f"[INFOMAPA] Error buscando PH {ph}: {e}")
    return None


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


def _match_coordenadas(filas, lat: float, lon: float, tol: float = 0.0005) -> Optional[Dict]:
    """Busca fila del CSV más cercana a las coordenadas dadas."""
    mejor = None
    menor = float('inf')
    for row in filas:
        try:
            dl = (lat - float(row.get('latitud', 0))) ** 2
            dn = (lon - float(row.get('longitud', 0))) ** 2
            d = (dl + dn) ** 0.5
            if d < menor and d <= tol:
                menor = d
                mejor = row
        except (ValueError, TypeError):
            continue
    return mejor


def enriquecer_con_infomapa(prop: Dict) -> Optional[Dict]:
    """
    Busca PH del CSV por coordenadas, luego llama API para obtener PDF.
    
    Returns dict con {ph, year, seccion, manzana, grafico, url_plano} o None.
    """
    lat, lon = prop.get('lat'), prop.get('lon')
    if not lat or not lon:
        logger.info(f"[INFOMAPA] Sin coordenadas para {prop.get('nombre', '?')}")
        return None

    filas = _cargar_csv()
    if not filas:
        return None

    match = _match_coordenadas(filas, float(lat), float(lon))
    if not match:
        logger.info(f"[INFOMAPA] Sin match CSV para ({lat}, {lon})")
        return None

    ph = match.get('ph', '')
    if not ph:
        return None

    url_plano = obtener_url_plano(ph)

    return {
        'ph': ph,
        'year': match.get('year', ''),
        'seccion': match.get('seccion', ''),
        'manzana': match.get('manzana', ''),
        'grafico': match.get('grafico', ''),
        'url_plano': url_plano,
    }

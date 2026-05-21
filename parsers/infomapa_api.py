"""
Infomapa Rosario API - Integración con datos catastrales oficiales.

Flujo:
1. Cargar CSV de PHs (rosario_avm_full.csv)
2. Buscar candidato por DIRECCIÓN (misma calle + misma centena + diff ≤ 10)
3. Buscar top 2 por COORDENADAS como alternativas (solo misma calle)
4. Obtener imágenes + nomenclatura de la API para cada candidato
5. El analista selecciona manualmente el PH correcto en la UI

Regla: los candidatos por coordenadas se filtran a la MISMA CALLE que la
propiedad valuada. No se ofrecen planos catastrales de otras calles, aunque
estén a pocos metros. Si no hay candidatos en la misma calle, se informa
ausencia de datos catastrales.
"""

import os
import csv
import re
import requests
import logging
from typing import Optional, Dict

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
    Solo considera candidatos de la MISMA CENTENA (misma cuadra en Rosario).
    
    Returns:
        La fila con diff num mínima (máx 10 de diferencia, misma centena) o None.
    """
    centena_sujeto = (numero // 100) * 100
    mejores = []
    for row in filas:
        csv_calle, csv_num = _extraer_calle_numero(row.get('direccion_nominatim', ''))
        if not csv_calle or not csv_num:
            continue
        if csv_calle != calle and calle not in csv_calle and csv_calle not in calle:
            continue
        # Rosario: la centena del número define la cuadra
        centena_csv = (csv_num // 100) * 100
        if centena_csv != centena_sujeto:
            continue
        diff = abs(csv_num - numero)
        if diff <= 10:
            row['centena_match'] = 'exacta'
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

    # PASO 1: Candidato por dirección (misma calle + misma centena + diff ≤ 10)
    calle, numero = _extraer_calle_numero(prop.get('direccion', ''))
    dir_candidate = None
    if calle and numero:
        dir_candidate = _match_por_direccion(filas, calle, numero)

    # PASO 2: Top 3 por coordenadas (~220m radio) como alternativas
    coord_candidates = _match_coordenadas(filas, float(lat), float(lon), tol=0.002)[:3]

    # Helper: filtrar candidato por coordenadas a la MISMA CALLE
    # (no ofrecer planos de calles diferentes, que serían incorrectos)
    def _misma_calle(row: dict) -> bool:
        if not calle:
            return True  # sin referencia de calle, no filtrar
        csv_calle, _ = _extraer_calle_numero(row.get('direccion_nominatim', ''))
        if not csv_calle:
            return False
        return csv_calle == calle or calle in csv_calle or csv_calle in calle

    # PASO 3: Combinar (máximo 3, sin duplicados)
    candidatos = []
    phs_vistos = set()

    if dir_candidate:
        dir_candidate['recomendado'] = True
        if 'centena_match' not in dir_candidate:
            dir_candidate['centena_match'] = 'exacta'
        candidatos.append(dir_candidate)
        phs_vistos.add(dir_candidate['ph'])

    for c in coord_candidates:
        if c['ph'] not in phs_vistos and len(candidatos) < 3:
            if _misma_calle(c):
                c['recomendado'] = False
                c['centena_match'] = 'coordenadas'
                candidatos.append(c)
                phs_vistos.add(c['ph'])

    # Si quedan menos de 3, buscar más en el pool completo
    if len(candidatos) < 3:
        pool = _match_coordenadas(filas, float(lat), float(lon), tol=0.002)
        for c in pool:
            if c['ph'] not in phs_vistos and len(candidatos) < 3:
                if _misma_calle(c):
                    c['recomendado'] = False
                    c['centena_match'] = 'coordenadas'
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

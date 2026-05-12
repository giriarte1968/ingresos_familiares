"""
Infomapa Rosario API - Integración con datos catastrales oficiales.

Proporciona acceso a:
- Número de PH (carpeta)
- Año de construcción
- Nomenclatura catastral (sección, manzana, gráfico, división)
- Coordenadas
- URL al PDF del plano de mensura

Usa los datos de rosario_avm_full.csv para evitar consultas directas a la API.
"""

import os
import csv
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

INFOMAPA_BASE = "https://infomapa.rosario.gov.ar"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CSV_PATH = os.path.join(DATA_DIR, 'rosario_avm_full.csv')


def construir_url_plano(ph: str, year: any) -> Optional[str]:
    """
    Construye la URL completa del plano PDF usando el formato de Infomapa.
    
    Args:
        ph: Número de carpeta PH (ej: "2874")
        year: Año del plano (ej: "1968" o 1998.0)
    
    Returns:
        URL completa al PDF del plano
    """
    if not ph:
        return None
    
    try:
        year_str = str(int(float(year)))
    except (ValueError, TypeError):
        year_str = "unknown"
    
    return f"{INFOMAPA_BASE}/emapa/servlets/verArchivo?path=pl_mens/{year_str}/c_{ph}.pdf"


def cargar_datos_infomapa() -> List[Dict]:
    """
    Carga los datos de Infomapa desde el CSV local.
    
    Returns:
        Lista de diccionarios con los datos de PHs
    """
    datos = []
    
    if not os.path.exists(CSV_PATH):
        logger.warning(f"CSV de Infomapa no encontrado: {CSV_PATH}")
        return datos
    
    try:
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('ph'):
                    datos.append({
                        'ph': str(row.get('ph', '')),
                        'year': row.get('year', ''),
                        'seccion': row.get('seccion', ''),
                        'manzana': row.get('manzana', ''),
                        'grafico': row.get('grafico', ''),
                        'division': row.get('division', ''),
                        'latitud': row.get('latitud', ''),
                        'longitud': row.get('longitud', ''),
                        'direccion': row.get('direccion_nominatim', '')
                    })
    except Exception as e:
        logger.error(f"Error leyendo CSV de Infomapa: {e}")
    
    logger.info(f"Cargados {len(datos)} registros de Infomapa desde CSV")
    return datos


def buscar_por_coordenadas(lat: float, lon: float, tolerancia: float = 0.0005) -> Optional[Dict]:
    """
    Busca un PH en el CSV usando coordenadas cercanas.
    
    Args:
        lat: Latitud de referencia
        lon: Longitud de referencia
        tolerancia: Tolerancia para encontrar coincidencias (en grados)
    
    Returns:
        Dict con datos del PH o None
    """
    datos = cargar_datos_infomapa()
    
    mejor_match = None
    menor_distancia = float('inf')
    
    for row in datos:
        try:
            lat_row = float(row.get('latitud', 0))
            lon_row = float(row.get('longitud', 0))
            
            if lat_row and lon_row:
                distancia = ((lat - lat_row)**2 + (lon - lon_row)**2)**0.5
                
                if distancia < menor_distancia and distancia <= tolerancia:
                    menor_distancia = distancia
                    mejor_match = row
        except (ValueError, TypeError):
            continue
    
    return mejor_match


def buscar_por_direccion(direccion: str) -> Optional[Dict]:
    """
    Busca un PH en el CSV usando la dirección.
    
    Args:
        direccion: Dirección a buscar
    
    Returns:
        Dict con datos del PH o None
    """
    if not direccion:
        return None
    
    datos = cargar_datos_infomapa()
    
    direccion_lower = direccion.lower().strip()
    
    for row in datos:
        dir_row = row.get('direccion', '').lower().strip()
        if dir_row and direccion_lower in dir_row or dir_row in direccion_lower:
            return row
    
    return None


def parsear_nomenclatura(nomenclatura: str) -> Dict[str, str]:
    """
    Parsea la nomenclatura catastral en componentes.
    
    Formato esperado: "01-01-01-0001-000-000" (Sección-Manzana-Grafico-División)
    
    Returns:
        Dict con 'seccion', 'manzana', 'grafico', 'division'
    """
    result = {'seccion': '', 'manzana': '', 'grafico': '', 'division': ''}
    
    if not nomenclatura:
        return result
    
    partes = nomenclatura.replace('-', ' ').split()
    if len(partes) >= 4:
        result['seccion'] = partes[0].zfill(2) if len(partes[0]) <= 2 else partes[0]
        result['manzana'] = partes[1].zfill(3) if len(partes[1]) <= 3 else partes[1]
        result['grafico'] = partes[2].zfill(4) if len(partes[2]) <= 4 else partes[2]
        result['division'] = partes[3].zfill(3) if len(partes[3]) <= 3 else partes[3]
    
    return result


def consultar_infomapa_por_carpeta(nro_carpeta: str) -> Optional[Dict[str, Any]]:
    """
    Consulta la API de Infomapa Rosario por número de carpeta PH.
    
    Args:
        nro_carpeta: Número de carpeta PH (ej: "2874")
    
    Returns:
        Dict con datos del catastro o None si hay error
    """
    try:
        url = f"{INFOMAPA_BASE}/emapa/planos/mensura/buscarPorCarpeta.htm"
        data = {'nroCarpeta': nro_carpeta}
        
        response = requests.post(url, data=data, timeout=15, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        
        if response.status_code == 200:
            json_data = response.json()
            
            if isinstance(json_data, list) and len(json_data) > 0:
                return _procesar_respuesta_infomapa(json_data[0])
            elif isinstance(json_data, dict) and json_data.get('carpeta'):
                return _procesar_respuesta_infomapa(json_data)
            else:
                logger.warning(f"Infomapa: No se encontraron datos para carpeta {nro_carpeta}")
                return None
        else:
            logger.warning(f"Infomapa API respondió con código {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("Timeout consultando Infomapa API")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión con Infomapa: {e}")
        return None
    except Exception as e:
        logger.error(f"Error consultando Infomapa: {e}")
        return None


def consultar_infomapa_por_nomenclatura(seccion: str, manzana: str, grafico: str, 
                                         division: str = "000") -> Optional[Dict[str, Any]]:
    """
    Consulta la API de Infomapa Rosario por nomenclatura catastral.
    NOTA: El endpoint principal es buscarPorCarpeta. Este método intenta
    buscar por nomenclatura si está disponible.
    
    Args:
        seccion: Sección (01-99)
        manzana: Manzana (001-999)
        grafico: Gráfico (0001-9999)
        division: División (000-999)
    
    Returns:
        Dict con datos del catastro o None si hay error
    """
    logger.warning("Búsqueda por nomenclatura no disponible directamente. Use número de carpeta PH.")
    return None


def consultar_infomapa_por_coordenadas(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Consulta la API de Infomapa Rosario por coordenadas geográficas.
    NOTA: El endpoint principal es buscarPorCarpeta. Este método intenta
    buscar por coordenadas si está disponible.
    
    Args:
        lat: Latitud
        lon: Longitud
    
    Returns:
        Dict con datos del catastro o None si hay error
    """
    logger.warning("Búsqueda por coordenadas no disponible directamente. Use número de carpeta PH.")
    return None


def _procesar_respuesta_infomapa(data: Dict) -> Dict[str, Any]:
    """
    Procesa la respuesta cruda de la API de Infomapa.
    
    Normaliza los campos al formato esperado por VPP.
    """
    if not data:
        return {}
    
    resultado = {}
    
    resultado['seccion'] = data.get('seccion', '')
    resultado['manzana'] = data.get('manzana', '')
    resultado['grafico'] = data.get('grafico', '')
    resultado['division'] = data.get('division', '')
    
    resultado['numero'] = data.get('numero', '')
    resultado['expediente'] = data.get('expediente', '')
    resultado['fechaIns'] = data.get('fechaIns', '')
    resultado['tipo'] = data.get('tipo', 'MENSURA Y DIVISION PH')
    
    profesionales = data.get('profesionales', [])
    if isinstance(profesionales, str):
        resultado['profesionales'] = [profesionales] if profesionales else []
    elif isinstance(profesionales, list):
        resultado['profesionales'] = profesionales
    else:
        resultado['profesionales'] = []
    
    imagenes = data.get('imagenes', [])
    if imagenes and isinstance(imagenes, list):
        primera_imagen = imagenes[0]
        ruta_pdf = primera_imagen.get('ruta', '')
        resultado['url_plano_pdf'] = construir_url_plano(ruta_pdf)
    else:
        resultado['url_plano_pdf'] = None
    
    catastrales = data.get('catastrales', [])
    if catastrales and isinstance(catastrales, list):
        cat = catastrales[0]
        resultado['nomenclatura'] = {
            'seccion': cat.get('secc', ''),
            'manzana': cat.get('mza', ''),
            'grafico': cat.get('graf', ''),
            'division': cat.get('div', '')
        }
    else:
        resultado['nomenclatura'] = {'seccion': '', 'manzana': '', 'grafico': '', 'division': ''}
    
    resultado['superficie'] = data.get('superficie', 0)
    resultado['domicilio'] = data.get('domicilio', '')
    
    return resultado


def consultar_infomapa_desde_propiedad(propiedad: Dict) -> Optional[Dict[str, Any]]:
    """
    Consulta Infomapa usando datos de la propiedad.
    
    Busca en el CSV local (rosario_avm_full.csv) usando coordenadas o dirección.
    
    Args:
        propiedad: Dict con datos de la propiedad
    
    Returns:
        Dict con datos catastrales o None
    """
    lat = propiedad.get('lat')
    lon = propiedad.get('lon')
    direccion = propiedad.get('direccion', '')
    
    ph_data = None
    
    if lat and lon:
        ph_data = buscar_por_coordenadas(float(lat), float(lon))
    
    if not ph_data and direccion:
        ph_data = buscar_por_direccion(direccion)
    
    if ph_data:
        ph = ph_data.get('ph', '')
        year = ph_data.get('year', '')
        
        url_pdf = construir_url_plano(ph, year)
        
        return {
            'ph': ph,
            'year': year,
            'seccion': ph_data.get('seccion', ''),
            'manzana': ph_data.get('manzana', ''),
            'grafico': ph_data.get('grafico', ''),
            'division': ph_data.get('division', ''),
            'url_plano_pdf': url_pdf,
            'direccion': ph_data.get('direccion', ''),
            'fuente': 'csv'
        }
    
    logger.info(f"No se encontró datos de Infomapa para: {propiedad.get('nombre', 'propiedad')}")
    return None


ESTUDIOS_PREMIUM = [
    'ESTUDIO ASOCIADO',
    'MOR',
    'FUNDAR',
    'OBRING',
    'MSR',
    'BARRE',
    'DUPONT',
    'GROSS',
    'LONGHI',
    'PAT',
    'CIA',
    'CAFI',
    'CEDIR',
]


def es_estudio_premium(profesional: str) -> bool:
    """
    Determina si un profesional belongs a un estudio premium.
    
    Args:
        profesional: Nombre del profesional/estudio
    
    Returns:
        True si es estudio premium
    """
    if not profesional:
        return False
    
    profesional_upper = profesional.upper()
    return any(estudio in profesional_upper for estudio in ESTUDIOS_PREMIUM)


def calcular_bonus_estudio_premium(profesionales: List[str]) -> float:
    """
    Calcula el bonus por estudios premium detectados.
    
    Args:
        profesionales: Lista de nombres de profesionales
    
    Returns:
        Bonus a aplicar (0.0 a 0.05)
    """
    if not profesionales:
        return 0.0
    
    estudios_premium_encontrados = [p for p in profesionales if es_estudio_premium(p)]
    
    if len(estudios_premium_encontrados) >= 2:
        return 0.05
    elif len(estudios_premium_encontrados) == 1:
        return 0.03
    
    return 0.0


def generar_texto_profesionales(profesionales: List[str]) -> str:
    """
    Genera texto legible para mostrar los profesionales.
    
    Args:
        profesionales: Lista de nombres de profesionales
    
    Returns:
        String formateado
    """
    if not profesionales:
        return "No informado"
    
    if len(profesionales) == 1:
        return profesionales[0]
    
    if len(profesionales) == 2:
        return f"{profesionales[0]} y {profesionales[1]}"
    
    return ", ".join(profesionales[:-1]) + " y " + profesionales[-1]
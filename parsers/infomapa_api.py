"""
Infomapa Rosario API - Integración con datos catastrales oficiales.

Proporciona acceso a:
- Profesionales (Arquitecto/Ingeniero)
- Número de Plano
- Fecha de Inscripción
- Expediente
- URL al PDF del plano de mensura
- Nomenclatura catastral (sección, manzana, gráfico, división)
"""

import requests
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

INFOMAPA_BASE = "https://mapa.rosario.gob.ar"


def construir_url_plano(ruta: str) -> Optional[str]:
    """
    Construye la URL completa del plano PDF.
    
    Args:
        ruta: Ruta relativa del archivo (ej: 'pl_mens/2009/161583.pdf')
    
    Returns:
        URL completa o None si la ruta es inválida
    """
    if not ruta:
        return None
    
    if ruta.startswith('http'):
        return ruta
    
    return f"{INFOMAPA_BASE}/emapa/servlets/verArchivo?path={ruta}"


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


def consultar_infomapa_por_nomenclatura(seccion: str, manzana: str, grafico: str, 
                                         division: str = "000") -> Optional[Dict[str, Any]]:
    """
    Consulta la API de Infomapa Rosario por nomenclatura catastral.
    
    Args:
        seccion: Sección (01-99)
        manzana: Manzana (001-999)
        grafico: Gráfico (0001-9999)
        division: División (000-999)
    
    Returns:
        Dict con datos del catastro o None si hay error
    """
    try:
        url = f"{INFOMAPA_BASE}/emapa/servlets/buscarPorNomenclatura"
        params = {
            'seccion': seccion,
            'manzana': manzana,
            'grafico': grafico,
            'division': division
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return _procesar_respuesta_infomapa(data)
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


def consultar_infomapa_por_coordenadas(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Consulta la API de Infomapa Rosario por coordenadas geográficas.
    
    Args:
        lat: Latitud
        lon: Longitud
    
    Returns:
        Dict con datos del catastro o None si hay error
    """
    try:
        url = f"{INFOMAPA_BASE}/emapa/servlets/buscarPorCoordenadas"
        params = {'lat': lat, 'lon': lon}
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return _procesar_respuesta_infomapa(data)
        else:
            logger.warning(f"Infomapa API respondió con código {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error consultando Infomapa por coordenadas: {e}")
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
    
    Intenta usar nomenclatura catastral primero, luego coordenadas.
    
    Args:
        propiedad: Dict con datos de la propiedad
    
    Returns:
        Dict con datos catastrales o None
    """
    nomenclatura = propiedad.get('nomenclatura_catastral', '')
    
    if nomenclatura:
        parsed = parsear_nomenclatura(nomenclatura)
        return consultar_infomapa_por_nomenclatura(
            parsed['seccion'],
            parsed['manzana'],
            parsed['grafico'],
            parsed['division']
        )
    
    lat = propiedad.get('lat')
    lon = propiedad.get('lon')
    
    if lat and lon:
        return consultar_infomapa_por_coordenadas(lat, lon)
    
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
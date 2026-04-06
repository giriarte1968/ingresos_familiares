import streamlit as st
import pandas as pd
import re
from datetime import datetime
import os
import io
import numpy as np
from PIL import Image
import requests
from urllib.parse import quote
import time
import json
import unicodedata
import calendar
import uuid

from subpagos import extraer_subpagos, generar_id

# Archivo de datos (ruta absoluta)
DATOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datos.json')

# Estructura de datos:
# {
#   "activos": [
#     {"id": 1, "tipo": "fondo_mutuo", "nombre": "...", ...},
#     {"id": 2, "tipo": "propiedad", "nombre": "...", ...}
#   ],
#   "meses": {
#     "2026-02": {
#       "ingresos_bancarios": [...],
#       "ganancia_fondos": 1041053,
#       "plusvalia_propiedades": 0,
#       "ajustes": [...]
#     }
#   }
# }


def cargar_datos():
    """Carga datos desde JSON"""
    try:
        if os.path.exists(DATOS_FILE):
            with open(DATOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error cargando datos: {e}")
    return {'activos': [], 'meses': {}}


def guardar_datos(datos, silent=False):
    """Guarda datos a JSON y actualiza session state"""
    try:
        # Contar egresos que se van a guardar
        total_egresos = 0
        for mes, mes_data in datos.get('meses', {}).items():
            cant = len(mes_data.get('egresos', []))
            total_egresos += cant
        
        # LOG: quién está llamando a guardar_datos
        import traceback
        stack = traceback.extract_stack()
        caller = stack[-2]  # Quien llamó a guardar_datos
        print(f"[GUARDAR] Llamado desde {caller.filename}:{caller.lineno} en {caller.name}")
        print(f"[GUARDAR] Total egresos a guardar: {total_egresos}")
        
        # Si estamos guardando 0 egresos y ya había datos, NO guardar
        if total_egresos == 0:
            import os
            if os.path.exists(DATOS_FILE):
                with open(DATOS_FILE, 'r', encoding='utf-8') as f:
                    datos_disco = json.load(f)
                total_disco = 0
                for mes, mes_data in datos_disco.get('meses', {}).items():
                    total_disco += len(mes_data.get('egresos', []))
                if total_disco > 0:
                    print(f"[GUARDAR] ⚠️ BLOQUEADO: Intentando guardar 0 egresos pero disco tiene {total_disco}")
                    return  # NO sobreescribir
        
        with open(DATOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        if 'datos' in st.session_state:
            st.session_state.datos = datos
        
        print(f"[GUARDAR] ✅ Guardado OK: {total_egresos} egresos")
    except Exception as e:
        print(f"Error guardando datos: {e}")


_paddle_reader = None

def get_paddle_reader():
    global _paddle_reader
    if _paddle_reader is None:
        import paddleocr
        _paddle_reader = paddleocr.PaddleOCR(use_angle_cls=True, lang='es', show_log=False)
    return _paddle_reader


try:
    import pymupdf
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

_ocr_reader = None

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(['es', 'en'], gpu=False)
    return _ocr_reader


@st.cache_data(ttl=86400*7)  # Cache por 7 días
def buscar_comercio_en_web(nombre_comercio, ciudad="Rosario Argentina"):
    """Busca información de un comercio en DuckDuckGo y analiza múltiples resultados"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Búsqueda con contexto geográfico
        busqueda = f"{nombre_comercio} {ciudad}"
        url = f"https://html.duckduckgo.com/html/?q={quote(busqueda)}"
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, 0, None, None
        
        html = response.text
        
        # Extraer títulos (hasta 5 resultados)
        titulos = re.findall(
            r'<a class="result__a"[^>]*>(.+?)</a>', 
            html, re.IGNORECASE
        )[:5]
        
        # Extraer snippets/descripciones
        snippets = re.findall(
            r'<a class="result__snippet"[^>]*>(.+?)</a>', 
            html, re.IGNORECASE
        )[:5]
        
        # Limpiar HTML de los textos
        def limpiar_html(texto):
            texto = re.sub(r'<[^>]+>', ' ', texto)
            texto = texto.replace('&amp;', '&').replace('&quot;', '"')
            texto = texto.replace('&#x27;', "'").replace('&lt;', '<')
            texto = texto.replace('&gt;', '>').replace('&nbsp;', ' ')
            return ' '.join(texto.split()).strip()
        
        titulos = [limpiar_html(t) for t in titulos]
        snippets = [limpiar_html(s) for s in snippets]
        
        # Combinar todo el texto encontrado
        texto_completo = ' '.join(titulos + snippets).lower()
        
        if not texto_completo.strip():
            return None, 0, None, None
        
        # Mapeo exhaustivo de palabras clave a categorías
        MAPEO_WEB = {
            # Comercios - Gastronomía
            ('comercios', 'restaurant'): [
                'restaurant', 'restaurante', 'resto', 'pizza', 'pizzeria', 
                'pizzería', 'burger', 'hamburgues', 'parrilla', 'grill',
                'bar ', 'pub ', 'cerveceria', 'cervecería', 'comida',
                'gastronomia', 'gastronomía', 'cocina', 'sushi',
                'empanada', 'lomiteria', 'lomitería', 'rotiseria',
                'rotisería', 'fast food', 'delivery', 'cafeteria',
                'cafetería', 'coffee', 'brunch', 'bistro', 'cantina',
                'bodegon', 'bodegón', 'tenedor libre'
            ],
            ('comercios', 'supermercado'): [
                'supermercado', 'hiper', 'hipermercado', 'autoservicio',
                'mayorista', 'minorista', 'almacen', 'almacén',
                'market', 'grocery', 'alimentos', 'comestibles',
                'fiambreria', 'fiambrería', 'dietética', 'dietetica',
                'productos alimenticios'
            ],
            ('comercios', 'farmacia'): [
                'farmacia', 'farmacéutica', 'farmaceutica', 'drogueria',
                'droguería', 'medicamento', 'perfumeria', 'perfumería',
                'cosmetic', 'salcobrand'
            ],
            ('comercios', 'combustible'): [
                'estacion de servicio', 'estación de servicio',
                'combustible', 'nafta', 'gasoil', 'gnc', 'shell',
                'ypf', 'axion', 'oil', 'petro', 'refinor', 'puma energy'
            ],
            ('comercios', 'indumentaria'): [
                'ropa', 'indumentaria', 'textil', 'calzado', 'zapateria',
                'zapatería', 'zapato', 'vestir', 'moda', 'fashion',
                'remera', 'pantalon', 'pantalón', 'camisa', 'campera',
                'jean', 'deportiva', 'outfit', 'boutique', 'tienda de ropa',
                'confeccion', 'confección', 'talles', 'sastreria',
                'sastrería', 'uniformes', 'lenceria', 'lencería'
            ],
            ('comercios', 'panaderia'): [
                'panaderia', 'panadería', 'panificadora', 'bakery',
                'facturas', 'medialunas', 'pasteleria', 'pastelería',
                'confiteria', 'confitería', 'tortas', 'dulces'
            ],
            ('comercios', 'carniceria'): [
                'carniceria', 'carnicería', 'carnes', 'frigorífico',
                'frigorifico', 'polleria', 'pollería', 'chacinado',
                'embutido'
            ],
            ('comercios', 'ferreteria'): [
                'ferreteria', 'ferretería', 'herramienta', 'tornilleria',
                'tornillería', 'bulonera', 'herraje', 'cerrajeria',
                'cerrajería'
            ],
            ('comercios', 'pintureria'): [
                'pintureria', 'pinturería', 'pintura', 'pinturas',
                'revestimiento', 'impermeabilizante', 'latex', 'esmalte',
                'color', 'colorimetria'
            ],
            ('comercios', 'bazar'): [
                'bazar', 'regaleria', 'regalería', 'regalo', 'menaje',
                'hogar', 'decoracion', 'decoración', 'deco ',
                'artículos para el hogar', 'articulos para el hogar',
                'parrilla', 'asado', 'accesorio para parrilla',
                'artículos de parrilla', 'articulos de parrilla',
                'quincho', 'carbón', 'carbon', 'leña', 'accesorios cocina'
            ],
            ('comercios', 'electronica'): [
                'electronica', 'electrónica', 'tecnologia', 'tecnología',
                'celular', 'telefono', 'teléfono', 'computadora',
                'notebook', 'informatica', 'informática', 'gaming',
                'audio', 'video', 'tv ', 'televisor', 'consola'
            ],
            ('comercios', 'heladeria'): [
                'heladeria', 'heladería', 'helado', 'helados',
                'freddo', 'persicco', 'ice cream'
            ],
            ('comercios', 'verduleria'): [
                'verduleria', 'verdulería', 'fruteria', 'frutería',
                'fruta', 'verdura', 'orgánico', 'organico'
            ],
            ('comercios', 'optica'): [
                'optica', 'óptica', 'lentes', 'anteojos', 'gafas',
                'oftalmolog', 'vision', 'visión', 'contacto'
            ],
            ('comercios', 'veterinaria'): [
                'veterinaria', 'veterinario', 'mascota', 'pet shop',
                'petshop', 'animal', 'canino', 'felino', 'alimento mascota'
            ],
            ('comercios', 'libreria'): [
                'libreria', 'librería', 'papeleria', 'papelería',
                'libro', 'editorial', 'cuaderno', 'artículos escolares'
            ],
            ('comercios', 'muebleria'): [
                'mueble', 'muebleria', 'mueblería', 'amoblamientos',
                'colchon', 'colchón', 'sommier', 'carpinteria',
                'carpintería', 'aberturas'
            ],
            ('comercios', 'automotor'): [
                'gomeria', 'gomería', 'neumatico', 'neumático', 'taller',
                'mecanica', 'mecánica', 'repuesto', 'autoparte',
                'lubricentro', 'alineacion', 'alineación', 'balanceo',
                'chapa', 'pintura automotor', 'lavadero'
            ],
            
            # Servicios
            ('servicios', 'salud'): [
                'clinica', 'clínica', 'hospital', 'sanatorio', 'medico',
                'médico', 'doctor', 'salud', 'diagnostico', 'diagnóstico',
                'laboratorio', 'análisis', 'analisis', 'imagenes',
                'imágenes', 'radiologia', 'radiología', 'ecografia',
                'ecografía', 'odontolog', 'dental', 'kinesio',
                'fisioterapia', 'psicolog', 'nutricion', 'nutrición',
                'prepaga', 'obra social', 'gamma', 'instituto medico'
            ],
            ('servicios', 'educacion'): [
                'universidad', 'facultad', 'colegio', 'escuela',
                'instituto', 'curso', 'capacitacion', 'capacitación',
                'idioma', 'academia', 'taller educativo', 'jardin',
                'jardín', 'guarderia', 'guardería'
            ],
            ('servicios', 'servicios_publicos'): [
                'edesur', 'edenor', 'edemsa', 'epe ', 'empresa provincial de energía',
                'metrogas', 'gasnor', 'litoral gas', 'gas natural',
                'agua', 'aguas santafesinas', 'aysa', 'assa',
                'luz', 'electricidad', 'energía eléctrica', 'energia electrica',
                'gas ', 'servicio público', 'servicio publico'
            ],
            ('servicios', 'telecomunicaciones'): [
                'movistar', 'claro', 'personal', 'telecom', 'telefonica',
                'telefónica', 'internet', 'wifi', 'fibra optica',
                'fibra óptica', 'flow', 'cablevision', 'cablevisión',
                'directv', 'telecentro', 'iplan'
            ],
            ('servicios', 'seguros'): [
                'seguro', 'aseguradora', 'sancor', 'la segunda',
                'san cristobal', 'san cristóbal', 'mapfre', 'zurich',
                'rivadavia', 'federacion patronal', 'federación patrimonial',
                'meridional', 'prevencion', 'prevención'
            ],
            ('servicios', 'seguridad'): [
                'adt', 'alarma', 'monitoreo', 'vigilancia', 'seguridad',
                'prosegur', 'securitas', 'camaras', 'cámaras'
            ],
            ('servicios', 'estacionamiento'): [
                'estacionamiento', 'parking', 'cochera', 'garage',
                'playa de estacionamiento'
            ],
            ('servicios', 'peluqueria'): [
                'peluqueria', 'peluquería', 'barberia', 'barbería',
                'salon de belleza', 'salón de belleza', 'estetica',
                'estética', 'spa', 'uñas', 'manicura'
            ],
            ('servicios', 'transporte'): [
                'uber', 'cabify', 'didi', 'taxi', 'remis', 'remise',
                'transporte', 'flete', 'mudanza', 'encomienda'
            ],
            ('servicios', 'alquiler'): [
                'alquiler', 'inmobiliaria', 'propiedad', 'inquilino',
                'arrendamiento', 'locacion', 'locación'
            ],
            ('servicios', 'gimnasio'): [
                'gimnasio', 'gym', 'fitness', 'crossfit', 'pilates',
                'yoga', 'natacion', 'natación', 'club deportivo',
                'entrenamiento'
            ],
            ('servicios', 'bancos'): [
                'banco', 'comision bancaria', 'comisión bancaria',
                'mantenimiento cuenta', 'cargo bancario',
                'cargo por servicio'
            ],
            
            # Impuestos
            ('impuestos', 'impuestos'): [
                'municipalidad', 'gobierno', 'ministerio', 'afip', 'arca',
                'dgi', 'api', 'rentas', 'tasa', 'impuesto', 'tributo',
                'monotributo', 'iibb', 'ingresos brutos', 'tgi',
                'contribucion', 'contribución', 'canon', 'sellado',
                'patente', 'inmobiliario', 'automotor impuesto'
            ],
            
            # Suscripciones
            ('suscripciones', 'streaming'): [
                'netflix', 'spotify', 'disney', 'amazon prime', 'hbo',
                'paramount', 'star+', 'youtube premium', 'apple tv',
                'crunchyroll', 'deezer', 'tidal'
            ],
            ('suscripciones', 'software'): [
                'google one', 'icloud', 'dropbox', 'microsoft 365',
                'adobe', 'chatgpt', 'canva', 'suscripcion', 'suscripción'
            ],
        }
        
        # Buscar en todos los textos encontrados
        mejor_categoria = None
        mejor_subcategoria = None
        mejor_puntaje = 0
        
        for (categoria, subcategoria), palabras in MAPEO_WEB.items():
            puntaje = 0
            for palabra in palabras:
                if palabra in texto_completo:
                    peso = len(palabra.split())
                    puntaje += peso
            
            if puntaje > mejor_puntaje:
                mejor_puntaje = puntaje
                mejor_categoria = categoria
                mejor_subcategoria = subcategoria
        
        if mejor_puntaje > 0:
            confianza = min(0.95, 0.60 + (mejor_puntaje * 0.10))
            resultado_texto = f"{mejor_categoria}/{mejor_subcategoria} (score:{mejor_puntaje})"
            return resultado_texto, confianza, mejor_categoria, mejor_subcategoria
        
        return None, 0, None, None
        
    except Exception as e:
        print(f"Error buscando comercio: {e}")
        return None, 0, None, None


@st.cache_data(ttl=86400*30)
def buscar_comercio_cuit_online(nombre_comercio):
    """Busca un comercio en CUIT Online (datos AFIP) para obtener su actividad económica"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        url = f"https://www.cuitonline.com/search?q={quote(nombre_comercio)}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None, 0, None, None
        
        html = response.text
        
        actividad = ''
        
        act_match = re.search(r'(?:actividad|act\.?\s*principal)[:\s]*([^<\n]+)', html, re.IGNORECASE)
        if act_match:
            actividad = act_match.group(1).strip().lower()
        
        if not actividad:
            detalle_match = re.search(r'href="(/detalle/[^"]+)"', html)
            if detalle_match:
                url_detalle = f"https://www.cuitonline.com{detalle_match.group(1)}"
                resp_detalle = requests.get(url_detalle, headers=headers, timeout=10)
                if resp_detalle.status_code == 200:
                    html_detalle = resp_detalle.text
                    act_match = re.search(r'(?:actividad|act\.?\s*principal)[:\s]*([^<\n]+)', html_detalle, re.IGNORECASE)
                    if act_match:
                        actividad = act_match.group(1).strip().lower()
        
        if not actividad:
            return None, 0, None, None
        
        MAPEO_ACTIVIDADES_AFIP = {
            ('comercios', 'combustible'): ['combustible', 'nafta', 'gasoil', 'estacion de servicio', 'estación de servicio', 'lubricante', 'gnc'],
            ('comercios', 'supermercado'): ['supermercado', 'hipermercado', 'autoservicio', 'almacen', 'almacén', 'comestible', 'alimento', 'minimercado', 'venta al por menor de alimentos'],
            ('comercios', 'farmacia'): ['farmacia', 'farmacéutic', 'farmaceutic', 'medicamento', 'drogueria', 'droguería', 'productos medicinales'],
            ('comercios', 'restaurant'): ['restaurant', 'gastronomia', 'gastronomía', 'comida', 'bar ', 'cafeteria', 'cafetería', 'servicio de comidas', 'elaboracion de comidas'],
            ('comercios', 'indumentaria'): ['indumentaria', 'ropa', 'textil', 'calzado', 'vestimenta', 'confeccion', 'confección', 'prendas de vestir'],
            ('comercios', 'ferreteria'): ['ferreteria', 'ferretería', 'herramienta', 'herraje', 'artículos de ferretería'],
            ('comercios', 'pintureria'): ['pintureria', 'pinturería', 'pintura', 'revestimiento'],
            ('comercios', 'panaderia'): ['panaderia', 'panadería', 'panificacion', 'panificación', 'productos de panaderia'],
            ('comercios', 'carniceria'): ['carniceria', 'carnicería', 'carne', 'frigorífico', 'frigorifico', 'matadero'],
            ('comercios', 'electronica'): ['electronica', 'electrónica', 'computacion', 'computación', 'informatica', 'informática', 'electrodomestico'],
            ('comercios', 'libreria'): ['libreria', 'librería', 'papeleria', 'papelería', 'artículos de librería'],
            ('comercios', 'veterinaria'): ['veterinaria', 'mascota', 'animal', 'pet shop', 'alimento para animales'],
            ('servicios', 'salud'): ['salud', 'medic', 'clinic', 'clínic', 'hospital', 'sanatorio', 'laboratorio', 'diagnóstico', 'diagnostico', 'odontolog', 'kinesio'],
            ('servicios', 'educacion'): ['educacion', 'educación', 'enseñanza', 'escuela', 'colegio', 'universidad', 'instituto'],
            ('servicios', 'seguros'): ['seguro', 'aseguradora', 'reaseguro', 'prevision'],
            ('servicios', 'transporte'): ['transporte', 'logistica', 'logística', 'flete', 'encomienda', 'mudanza'],
            ('impuestos', 'impuestos'): ['recaudacion', 'recaudación', 'impositiv', 'tributari', 'fiscal'],
        }
        
        mejor_cat = None
        mejor_subcat = None
        mejor_puntaje = 0
        
        for (categoria, subcategoria), palabras in MAPEO_ACTIVIDADES_AFIP.items():
            puntaje = 0
            for palabra in palabras:
                if palabra in actividad:
                    puntaje += len(palabra.split())
            if puntaje > mejor_puntaje:
                mejor_puntaje = puntaje
                mejor_cat = categoria
                mejor_subcat = subcategoria
        
        if mejor_puntaje > 0:
            confianza = min(0.98, 0.80 + (mejor_puntaje * 0.05))
            return actividad, confianza, mejor_cat, mejor_subcat
        
        return actividad, 0.3, None, None
        
    except Exception as e:
        print(f"Error buscando en CUIT Online: {e}")
        return None, 0, None, None


CATEGORIAS_WEB = {
    'comercios': {
        'supermercado': ['supermercado', 'hiper', 'atomo', 'changomas', 'carrefour', 'walmart', 'jumbo', 'disco', 'vea', 'coto'],
        'restaurant': ['restaurant', 'resto', 'pizza', 'pizzer', 'burger', 'mcdonald', 'burger king', 'kfc', 'fast food', 'comida rapida'],
        'farmacia': ['farmacia', 'farmacity', 'fv', 'disfarma', 'social'],
        'combustible': ['estacion', 'shell', 'ypf', 'axion', 'oil', 'petro', ' refinery'],
        'indumentaria': ['ropa', 'indumentaria', 'zara', 'h&m', 'nike', 'adidas', 'local'],
        'electronica': ['tecnologia', 'samsung', 'lg', 'sony', 'musimundo', 'garbarino', 'fravega'],
        'gimnasio': ['gimnasio', 'gym', 'fitness', 'club'],
        'panaderia': ['panader', 'bakery', 'pan'],
        'carniceria': ['carniceria', 'carnes', 'polleria'],
        'pintureria': ['pinturer', 'pintura', 'color'],
        'veterinaria': ['veterinaria', 'vet', 'mascota', 'pet'],
        'optica': ['optica', 'lentes', 'vision'],
        'bazar': ['bazar', 'regaleria', 'regalos'],
        'heladeria': ['heladeria', 'helado', 'freddo', 'persicco'],
        'cafeteria': ['cafeteria', 'coffee', 'cafe', 'starbucks'],
        'verduleria': ['verduleria', 'fruteria', 'fruta', 'verdura'],
        'almacen': ['almacen', 'market', 'kiosko', 'kiosco'],
    },
    'servicios': {
        'salud': ['clinica', 'hospital', 'sanatorio', 'doctor', 'medico', 'salud', 'gamma', 'diagnostico', 'laboratorio', 'imagenes'],
        'educacion': ['universidad', 'facultad', 'colegio', 'escuela', 'curso', 'educacion', 'idiomas'],
        'transporte': ['uber', 'cabify', 'taxi', 'remis', 'transporte', 'combis', ' colectivos'],
        'bancos': ['banco', 'galicia', 'santander', 'bbva', 'macro', 'provincia', 'nacion'],
        'servicios_publicos': ['edesur', 'edenor', 'metrogas', 'gas', 'agua', 'luz', 'telefono', 'internet', 'movistar', 'claro', 'personal'],
        'seguros': ['seguro', 'san cristobal', 'prevencion', 'meridional'],
        'alquiler': ['alquiler', 'alquilo', 'propiedad'],
        'estacionamiento': ['estacionamiento', 'parking', 'cochera'],
        'peluqueria': ['peluqueria', 'barberia', 'salon', 'belleza'],
    },
    'impuestos': ['afip', 'dgi', 'impuesto', 'rentas', 'municipalidad', 'tasa'],
    'suscripciones': ['netflix', 'spotify', 'disney', 'amazon', 'hbo', 'paramount', 'suscripcion'],
}


# Cache para precios de Binance
@st.cache_data(ttl=3600)
def obtener_precio_binance(simbolo, fecha=None):
    """Obtiene el precio de cierre de USDT en la moneda especificada"""
    try:
        url = f"https://api.binance.com/api/v3/klines"
        params = {
            'symbol': simbolo,
            'interval': '1d',
            'limit': 1
        }
        
        if fecha:
            timestamp = int(datetime.strptime(fecha, '%Y-%m-%d').timestamp() * 1000)
            params['startTime'] = timestamp
            params['endTime'] = timestamp + 86400000  # Un día después
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data and len(data) > 0:
            return float(data[0][4])  # Precio de cierre
        return None
    except Exception as e:
        print(f"Error obteniendo precio {simbolo}: {e}")
        return None


@st.cache_data(ttl=86400)
def obtener_usdt_ars_binance(fecha=None):
    """Obtiene USDT/ARS de CryptoCompare API (más preciso que CoinGecko)"""
    try:
        if not fecha:
            url = 'https://min-api.cryptocompare.com/data/pricemulti?fsyms=USDT&tsyms=ARS'
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'USDT' in data:
                    return data['USDT']['ARS']
            return None
        
        # Parsear fecha
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            try:
                fecha_obj = datetime.strptime(fecha, '%Y-%m')
                fecha_obj = fecha_obj.replace(day=28)
            except ValueError:
                print(f"Formato de fecha no reconocido: {fecha}")
                return None
        
        timestamp = int(fecha_obj.timestamp())
        url = f'https://min-api.cryptocompare.com/data/v2/histoday?fsym=USDT&tsym=ARS&limit=1&toTs={timestamp}'
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'Data' in data and 'Data' in data['Data'] and len(data['Data']['Data']) > 0:
                return data['Data']['Data'][0]['close']
        return None
    except Exception as e:
        print(f"Error obteniendo USDT/ARS: {e}")
        return None


@st.cache_data(ttl=86400)
def obtener_precios_historicos(fecha=None):
    """Obtiene USDT/CLP de CoinGecko y USDT/ARS de CryptoCompare"""
    try:
        usd_clp = None
        usdt_ars = None
        
        if not fecha:
            return None, None
        
        # Determinar el formato de fecha y crear objeto datetime
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            try:
                fecha_obj = datetime.strptime(fecha, '%Y-%m')
                # Si es solo año-mes, usar el último día del mes
                fecha_obj = fecha_obj.replace(day=28)
            except ValueError:
                print(f"Formato de fecha no reconocido: {fecha}")
                return None, None
        
        # USDT/CLP desde CoinGecko
        fecha_cg = fecha_obj.strftime('%d-%m-%Y')
        url = f'https://api.coingecko.com/api/v3/coins/tether/history?date={fecha_cg}&localization=false'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'market_data' in data:
                usd_clp = data['market_data']['current_price'].get('clp')
        
        # USDT/ARS desde CryptoCompare
        usdt_ars = obtener_usdt_ars_binance(fecha)
        
        return usd_clp, usdt_ars
    except Exception as e:
        print(f"Error obteniendo precios: {e}")
        return None, None


@st.cache_data(ttl=86400)
def obtener_usdt_clp(fecha=None):
    """Obtiene el precio de USDT en CLP usando CoinGecko API"""
    clp, _ = obtener_precios_historicos(fecha)
    return clp


# Valor USD/CLP - El usuario puede ingresarlo manualmente en la UI
if 'usd_clp' not in st.session_state:
    # Intentar obtener de CoinGecko al iniciar
    st.session_state.usd_clp = obtener_usdt_clp() or 900.0


def convertir_clp_a_ars(monto_clp, fecha):
    """Convierte un monto en CLP a ARS usando precios históricos"""
    try:
        # Obtener USDT/CLP y USDT/ARS históricos para la misma fecha
        usd_clp, usdt_ars = obtener_precios_historicos(fecha)
        
        # Si no se puede obtener el precio histórico, usar el actual
        if not usd_clp:
            usd_clp = st.session_state.usd_clp
        if not usdt_ars:
            usdt_ars = obtener_usdt_ars_binance()  # Precio actual
        
        if usdt_ars and usd_clp:
            # ARS = (CLP / USD_CLP) * USDT_ARS
            monto_ars = (monto_clp / usd_clp) * usdt_ars
            return monto_ars, usd_clp, usdt_ars
        return None, None, None
    except Exception as e:
        print(f"Error en conversión: {e}")
        return None, None, None


def extraer_texto_pdf(archivo, password=None):
    """Extrae texto de un PDF usando PyMuPDF"""
    if not PDF_AVAILABLE:
        return None
    
    try:
        pdf_bytes = archivo.read()
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        
        # Si está encriptado y hay password, intentar desbloquear
        if doc.is_encrypted and password:
            doc.authenticate(password)
        elif doc.is_encrypted and not password:
            # PDF encriptado, no se puede leer
            st.error("El PDF está encriptado. Ingresa la password para desbloquearlo.")
            return None
        
        texto = ""
        for page in doc:
            texto += page.get_text() + "\n"
        doc.close()
        return texto
    except Exception as e:
        # Posiblemente password incorrecta
        if "invalid" in str(e).lower() or "authentication" in str(e).lower():
            st.error("Password incorrecta. Intenta de nuevo.")
        else:
            st.error(f"Error al leer PDF: {e}")
        return None


def extraer_texto_imagen(archivo):
    """Extrae texto de una imagen usando EasyOCR"""
    if not EASYOCR_AVAILABLE:
        return None
    
    try:
        imagen = Image.open(archivo)
        img_array = np.array(imagen)
        
        reader = get_ocr_reader()
        resultados = reader.readtext(img_array)
        
        texto = ""
        for (_, text, _) in resultados:
            texto += text + " "
        
        return texto
    except Exception as e:
        st.error(f"Error al leer imagen: {e}")
        return None


def extraer_fondos_mutuos(archivo, password=None):
    """Extrae fondos mutuos de un PDF de Santander Chile"""
    if not PDF_AVAILABLE:
        return None, None, None
    
    try:
        pdf_bytes = archivo.read()
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        
        if doc.is_encrypted and password:
            doc.authenticate(password)
        elif doc.is_encrypted and not password:
            st.error("El PDF está encriptado. Ingresa la password.")
            return None, None, None
        
        texto = ""
        for page in doc:
            texto += page.get_text() + "\n"
        doc.close()
        
        lines = texto.split('\n')
        
        usd_clp, usdt_ars = None, None
        
        # Buscar la fecha en el PDF (formato: Hasta : XX/XX/XXXX)
        fecha_encontrada = None
        for linea in lines:
            if 'Hasta' in linea:
                match = re.search(r'Hasta\s*:\s*(\d{2})/(\d{2})/(\d{4})', linea)
                if match:
                    fecha_encontrada = f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
                    break
        
        if fecha_encontrada:
            usd_clp, usdt_ars = obtener_precios_historicos(fecha_encontrada)
        
        if not usd_clp:
            usd_clp = obtener_usdt_clp()
        if not usdt_ars:
            usdt_ars = obtener_usdt_ars_binance()
        
        # Mapeo de líneas: (nombre, linea_inicial, linea_final, moneda)
        # Initial: 34,44,53,62 (CLP), 76,85 (USD)
        # Final: 37,47,56,65 (CLP), 79,88 (USD)
        fondos_data = [
            ('AHORRO MEDIANO PLAZO', 34, 37, 'CLP'),
            ('BONOS NACIONALES', 44, 47, 'CLP'),
            ('GESTION ACTIVA AGRESIVA', 53, 56, 'CLP'),
            ('GO ACC GLOBALES ESG', 62, 65, 'CLP'),
            ('EQUILIBRIO DOLAR', 76, 79, 'USD'),
            ('MONEY MARKET DOLAR USD', 85, 88, 'USD'),
        ]
        
        fondos = []
        for nombre, line_ini, line_fin, moneda in fondos_data:
            linea_ini = lines[line_ini]
            linea_fin = lines[line_fin]
            
            if moneda == 'CLP':
                match_ini = re.search(r'\$([0-9]+\.[0-9]+\.[0-9]+)', linea_ini)
                match_fin = re.search(r'\$([0-9]+\.[0-9]+\.[0-9]+)', linea_fin)
                val_ini = float(match_ini.group(1).replace('.', '')) if match_ini else 0
                val_fin = float(match_fin.group(1).replace('.', '')) if match_fin else 0
            else:  # USD
                match_ini = re.search(r'US\$([0-9.]+),([0-9]+)', linea_ini)
                match_fin = re.search(r'US\$([0-9.]+),([0-9]+)', linea_fin)
                val_ini = float(match_ini.group(1).replace('.', '') + '.' + match_ini.group(2)) if match_ini else 0
                val_fin = float(match_fin.group(1).replace('.', '') + '.' + match_fin.group(2)) if match_fin else 0
            
            # Calcular ganancia en moneda original
            ganancia = val_fin - val_ini
            
            # Convertir ganancia a ARS
            if moneda == 'CLP':
                ganancia_ars = (ganancia / usd_clp) * usdt_ars if usd_clp and usdt_ars else 0
            else:
                ganancia_ars = ganancia * usdt_ars if usdt_ars else 0
            
            # Valor final en ARS (para mostrar total)
            if moneda == 'CLP':
                valor_final_ars = (val_fin / usd_clp) * usdt_ars if usd_clp and usdt_ars else 0
            else:
                valor_final_ars = val_fin * usdt_ars if usdt_ars else 0
            
            fondos.append({
                'nombre': nombre,
                'moneda': moneda,
                'valor_inicial': val_ini,
                'valor_final': val_fin,
                'ganancia': ganancia,
                'valor_final_ars': valor_final_ars,
                'ganancia_ars': ganancia_ars,
                'fecha': fecha_encontrada,
                'tasas': f"USDT/CLP: {usd_clp:.2f}, USDT/ARS: {usdt_ars:.2f}" if usd_clp and usdt_ars else None
            })
        
        # Calcular totales
        total_ars = sum(f['valor_final_ars'] for f in fondos)
        total_ganancia_ars = sum(f['ganancia_ars'] for f in fondos)
        
        return fondos, total_ars, fecha_encontrada, total_ganancia_ars
        
    except Exception as e:
        st.error(f"Error al leer fondos mutuos: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None


def convertir_monto_argentino(valor):
    """Convierte monto formato argentino a float: 260.000,00 -> 260000.00"""
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    valor_str = str(valor).strip()
    if not valor_str:
        return 0.0
    # Formato argentino: 260.000,00 -> 260000.00
    valor_limpio = valor_str.replace('.', '').replace(',', '.')
    try:
        return float(valor_limpio)
    except:
        return 0.0


def extraer_movimientos_excel(archivo, banco='galicia'):
    """Extrae movimientos de un archivo Excel - retorna lista de diccionarios"""
    try:
        if banco == 'galicia' or 'galicia' in banco.lower():
            from parsers.galicia_excel import extraer_movimientos_galicia_excel
            return extraer_movimientos_galicia_excel(archivo)

        # Para otros bancos: lógica genérica
        movimientos = []
        df = pd.read_excel(archivo, sheet_name=0)
        columnas = df.columns.tolist()

        col_fecha = None
        col_desc = None
        col_credito = None

        for col in columnas:
            col_lower = col.lower() if isinstance(col, str) else ''
            if 'fecha' in col_lower:
                col_fecha = col
            elif 'desc' in col_lower or 'movimiento' in col_lower:
                col_desc = col
            elif 'crédito' in col_lower or 'abono' in col_lower:
                col_credito = col

        if col_credito:
            for _, row in df.iterrows():
                monto = convertir_monto_argentino(row.get(col_credito, 0))
                if monto > 0:
                    fecha = str(row.get(col_fecha, '')) if col_fecha else ''
                    desc = str(row.get(col_desc, '')).strip() if col_desc else ''
                    movimientos.append({
                        'fecha': fecha,
                        'descripcion': desc[:150],
                        'monto': monto,
                        'monto_ars': None,
                        'banco': banco,
                        'categoria': detectar_categoria(desc),
                        'tasas': None
                    })

        return movimientos

    except Exception as e:
        print(f"Error al leer Excel: {e}")
        import traceback
        traceback.print_exc()
        return []

st.set_page_config(page_title="Ingresos Familiares", layout="wide")

# Cargar datos desde JSON al iniciar
datos_iniciales = cargar_datos()

if 'movimientos' not in st.session_state:
    st.session_state.movimientos = datos_iniciales.get('movimientos', [])

if 'activos' not in st.session_state:
    st.session_state.activos = datos_iniciales.get('activos', [])

if 'usuarios' not in st.session_state:
    st.session_state.usuarios = ['Usuario 1', 'Usuario 2', 'Usuario 3']

BANCO_PATTERNS = {
    'galicia': ['CRÉDITO', 'ACREDITACIÓN', 'ABONO', 'neto', 'haberes'],
    'santander_chile': ['DEPÓSITO', 'ABONO', 'TRANSFERENCIA RECIBIDA'],
    'icbc': ['ACREDITACIÓN', 'CR', 'DEPÓSITO'],
    'mercadopago': ['Entrada', 'RECIBIDO', 'COBRO', '+'],
    'bbva': ['ABONO', 'DEPÓSITO', 'CRÉDITO'],
}

CATEGORIAS = {
    'sueldo': ['sueldo', 'haberes', 'neto', 'remuneración', 'salario', 'nómina'],
    'alquiler': ['alquiler', 'renta', 'inquilino', 'cobro alquiler'],
    'intereses': ['interés', 'rendimiento', 'ganancia', 'fondo mutuo', 'renta'],
    'inversion': ['dividendo', 'acción', 'bono', 'plazo fijo', 'valorización'],
    'transferencia': ['transferencia', 'depósito', 'entrada', 'recibido'],
    'otro': [],
}


def detectar_banco(texto):
    texto_lower = texto.lower()
    for banco, keywords in BANCO_PATTERNS.items():
        for kw in keywords:
            if kw.lower() in texto_lower:
                return banco
    return 'otro'


def detectar_categoria(descripcion):
    desc_lower = descripcion.lower()
    for cat, palabras in CATEGORIAS.items():
        for palabra in palabras:
            if palabra in desc_lower:
                return cat
    return 'otro'


def extraer_montos(texto):
    """Extrae montos en diferentes formatos: $1.000, 1.000.000, 1000000"""
    montos = []
    
    # Formato con $: $1.000, $1.000.000
    patron_dolar = r'\$[\d.,]+'
    matches = re.findall(patron_dolar, texto)
    for m in matches:
        valor = m.replace('$', '').replace('.', '').replace(',', '.')
        try:
            montos.append(float(valor))
        except:
            pass
    
    # Formato chileno sin $: 1.000.000 (puntos como separador de miles)
    # Usar lookahead/lookbehind para números con formato de miles
    patron_chileno = r'(?<!\d)\d{1,3}\.\d{3}(?:\.\d{3})*(?!\d)'
    matches = re.findall(patron_chileno, texto)
    for m in matches:
        valor = m.replace('.', '')
        try:
            montos.append(float(valor))
        except:
            pass
    
    # Formato simple: 1000000 o 1000,50
    patron_simple = r'(?<!\d)(\d{4,7})(?:,(\d{2}))?(?!\d)'
    matches = re.findall(patron_simple, texto)
    for m in matches:
        if m[1]:
            valor = f"{m[0]}.{m[1]}"
        else:
            valor = m[0]
        try:
            montos.append(float(valor))
        except:
            pass
    
    return montos


def extraer_fechas(texto):
    patrones = [
        r'\d{2}/\d{2}/\d{4}',   # 25/02/2026
        r'\d{2}-\d{2}-\d{4}',   # 25-02-2026
        r'\d{4}/\d{2}/\d{2}',   # 2026/02/25
        r'\d{2}/\d{2}',          # 25/02 (sin año)
    ]
    fechas = []
    for patron in patrones:
        matches = re.findall(patron, texto)
        for m in matches:
            for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d', '%d/%m']:
                try:
                    if fmt == '%d/%m':
                        fecha = datetime.strptime(m, fmt)
                        fecha = fecha.replace(year=datetime.now().year)
                    else:
                        fecha = datetime.strptime(m, fmt)
                    fechas.append(fecha)
                    break
                except:
                    pass
    return fechas


def parsear_texto(texto):
    movimientos = []
    lineas = texto.split('\n')
    
    es_santander = 'santander' in texto.lower() or 'cartola' in texto.lower()
    
    INGRESO_KEYWORDS = [
        'crédito', 'credito', 'acredit', 'abono', 'depósito', 'deposito',
        'entrada', 'recibido', 'cobro', 'haberes', 'sueldo', 'neto',
        'remuneración', 'renta', 'alquiler', 'interés', 'interes',
        'rendimiento', 'ganancia', 'dividendo', 'fondo mutuo',
        'valorización', 'incremento', 'cobrado', 'pago recibido',
        'transferencia recibida', 'depósito recibido', 'depósito a la vista',
        'deposito', 'deposit', 'abonos', 'pago proveedor'
    ]
    
    GASTO_KEYWORDS = [
        'pago a', 'transf a',
        'debito', 'débito',
        'compra', 'extracción', 'extraccion', 'retiro', 'cargo', 'comisión',
        'comision', 'impuesto', 'servicio', 'factura', 'suscripción', 'suscripcion',
        'movimiento', 'salida', 'pagado', 'a pagar', 'cheque', 'cheques',
        'mantencion', 'mantención', 'com.mant'
    ]
    
    # Para Santander: procesar líneas con FECHA + siguientes líneas para montos
    if es_santander:
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            linea_lower = linea.lower()
            
            # Buscar línea con fecha
            fechas = extraer_fechas(linea)
            if not fechas:
                i += 1
                continue
            
            # Verificar si es gasto: tiene "transf a" o "pago a"
            tiene_transf_enviada = 'transf a' in linea_lower or 'pago a' in linea_lower
            
            # Verificar si es ingreso
            es_ingreso = any(kw in linea_lower for kw in INGRESO_KEYWORDS)
            
            # Para Santander Chile: el monto puede estar en siguientes líneas
            if tiene_transf_enviada:
                i += 1
                continue
            
            if not es_ingreso:
                i += 1
                continue
            
            # Buscar monto en líneas siguientes (puede estar 1-3 líneas después)
            monto_encontrado = None
            for j in range(1, 5):
                if i + j >= len(lineas):
                    break
                sig_linea = lineas[i + j]
                montos_sig = extraer_montos(sig_linea)
                if montos_sig:
                    # Tomar el monto válido (> 1000, no muy grande para ser saldo)
                    monto_valido = [m for m in montos_sig if m > 1000]
                    if monto_valido:
                        monto_encontrado = min(monto_valido)  # El abono es menor que el saldo
                        break
            
            if monto_encontrado:
                fecha_str = fechas[0].strftime('%Y-%m-%d')
                resultado = convertir_clp_a_ars(monto_encontrado, fecha_str)
                
                monto_ars = monto_encontrado
                usdt_clp, usdt_ars = None, None
                if resultado[0]:
                    monto_ars = resultado[0]
                    usdt_clp = resultado[1]
                    usdt_ars = resultado[2]
                
                # Guardar el monto en ARS como monto principal (para mostrar y totalizar)
                movimientos.append({
                    'fecha': fecha_str,
                    'descripcion': linea[:150],
                    'monto': monto_ars,  # Valor en ARS para mostrar
                    'monto_original_clp': monto_encontrado,  # Guardar CLP original
                    'banco': 'santander_chile',
                    'categoria': detectar_categoria(linea),
                    'tasas': f"USDT CLP: {usdt_clp}, USDT ARS: {usdt_ars}" if usdt_clp else None
                })
            
            i += 1
        
        return movimientos
    
    # Para otros bancos: lógica original
    for linea in lineas:
        if not linea.strip():
            continue
            
        linea_lower = linea.lower()
        
        monto = extraer_montos(linea)
        fecha = extraer_fechas(linea)
        
        if not monto or not fecha:
            continue
        
        es_gasto = any(kw in linea_lower for kw in GASTO_KEYWORDS)
        if es_gasto:
            continue
        
        es_ingreso = any(kw in linea_lower for kw in INGRESO_KEYWORDS)
        tiene_mas = '+' in linea
        
        if es_ingreso or tiene_mas:
            monto_max = max(monto)
            
            if monto_max > 0:
                fecha_str = fecha[0].strftime('%Y-%m-%d')
                
                movimientos.append({
                    'fecha': fecha_str,
                    'descripcion': linea[:150],
                    'monto': monto_max,
                    'monto_ars': None,
                    'banco': detectar_banco(linea),
                    'categoria': detectar_categoria(linea),
                })
    
    return movimientos


def main():
    st.title("Gestor de Ingresos Familiares")
    
    # Inicializar datos en session state si no existen
    if 'datos' not in st.session_state:
        st.session_state.datos = cargar_datos()
    
    # Selector de mes
    meses_disponibles = list(st.session_state.datos.get('meses', {}).keys())
    if not meses_disponibles:
        meses_disponibles = ['2026-02']  # Mes por defecto
    
    # Ordenar meses
    meses_disponibles = sorted(meses_disponibles)
    
    st.sidebar.header("Periodo")
    mes_seleccionado = st.sidebar.selectbox(
        "Seleccionar Mes",
        meses_disponibles,
        index=len(meses_disponibles) - 1
    )
    
    # Agregar nuevo mes desde el sidebar
    with st.sidebar.expander("+ Agregar Período"):
        _anios = list(range(datetime.now().year, 1999, -1))
        _meses_nombres = [
            (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
            (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
            (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre")
        ]
        _sb_anio = st.selectbox("Año", _anios, key="sb_nuevo_anio")
        _sb_mes_num = st.selectbox(
            "Mes", [m[0] for m in _meses_nombres],
            format_func=lambda x: dict(_meses_nombres)[x],
            key="sb_nuevo_mes_num"
        )
        _nuevo_mes = f"{_sb_anio}-{_sb_mes_num:02d}"
        st.caption(f"Período: {_nuevo_mes}")
        if st.button("Crear Período", key="sb_crear_mes_btn"):
            _datos_disco = cargar_datos()
            if _nuevo_mes not in _datos_disco.get('meses', {}):
                _datos_disco.setdefault('meses', {})[_nuevo_mes] = {
                    'ingresos_bancarios': [],
                    'egresos': [],
                    'ganancia_fondos': 0,
                    'plusvalia_propiedades': 0,
                    'ajustes': []
                }
                # Escritura directa al JSON (bypass del guard de 0 egresos)
                with open(DATOS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(_datos_disco, f, ensure_ascii=False, indent=2)
                st.session_state.datos = _datos_disco
                st.sidebar.success(f"✅ {_nuevo_mes} creado")
                st.rerun()
            else:
                st.sidebar.warning("El período ya existe")

    # Menú principal
    menu = st.sidebar.selectbox(
        "Menú",
        ["Dashboard", "Cargar Extracto", "Cargar Fondos Mutuos", "Movimientos", "Egresos", "Propiedades", "Activos", "Ajustes", "Reportes", "Exportar"]
    )
    
    if menu == "Dashboard":
        mostrar_dashboard(mes_seleccionado)
    elif menu == "Cargar Extracto":
        cargar_extracto(mes_seleccionado)
    elif menu == "Cargar Fondos Mutuos":
        cargar_fondos_mutuos(mes_seleccionado)
    elif menu == "Movimientos":
        mostrar_movimientos(mes_seleccionado)
    elif menu == "Egresos":
        mostrar_egresos()
    elif menu == "Propiedades":
        mostrar_propiedades(mes_seleccionado)
    elif menu == "Activos":
        mostrar_activos()
    elif menu == "Ajustes":
        mostrar_ajustes(mes_seleccionado)
    elif menu == "Reportes":
        from ui.reportes import mostrar_reportes
        mostrar_reportes(mes_seleccionado)
    elif menu == "Exportar":
        exportar_datos()


def mostrar_dashboard(mes):
    st.header(f"Dashboard - {mes}")
    
    datos = st.session_state.datos
    mes_data = datos.get('meses', {}).get(mes, {
        'ingresos_bancarios': [],
        'ganancia_fondos': 0,
        'plusvalia_propiedades': 0,
        'ajustes': []
    })
    
    # Obtener tasas de cambio para el mes
    usd_clp, usdt_ars = obtener_precios_historicos(mes)
    if not usd_clp:
        usd_clp = 900  #默认值
    if not usdt_ars:
        usdt_ars = 1500  #默认值
    
    # Convertir ingresos bancarios a ARS
    def convertir_a_ars(movimiento):
        monto = movimiento.get('monto', 0)
        # Si ya tiene monto_original_clp, es porque viene de Santander Chile en CLP
        if 'monto_original_clp' in movimiento and movimiento['monto_original_clp']:
            clp = movimiento['monto_original_clp']
            return (clp / usd_clp) * usdt_ars
        # Si tiene campo banco y es ARS (Galicia), ya está en ARS
        elif movimiento.get('banco') == 'galicia':
            return monto  # Ya está en ARS
        else:
            return monto  # Por defecto asume ARS
    
    # Calcular totales del mes (todos en ARS)
    total_ingresos_bancarios = sum(convertir_a_ars(m) for m in mes_data.get('ingresos_bancarios', []))
    
    # Ganancia fondos mutuos (del mes) - ya viene en ARS
    total_ganancia_fondos = mes_data.get('ganancia_fondos', 0)
    
    # Plusvalía propiedades (del mes)
    total_plusvalia = mes_data.get('plusvalia_propiedades', 0)
    
    # Ajustes (pueden ser en ARS o CLP)
    def convertir_ajuste_a_ars(ajuste):
        monto = ajuste.get('monto', 0)
        moneda = ajuste.get('moneda', 'ARS')
        if moneda == 'CLP':
            return (monto / usd_clp) * usdt_ars
        elif moneda == 'USD':
            return monto * usdt_ars
        return monto
    
    total_ajustes = sum(convertir_ajuste_a_ars(a) for a in mes_data.get('ajustes', []))
    
    # Plusvalía ADRs (del mes)
    total_plusvalia_adrs = mes_data.get('plusvalia_adrs', 0)
    
    # Total del mes
    total_mes = total_ingresos_bancarios + total_ganancia_fondos + total_plusvalia + total_plusvalia_adrs + total_ajustes
    
    # Mostrar métricas
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    col1.metric("Ingresos Bancarios", f"${total_ingresos_bancarios:,.0f}")
    col2.metric("Gan. Fondos Mutuos", f"${total_ganancia_fondos:,.0f}", 
                delta=f"${total_ganancia_fondos:,.0f}")
    col3.metric("Plusv. Propiedades", f"${total_plusvalia:,.0f}", 
                delta=f"${total_plusvalia:,.0f}")
    col4.metric("Plusv. ADRs", f"${total_plusvalia_adrs:,.0f}", 
                delta=f"${total_plusvalia_adrs:,.0f}")
    col5.metric("Ajustes", f"${total_ajustes:,.0f}", 
                delta=f"${total_ajustes:,.0f}")
    col6.metric("TOTAL MES", f"${total_mes:,.0f}", 
                delta=f"${total_mes:,.0f}")
    
    # Mostrar tasas usadas
    st.caption(f"Tasas usadas: USDT/CLP: {usd_clp:.2f}, USDT/ARS: {usdt_ars:.2f}")
    
    st.divider()
    
    # Resumen de activos
    st.subheader("Resumen de Activos")
    activos = datos.get('activos', [])
    
    if activos:
        fondos = [a for a in activos if a.get('tipo') == 'fondo_mutuo']
        propiedades = [a for a in activos if a.get('tipo') == 'propiedad']
        
        col1, col2, col3 = st.columns(3)
        total_fondos = sum(a.get('valor_final_ars', 0) for a in fondos)
        total_props = sum(a.get('valor_tasacion_ars', 0) for a in propiedades)
        
        col1.metric("Total Fondos Mutuos", f"${total_fondos:,.0f}")
        col2.metric("Total Propiedades", f"${total_props:,.0f}")
        col3.metric("Total Activos", f"${total_fondos + total_props:,.0f}")
    
    # Detalles por categoría
    if activos:
        activos = datos.get('activos', [])
        propiedades = [a for a in activos if a.get('tipo') == 'propiedad']
        if propiedades:
            st.subheader("Propiedades")
            df_props = pd.DataFrame(propiedades)
            cols_to_show = ['nombre', 'zona', 'm2', 'valor_tasacion_ars']
            available = [c for c in cols_to_show if c in df_props.columns]
            if available:
                st.dataframe(df_props[available])


def mostrar_movimientos(mes):
    st.header(f"Movimientos - {mes}")
    
    datos = st.session_state.datos
    ingresos = datos.get('meses', {}).get(mes, {}).get('ingresos_bancarios', [])
    
    if ingresos:
        # Obtener tasas de cambio
        usd_clp, usdt_ars = obtener_precios_historicos(mes)
        if not usd_clp:
            usd_clp = 900
        if not usdt_ars:
            usdt_ars = 1500
        
        # Función para convertir a ARS
        def convertir_a_ars(movimiento):
            monto = movimiento.get('monto', 0)
            if 'monto_original_clp' in movimiento and movimiento['monto_original_clp']:
                clp = movimiento['monto_original_clp']
                return (clp / usd_clp) * usdt_ars
            return monto  # Ya está en ARS
        
        # Convertir todos los montos a ARS para mostrar
        for m in ingresos:
            m['monto_ars'] = convertir_a_ars(m)
        
        df = pd.DataFrame(ingresos)
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            if 'banco' in df.columns:
                bancos = ["Todos"] + list(df['banco'].unique().tolist())
                filtro_banco = st.selectbox("Filtrar por banco", bancos)
            else:
                filtro_banco = "Todos"
        with col2:
            if 'categoria' in df.columns:
                categorias = ["Todos"] + list(df['categoria'].unique().tolist())
                filtro_categoria = st.selectbox("Filtrar por categoría", categorias)
            else:
                filtro_categoria = "Todos"
        
        # Aplicar filtros
        if filtro_banco != "Todos":
            df = df[df['banco'] == filtro_banco]
        if filtro_categoria != "Todos":
            df = df[df['categoria'] == filtro_categoria]
        
        # Asegurar que df es DataFrame
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(df)
        
        # Calcular total en ARS
        total = df['monto_ars'].sum() if 'monto_ars' in df.columns else 0
        st.metric("Total Ingresos (ARS)", f"${total:,.0f}")
        
        # Mostrar tabla con montos originales y en ARS
        cols_to_show = ['fecha', 'descripcion', 'banco', 'monto', 'monto_ars']
        available = [c for c in cols_to_show if c in df.columns]
        if available:
            df_display = df[available].copy()
            if 'monto' in df_display.columns:
                df_display['monto'] = df_display['monto'].apply(lambda x: f"${x:,.2f}")
            if 'monto_ars' in df_display.columns:
                df_display['monto_ars'] = df_display['monto_ars'].apply(lambda x: f"${x:,.0f}")
            st.dataframe(df_display)
        
        # Mostrar tasas usadas
        st.caption(f"Tasas: USDT/CLP: {usd_clp:.2f}, USDT/ARS: {usdt_ars:.2f}")
        
        # Limpiar
        if st.button("Limpiar Movimientos"):
            datos.get('meses', {}).setdefault(mes, {})['ingresos_bancarios'] = []
            guardar_datos(datos)
            st.rerun()
    else:
        st.info("No hay movimientos bancarios para este mes")


# Nuevas keywords más exhaustivas para CATEGORIAS_EGRESOS
CATEGORIAS_EGRESOS = {
    'impuestos': ['arca', 'api', 'tgi', 'brassey', 'monotributo', 'afip', 'agna',
                  'percepcion', 'percepción', 'iibb', 'ingresos brutos', 'rentas',
                  'municipalidad', 'tasa', 'tributo', 'sellado', 'patente'],
    'servicios': {
        'salud': ['clinica', 'clínica', 'hospital', 'sanatorio', 'medico', 'médico',
                  'doctor', 'salud', 'diagnostico', 'diagnóstico', 'laboratorio',
                  'cirugía', 'cirugia', 'odontolog', 'dental', 'kinesio', 'fisioterapia',
                  'psicolog', 'nutricion', 'nutrición', 'prepaga', 'obra social',
                  'gamma', 'instituto medico', 'osde', 'swiss medical', 'galeno',
                  'medife', 'omint', 'radiolog'],
        'veterinaria': ['veterinari', 'cirugia rex', 'cirugia vet',
                        'castración', 'castracion', 'vacuna mascota'],
        'servicios_publicos': ['edesur', 'edenor', 'edemsa', 'epe', 'epec',
                               'empresa provincial', 'metrogas', 'gasnor',
                               'litoral gas', 'litoralgas', 'gas natural',
                               'aguas santafesinas', 'aysa', 'assa',
                               'gas s a', 'gas sa', 'electricidad', 'energía',
                               'energia', 'servicio publico', 'servicio público'],
        'telecomunicaciones': ['movistar', 'claro', 'personal', 'telecom',
                               'telefonica', 'telefónica', 'internet', 'wifi',
                               'fibra optica', 'flow', 'cablevision', 'cablevisión',
                               'directv', 'telecentro', 'iplan'],
        'seguros': ['seguro', 'aseguradora', 'sancor', 'la segunda',
                    'san cristobal', 'san cristóbal', 'mapfre', 'zurich',
                    'rivadavia', 'federacion patronal', 'meridional',
                    'prevencion', 'prevención', 'prev seg'],
        'seguridad': ['adt', 'alarma', 'monitoreo', 'vigilancia', 'prosegur',
                      'securitas', 'camaras de seguridad'],
        'estacionamiento': ['estacionamiento', 'parking', 'cochera', 'garage',
                            'playa de estacionamiento', 'merpago tran', 'transito'],
        'peluqueria': ['peluqueria', 'peluquería', 'barberia', 'barbería',
                       'salon de belleza', 'salón de belleza', 'estetica',
                       'estética', 'spa', 'uñas', 'manicura', 'nuria'],
        'transporte': ['uber', 'cabify', 'didi', 'taxi', 'remis', 'remise',
                       'transporte', 'flete', 'mudanza', 'encomienda', 'combis'],
        'educacion': ['universidad', 'facultad', 'colegio', 'escuela',
                      'instituto', 'curso', 'capacitacion', 'capacitación',
                      'idioma', 'academia', 'jardin', 'jardín', 'guarderia',
                      'guardería'],
        'suscripciones': ['netflix', 'spotify', 'disney', 'amazon prime', 'hbo',
                          'paramount', 'star+', 'youtube premium', 'apple tv',
                          'crunchyroll', 'chatgpt', 'canva', 'google one',
                          'icloud', 'dropbox', 'microsoft 365', 'adobe'],
        'bancos': ['banco', 'comision bancaria', 'comisión bancaria',
                   'mantenimiento cuenta', 'cargo bancario', 'cargo por servicio',
                   'pluspagos'],
        'alquiler': ['alquiler', 'inmobiliaria', 'propiedad', 'inquilino',
                     'arrendamiento', 'locacion', 'locación'],
        'gimnasio': ['gimnasio', 'gym', 'fitness', 'crossfit', 'pilates',
                     'yoga', 'natacion', 'natación', 'club deportivo'],
    },
    'comercios': {
        'combustible': ['ypf', 'shell', 'axion', 'estacion de servicio',
                        'estación de servicio', 'petro', 'oil', 'refinor',
                        'puma energy', 'gnc', 'nafta', 'gasoil', 'combustible'],
        'carniceria': ['carniceria', 'carnicería', 'carne', 'fiambreria',
                       'fiambrería', 'polleria', 'pollería', 'chacinado',
                       'embutido', 'meneghini'],
        'panaderia': ['panaderia', 'panadería', 'panificadora', 'bakery',
                      'facturas', 'medialunas', 'pasteleria', 'pastelería',
                      'confiteria', 'confitería', 'tortas', 'aldana'],
        'supermercado': ['supermercado', 'hiper', 'hipermercado', 'autoservicio',
                         'mayorista', 'minorista', 'almacen', 'almacén',
                         'market', 'grocery', 'alimentos', 'comestibles',
                         'dietética', 'dietetica', 'coto', 'changomas',
                         'carrefour', 'walmart', 'jumbo', 'disco', 'vea',
                         'cencosud', 'super gloria', 'despensa', 'aldea market'],
        'farmacia': ['farmacia', 'farmacéutica', 'farmaceutica', 'drogueria',
                     'droguería', 'medicamento', 'perfumeria', 'perfumería',
                     'cosmetic', 'salcobrand', 'farmacity', 'ceschin', 'cubells'],
        'pintureria': ['pintureria', 'pinturería', 'pintura', 'pinturas',
                       'revestimiento', 'colibri', 'pintu'],
        'verduleria': ['verduleria', 'verdulería', 'fruteria', 'frutería',
                       'fruta', 'verdura', 'orgánico', 'organico'],
        'restaurant': ['restaurant', 'restaurante', 'resto', 'pizza', 'pizzeria',
                       'pizzería', 'burger', 'hamburgues', 'parrilla', 'grill',
                       'bar', 'pub', 'cerveceria', 'cervecería', 'comida',
                       'gastronomia', 'gastronomía', 'cocina', 'sushi',
                       'empanada', 'lomiteria', 'lomitería', 'rotiseria',
                       'rotisería', 'fast food', 'cafeteria', 'cafetería',
                       'coffee', 'brunch', 'bistro', 'cantina', 'bodegon',
                       'bodegón', 'tenedor libre', 'heladeria', 'heladería',
                       'helado', 'freddo', 'havanna', 'gianduia', 'nuria',
                       'fisherton'],
        'indumentaria': ['ropa', 'indumentaria', 'textil', 'calzado', 'zapateria',
                         'zapatería', 'zapato', 'vestir', 'moda', 'fashion',
                         'boutique', 'tienda de ropa', 'confeccion', 'confección',
                         'talles', 'sastreria', 'sastrería', 'uniformes',
                         'lenceria', 'lencería', 'unisport', 'polibot',
                         'monacle', 'monocle'],
        'optica': ['optica', 'óptica', 'lentes', 'anteojos', 'gafas', 'vision',
                   'visión'],
        'veterinaria_comercio': ['veterinaria', 'veterinario', 'mascota', 'pet shop',
                        'petshop', 'alimento mascota'],
        'libreria': ['libreria', 'librería', 'papeleria', 'papelería',
                     'libro', 'editorial', 'cuaderno', 'artículos escolares'],
        'ferreteria': ['ferreteria', 'ferretería', 'herramienta', 'tornilleria',
                       'tornillería', 'bulonera', 'herraje', 'cerrajeria',
                       'cerrajería', 'remo franco'],
        'electronica': ['electronica', 'electrónica', 'tecnologia', 'tecnología',
                        'celular', 'computadora', 'notebook', 'informatica',
                        'informática', 'gaming', 'fravega'],
        'bazar': ['bazar', 'regaleria', 'regalería', 'regalo', 'menaje',
                  'hogar', 'decoracion', 'decoración', 'tu quincho', 'quincho'],
        'automotor': ['gomeria', 'gomería', 'neumatico', 'neumático', 'taller',
                      'mecanica', 'mecánica', 'repuesto', 'autoparte',
                      'lubricentro', 'lavadero', 'chapa y pintura'],
        'otros': []
    },
    'otros': ['transf', 'familia', 'otros']
}

# Diccionario de comerciantes conocidos
COMERCIOS_CONOCIDOS = {
    # Combustible
    'miguel': {'categoria': 'comercios', 'subcategoria': 'combustible', 'gasto': 'Estación de Servicio'},
    
    # Carnicería
    'juan': {'categoria': 'comercios', 'subcategoria': 'carniceria', 'gasto': 'Carnicería'},
    
    # Panadería
    'pepe': {'categoria': 'comercios', 'subcategoria': 'panaderia', 'gasto': 'Panadería'},
    'panaderia sc ii': {'categoria': 'comercios', 'subcategoria': 'panaderia', 'gasto': 'Panadería SC II'},
    
    # Restaurant
    'gge alfa park': {'categoria': 'comercios', 'subcategoria': 'restaurant', 'gasto': 'GGE Alfa Park'},
    'rosati damian': {'categoria': 'comercios', 'subcategoria': 'restaurant', 'gasto': 'Pizzería Rosati'},
    'la gran argentina': {'categoria': 'comercios', 'subcategoria': 'restaurant', 'gasto': 'La Gran Argentina'},
    'diego rey': {'categoria': 'comercios', 'subcategoria': 'restaurant', 'gasto': 'Diego Rey'},
    
    # Salud
    'instituto gamma': {'categoria': 'servicios', 'subcategoria': 'salud', 'gasto': 'Instituto Gamma'},
    'gamma': {'categoria': 'servicios', 'subcategoria': 'salud', 'gasto': 'Instituto Gamma'},
    
    # Indumentaria
    'sebastian montene': {'categoria': 'comercios', 'subcategoria': 'indumentaria', 'gasto': 'Indumentaria'},
    'remo franco': {'categoria': 'comercios', 'subcategoria': 'indumentaria', 'gasto': 'Remo Franco SRL'},
    
    # Bancos
    'pluspagos': {'categoria': 'servicios', 'subcategoria': 'bancos', 'gasto': 'PlusPagos'},
    'cargo por servicio': {'categoria': 'servicios', 'subcategoria': 'bancos', 'gasto': 'Cargo Bancario'},
    
    # Estacionamiento
    'estacionamiento ocampo': {'categoria': 'servicios', 'subcategoria': 'estacionamiento', 'gasto': 'Estacionamiento Ocampo'},
    'merpago*tran': {'categoria': 'servicios', 'subcategoria': 'estacionamiento', 'gasto': 'Estacionamiento Tránsito Rosario'},
    'merpago': {'categoria': 'servicios', 'subcategoria': 'estacionamiento', 'gasto': 'Estacionamiento Tránsito Rosario'},
    
    # Bazar / Artículos parrilla
    'tu quincho': {'categoria': 'comercios', 'subcategoria': 'bazar', 'gasto': 'Tu Quincho'},
    
    # Pinturería
    'pinturerias colibri': {'categoria': 'comercios', 'subcategoria': 'pintureria', 'gasto': 'Pinturerías Colibrí'},
    
    # Servicios Públicos
    'epe': {'categoria': 'servicios', 'subcategoria': 'servicios_publicos', 'gasto': 'EPE (Energía)'},
    'aguas santafesinas': {'categoria': 'servicios', 'subcategoria': 'servicios_publicos', 'gasto': 'Aguas Santafesinas'},
    
    # Telecomunicaciones
    'movistar': {'categoria': 'servicios', 'subcategoria': 'telecomunicaciones', 'gasto': 'Movistar'},
    'personal': {'categoria': 'servicios', 'subcategoria': 'telecomunicaciones', 'gasto': 'Personal'},
    
    # Seguridad
    'adt': {'categoria': 'servicios', 'subcategoria': 'seguridad', 'gasto': 'ADT Seguridad'},
    
    # Impuestos
    'municipalidad': {'categoria': 'impuestos', 'subcategoria': 'impuestos', 'gasto': 'Municipalidad'},
    
    # Familia - hijos
    'sol belen iriarte rojo': {'categoria': 'familia', 'subcategoria': 'hijos', 'gasto': 'Sol Belén Iriarte Rojo'},
    'tomas lautaro iriarte rojo': {'categoria': 'familia', 'subcategoria': 'hijos', 'gasto': 'Tomás Lautaro Iriarte Rojo'},
    'veronica rojo': {'categoria': 'familia', 'subcategoria': 'esposa', 'gasto': 'Verónica Rojo'},
    
    # Familia - SOC
    'magdalena soler': {'categoria': 'familia', 'subcategoria': 'soc', 'gasto': 'Magdalena Soler'},
    'zurcher carlos augusto': {'categoria': 'familia', 'subcategoria': 'soc', 'gasto': 'Zurcher Carlos Augusto'},
    'zurcher': {'categoria': 'familia', 'subcategoria': 'soc', 'gasto': 'Zurcher'},
    
    # Peluquería (transferencia recurrente Galicia)
    'nrjx': {'categoria': 'servicios', 'subcategoria': 'peluqueria', 'gasto': 'Peluquería'},
    '20441772913': {'categoria': 'servicios', 'subcategoria': 'peluqueria', 'gasto': 'Peluquería'},
    
    # Colegio Santa María (educación)
    'col s maris': {'categoria': 'servicios', 'subcategoria': 'educacion', 'gasto': 'Colegio Santa María'},
    'maris': {'categoria': 'servicios', 'subcategoria': 'educacion', 'gasto': 'Colegio Santa María'},
    
    # Supermercados y tiendas
    'cencosud': {'categoria': 'comercios', 'subcategoria': 'supermercado', 'gasto': 'Cencosud'},
    'fravega': {'categoria': 'comercios', 'subcategoria': 'electronica', 'gasto': 'Frávega'},
    
    # ICBC - Seguros
    'federacion': {'categoria': 'servicios', 'subcategoria': 'seguros', 'gasto': 'Federación Patronal'},
    'pago federacion': {'categoria': 'servicios', 'subcategoria': 'seguros', 'gasto': 'Federación Patronal'},
    
    # ICBC - Impuestos
    'iva serv': {'categoria': 'impuestos', 'subcategoria': 'impuestos', 'gasto': 'IVA Servicios Digitales'},
    'iva serv dig': {'categoria': 'impuestos', 'subcategoria': 'impuestos', 'gasto': 'IVA Servicios Digitales'},
    'percepcion td': {'categoria': 'impuestos', 'subcategoria': 'impuestos', 'gasto': 'Percepción'},
    'percepcion': {'categoria': 'impuestos', 'subcategoria': 'impuestos', 'gasto': 'Percepción'},
    
    # ICBC - Seguros Previsión
    'pago prev.seg': {'categoria': 'servicios', 'subcategoria': 'seguros', 'gasto': 'Previsión Seguros'},
    'prev.seg': {'categoria': 'servicios', 'subcategoria': 'seguros', 'gasto': 'Previsión Seguros'},
    
    # Suscripciones
    'netflix': {'categoria': 'servicios', 'subcategoria': 'suscripciones', 'gasto': 'Netflix'},
    'cpa. netflix': {'categoria': 'servicios', 'subcategoria': 'suscripciones', 'gasto': 'Netflix'},
    
    # Herrero - Combustible
    'herrero srl': {'categoria': 'comercios', 'subcategoria': 'combustible', 'gasto': 'Estación Herrero'},
    'herrero': {'categoria': 'comercios', 'subcategoria': 'combustible', 'gasto': 'Estación Herrero'},
    'cpa. herrero': {'categoria': 'comercios', 'subcategoria': 'combustible', 'gasto': 'Estación Herrero'},
    
    # Carnicería
    'meneghini': {'categoria': 'comercios', 'subcategoria': 'carniceria', 'gasto': 'Carnicería Meneghini'},
    'victor meneghini': {'categoria': 'comercios', 'subcategoria': 'carniceria', 'gasto': 'Carnicería Meneghini'},
    
    # Mascotas
    'mascotas del oeste': {'categoria': 'comercios', 'subcategoria': 'veterinaria', 'gasto': 'Mascotas Del Oeste'},
    'mascotas': {'categoria': 'comercios', 'subcategoria': 'veterinaria', 'gasto': 'Mascotas'},
    
    # Combustible
    'ypf herrero': {'categoria': 'comercios', 'subcategoria': 'combustible', 'gasto': 'YPF Herrero'},
    'ypf': {'categoria': 'comercios', 'subcategoria': 'combustible', 'gasto': 'YPF'},
    
    # Panadería
    'aldana panaderias': {'categoria': 'comercios', 'subcategoria': 'panaderia', 'gasto': 'Aldana Panaderías'},
    'aldana': {'categoria': 'comercios', 'subcategoria': 'panaderia', 'gasto': 'Aldana Panaderías'},
    
    # Supermercado
    'super gloria': {'categoria': 'comercios', 'subcategoria': 'supermercado', 'gasto': 'Super Gloria'},
    'suc coto': {'categoria': 'comercios', 'subcategoria': 'supermercado', 'gasto': 'Coto'},
    'coto c.i.c.s.a': {'categoria': 'comercios', 'subcategoria': 'supermercado', 'gasto': 'Coto'},
    
    # Farmacia
    'farmacia ceschin': {'categoria': 'comercios', 'subcategoria': 'farmacia', 'gasto': 'Farmacia Ceschin'},
    'ceschin': {'categoria': 'comercios', 'subcategoria': 'farmacia', 'gasto': 'Farmacia Ceschin'},
    'farmacia cubells': {'categoria': 'comercios', 'subcategoria': 'farmacia', 'gasto': 'Farmacia Cubells'},
    'cubells': {'categoria': 'comercios', 'subcategoria': 'farmacia', 'gasto': 'Farmacia Cubells'},
    
    # Librería
    'la libreria del cole': {'categoria': 'comercios', 'subcategoria': 'libreria', 'gasto': 'La Librería del Cole'},
    'libreria del cole': {'categoria': 'comercios', 'subcategoria': 'libreria', 'gasto': 'La Librería del Cole'},
    
    # Almacén/Despensa
    'la despensa': {'categoria': 'comercios', 'subcategoria': 'almacen', 'gasto': 'La Despensa'},
    
    # Ignorar (basura del OCR)
    'correcto': None,
    'historial': None,
    'pago con': None,
    'fecha': None,
    'todos los': None,
}


def detectar_fuente(nombre_archivo):
    """Detecta la fuente de pago desde el nombre del archivo"""
    nombre = nombre_archivo.lower()
    
    fuentes = [
        # Galicia
        ('tarjeta_debito_galicia_gustavo', ['tarjeta', 'galicia', 'gustavo'], 3),
        ('tarjeta_debito_galicia', ['tarjeta', 'galicia'], 2),
        
        # MercadoPago - más keywords
        ('mercadopago_gustavo', ['mercadopago', 'mercado', 'mp', 'pago', 'gustavo'], 3),
        ('mercadopago_veronica', ['mercadopago', 'mercado', 'mp', 'pago', 'veronica'], 3),
        ('mercadopago_sol', ['mercadopago', 'mercado', 'mp', 'pago', 'sol'], 3),
        ('mercadopago', ['mercadopago', 'mercado', 'mp', 'pago'], 2),
        
        # Bybit
        ('bybit_qr_gustavo', ['bybit', 'qr', 'gustavo'], 3),
        ('bybit_tarjeta_gustavo', ['bybit', 'tarjeta', 'gustavo'], 3),
        ('bybit_qr_veronica', ['bybit', 'qr', 'veronica'], 3),
        ('bybit_tarjeta_veronica', ['bybit', 'tarjeta', 'veronica'], 3),
        ('bybit_qr_sol', ['bybit', 'qr', 'sol'], 3),
        ('bybit_tarjeta_sol', ['bybit', 'tarjeta', 'sol'], 3),
        ('bybit_qr', ['bybit', 'qr'], 2),
        ('bybit_tarjeta', ['bybit', 'tarjeta'], 2),
        
        # ICBC
        ('tarjeta_debito_icbc_veronica', ['tarjeta', 'icbc', 'veronica'], 3),
        ('icbc', ['icbc'], 1),
        
        # Binance
        ('binance_qr_veronica', ['binance', 'qr', 'veronica'], 3),
        ('binance', ['binance'], 1),
    ]
    
    mejor_fuente = 'desconocido'
    mejor_puntaje = 0
    
    for fuente, keywords, peso in fuentes:
        matches = sum(1 for kw in keywords if kw in nombre)
        if matches > 0:
            puntaje = matches * peso
            if puntaje > mejor_puntaje:
                mejor_puntaje = puntaje
                mejor_fuente = fuente
    
    return mejor_fuente


def normalizar_texto(s: str) -> str:
    """Normaliza texto para comparación: minúsculas, sin acentos, sin símbolos."""
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ====== HEURÍSTICAS DE INFERENCIA POR NOMBRE ======

# Patrones que indican nombre de persona (transferencia)
PATRON_NOMBRE_PERSONA = re.compile(
    r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+'      # Nombre (capitalizado)
    r'(?:[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+)*'   # Segundo nombre (opcional)
    r'[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+$'          # Apellido
)

# Sufijos corporativos que indican empresa
SUFIJOS_EMPRESA = ['s a', 'sa', 'sas', 's r l', 'srl', 'ltda', 'inc']

# Palabras que indican tipo de comercio incluso sin match exacto
INFERENCIA_CONTEXTO = {
    ('comercios', 'supermercado'): ['market', 'almacen', 'grocery', 'tienda', 'store', 'shop'],
    ('comercios', 'restaurant'): ['resto', 'cocina', 'grill', 'food', 'eat', 'cuisine', 'gastro', 'deli'],
    ('comercios', 'farmacia'): ['farma', 'pharm', 'drug', 'botica'],
    ('comercios', 'indumentaria'): ['wear', 'fashion', 'style', 'outfit', 'cloth', 'textile'],
    ('comercios', 'optica'): ['optic', 'vision', 'lens', 'eye', 'glass'],
    ('comercios', 'veterinaria'): ['vet', 'pet', 'animal', 'mascota'],
    ('servicios', 'salud'): ['clinic', 'medic', 'health', 'salud', 'cirug', 'dental', 'odonto',
                              'fisio', 'kinesio', 'nutri', 'psico', 'lab', 'diagnos'],
    ('servicios', 'servicios_publicos'): ['gas s', 'energia', 'electric', 'agua'],
    ('servicios', 'educacion'): ['school', 'academy', 'academ', 'educa', 'learn', 'college'],
}


def _pre_normalizar_ocr(texto: str) -> str:
    """Corrige errores comunes de OCR: palabras pegadas, caracteres basura."""
    if not texto:
        return texto

    # Insertar espacio antes de mayúscula pegada: "LitoralGas" -> "Litoral Gas"
    resultado = re.sub(r'([a-záéíóúñ])([A-ZÁÉÍÓÚÑ])', r'\1 \2', texto)

    # Separar letras pegadas a puntos: "s.A" -> "s.a."
    resultado = re.sub(r'\.([A-Z])', r'. \1', resultado)

    # Separar "sA" -> "s a"
    resultado = re.sub(r'([sS])([aA])$', r's a', resultado)

    # Limpiar espacios múltiples
    resultado = re.sub(r'\s+', ' ', resultado).strip()

    return resultado


def _es_nombre_persona(nombre: str) -> bool:
    """Detecta si un texto parece nombre de persona"""
    nombre = nombre.strip()
    nombre_lower = nombre.lower()

    # Si tiene sufijo corporativo, NO es persona
    for sufijo in SUFIJOS_EMPRESA:
        if nombre_lower.endswith(sufijo) or f' {sufijo}' in nombre_lower:
            return False

    # Verificar patrón Nombre Apellido
    if PATRON_NOMBRE_PERSONA.match(nombre):
        palabras = nombre.split()
        if 2 <= len(palabras) <= 4:
            if all(p[0].isupper() and p[1:].islower() for p in palabras if len(p) > 1):
                if not any(c.isdigit() for c in nombre):
                    return True

    return False


def _inferir_por_contexto(nombre_norm: str) -> tuple:
    """Intenta inferir categoría por palabras parciales en el nombre"""
    for (cat, subcat), palabras in INFERENCIA_CONTEXTO.items():
        for palabra in palabras:
            if palabra in nombre_norm:
                return cat, subcat
    return None, None


def categorizar_gasto(descripcion, datos=None):
    """Categoriza un gasto: 1) pre-normalizar OCR, 2) conocidos, 3) keywords, 4) web search"""
    
    # Limpiar descripción
    desc_limpia = ' '.join(descripcion.split())
    nombre_crudo = desc_limpia.split('  ')[0].split(' - ')[0].split('\t')[0].strip()

    # 0) PRE-NORMALIZAR OCR
    nombre_limpio = _pre_normalizar_ocr(nombre_crudo)
    nombre_norm = normalizar_texto(nombre_limpio)
    
    if not nombre_norm:
        return 'otros', 'otros', nombre_crudo.title() or 'Sin descripcion'
    
    # 1) Comercios conocidos
    for conocido, info in COMERCIOS_CONOCIDOS.items():
        if info is None:
            continue
        conocido_norm = normalizar_texto(conocido)
        if conocido_norm and conocido_norm in nombre_norm:
            return info['categoria'], info['subcategoria'], info['gasto']
    
    # 2) Keywords locales
    for categoria, keywords in CATEGORIAS_EGRESOS.items():
        if isinstance(keywords, dict):
            # servicios y comercios tienen subcategorías
            for subcategoria, palabras in keywords.items():
                for palabra in palabras:
                    if normalizar_texto(palabra) in nombre_norm:
                        return categoria, subcategoria, nombre_limpio.title()
        elif isinstance(keywords, list):
            # impuestos, otros (listas planas)
            for palabra in keywords:
                if normalizar_texto(palabra) in nombre_norm:
                    return categoria, categoria, nombre_limpio.title()
    
    # 3) Reglas específicas familiares
    if any(nombre in nombre_norm for nombre in [
        'sol belen iriarte', 'tomas lautaro iriarte',
        'veronica rojo', 'magdalena soler', 'zurcher'
    ]):
        return 'familia', 'familia', nombre_limpio.title()

    # 4) Inferencia por contexto
    cat_inf, subcat_inf = _inferir_por_contexto(nombre_norm)
    if cat_inf and subcat_inf:
        return cat_inf, subcat_inf, nombre_limpio.title()

    # 5) Detección de nombre de persona
    if _es_nombre_persona(nombre_limpio):
        return 'familia', 'transferencia', nombre_limpio.title()
    
    # 6) Búsqueda CUIT Online
    resultado_cuit = buscar_comercio_cuit_online(nombre_limpio)
    
    if resultado_cuit and len(resultado_cuit) >= 4:
        actividad, confianza, cat_cuit, subcat_cuit = resultado_cuit
        if confianza >= 0.70 and cat_cuit and subcat_cuit:
            COMERCIOS_CONOCIDOS[nombre_norm] = {
                'categoria': cat_cuit,
                'subcategoria': subcat_cuit,
                'gasto': nombre_limpio.title()
            }
            return cat_cuit, subcat_cuit, nombre_limpio.title()
    
    # 7) Búsqueda DuckDuckGo
    resultado = buscar_comercio_en_web(nombre_limpio)
    
    if resultado and len(resultado) >= 4:
        texto_resultado, confianza, cat_web, subcat_web = resultado
        
        if confianza >= 0.60 and cat_web and subcat_web:
            COMERCIOS_CONOCIDOS[nombre_norm] = {
                'categoria': cat_web,
                'subcategoria': subcat_web,
                'gasto': nombre_limpio.title()
            }
            return cat_web, subcat_web, nombre_limpio.title()
    
    # 8) Fallback
    return 'otros', 'otros', nombre_limpio.title()


def extraer_subpagos_desde_comprobante(reader, comprobante) -> list[dict]:
    """
    Usa OCR del comprobante para inferir sub-pagos.
    Retorna lista de dicts con monto/fecha/medio_pago/descripcion.
    """
    
    try:
        if hasattr(comprobante, 'read'):
            comprobante.seek(0)
            results = reader.readtext(comprobante.read())
        else:
            results = reader.readtext(comprobante)
        
        texto = ""
        for (bbox, text, prob) in results:
            texto += text + "\n"
        
        lineas = texto.split('\n')
        sub_pagos = []
        
        pesos_pattern = re.compile(r'\$\s*([\d.,]+)')
        servicio_palabras = ['SERVICIO', 'IMPORTE', 'TOTAL', 'SUBTOTAL', 'NETO', 'BRUTO', 'IVA', 'ABONO', 'DEBITO', 'CREDITO']
        
        i = 0
        while i < len(lineas):
            linea = lineas[i].strip()
            
            if not linea:
                i += 1
                continue
            
            linea_upper = linea.upper()
            
            es_servicio = any(palabra in linea_upper for palabra in servicio_palabras)
            
            if es_servicio and len(linea) > 2:
                servicio_nombre = linea.strip()
                
                monto_encontrado = None
                
                for j in range(i + 1, min(i + 5, len(lineas))):
                    sig_linea = lineas[j].strip()
                    if not sig_linea:
                        continue
                    
                    pesos_match = pesos_pattern.search(sig_linea)
                    if pesos_match:
                        monto_str = pesos_match.group(1).replace(',', '')
                        try:
                            if '.' in monto_str and monto_str.count('.') == 1:
                                monto_encontrado = float(monto_str)
                            elif ',' in monto_str:
                                monto_partes = monto_str.split(',')
                                if len(monto_partes) == 2 and len(monto_partes[1]) <= 2:
                                    monto_encontrado = float(monto_str.replace(',', '.'))
                                else:
                                    monto_encontrado = float(monto_str.replace(',', ''))
                            else:
                                monto_encontrado = float(monto_str)
                            break
                        except ValueError:
                            continue
                
                if monto_encontrado and monto_encontrado > 100:
                    sub_pagos.append({
                        'monto': monto_encontrado,
                        'descripcion': servicio_nombre,
                        'fecha': '',
                        'medio_pago': ''
                    })
            
            i += 1
        
        seen = set()
        sub_pagos_dedup = []
        for sp in sub_pagos:
            key = (sp.get('descripcion', '').lower()[:20], round(sp.get('monto', 0), 2))
            if key not in seen:
                seen.add(key)
                sub_pagos_dedup.append(sp)
        
        return sub_pagos_dedup, texto
    except Exception as e:
        st.error(f"Error en OCR: {e}")
        return [], ""


def filtrar_y_guardar_temp(gastos, mes_seleccionado):
    """Filtra gastos por período y los deja listos para preview"""
    gastos_del_mes = []
    gastos_fuera = []

    for g in gastos:
        fecha = str(g.get('fecha', '')).strip()

        if not fecha or fecha.startswith(mes_seleccionado):
            # Sin fecha o del mes correcto -> incluir
            gastos_del_mes.append(g)
        else:
            gastos_fuera.append(g)

    if gastos_fuera:
        # Mostrar qué meses tienen los descartados
        meses_fuera = set()
        for g in gastos_fuera:
            f = g.get('fecha', '')[:7]
            if f:
                meses_fuera.add(f)
        st.warning(
            f"⚠️ {len(gastos_fuera)} egresos descartados "
            f"(pertenecen a: {', '.join(sorted(meses_fuera))}). "
            f"Seleccioná el periodo correcto para cargarlos."
        )

    st.session_state.egresos_procesados_temp = gastos_del_mes

    if gastos_del_mes:
        st.success(f"✅ {len(gastos_del_mes)} egresos listos para guardar en {mes_seleccionado}")
    else:
        st.warning(f"No hay egresos para {mes_seleccionado}. Verificá el periodo seleccionado.")

    st.rerun()



def mostrar_egresos():
    st.header("Egresos")
    
    # SIEMPRE leer desde disco como fuente de verdad
    datos = cargar_datos()
    st.session_state.datos = datos
    
    # Inicializar session state para egresos procesados temporalmente
    if 'egresos_procesados_temp' not in st.session_state:
        st.session_state.egresos_procesados_temp = None
    
    # Selector de mes
    meses_disponibles = list(datos.get('meses', {}).keys())
    if not meses_disponibles:
        meses_disponibles = ['2026-02']
    meses_disponibles = sorted(meses_disponibles)
    
    # Inicializar session state para sub-pagos si no existe
    if 'subpagos_por_egreso' not in st.session_state:
        st.session_state.subpagos_por_egreso = {}
    if 'comprobante_por_egreso' not in st.session_state:
        st.session_state.comprobante_por_egreso = {}
    if 'ui_subpagos_abierto' not in st.session_state:
        st.session_state.ui_subpagos_abierto = {}
    
    col1, col2 = st.columns([3, 1])
    with col1:
        # Si hay un mes pendiente de selección, usarlo como índice inicial
        mes_default = st.session_state.get("pending_mes_egresos")

        if mes_default in meses_disponibles:
            index_default = meses_disponibles.index(mes_default)
        elif st.session_state.get('mes_egresos_actual') in meses_disponibles:
            index_default = meses_disponibles.index(st.session_state.get('mes_egresos_actual'))
        else:
            index_default = len(meses_disponibles) - 1

        mes_seleccionado = st.selectbox(
            "Mes",
            meses_disponibles,
            index=index_default,
            key="sel_mes_egresos"
        )

        # Limpiar pendiente después de usarlo
        if "pending_mes_egresos" in st.session_state:
            del st.session_state["pending_mes_egresos"]

        st.session_state.mes_egresos_actual = mes_seleccionado
    
    # Limpiar debug info al cambiar de mes
    debug_info = st.session_state.get('debug_guardado')
    if debug_info is None or debug_info.get('mes') != mes_seleccionado:
        st.session_state.debug_guardado = None
    
    with col2:
        st.write("")  # Espaciador
        st.write("")  # Espaciador
        with st.expander("+ Nuevo Mes"):
            anios_opciones = list(range(datetime.now().year, 2015, -1))
            meses_opciones = [
                (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
                (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
                (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre")
            ]
            nuevo_anio = st.selectbox("Año", anios_opciones, key="nuevo_mes_anio")
            nuevo_mes_num = st.selectbox(
                "Mes",
                [m[0] for m in meses_opciones],
                format_func=lambda x: dict(meses_opciones)[x],
                key="nuevo_mes_num"
            )
            nuevo_mes = f"{nuevo_anio}-{nuevo_mes_num:02d}"
            st.caption(f"Período: {nuevo_mes}")
            if st.button("Crear", key="crear_mes_btn"):
                # Leer del disco para evitar el guard de guardar_datos (no depende de session_state)
                datos_disco = cargar_datos()
                if nuevo_mes not in datos_disco.get('meses', {}):
                    datos_disco.setdefault('meses', {})[nuevo_mes] = {
                        'ingresos_bancarios': [],
                        'egresos': [],
                        'ajustes': [],
                        'ganancia_fondos': 0,
                        'plusvalia_propiedades': 0
                    }
                    # Escritura directa al JSON (bypass del guard de 0 egresos)
                    with open(DATOS_FILE, 'w', encoding='utf-8') as f:
                        json.dump(datos_disco, f, ensure_ascii=False, indent=2)
                    st.session_state.datos = datos_disco
                    st.session_state.mes_egresos_actual = nuevo_mes
                    st.session_state["pending_mes_egresos"] = nuevo_mes
                    st.success(f"✅ Mes {nuevo_mes} creado y guardado")
                    st.rerun()
                else:
                    st.warning("El mes ya existe")
    
    # Selectores de owner y medio de pago para los egresos
    OWNERS = ["Gustavo", "Vero", "Sol"]
    MEDIOS_PAGO = ["Banco Galicia", "ICBC", "QR Binance", "QR Bybit", "Tarjeta Prepaga Bybit", "Visa", "Mastercard", "Efectivo", "Mercado Pago", "Otro"]
    
    col_o, col_m, col_p = st.columns([2, 2, 1])
    
    with col_o:
        owners_with_todos = ["TODOS"] + OWNERS
        owner_egreso = st.selectbox("Owner", owners_with_todos, index=0, key="owner_egreso_selector")
    
    with col_m:
        medios_con_todos = ["TODOS"] + MEDIOS_PAGO
        medio_egreso = st.selectbox("Medio de Pago", medios_con_todos, index=0, key="medio_pago_selector")
    
    with col_p:
        st.write("")
        st.write("")
        if st.button("Borrar Periodo", key="btn_borrar_periodo", type="primary"):
            datos['meses'][mes_seleccionado] = {
                'ingresos_bancarios': [],
                'egresos': [],
                'ajustes': [],
                'ganancia_fondos': 0,
                'plusvalia_propiedades': 0
            }
            guardar_datos(datos)
            st.session_state.datos = datos
            st.success(f"Periodo {mes_seleccionado} borrado.")
            st.rerun()
    
    # ====================== CARGA DE EGRESOS ======================
    st.subheader(f"Cargar Egresos - {mes_seleccionado}")
    
    # Cargar todos los egresos del mes
    egresos_completos = datos.get('meses', {}).get(mes_seleccionado, {}).get('egresos', [])
    
    # Filtrar por owner y medio de pago
    egresos = []
    for egreso in egresos_completos:
        matches_owner = (owner_egreso == "TODOS") or (egreso.get('owner', '') == owner_egreso)
        matches_medio = (medio_egreso == "TODOS") or (egreso.get('medio_pago', '') == medio_egreso)
        
        if matches_owner and matches_medio:
            egresos.append(egreso)
    
    if len(egresos) != len(egresos_completos):
        st.caption(f"Mostrando {len(egresos)} de {len(egresos_completos)} egresos")
    
    archivo = st.file_uploader(
        "Seleccionar archivo de egresos (imagen, PDF, texto o Excel)",
        type=['jpg', 'jpeg', 'png', 'pdf', 'txt', 'xlsx', 'xls'],
        key=f"uploader_{mes_seleccionado}"
    )
    
    if archivo:
        fuente = detectar_fuente(archivo.name)
        st.info(f"Fuente detectada: {fuente}")
        
        if st.button("Procesar Egresos"):
            with st.spinner("Procesando egresos..."):
                texto = ""
                
                # Determinar tipo de archivo
                file_name = archivo.name.lower()
                
                # ---- MERCADOPAGO APP (JPG/PNG) ----
                if file_name.endswith(('.jpg', '.jpeg', '.png')) and 'mercadopago' in file_name:
                    from parsers.mercadopago_app import procesar_mercadopago_app

                    gastos, texto_debug, error = procesar_mercadopago_app(
                        archivo=archivo,
                        owner=owner_egreso,
                        medio_pago=medio_egreso,
                        datos=datos,
                        categorizar_gasto_fn=categorizar_gasto
                    )

                    if texto_debug:
                        with st.expander("DEBUG: Texto OCR MercadoPago App"):
                            st.text(texto_debug)

                    if error:
                        st.error(error)
                    elif gastos:
                        filtrar_y_guardar_temp(gastos, mes_seleccionado)
                    else:
                        st.warning("No se detectaron egresos")

                    st.stop()

                # ---- MERCADOPAGO PDF ----
                if file_name.endswith('.pdf') and 'mercadopago' in file_name:
                    from parsers.mercadopago_pdf import procesar_mercadopago_pdf

                    gastos, texto_debug, error = procesar_mercadopago_pdf(
                        archivo=archivo,
                        owner=owner_egreso,
                        medio_pago=medio_egreso,
                        datos=datos,
                        categorizar_gasto_fn=categorizar_gasto
                    )

                    if texto_debug:
                        with st.expander("DEBUG: PDF MercadoPago", expanded=True):
                            st.text(texto_debug)

                    if error:
                        st.error(error)
                    elif gastos:
                        filtrar_y_guardar_temp(gastos, mes_seleccionado)
                    else:
                        st.warning("No se detectaron egresos en el PDF")

                    st.stop()

                # ---- GALICIA IMG ----
                if file_name.endswith(('.jpg', '.jpeg', '.png')) and 'galicia' in file_name:
                    from parsers.galicia_img import procesar_galicia_img

                    with st.spinner("Procesando imagen Galicia..."):
                        gastos, texto_debug, error = procesar_galicia_img(
                            archivo, owner_egreso, medio_egreso, datos, categorizar_gasto
                        )

                        if texto_debug:
                            with st.expander("DEBUG: Texto OCR Galicia IMG"):
                                st.text(texto_debug)

                        if error:
                            st.error(error)
                        elif gastos:
                            filtrar_y_guardar_temp(gastos, mes_seleccionado)
                        else:
                            st.warning("No se detectaron egresos en la imagen")

                    st.stop()

                # ---- GALICIA EXCEL ----
                if file_name.endswith(('.xlsx', '.xls')):
                    try:
                        from parsers.galicia_excel import extraer_egresos_galicia_excel

                        archivo.seek(0)
                        gastos_excel = extraer_egresos_galicia_excel(
                            archivo=archivo,
                            categorizar_gasto_fn=categorizar_gasto,
                            datos=datos,
                            owner=owner_egreso,
                            medio_pago=medio_egreso,
                            generar_id_fn=generar_id
                        )

                        if gastos_excel:
                            filtrar_y_guardar_temp(gastos_excel, mes_seleccionado)
                        else:
                            st.warning("No se detectaron egresos en el Excel")

                    except Exception as e:
                        st.error(f"Error procesando Excel Galicia: {e}")

                    st.stop()
                
                # ---- BYBIT QR JPG ----
                if file_name.endswith(('.jpg', '.jpeg', '.png')) and 'bybit' in file_name and 'qr' in file_name:
                    from parsers.bybit_qr import procesar_bybit_qr
                    
                    with st.spinner("Procesando JPG de Bybit QR..."):
                        gastos, texto_debug, error = procesar_bybit_qr(
                            archivo, owner_egreso, medio_egreso, datos, categorizar_gasto
                        )
                        
                        if texto_debug:
                            with st.expander("DEBUG: Texto OCR Bybit QR"):
                                st.text(texto_debug)
                        
                        if error:
                            st.error(error)
                        elif gastos:
                            filtrar_y_guardar_temp(gastos, mes_seleccionado)
                        else:
                            st.warning("No se detectaron gastos en la imagen")
                    
                    st.stop()

                # ---- BYBIT TARJETA JPG ----
                if file_name.endswith(('.jpg', '.jpeg', '.png')) and 'bybit' in file_name and 'tarjeta' in file_name:
                    from parsers.bybit_tarjeta import procesar_bybit_tarjeta
                    
                    with st.spinner("Procesando JPG de Bybit Tarjeta..."):
                        gastos, texto_debug, error = procesar_bybit_tarjeta(
                            archivo, owner_egreso, medio_egreso, datos, categorizar_gasto
                        )
                        
                        if texto_debug:
                            with st.expander("DEBUG: Texto OCR Bybit Tarjeta"):
                                st.text(texto_debug)
                        
                        if error:
                            st.error(error)
                        elif gastos:
                            filtrar_y_guardar_temp(gastos, mes_seleccionado)
                        else:
                            st.warning("No se detectaron gastos en la imagen")
                    
                    st.stop()
                
                # ---- ICBC JPG: usar parser específico ----
                elif file_name.endswith(('.jpg', '.jpeg', '.png')) and 'icbc' in file_name:
                    from parsers.icbc import procesar_icbc
                    
                    with st.spinner("Procesando JPG de ICBC con parser específico..."):
                        gastos, texto_debug, error = procesar_icbc(
                            archivo, owner_egreso, medio_egreso, datos
                        )
                        
                        if texto_debug:
                            with st.expander("DEBUG: Texto OCR ICBC"):
                                st.text(texto_debug)
                        
                        if error:
                            st.error(error)
                        elif gastos:
                            filtrar_y_guardar_temp(gastos, mes_seleccionado)
                        else:
                            st.warning("No se detectaron gastos en la imagen")
                    
                    st.stop()

                # ---- MERCADOPAGO APP JPG ----
                if 'mercadopago' in file_name.lower() or 'mercado' in file_name.lower() or 'mp' in file_name.lower():
                    from parsers.mercadopago_app import procesar_mercadopago_app
                    
                    gastos, texto_debug, error = procesar_mercadopago_app(
                        archivo, owner_egreso, medio_egreso, datos, categorizar_gasto
                    )
                    
                    st.info(f"DEBUG: Fuente = {detectar_fuente(archivo.name)}")
                    
                    if texto_debug:
                        with st.expander("DEBUG: Texto OCR MercadoPago App", expanded=True):
                            st.text(texto_debug)
                    
                    if error:
                        st.error(error)
                    elif gastos:
                        filtrar_y_guardar_temp(gastos, mes_seleccionado)
                    else:
                        st.warning("No se detectaron egresos")
                    
                    st.stop()
                
                # ---- BINANCE QR JPG ----
                if file_name.endswith(('.jpg', '.jpeg', '.png')) and 'binance' in file_name.lower():
                    from parsers.binance_qr import procesar_binance_qr

                    gastos, texto_debug, error = procesar_binance_qr(
                        archivo, owner_egreso, medio_egreso, datos, categorizar_gasto
                    )

                    if texto_debug:
                        with st.expander("DEBUG: Texto OCR Binance QR", expanded=True):
                            st.text(texto_debug)

                    if error:
                        st.error(error)
                    elif gastos:
                        filtrar_y_guardar_temp(gastos, mes_seleccionado)
                    else:
                        st.warning("No se detectaron egresos Binance QR")

                    st.stop()

                elif file_name.endswith(('.jpg', '.jpeg', '.png')):
                    if EASYOCR_AVAILABLE:
                        archivo.seek(0)
                        try:
                            import easyocr
                            reader = easyocr.Reader(['es', 'en'], gpu=False)
                            results = reader.readtext(archivo.read())
                            for (bbox, text, prob) in results:
                                texto += text + "\n"
                        except Exception as e:
                            st.error(f"Error con EasyOCR: {e}")
                    else:
                        st.warning("EasyOCR no está instalado")
                elif file_name.endswith('.pdf'):
                    if PDF_AVAILABLE:
                        archivo.seek(0)
                        try:
                            import pymupdf
                            doc = pymupdf.open(stream=archivo.read(), filetype="pdf")
                            for page in doc:
                                texto += page.get_text() + "\n"
                            doc.close()
                        except Exception as e:
                            st.error(f"Error con PDF: {e}")
                    else:
                        st.warning("PyMuPDF no está instalado")
                else:
                    texto = archivo.read().decode('utf-8')
                
                if texto:
                    st.success("Texto extraído")
                    
                    with st.expander("DEBUG: Texto OCR extraído"):
                        st.text_area("Texto raw", texto, height=200)
                    
                    # Parsear gastos
                    gastos = []
                    lineas = texto.split('\n')
                    
                    st.info(f"Líneas encontradas: {len(lineas)}")
                    
                    # Pattern 1: Amount ARS Description (monto al inicio)
                    # Example: "10,150.00 ARS GGE ALFA PARK - restaurant"
                    amount_ars_pattern1 = re.compile(r'([\d.,]+)\s*ARS\s*(.+)', re.IGNORECASE)
                    # Pattern 2a: Description Amount ARS (monto al final CON descripción)
                    # Example: "GGE ALFA PARK 10,150.00 ARS"
                    amount_ars_pattern2a = re.compile(r'(.+)\s+([\d.,]+)\s+ARS$', re.IGNORECASE)
                    # Pattern 2b: ONLY Amount ARS (sin descripción en esta línea)
                    # Example: "10,150.00 ARS"
                    amount_ars_pattern2b = re.compile(r'^([\d.,]+)\s+ARS$', re.IGNORECASE)
                    fecha_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})')
                    
                    # Textos a ignorar
                    ignorados = ['historial', 'correcto', 'pago con', 'fecha', 'todos los', 
                                 'tipos', 'estados', 'qr', 'con qr', 'sin']
                    
                    debug_info = []
                    
                    # Process lines looking for ARS amounts - the format in the OCR is:
                    # Line N: Commerce name
                    # Line N+1: Amount ARS
                    # Line N+2: Date info
                    i = 0
                    while i < len(lineas):
                        linea = lineas[i].strip()
                        
                        if not linea:
                            i += 1
                            continue
                        
                        debe_ignorar = any(ig.lower() in linea.lower() for ig in ignorados)
                        if debe_ignorar:
                            i += 1
                            continue
                        
                        ars_match = None
                        matched_pattern = None
                        
                        # PATTERN 1: Amount at start (e.g., "10,150.00 ARS GGE ALFA PARK")
                        match = amount_ars_pattern1.search(linea)
                        if match:
                            ars_match = match
                            matched_pattern = amount_ars_pattern1
                        
                        # PATTERN 2a: Amount at end with description (e.g., "GGE ALFA PARK 10,150.00 ARS")
                        if not ars_match:
                            match = amount_ars_pattern2a.search(linea)
                            if match:
                                ars_match = match
                                matched_pattern = amount_ars_pattern2a
                        
                        # PATTERN 2b/3: ONLY Amount ARS (no description in this line)
                        # This handles both Pattern 2b and the "solo amount" case
                        if not ars_match and 'ARS' in linea.upper():
                            solo_monto = re.match(r'^[\d.,\s]+ARS$', linea.strip(), re.IGNORECASE)
                            monto_match = re.search(r'([\d.,]+)', linea)
                            if solo_monto and monto_match:
                                # Find ALL valid description lines from previous lines
                                partes_desc = []
                                for k in range(i-1, -1, -1):
                                    prev = lineas[k].strip()
                                    if not prev:
                                        continue
                                    if any(ig.lower() in prev.lower() for ig in ignorados):
                                        if partes_desc:
                                            break  # Stop if we already found some parts
                                        continue
                                    if 'ars' in prev.lower():
                                        continue
                                    if re.match(r'^[\d.,]+$', prev):
                                        continue
                                    partes_desc.append(prev)
                                    # Continue searching to find ALL parts (e.g., "tu" + "quincho")
                                
                                if partes_desc:
                                    # Reverse to get correct order (oldest first)
                                    partes_desc.reverse()
                                    descripcion = ' '.join(partes_desc)
                                    ars_match = monto_match
                                    matched_pattern = 'solo_ars'
                                    debug_info.append(f"  -> Desc concat: '{descripcion}'")
                        
                        if ars_match:
                            descripcion = ''  # Initialize
                            if matched_pattern == amount_ars_pattern1:
                                monto_str = ars_match.group(1).replace(',', '')
                                descripcion = ars_match.group(2).strip()
                            elif matched_pattern == amount_ars_pattern2a:
                                descripcion = ars_match.group(1).strip()
                                monto_str = ars_match.group(2).replace(',', '')
                            elif matched_pattern == 'solo_ars':
                                monto_str = ars_match.group(1).replace(',', '')
                                # descripcion already set by the consolidated logic above
                            else:
                                monto_str = ars_match.group(1).replace(',', '')
                                descripcion = ''
                            
                            try:
                                cleaned_monto = ''.join(c for c in monto_str if c.isdigit() or c in ',.')
                                
                                if cleaned_monto:
                                    dot_count = cleaned_monto.count('.')
                                    comma_count = cleaned_monto.count(',')
                                    
                                    if dot_count > 0 and comma_count > 0:
                                        last_dot = cleaned_monto.rfind('.')
                                        last_comma = cleaned_monto.rfind(',')
                                        if last_comma > last_dot:
                                            cleaned_monto = cleaned_monto.replace('.', '').replace(',', '.')
                                        else:
                                            cleaned_monto = cleaned_monto.replace(',', '')
                                    elif comma_count > 0 and dot_count == 0:
                                        if len(cleaned_monto) >= 4 and cleaned_monto[-4] == ',' and cleaned_monto[-3:].isdigit():
                                            cleaned_monto = cleaned_monto.replace(',', '')
                                        else:
                                            cleaned_monto = cleaned_monto.replace(',', '.')
                                    elif dot_count > 0 and comma_count == 0:
                                        if len(cleaned_monto) >= 4 and cleaned_monto[-4] == '.' and cleaned_monto[-3:].isdigit():
                                            cleaned_monto = cleaned_monto.replace('.', '')
                                
                                monto = float(cleaned_monto)
                                debug_info.append(f"Línea con monto ARS: '{linea[:60]}' -> monto: {monto}")
                                
                                if monto > 100:
                                    gasto_desc = descripcion
                                    
                                    # Si la descripción es muy corta o inválida, buscar en líneas anteriores
                                    if not gasto_desc or len(gasto_desc) < 3 or gasto_desc.lower() in ['con qr', 'pago con', 'pago', 'or', '-']:
                                        if i > 0:
                                            # Buscar hacia atrás líneas válidas y concatenarlas
                                            partes_desc = []
                                            for k in range(i-1, -1, -1):
                                                prev_linea = lineas[k].strip()
                                                if not prev_linea:
                                                    continue
                                                prev_ignore = any(ig.lower() in prev_linea.lower() for ig in ignorados)
                                                prev_has_ars = 'ars' in prev_linea.lower()
                                                prev_is_solo_monto = re.match(r'^[\d.,\s]+ARS$', prev_linea, re.IGNORECASE)
                                                if not prev_ignore and not prev_has_ars and not prev_is_solo_monto and len(prev_linea) > 1:
                                                    partes_desc.append(prev_linea)
                                                else:
                                                    # Si encontramos una línea que no es válida, parar
                                                    if partes_desc:
                                                        break
                                            if partes_desc:
                                                # Concatenar en orden inverso (de más antiguo a más reciente)
                                                gasto_desc = ' '.join(reversed(partes_desc))
                                                debug_info.append(f"  -> Desc de líneas anteriores: '{gasto_desc}'")
                                    
                                    # Limpiar la descripción
                                    gasto_desc = gasto_desc.replace('con QR', '').replace('Pago con', '').replace('Pago', '').replace('OR', '').replace('QR', '').replace('-', '').strip()
                                    
                                    if gasto_desc and len(gasto_desc) >= 2:
                                        categoria, subcategoria, gasto_final = categorizar_gasto(gasto_desc, datos)
                                        debug_info.append(f"  -> Categorizado: {categoria}/{subcategoria} = {gasto_final}")
                                        
                                        fecha = ""
                                        for j in range(max(0, i-2), min(i+3, len(lineas))):
                                            fecha_match = fecha_pattern.search(lineas[j])
                                            if fecha_match:
                                                fecha = fecha_match.group(1)
                                                break
                                        
                                        gastos.append({
                                            'fecha': fecha,
                                            'gasto': gasto_final,
                                            'monto': monto,
                                            'moneda': 'ARS',
                                            'fuente': fuente,
                                            'categoria': categoria,
                                            'subcategoria': subcategoria,
                                            'owner': owner_egreso,
                                            'medio_pago': medio_egreso,
                                            'u_id': generar_id()
                                        })
                                    else:
                                        debug_info.append(f"  -> Descripción vacía o muy corta, ignorado")
                                else:
                                    debug_info.append(f"  -> Monto muy pequeño ({monto}), ignorado")
                            except ValueError as e:
                                debug_info.append(f"  ERROR monto '{monto_str}': {e}")
                            except Exception as e:
                                debug_info.append(f"  ERROR inesperado: {e}")
                        else:
                            if any(c.isdigit() for c in linea):
                                debug_info.append(f"Línea con dígitos sin ARS: '{linea[:50]}'")
                        
                        i += 1
                    
                    seen = set()
                    gastos_dedup = []
                    for g in gastos:
                        key = (g.get('gasto', '').lower(), round(g.get('monto', 0), 2))
                        if key not in seen:
                            seen.add(key)
                            gastos_dedup.append(g)
                    debug_info.append(f"Após dedup: {len(gastos_dedup)} de {len(gastos)} gastos")
                    gastos = gastos_dedup
                    
                    # FILTRO: Solo gastos del mes seleccionado
                    mes_year, mes_num = mes_seleccionado.split('-')
                    gastos_filtrados = []
                    gastos_ignorados = 0
                    for g in gastos:
                        fecha_gasto = g.get('fecha', '')
                        if fecha_gasto:
                            # Extraer YYYY-MM de la fecha del gasto
                            fecha_match = re.search(r'(\d{4})-(\d{2})', fecha_gasto)
                            if fecha_match:
                                g_year, g_month = fecha_match.groups()
                                if g_year == mes_year and g_month == mes_num:
                                    gastos_filtrados.append(g)
                                else:
                                    gastos_ignorados += 1
                                    debug_info.append(f"  IGNORADO (mes diferente): {g.get('gasto', '')} - fecha: {fecha_gasto}")
                            else:
                                # Si no se puede extraer fecha, incluir igual
                                gastos_filtrados.append(g)
                        else:
                            # Si no tiene fecha, incluir igual
                            gastos_filtrados.append(g)
                    
                    # TEMPORAL: Sin filtro de fecha para testing
                    # if gastos_ignorados > 0:
                    #     debug_info.append(f"Gastos ignorados por fecha: {gastos_ignorados}")
                    #     if len(gastos_filtrados) == 0:
                    #         st.warning(f"ATENCION: Todos los {gastos_ignorados} gastos fueron ignorados porque sus fechas no corresponden a {mes_seleccionado}.")
                    
                    # Temporal: no filtrar, guardar todos los gastos
                    # gastos = gastos_filtrados
                    
                    with st.expander("DEBUG: Procesamiento"):
                        for info in debug_info:
                            st.text(info)
                        st.info(f"Total gastos detectados: {len(gastos)}")
                    
                    if gastos:
                        filtrar_y_guardar_temp(gastos, mes_seleccionado)
                    else:
                        st.warning("No se detectaron gastos en el archivo")
    
    # ==================== MOSTRAR PREVIEW DE EGRESOS PROCESADOS ====================
    gastos_temp = st.session_state.get('egresos_procesados_temp', [])

    if gastos_temp:
        st.success(f"✅ {len(gastos_temp)} egresos listos para guardar")

        df_preview = pd.DataFrame(gastos_temp)

        # Asegurar columnas
        columnas_preview = ['fecha', 'gasto', 'monto', 'categoria', 'subcategoria']
        for col in columnas_preview:
            if col not in df_preview.columns:
                df_preview[col] = ''

        df_preview = df_preview[columnas_preview].copy()
        df_preview = df_preview.rename(columns={'gasto': 'GASTO'})

        st.dataframe(df_preview, use_container_width=True)

        total = sum(g.get('monto', 0) for g in gastos_temp)
        st.metric("Total a guardar", f"${total:,.2f} ARS")

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("💾 Guardar Egresos", type="primary", use_container_width=True):
                gastos = gastos_temp

                # 1. Leer datos FRESCOS desde disco
                datos_disco = cargar_datos()

                # 2. Asegurar estructura del mes
                if 'meses' not in datos_disco:
                    datos_disco['meses'] = {}
                if mes_seleccionado not in datos_disco['meses']:
                    datos_disco['meses'][mes_seleccionado] = {
                        'ingresos_bancarios': [],
                        'egresos': [],
                        'ajustes': [],
                        'ganancia_fondos': 0,
                        'plusvalia_propiedades': 0
                    }
                if 'egresos' not in datos_disco['meses'][mes_seleccionado]:
                    datos_disco['meses'][mes_seleccionado]['egresos'] = []

                egresos_en_disco = datos_disco['meses'][mes_seleccionado]['egresos']

                # 3. Deduplicar por u_id (más preciso que gasto+monto+fecha)
                ids_existentes = {e.get('u_id') for e in egresos_en_disco if e.get('u_id')}

                nuevos = []
                for g in gastos:
                    uid = g.get('u_id', '')

                    # Dedup por u_id si existe
                    if uid and uid in ids_existentes:
                        continue

                    # Dedup por contenido (solo si mismo gasto + monto + fecha + owner + medio_pago)
                    duplicado = False
                    for e in egresos_en_disco:
                        if (e.get('gasto', '').lower() == g.get('gasto', '').lower()
                            and abs(e.get('monto', 0) - g.get('monto', 0)) < 0.01
                            and e.get('fecha', '') == g.get('fecha', '')
                            and e.get('owner', '') == g.get('owner', '')
                            and e.get('medio_pago', '') == g.get('medio_pago', '')):
                            duplicado = True
                            break

                    if not duplicado:
                        nuevos.append(g)

                # 4. Guardar
                egresos_en_disco.extend(nuevos)
                datos_disco['meses'][mes_seleccionado]['egresos'] = egresos_en_disco
                guardar_datos(datos_disco)

                # 5. Verificar persistencia
                verificacion = cargar_datos()
                egresos_verificados = len(verificacion.get('meses', {}).get(mes_seleccionado, {}).get('egresos', []))

                # 6. Actualizar sesión
                st.session_state.datos = verificacion
                st.session_state.egresos_procesados_temp = []

                if nuevos:
                    st.success(f"✅ {len(nuevos)} egresos guardados para {mes_seleccionado} (total en disco: {egresos_verificados})")
                else:
                    st.warning(f"No se guardaron nuevos egresos (todos duplicados). Total en disco: {egresos_verificados}")

                st.rerun()

        with col2:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.egresos_procesados_temp = []
                st.rerun()
    
    # Mostrar debug persistente si hay info guardada
    if st.session_state.get('debug_guardado'):
        debug = st.session_state.debug_guardado
        if debug.get('mes') == mes_seleccionado:
            st.divider()
            st.subheader("📋 DEBUG - Último Guardado")
            st.write(f"**Egresos en disco ANTES:** {debug.get('antes', 0)}")
            st.write(f"**Egresos en disco DESPUÉS de agregar:** {debug.get('despues', 0)}")
            st.write(f"**Verificación (persistencia):** {debug.get('verificacion', 0)}")
            if debug.get('antes') == debug.get('verificacion'):
                st.success("✅ Datos correctamente persistidos")
            else:
                st.error("❌ ERROR: Los datos no se persistieron correctamente")
    
    # Mostrar egresos del mes seleccionado
    st.divider()
    st.subheader(f"Egresos de {mes_seleccionado}")
    
    if egresos:
        # ====================== LIMPIAR Y RECATEGORIZAR EGRESOS ======================
        CORRECIONES_SUBCATEGORIA = {
            'Sebastian Hacio Montene': {'categoria': 'comercios', 'subcategoria': 'indumentaria'},
            'Diego Alberto Rey': {'categoria': 'comercios', 'subcategoria': 'restaurant'},
            'Remo Franco SRL': {'categoria': 'comercios', 'subcategoria': 'indumentaria'},
            'Quincho': {'categoria': 'servicios', 'subcategoria': 'alquiler'},
            'Tu quincho': {'categoria': 'servicios', 'subcategoria': 'alquiler'},
            'MUNICIPALIDAD DE ROSARIO': {'categoria': 'impuestos', 'subcategoria': 'impuestos'},
            'EPE': {'categoria': 'servicios', 'subcategoria': 'servicios_publicos'},
            'CARGO POR SERVICIO': {'categoria': 'servicios', 'subcategoria': 'bancos'},
            'MOVISTAR': {'categoria': 'servicios', 'subcategoria': 'telefonia'},
            'ADT': {'categoria': 'servicios', 'subcategoria': 'seguridad'},
            'AGUAS SANTAFESINAS': {'categoria': 'servicios', 'subcategoria': 'servicios_publicos'},
            'PERSONAL': {'categoria': 'servicios', 'subcategoria': 'telefonia'},
            'Instituto Gamma': {'categoria': 'servicios', 'subcategoria': 'salud'},
        }
        
        for egreso in egresos:
            gasto = egreso.get('gasto', '')
            for clave, valores in CORRECIONES_SUBCATEGORIA.items():
                if clave.lower() in gasto.lower():
                    egreso['categoria'] = valores['categoria']
                    egreso['subcategoria'] = valores['subcategoria']
                    break
            if egreso.get('categoria') == 'otros':
                categoria, subcategoria, _ = categorizar_gasto(gasto, datos)
                egreso['categoria'] = categoria
                egreso['subcategoria'] = subcategoria
        
        # NO guardar a disco - solo actualizar en memoria para mostrar
        # (los datos ya fueron guardados correctamente en el botón)
        
        # ====================== MOSTRAR EGRESOS ======================
        df = pd.DataFrame(egresos)
        
        total = sum(e.get('monto', 0) for e in egresos)
        st.metric("Total Egresos del Mes", f"${total:,.2f} ARS")
        
        if 'categoria' in df.columns and 'monto' in df.columns:
            try:
                st.subheader("Por Categoría")
                por_cat = df.groupby('categoria')['monto'].sum()
                st.bar_chart(por_cat)
            except Exception:
                pass
        
        # ====================== TABLA DE DETALLE DE EGRESOS ======================
        st.subheader("Detalle de Egresos")
        
        df_egresos = pd.DataFrame(egresos)
        columnas_mostrar = ['fecha', 'gasto', 'monto', 'categoria', 'subcategoria']
        
        for col in columnas_mostrar:
            if col not in df_egresos.columns:
                df_egresos[col] = ''
        
        df_display = df_egresos[columnas_mostrar].copy()
        df_display.columns = ['Fecha', 'Gasto', 'Monto (ARS)', 'Categoría', 'Sub-Categoría']
        
        if 'Monto (ARS)' in df_display.columns:
            df_display['Monto (ARS)'] = df_display['Monto (ARS)'].apply(
                lambda x: f"${x:,.2f}" if pd.notna(x) and x > 0 else '-'
            )
        
        st.dataframe(
            df_display,
            width='stretch',
            hide_index=True,
            column_config={
                "Fecha": st.column_config.TextColumn(width="small"),
                "Gasto": st.column_config.TextColumn(width="medium"),
                "Monto (ARS)": st.column_config.TextColumn(width="small"),
                "Categoría": st.column_config.TextColumn(width="small"),
                "Sub-Categoría": st.column_config.TextColumn(width="small"),
            }
        )
    else:
        st.info("No hay egresos que coincidan con los filtros seleccionados")
    
    # ---- SECCION: DESGLOSAR PAGOS (SUB-PAGOS) ----
    st.divider()
    st.subheader("Desglosar Pago (Sub-pagos)")
    
    # Solo pagos que se pueden desglosar (no son hijos, no tienen subpagos aun)
    pagos_divisibles = [
        e for e in egresos
        if not e.get('parent_id')
        and not e.get('sub_pagos')
        and e.get('monto', 0) > 0
    ]
    
    if not pagos_divisibles:
        st.info("No hay pagos disponibles para desglosar.")
    else:
            opciones = {
                e.get('u_id', f"idx_{i}"): f"{e.get('fecha','-')[:10]} | {e.get('gasto','-')} | ${e.get('monto',0):,.2f} | {e.get('owner','-')}"
                for i, e in enumerate(egresos)
                if not e.get('parent_id') and not e.get('sub_pagos') and e.get('monto', 0) > 0
            }
            
            col_sel, col_upl = st.columns([1, 1])
            with col_sel:
                pago_id = st.selectbox("Seleccionar pago a desglosar:", options=list(opciones.keys()), format_func=lambda x: opciones.get(x, x))
            
            pago_original = next((e for e in egresos if e.get('u_id') == pago_id), None)
            
            if pago_original:
                st.caption(f"**Pago seleccionado:** {pago_original.get('gasto', '-')} — ${pago_original.get('monto', 0):,.2f}")
            
            with col_upl:
                ticket_file = st.file_uploader("Subir ticket (JPG/PDF):", type=['jpg', 'jpeg', 'png', 'pdf'], key="upl_ticket_sp")
            
            if ticket_file:
                col_info, col_btn = st.columns([2, 1])
                with col_info:
                    if ticket_file.type.startswith('image'):
                        st.image(ticket_file, width=300)
                    else:
                        st.write(f"Archivo PDF: {ticket_file.name}")
                with col_btn:
                    if st.button("Extraer Sub-pagos (PaddleOCR)", key="btn_extraer_sp", type="primary"):
                        with st.spinner("Extrayendo sub-pagos..."):
                            subpagos_raw, texto_raw = extraer_subpagos(ticket_file, datos)
                            if subpagos_raw:
                                st.session_state['sp_tmp'] = subpagos_raw
                                st.session_state['sp_parent_id'] = pago_id
                                st.success(f"{len(subpagos_raw)} sub-pagos detectados.")
                            else:
                                st.warning("No se detectaron sub-pagos.")
                                with st.expander("Texto OCR:"):
                                    st.text(texto_raw or "(vacio)")
            
            # Si hay subpagos detectados para revision
            if st.session_state.get('sp_tmp') and st.session_state.get('sp_parent_id') == pago_id:
                subpagos_rev = st.session_state['sp_tmp']
                st.write(f"**{len(subpagos_rev)} sub-pagos detectados — revisalos antes de confirmar:**")
                
                total_rev = 0
                for si, sp in enumerate(subpagos_rev):
                    sk = f"sp_{pago_id}_{si}"
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        sp['descripcion'] = st.text_input("Descripcion", sp.get('descripcion', ''), key=f"desc_{sk}", label_visibility="collapsed")
                    with c2:
                        sp['monto'] = st.number_input("Monto", value=float(sp.get('monto', 0)), min_value=0.0, key=f"monto_{sk}", label_visibility="collapsed")
                    with c3:
                        st.text(f"${sp.get('monto', 0):,.2f}")
                    total_rev += sp.get('monto', 0)
                
                dif = (pago_original.get('monto', 0) if pago_original else 0) - total_rev
                col_met, col_conf, col_canc = st.columns([2, 1, 1])
                with col_met:
                    st.metric("Total desglosado", f"${total_rev:,.2f}", delta=f"Dif: ${dif:,.2f}", delta_color="off")
                with col_canc:
                    if st.button("Descartar", key="btn_descartar_sp"):
                        st.session_state.pop('sp_tmp', None)
                        st.session_state.pop('sp_parent_id', None)
                        st.rerun()
                with col_conf:
                    if st.button("Confirmar Division", key="btn_confirmar_sp", type="primary", width='stretch'):
                        if pago_original:
                            padre_fecha = pago_original.get('fecha', '')
                            padre_owner = pago_original.get('owner', '')
                            padre_medio = pago_original.get('medio_pago', '')
                            padre_moneda = pago_original.get('moneda', 'ARS')
                            padre_fuente = pago_original.get('fuente', '')
                            
                            # 1. Leer datos FRESCOS desde disco
                            datos_disco = cargar_datos()
                            egresos_disco = datos_disco.get('meses', {}).get(mes_seleccionado, {}).get('egresos', [])
                            
                            # 2. Eliminar padre de los egresos en disco
                            egresos_disco = [e for e in egresos_disco if e.get('u_id') != pago_id]
                            
                            # 3. Crear hijos
                            hijos = []
                            for sp in subpagos_rev:
                                desc_sp = sp.get('descripcion', '').strip()
                                monto_sp = sp.get('monto', 0)
                                if desc_sp and monto_sp > 0:
                                    cat, subcat, _ = categorizar_gasto(desc_sp, datos_disco)
                                    hijos.append({
                                        'u_id': generar_id(),
                                        'parent_id': pago_id,
                                        'fecha': padre_fecha,
                                        'gasto': desc_sp,
                                        'monto': monto_sp,
                                        'moneda': padre_moneda,
                                        'fuente': padre_fuente or 'Santa Fe Servicios',
                                        'categoria': cat,
                                        'subcategoria': subcat,
                                        'owner': padre_owner,
                                        'medio_pago': padre_medio,
                                    })
                            
                            # 4. Agregar hijos a los egresos de disco
                            egresos_disco.extend(hijos)
                            
                            # 5. Guardar en disco
                            datos_disco['meses'][mes_seleccionado]['egresos'] = egresos_disco
                            guardar_datos(datos_disco)
                            st.session_state.datos = datos_disco
                            
                            # 6. Limpiar estado temporal
                            st.session_state.pop('sp_tmp', None)
                            st.session_state.pop('sp_parent_id', None)
                            
                            st.success(f"Pago desglosado en {len(hijos)} sub-pagos.")
                            st.rerun()


def mostrar_propiedades(mes):
    st.header("Propiedades")

    datos = st.session_state.datos
    
    # 1. Boton Actulizar Mercado Inmobiliario en Tiempo Real
    c1, c2 = st.columns([3, 2])
    with c2:
        if st.button("🌐 Actualizar Base Mercado (Scraping)", help="Recalcula el valor referencial (Base Ciudad 2026) escaneando ofertas reales en la web hoy."):
            with st.spinner("Consultando precio del m² en vivo desde Argenprop... (puede demorar unos segundos)"):
                try:
                    from parsers.mercado_inmobiliario import actualizar_base_ciudad_web
                    nuevo_valor = actualizar_base_ciudad_web()
                    if nuevo_valor:
                        st.success(f"¡Base de tasación actualizada! Nuevo promedio general base p/ Rosario: USD {nuevo_valor}/m²")
                    else:
                        st.error("No se pudo extraer el valor del mercado en este momento.")
                except Exception as e:
                    st.error(f"Fallo al conectar con el portal inmobiliario: {e}")

    # 2. Selector de período local
    meses_disponibles = sorted(datos.get('meses', {}).keys(), reverse=True)
    if meses_disponibles:
        idx_default = meses_disponibles.index(mes) if mes in meses_disponibles else 0
        mes_prop = st.selectbox(
            "📅 Período de valuación y plusvalía",
            meses_disponibles,
            index=idx_default,
            key="mes_prop_selector"
        )
    else:
        mes_prop = mes

    activos = datos.get('activos', [])
    propiedades = [a for a in activos if a.get('tipo') == 'propiedad']

    usdt_ars = obtener_usdt_ars_binance() or 1500

    # Agregar propiedad (formulario colapsable)
    with st.expander("➕ Agregar Propiedad", expanded=False):
        with st.form("agregar_propiedad"):
            st.caption("Datos básicos")
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre de la propiedad")
                tipo = st.selectbox("Tipo", ["departamento", "casa", "local", "oficina", "terreno"])
                zona = st.selectbox("Zona / Barrio", [
                    "Centro", "Macrocentro", "Barrio Inglés", "Pichincha", "Abasto",
                    "Martin", "Facultades", "Puerto Norte", "Barrio Tigre",
                    "Rosario Norte", "Alvear", "San Martín", "General Paz",
                    "Echesortu", "Fisherton", "Ruta 9", "Sur", "Norte", "Oeste",
                    "República de la Sexta", "Otro"
                ])
                direccion = st.text_input("Dirección (opcional)")
            with col2:
                m2 = st.number_input("Metros cuadrados (m²)", min_value=0, step=1)
                m2_cubiertos = st.number_input("Metros cubiertos (m²)", min_value=0, step=1)
                dormitorios = st.number_input("Dormitorios", min_value=0, max_value=10)
                baños = st.number_input("Baños", min_value=0, max_value=10)
                antiguedad = st.number_input("Antigüedad (años)", min_value=0)

            st.caption("Características constructivas y de mercado")
            col3, col4 = st.columns(2)
            with col3:
                estado_detalle = st.selectbox("Estado detallado", [
                    "a estrenar", "excelente", "muy bueno", "bueno", "regular", "a refaccionar"
                ], index=3)
                piso = st.number_input("Piso (0 = planta baja)", min_value=0, max_value=30, value=0)
                orientacion = st.selectbox("Orientación", [
                    "norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"
                ], index=2)
                calidad_edificio = st.selectbox("Calidad del edificio", ["premium", "media", "economica"], index=1)
                ventilacion = st.selectbox("Ventilación", ["cruzada", "simple", "ninguna"], index=1)
            with col4:
                terminaciones_suelo = st.selectbox("Terminaciones de suelo", ["madera_noble", "porcelanato", "ceramico", "estandar"], index=3)
                distribucion_cocina = st.selectbox("Distribución de cocina", ["independiente", "lavadero_sectorizado", "integrada"], index=2)
                carpinteria = st.selectbox("Carpintería / Vidrios", ["piso_techo", "dvh", "estandar"], index=2)
                detalles_cat = st.multiselect("Detalles de Categoría / Amenities", [
                    "caldera_central", "radiadores", "seguridad_24hs", "totem_seguridad",
                    "aberturas_premium", "balcon_terraza", "pileta", "sum", "gym"
                ])
                cochera = st.checkbox("Cochera")

            st.caption("Datos de compra")
            col5, col6 = st.columns(2)
            with col5:
                valor_compra_usd = st.number_input("Valor de compra (USD)", min_value=0.0, step=1000.0)
                fecha_compra = st.date_input("Fecha de compra", value=datetime(2020, 1, 1), min_value=datetime(2000, 1, 1))
            with col6:
                moneda_compra = st.selectbox("Moneda de compra", ["USD", "ARS"])

            submitted = st.form_submit_button("Guardar Propiedad")

            if submitted and nombre:
                existe = any(a.get('nombre') == nombre and a.get('tipo') == 'propiedad' for a in activos)
                if existe:
                    st.warning(f"La propiedad '{nombre}' ya existe")
                else:
                    from parsers.mercado_inmobiliario import valuar_propiedad
                    prop_data = {
                    'id': f"prop_{uuid.uuid4().hex[:8]}",
                    'tipo': 'propiedad',
                    'nombre': nombre,
                    'tipo_inmueble': tipo,
                    'zona': zona,
                    'direccion': direccion,
                    'm2': m2,
                    'm2_cubiertos': m2_cubiertos,
                    'dormitorios': dormitorios,
                    'baños': baños,
                    'antiguedad': antiguedad,
                    'estado_detalle': estado_detalle,
                    'piso': piso,
                    'orientacion': orientacion,
                    'calidad_edificio': calidad_edificio,
                    'ventilacion': ventilacion,
                    'terminaciones_suelo': terminaciones_suelo,
                    'distribucion_cocina': distribucion_cocina,
                    'carpinteria': carpinteria,
                    'detalles_categoria': detalles_cat,
                    'cochera': cochera,
                    'espacios_exteriores': [], # Legacy
                    'valor_compra_usd': valor_compra_usd,
                    'fecha_compra': fecha_compra.strftime('%Y-%m-%d'),
                    'moneda_compra': moneda_compra,
                    'valor_tasacion_usd': 0,
                    'valor_tasacion_ars': 0,
                    'valor_anterior_ars': 0,
                    'valor_m2_usd': 0,
                    'tasaciones': [],
                    'ultima_valuacion': None
                }
                activos.append(prop_data)
                datos['activos'] = activos
                guardar_datos(datos)
                # Limpiar session_state de valuaciones para evitar datos stale
                keys_to_clear = [k for k in st.session_state.keys() if k.startswith("valuacion_prop_")]
                for k in keys_to_clear:
                    del st.session_state[k]
                st.success(f"Propiedad '{nombre}' guardada como activo")
                st.rerun()

    # Mostrar propiedades existentes
    if propiedades:
        st.subheader("Propiedades Registradas")
        df = pd.DataFrame(propiedades)
        cols = ['nombre', 'tipo_inmueble', 'zona', 'm2', 'dormitorios', 'baños',
                'estado_detalle', 'calidad_edificio', 'valor_tasacion_usd']
        available = [c for c in cols if c in df.columns]
        st.dataframe(df[available], use_container_width=True)

    # Sección: Valuación automática + Editar
    for prop in propiedades:
        with st.container():
            st.divider()

            # SIEMPRE calcular del motor v4.0 (serie histórica real)
            from parsers.mercado_inmobiliario import valuar_propiedad
            resultado = valuar_propiedad(prop, fecha_ref=mes_prop)
            valor_display = resultado['valor_propiedad_usd']
            m2_display = resultado['valor_m2_actual_usd']

            # Plusvalía: comparar mes seleccionado vs mes anterior (ambos del motor)
            mes_anterior_dt = datetime.strptime(mes_prop, "%Y-%m") - timedelta(days=1)
            mes_anterior = mes_anterior_dt.strftime("%Y-%m")
            resultado_anterior = valuar_propiedad(prop, fecha_ref=mes_anterior)
            plusvalia_usd = valor_display - resultado_anterior['valor_propiedad_usd']
            plusvalia_pct = ((valor_display / resultado_anterior['valor_propiedad_usd']) - 1) * 100 if resultado_anterior['valor_propiedad_usd'] > 0 else 0

            # Header de la propiedad
            c_head1, c_head2, c_head3 = st.columns([3, 1, 1])
            with c_head1:
                st.write(f"**{prop['nombre']}**")
                st.caption(
                    f"{prop.get('zona', '')} | {prop.get('m2', 0)}m² | "
                    f"{prop.get('estado_detalle', '')} | {prop.get('calidad_edificio', '')}"
                )
                if valor_display > 0:
                    st.metric(f"Valor ({mes_prop})", f"${valor_display:,.0f} USD")
                    st.caption("💡 Serie histórica real v4.0")
            with c_head2:
                if st.button("✏️ Editar", key=f"edit_btn_{prop['id']}"):
                    st.session_state[f"editing_prop_{prop['id']}"] = True
            with c_head3:
                if st.button("🗑 Eliminar", key=f"del_prop_{prop['id']}", type="secondary"):
                    datos['activos'] = [a for a in activos if a.get('id') != prop['id']]
                    guardar_datos(datos)
                    st.session_state.datos = datos
                    # Limpiar valuación y edición de esta propiedad
                    st.session_state.pop(f"valuacion_{prop['id']}", None)
                    st.session_state.pop(f"editing_prop_{prop['id']}", None)
                    st.success(f"Propiedad '{prop['nombre']}' eliminada")
                    st.rerun()

            # Formulario de edición
            if st.session_state.get(f"editing_prop_{prop['id']}", False):
                with st.form(f"form_edit_{prop['id']}"):
                    st.caption("Editar datos de la propiedad")
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_nombre = st.text_input("Nombre", value=prop.get('nombre', ''), key=f"e_nombre_{prop['id']}")
                        e_tipo = st.selectbox("Tipo", ["departamento", "casa", "local", "oficina", "terreno"],
                                             index=["departamento", "casa", "local", "oficina", "terreno"].index(prop.get('tipo_inmueble', 'departamento')),
                                             key=f"e_tipo_{prop['id']}")
                        e_zona = st.selectbox("Zona / Barrio", [
                            "Centro", "Macrocentro", "Barrio Inglés", "Pichincha", "Abasto",
                            "Martin", "Facultades", "Puerto Norte", "Barrio Tigre",
                            "Rosario Norte", "Alvear", "San Martín", "General Paz",
                            "Echesortu", "Fisherton", "Ruta 9", "Sur", "Norte", "Oeste",
                            "República de la Sexta", "Otro"
                        ], index=["Centro", "Macrocentro", "Barrio Inglés", "Pichincha", "Abasto",
                            "Martin", "Facultades", "Puerto Norte", "Barrio Tigre",
                            "Rosario Norte", "Alvear", "San Martín", "General Paz",
                            "Echesortu", "Fisherton", "Ruta 9", "Sur", "Norte", "Oeste",
                            "República de la Sexta", "Otro"].index(prop.get('zona', 'Otro')),
                            key=f"e_zona_{prop['id']}")
                        e_m2 = st.number_input("Metros cuadrados (m²)", min_value=0, value=prop.get('m2', 0), key=f"e_m2_{prop['id']}")
                    with ec2:
                        e_dorm = st.number_input("Dormitorios", min_value=0, max_value=10, value=prop.get('dormitorios', 0), key=f"e_dorm_{prop['id']}")
                        e_baños = st.number_input("Baños", min_value=0, max_value=10, value=prop.get('baños', 0), key=f"e_baños_{prop['id']}")
                        e_estado = st.selectbox("Estado detallado", ["a estrenar", "excelente", "muy bueno", "bueno", "regular", "a refaccionar"],
                                               index=["a estrenar", "excelente", "muy bueno", "bueno", "regular", "a refaccionar"].index(prop.get("estado_detalle", "bueno")) if prop.get("estado_detalle") in ["a estrenar", "excelente", "muy bueno", "bueno", "regular", "a refaccionar"] else 3,
                                               key=f"e_estado_{prop['id']}")
                        e_calidad = st.selectbox("Calidad del edificio", ["premium", "media", "economica"],
                                                index=["premium", "media", "economica"].index(prop.get('calidad_edificio', 'media')),
                                                key=f"e_calidad_{prop['id']}")
                        e_vent = st.selectbox("Ventilación", ["cruzada", "simple", "ninguna"],
                                             index=["cruzada", "simple", "ninguna"].index(prop.get('ventilacion', 'simple')) if prop.get('ventilacion') in ["cruzada", "simple", "ninguna"] else 1,
                                             key=f"e_vent_{prop['id']}")
                        e_suelo = st.selectbox("Suelo", ["madera_noble", "porcelanato", "ceramico", "estandar"],
                                              index=["madera_noble", "porcelanato", "ceramico", "estandar"].index(prop.get('terminaciones_suelo', 'estandar')) if prop.get('terminaciones_suelo') in ["madera_noble", "porcelanato", "ceramico", "estandar"] else 3,
                                              key=f"e_suelo_{prop['id']}")
                        e_cocina = st.selectbox("Cocina", ["independiente", "lavadero_sectorizado", "integrada"],
                                               index=["independiente", "lavadero_sectorizado", "integrada"].index(prop.get('distribucion_cocina', 'integrada')) if prop.get('distribucion_cocina') in ["independiente", "lavadero_sectorizado", "integrada"] else 2,
                                               key=f"e_cocina_{prop['id']}")
                        e_carp = st.selectbox("Carpintería", ["piso_techo", "dvh", "estandar"],
                                             index=["piso_techo", "dvh", "estandar"].index(prop.get('carpinteria', 'estandar')) if prop.get('carpinteria') in ["piso_techo", "dvh", "estandar"] else 2,
                                             key=f"e_carp_{prop['id']}")
                        e_detalles = st.multiselect("Detalles", [
                            "caldera_central", "radiadores", "seguridad_24hs", "totem_seguridad",
                            "aberturas_premium", "balcon_terraza", "pileta", "sum", "gym"
                        ], default=prop.get('detalles_categoria', []), key=f"e_detalles_{prop['id']}")

                    e_submit = st.form_submit_button("Guardar Cambios")
                    if e_submit and e_nombre:
                        for activo in datos.get('activos', []):
                            if activo.get('id') == prop['id']:
                                activo['nombre'] = e_nombre
                                activo['tipo_inmueble'] = e_tipo
                                activo['zona'] = e_zona
                                activo['m2'] = e_m2
                                activo['dormitorios'] = e_dorm
                                activo['baños'] = e_baños
                                activo['estado_detalle'] = e_estado
                                activo['calidad_edificio'] = e_calidad
                                activo['ventilacion'] = e_vent
                                activo['terminaciones_suelo'] = e_suelo
                                activo['distribucion_cocina'] = e_cocina
                                activo['carpinteria'] = e_carp
                                activo['detalles_categoria'] = e_detalles
                        guardar_datos(datos)
                        st.session_state.datos = datos
                        st.session_state[f"editing_prop_{prop['id']}"] = False
                        st.success(f"Propiedad '{e_nombre}' actualizada")
                        st.rerun()

                if st.button("Cancelar edición", key=f"cancel_edit_{prop['id']}"):
                    st.session_state[f"editing_prop_{prop['id']}"] = False
                    st.rerun()
                st.divider()

            # Valuación automática del motor
            st.caption("Valuación Automática")
            if st.button("💾 Guardar valuación", key=f"valuar_{prop['id']}"):
                valor_m2 = resultado['valor_m2_actual_usd']
                valor_prop = resultado['valor_propiedad_usd']
                tendencia = resultado['tendencia']
                confianza = resultado['nivel_confianza']

                # Actualizar propiedad con valuación
                for activo in datos.get('activos', []):
                    if activo.get('id') == prop['id']:
                        activo['valor_tasacion_usd'] = valor_prop
                        activo['valor_tasacion_ars'] = valor_prop * usdt_ars
                        activo['valor_m2_usd'] = valor_m2
                        activo['ultima_valuacion'] = datetime.now().strftime('%Y-%m-%d')

                        tasacion = {
                            'fecha': datetime.now().strftime('%Y-%m-%d'),
                            'valor_usd': valor_prop,
                            'valor_ars': valor_prop * usdt_ars,
                            'valor_m2_usd': valor_m2,
                            'mes': mes_prop,
                            'fuente': 'motor_valuacion'
                        }
                        activo.setdefault('tasaciones', []).append(tasacion)

                # Guardar plusvalía en el mes seleccionado
                plusvalia_ars = plusvalia_usd * usdt_ars
                datos.setdefault('meses', {}).setdefault(mes_prop, {}).setdefault('plusvalia_propiedades', 0)
                datos['meses'][mes_prop]['plusvalia_propiedades'] = plusvalia_ars

                guardar_datos(datos)
                st.session_state.datos = datos
                st.success(f"Valuación guardada para {mes_prop}: USD {valor_prop:,.0f}")
                st.rerun()

            # Mostrar resultados del motor
            st.success(f"Valuación {mes_prop}: USD {valor_display:,.0f}")
            col_v1, col_v2, col_v3, col_v4 = st.columns(4)
            col_v1.metric("Valor m² (USD)", f"${m2_display:,.0f}")
            col_v2.metric("Valor Propiedad", f"${valor_display:,.0f}")
            col_v3.metric("Tendencia", {"alcista": "📈", "bajista": "📉", "neutral": "➡️"}.get(resultado['tendencia'], "➡️"))
            col_v4.metric("Confianza", {"alto": "🟢", "medio": "🟡", "bajo": "🔴"}.get(resultado['nivel_confianza'], "🟡"))

            p_col1, p_col2 = st.columns(2)
            p_col1.metric(
                f"Plusvalía vs {mes_anterior}",
                f"USD {plusvalia_usd:,.0f}",
                delta=f"{plusvalia_pct:+.2f}%",
                delta_color="normal"
            )
            p_col2.caption("Fuente: motor v4.0 (serie histórica real)")

            with st.expander("Detalle de la valuación"):
                st.write(resultado['justificacion'])
                st.write(f"**Rango estimado:** {resultado['rango_m2']}")
                st.write(f"**Plusvalía mensual (motor):** {resultado['plusvalia_mensual_pct']:+.2f}%")
                st.write(f"**Plusvalía acumulada:** {resultado['plusvalia_acumulada_pct']:+.2f}%")

                serie = resultado.get('serie_mensual_m2', [])
                if serie:
                    st.caption("Serie histórica del m² (USD)")
                    df_serie = pd.DataFrame(serie)
                    df_serie.columns = ['Fecha', 'Valor m² USD', 'Fuente']
                    st.line_chart(df_serie.set_index('Fecha')['Valor m² USD'])

            st.divider()

    # Mostrar plusvalía total del mes seleccionado
    if propiedades:
        st.divider()
        plusvalia_total_mes = datos.get('meses', {}).get(mes_prop, {}).get('plusvalia_propiedades', 0)
        st.metric(f"Plusvalía Total Propiedades ({mes_prop})", f"${plusvalia_total_mes:,.0f} ARS")

        with st.expander("📊 Historial de plusvalía por mes"):
            hist = {
                m: v.get('plusvalia_propiedades', 0)
                for m, v in datos.get('meses', {}).items()
                if v.get('plusvalia_propiedades', 0) != 0
            }
            if hist:
                # Ordenar por clave (mes)
                sorted_hist = sorted(hist.items())
                df_hist = pd.DataFrame(sorted_hist, columns=['Mes', 'Plusvalía ARS'])
                st.bar_chart(df_hist.set_index('Mes'))
                st.table(df_hist)
            else:
                st.info("No hay datos de plusvalía guardados para mostrar en el historial.")


def mostrar_ajustes(mes_from_sidebar):
    st.header("Ajustes Manuales y Efectivo")

    datos = st.session_state.datos

    # ====== SELECTOR DE PERIODO PROPIO ======
    meses_disponibles = sorted(datos.get('meses', {}).keys())
    if not meses_disponibles:
        meses_disponibles = [mes_from_sidebar or '2026-03']

    if mes_from_sidebar in meses_disponibles:
        default_idx = meses_disponibles.index(mes_from_sidebar)
    else:
        default_idx = len(meses_disponibles) - 1

    mes = st.selectbox(
        "Periodo para este ajuste",
        meses_disponibles,
        index=default_idx,
        key="ajuste_periodo_selector"
    )

    # Asegurar estructura del mes
    if mes not in datos.get('meses', {}):
        datos.setdefault('meses', {})[mes] = {
            'ingresos_bancarios': [],
            'egresos': [],
            'ganancia_fondos': 0,
            'plusvalia_propiedades': 0,
            'ajustes': []
        }

    ajustes = datos['meses'][mes].get('ajustes', [])

    # ====== TABS: EFECTIVO vs OTROS AJUSTES ======
    tab_efectivo, tab_ajuste, tab_ver = st.tabs([
        "💵 Efectivo (Ingreso/Egreso)",
        "🔧 Ajuste Manual",
        "📋 Ver Ajustes del Periodo"
    ])

    # ====== TAB EFECTIVO ======
    with tab_efectivo:
        st.subheader(f"Registrar Movimiento en Efectivo — {mes}")
        st.info("Usá esta sección para cargar ingresos o egresos en efectivo que no aparecen en extractos bancarios.")

        OWNERS = ["Gustavo", "Vero", "Sol", "Tomas"]

        CATEGORIAS_EGRESO_EFECTIVO = [
            "(auto-detectar)",
            "comercios/supermercado",
            "comercios/restaurant",
            "comercios/carniceria",
            "comercios/panaderia",
            "comercios/verduleria",
            "comercios/farmacia",
            "comercios/combustible",
            "comercios/indumentaria",
            "comercios/ferreteria",
            "comercios/bazar",
            "comercios/otros",
            "servicios/salud",
            "servicios/transporte",
            "servicios/educacion",
            "servicios/peluqueria",
            "servicios/otros",
            "familia/hijos",
            "familia/transferencia",
            "impuestos/impuestos",
            "otros/otros",
        ]

        CATEGORIAS_INGRESO_EFECTIVO = [
            "sueldo",
            "alquiler",
            "honorarios",
            "venta",
            "prestamo",
            "regalo",
            "otro",
        ]

        with st.form("form_efectivo", clear_on_submit=True):
            direccion = st.radio(
                "Tipo de movimiento",
                ["Egreso", "Ingreso"],
                horizontal=True
            )

            col1, col2 = st.columns(2)

            with col1:
                owner_ef = st.selectbox("¿Quién?", OWNERS, key="ef_owner")
                fecha_ef = st.date_input(
                    "Fecha",
                    value=datetime.now(),
                    key="ef_fecha"
                )

            with col2:
                descripcion_ef = st.text_input(
                    "Descripción",
                    placeholder="Ej: Compra verdulería, Regalo cumple, etc.",
                    key="ef_desc"
                )
                monto_ef = st.number_input(
                    "Monto ($ARS)",
                    min_value=0.0,
                    step=100.0,
                    key="ef_monto"
                )

            # Ambos selectbox siempre visibles, el usuario usa el que corresponda
            cat_col1, cat_col2 = st.columns(2)
            with cat_col1:
                cat_rapida_egreso = st.selectbox(
                    "Categoría (si es egreso)",
                    CATEGORIAS_EGRESO_EFECTIVO,
                    index=0,
                    key="ef_cat_egreso"
                )
            with cat_col2:
                cat_rapida_ingreso = st.selectbox(
                    "Categoría (si es ingreso)",
                    CATEGORIAS_INGRESO_EFECTIVO,
                    index=0,
                    key="ef_cat_ingreso"
                )

            submitted = st.form_submit_button("💾 Guardar Movimiento Efectivo", type="primary")

        # Procesar FUERA del form pero usando los valores
        if submitted and monto_ef > 0 and descripcion_ef.strip():
            fecha_str = fecha_ef.strftime('%Y-%m-%d')

            if direccion == "Egreso":
                if cat_rapida_egreso == "(auto-detectar)":
                    cat, subcat, gasto_final = categorizar_gasto(descripcion_ef, datos)
                else:
                    partes = cat_rapida_egreso.split('/')
                    cat = partes[0]
                    subcat = partes[1] if len(partes) > 1 else partes[0]
                    gasto_final = descripcion_ef.strip().title()

                egreso = {
                    'fecha': fecha_str,
                    'gasto': gasto_final,
                    'monto': monto_ef,
                    'moneda': 'ARS',
                    'fuente': 'Efectivo',
                    'categoria': cat,
                    'subcategoria': subcat,
                    'owner': owner_ef,
                    'medio_pago': 'Efectivo',
                    'u_id': generar_id()
                }

                datos_disco = cargar_datos()
                datos_disco.setdefault('meses', {}).setdefault(mes, {
                    'ingresos_bancarios': [], 'egresos': [], 'ajustes': [],
                    'ganancia_fondos': 0, 'plusvalia_propiedades': 0
                })
                datos_disco['meses'][mes].setdefault('egresos', []).append(egreso)
                guardar_datos(datos_disco)
                st.session_state.datos = datos_disco
                st.success(f"✅ Egreso efectivo guardado: {gasto_final} ${monto_ef:,.2f} ({owner_ef})")
                st.rerun()

            else:  # Ingreso
                ingreso = {
                    'fecha': fecha_str,
                    'descripcion': descripcion_ef.strip(),
                    'monto': monto_ef,
                    'monto_ars': None,
                    'banco': 'efectivo',
                    'categoria': cat_rapida_ingreso,
                    'tasas': None,
                    'owner': owner_ef
                }

                datos_disco = cargar_datos()
                datos_disco.setdefault('meses', {}).setdefault(mes, {
                    'ingresos_bancarios': [], 'egresos': [], 'ajustes': [],
                    'ganancia_fondos': 0, 'plusvalia_propiedades': 0
                })
                datos_disco['meses'][mes].setdefault('ingresos_bancarios', []).append(ingreso)
                guardar_datos(datos_disco)
                st.session_state.datos = datos_disco
                st.success(f"✅ Ingreso efectivo guardado: {descripcion_ef} ${monto_ef:,.2f} ({owner_ef})")
                st.rerun()

        elif submitted:
            st.warning("Completá descripción y monto mayor a 0")

    # ====== TAB AJUSTE MANUAL - SIMPLIFICADO ======
    with tab_ajuste:
        st.subheader(f"Ajuste Manual — {mes}")
        st.info(
            "Para correcciones puntuales: "
            "diferencias de cambio, devoluciones, préstamos, etc. "
            "Se registran como ajuste contable, NO como egreso ni ingreso."
        )

        with st.form("form_ajuste", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                tipo_aj = st.selectbox("Tipo", [
                    "correccion", "devolucion", "ajuste_cambio",
                    "prestamo", "otro"
                ])
                descripcion_aj = st.text_input("Descripción", key="aj_desc")
            with col2:
                monto_aj = st.number_input("Monto", min_value=0.0, key="aj_monto")
                moneda_aj = st.selectbox("Moneda", ["ARS", "USD", "CLP"])
                signo_aj = st.radio("Signo", ["Positivo (+)", "Negativo (-)"], horizontal=True)

            submitted_aj = st.form_submit_button("Agregar Ajuste")

        if submitted_aj and descripcion_aj and monto_aj > 0:
            monto_final = monto_aj if "Positivo" in signo_aj else -monto_aj

            ajuste = {
                'tipo': tipo_aj,
                'descripcion': descripcion_aj,
                'monto': monto_final,
                'moneda': moneda_aj,
                'fecha': datetime.now().strftime('%Y-%m-%d'),
                'periodo': mes
            }

            datos_disco = cargar_datos()
            datos_disco.setdefault('meses', {}).setdefault(mes, {
                'ingresos_bancarios': [], 'egresos': [], 'ajustes': [],
                'ganancia_fondos': 0, 'plusvalia_propiedades': 0
            })
            datos_disco['meses'][mes].setdefault('ajustes', []).append(ajuste)
            guardar_datos(datos_disco)
            st.session_state.datos = datos_disco
            st.success(f"Ajuste guardado: {descripcion_aj} {moneda_aj} {monto_final:,.2f}")
            st.rerun()

    # ====== TAB VER AJUSTES ======
    with tab_ver:
        st.subheader(f"Ajustes y Efectivo del Periodo — {mes}")

        # Mostrar ajustes
        ajustes_mes = datos.get('meses', {}).get(mes, {}).get('ajustes', [])
        if ajustes_mes:
            st.caption(f"{len(ajustes_mes)} ajustes")
            df_aj = pd.DataFrame(ajustes_mes)
            st.dataframe(df_aj, use_container_width=True)

            total_aj = sum(a.get('monto', 0) for a in ajustes_mes)
            st.metric("Total Ajustes", f"${total_aj:,.2f}")
        else:
            st.info("Sin ajustes manuales")

        # Mostrar egresos en efectivo del mes
        egresos_mes = datos.get('meses', {}).get(mes, {}).get('egresos', [])
        efectivo_egresos = [e for e in egresos_mes if e.get('medio_pago') == 'Efectivo']

        if efectivo_egresos:
            st.divider()
            st.caption(f"{len(efectivo_egresos)} egresos en efectivo")
            df_ef = pd.DataFrame(efectivo_egresos)
            cols = ['fecha', 'gasto', 'monto', 'categoria', 'subcategoria', 'owner']
            available = [c for c in cols if c in df_ef.columns]
            st.dataframe(df_ef[available], use_container_width=True)

            total_ef = sum(e.get('monto', 0) for e in efectivo_egresos)
            st.metric("Total Egresos Efectivo", f"${total_ef:,.2f}")

        # Mostrar ingresos en efectivo del mes
        ingresos_mes = datos.get('meses', {}).get(mes, {}).get('ingresos_bancarios', [])
        efectivo_ingresos = [i for i in ingresos_mes if i.get('banco') == 'efectivo']

        if efectivo_ingresos:
            st.divider()
            st.caption(f"{len(efectivo_ingresos)} ingresos en efectivo")
            df_ing = pd.DataFrame(efectivo_ingresos)
            cols = ['fecha', 'descripcion', 'monto', 'categoria', 'owner']
            available = [c for c in cols if c in df_ing.columns]
            st.dataframe(df_ing[available], use_container_width=True)

            total_ing = sum(i.get('monto', 0) for i in efectivo_ingresos)
            st.metric("Total Ingresos Efectivo", f"${total_ing:,.2f}")

        if not ajustes_mes and not efectivo_egresos and not efectivo_ingresos:
            st.info("No hay movimientos de efectivo ni ajustes para este periodo")

    # ====== ZONA DE PELIGRO ======
    st.divider()
    st.subheader("Zona de Peligro")
    st.warning("Estas acciones son irreversibles.")

    col_b1, col_b2, col_b3, col_b4 = st.columns(4)

    with col_b1:
        if st.button("🧹 Limpiar Ajustes", type="secondary"):
            datos_disco = cargar_datos()
            if mes in datos_disco.get('meses', {}):
                datos_disco['meses'][mes]['ajustes'] = []
                guardar_datos(datos_disco)
                st.session_state.datos = datos_disco
                st.success(f"Ajustes de {mes} eliminados")
                st.rerun()

    with col_b2:
        if st.button("🧹 Limpiar Efectivo", type="secondary"):
            datos_disco = cargar_datos()
            if mes in datos_disco.get('meses', {}):
                egresos = datos_disco['meses'][mes].get('egresos', [])
                ingresos = datos_disco['meses'][mes].get('ingresos_bancarios', [])

                egresos_efectivo = [e for e in egresos if e.get('medio_pago') == 'Efectivo']
                ingresos_efectivo = [i for i in ingresos if i.get('banco') == 'efectivo']
                cant_borrados = len(egresos_efectivo) + len(ingresos_efectivo)

                datos_disco['meses'][mes]['egresos'] = [
                    e for e in egresos if e.get('medio_pago') != 'Efectivo'
                ]
                datos_disco['meses'][mes]['ingresos_bancarios'] = [
                    i for i in ingresos if i.get('banco') != 'efectivo'
                ]

                guardar_datos(datos_disco)
                st.session_state.datos = datos_disco
                st.success(f"{cant_borrados} movimientos en efectivo de {mes} eliminados")
                st.rerun()

    with col_b3:
        if st.button("💣 Borrar Periodo Completo", type="primary"):
            datos_disco = cargar_datos()
            if mes in datos_disco.get('meses', {}):
                datos_disco['meses'][mes] = {
                    'ingresos_bancarios': [],
                    'egresos': [],
                    'ganancia_fondos': 0,
                    'plusvalia_propiedades': 0,
                    'ajustes': []
                }
                guardar_datos(datos_disco)
                st.session_state.datos = datos_disco
                st.success(f"Periodo {mes} borrado completamente")
                st.rerun()

    with col_b4:
        if st.button("☢️ Borrar TODOS los Datos", type="primary"):
            datos_limpios = {'activos': [], 'meses': {}}
            guardar_datos(datos_limpios)
            st.session_state.datos = datos_limpios
            st.success("Todos los datos eliminados")
            st.rerun()

    # ====== BORRAR EGRESOS INDIVIDUALES ======
    st.divider()
    st.subheader(f"Borrar Egresos Individuales — {mes}")

    egresos_mes = datos.get('meses', {}).get(mes, {}).get('egresos', [])

    if egresos_mes:
        opciones_borrar = {}
        for e in egresos_mes:
            uid = e.get('u_id', '')
            label = (
                f"{e.get('fecha', '-')[:10]} | "
                f"{e.get('gasto', '-')} | "
                f"${e.get('monto', 0):,.2f} | "
                f"{e.get('medio_pago', '-')} | "
                f"{e.get('owner', '-')}"
            )
            opciones_borrar[uid] = label

        seleccionados = st.multiselect(
            "Seleccionar egresos a borrar",
            options=list(opciones_borrar.keys()),
            format_func=lambda x: opciones_borrar.get(x, x),
            key="borrar_egresos_individual"
        )

        if seleccionados and st.button("🗑 Borrar Seleccionados", type="primary"):
            datos_disco = cargar_datos()
            egresos_disco = datos_disco.get('meses', {}).get(mes, {}).get('egresos', [])

            antes = len(egresos_disco)
            datos_disco['meses'][mes]['egresos'] = [
                e for e in egresos_disco if e.get('u_id') not in seleccionados
            ]
            despues = len(datos_disco['meses'][mes]['egresos'])

            guardar_datos(datos_disco)
            st.session_state.datos = datos_disco
            st.success(f"✅ {antes - despues} egresos eliminados de {mes}")
            st.rerun()
    else:
        st.info(f"No hay egresos en {mes}")


def cargar_extracto(mes):
    st.header("Cargar Extracto Bancario")
    
    # Input para valor USD/CLP
    col1, col2 = st.columns(2)
    with col1:
        usd_clp_input = st.number_input(
            "Valor USD/CLP (tipo de cambio)",
            min_value=0.0,
            value=st.session_state.usd_clp,
            step=10.0,
            help="Ingresa el valor de 1 USD en CLP. Para febrero 2026, aproximadamente 1050-1100 CLP"
        )
    if usd_clp_input != st.session_state.usd_clp:
        st.session_state.usd_clp = usd_clp_input
        st.rerun()
    
    st.info("Sube tu extracto bancario (PDF, Excel, imagen o texto). El sistema detectará los ingresos automáticamente.")
    
    archivo = st.file_uploader(
        "Seleccionar archivo",
        type=['jpg', 'jpeg', 'png', 'pdf', 'txt', 'xlsx', 'xls']
    )
    
    if archivo:
        texto = None
        
        # Determinar tipo de archivo por MIME o extensión
        file_type = archivo.type
        file_name = archivo.name.lower() if archivo.name else ""
        
        # Si el tipo MIME no es preciso, usar la extensión
        if not file_type or file_type == "application/octet-stream":
            if file_name.endswith('.pdf'):
                file_type = "application/pdf"
            elif file_name.endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                file_type = "image/jpeg"
            elif file_name.endswith('.txt'):
                file_type = "text/plain"
            elif file_name.endswith(('.xlsx', '.xls')):
                file_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        if file_type == "text/plain":
            texto = archivo.read().decode('utf-8')
        
        # Detectar si es Santander Chile PDF
        if file_type == "application/pdf" and ('santander' in file_name or 'cartola' in file_name):
            if PDF_AVAILABLE:
                pdf_password = st.text_input("Password del PDF (si está encriptado)", type="password")

                if st.button("Procesar Extracto Santander Chile"):
                    with st.spinner("Procesando cartola Santander Chile..."):
                        from parsers.santander_chile_pdf import procesar_santander_chile_pdf
                        archivo.seek(0)
                        datos = st.session_state.datos
                        ingresos, _, texto_debug, error = procesar_santander_chile_pdf(
                            archivo, None, None, datos, categorizar_gasto, pdf_password or None
                        )

                    if texto_debug:
                        with st.expander("DEBUG: Procesamiento Santander Chile"):
                            st.text(texto_debug)

                    if error:
                        st.error(error)
                    elif ingresos:
                        # Guardar en session_state para persistir entre reruns
                        st.session_state['ingresos_santander'] = ingresos
                        st.session_state['ingresos_santander_debug'] = texto_debug
                        st.success(f"✅ {len(ingresos)} ingresos detectados")
                        df_ing = pd.DataFrame(ingresos)
                        st.dataframe(df_ing[['fecha', 'descripcion', 'monto', 'banco']])

                        total_clp = sum(i.get('monto', 0) for i in ingresos)
                        st.metric("Total Ingresos (CLP)", f"${total_clp:,.0f}")
                    else:
                        st.warning("No se detectaron ingresos en la cartola")

                # Mostrar ingresos guardados en session_state y botón de guardar
                if 'ingresos_santander' in st.session_state and st.session_state['ingresos_santander']:
                    ingresos = st.session_state['ingresos_santander']
                    texto_debug = st.session_state.get('ingresos_santander_debug', '')

                    if texto_debug:
                        with st.expander("DEBUG: Procesamiento Santander Chile"):
                            st.text(texto_debug)

                    st.success(f"✅ {len(ingresos)} ingresos listos para guardar")
                    df_ing = pd.DataFrame(ingresos)
                    st.dataframe(df_ing[['fecha', 'descripcion', 'monto', 'banco']])

                    total_clp = sum(i.get('monto', 0) for i in ingresos)
                    st.metric("Total Ingresos (CLP)", f"${total_clp:,.0f}")

                    if st.button("Guardar Ingresos", key="guardar_ingresos_santander"):
                        datos_disco = cargar_datos()
                        datos_disco.setdefault('meses', {}).setdefault(mes, {
                            'ingresos_bancarios': [], 'egresos': [], 'ajustes': [],
                            'ganancia_fondos': 0, 'plusvalia_propiedades': 0
                        })
                        datos_disco['meses'][mes].setdefault('ingresos_bancarios', []).extend(ingresos)
                        guardar_datos(datos_disco)
                        st.session_state.datos = datos_disco
                        st.success(f"✅ {len(ingresos)} ingresos guardados en {mes}")
                        # Limpiar session_state
                        del st.session_state['ingresos_santander']
                        if 'ingresos_santander_debug' in st.session_state:
                            del st.session_state['ingresos_santander_debug']
                        st.rerun()

                return
        elif file_type == "application/pdf":
            if PDF_AVAILABLE:
                # Input para password si el PDF está encriptado
                pdf_password = None
                if file_name.endswith('.pdf'):
                    pdf_password = st.text_input("Password del PDF (si está encriptado)", type="password")
                
                with st.spinner("Extrayendo texto del PDF..."):
                    archivo.seek(0)
                    texto = extraer_texto_pdf(archivo, pdf_password)
                if texto:
                    st.success("Texto extraído del PDF")
                else:
                    st.error("No se pudo extraer texto del PDF")
            else:
                st.warning("PyMuPDF no está instalado. Puedes pegar el texto manualmente.")
        elif file_type and file_type.startswith('image/'):
            if EASYOCR_AVAILABLE:
                with st.spinner("Extrayendo texto de la imagen (puede tomar unos segundos)..."):
                    archivo.seek(0)
                    texto = extraer_texto_imagen(archivo)
                if texto:
                    st.success("Texto extraído de la imagen")
                else:
                    st.error("No se pudo extraer texto de la imagen")
            else:
                st.warning("EasyOCR no está instalado. Puedes pegar el texto manualmente.")
        elif 'excel' in file_type or file_name.endswith(('.xlsx', '.xls')):
            with st.spinner("Extrayendo movimientos del Excel..."):
                archivo.seek(0)
                # Detectar banco por nombre de archivo
                banco = 'galicia'
                if 'santander' in file_name:
                    banco = 'santander_chile'
                elif 'icbc' in file_name:
                    banco = 'icbc'
                elif 'mercadopago' in file_name or 'mp' in file_name:
                    banco = 'mercadopago'
                
                movimientos_excel = extraer_movimientos_excel(archivo, banco)
            
            if movimientos_excel and len(movimientos_excel) > 0:
                st.success(f"Movimientos extraídos del Excel: {len(movimientos_excel)} ingresos")
                
                # Mostrar preview
                df_prev = pd.DataFrame(movimientos_excel)
                st.dataframe(df_prev)
                
                if st.button("Guardar Movimientos"):
                    datos = st.session_state.datos
                    ingresos = datos.get('meses', {}).setdefault(mes, {}).get('ingresos_bancarios', [])
                    ingresos.extend(movimientos_excel)
                    datos.setdefault('meses', {})[mes]['ingresos_bancarios'] = ingresos
                    guardar_datos(datos)
                    st.success("Movimientos guardados correctamente")
            else:
                st.error("No se pudieron extraer movimientos del Excel")
        else:
            st.warning("Tipo de archivo no reconocido. Puedes pegar el texto manualmente.")
        
        if not texto:
            texto = st.text_area("Pega el texto del extracto aquí:", height=200)
        
        if texto:
            with st.expander("Ver texto extraído"):
                st.text(texto[:5000] + "..." if len(texto) > 5000 else texto)
            
            movimientos = parsear_texto(texto)
            
            if movimientos:
                st.success(f"Se detectaron {len(movimientos)} ingresos")
                
                df_prev = pd.DataFrame(movimientos)
                st.dataframe(df_prev)
                
                if st.button("Guardar Movimientos"):
                    datos = st.session_state.datos
                    ingresos = datos.get('meses', {}).setdefault(mes, {}).get('ingresos_bancarios', [])
                    ingresos.extend(movimientos)
                    datos.setdefault('meses', {})[mes]['ingresos_bancarios'] = ingresos
                    guardar_datos(datos)
                    st.success("Movimientos guardados correctamente")
            else:
                st.warning("No se detectaron ingresos en el texto")


def exportar_datos():
    st.header("Exportar Datos")
    
    datos = st.session_state.datos
    
    # Exportar JSON
    if st.button("Exportar JSON"):
        json_str = json.dumps(datos, ensure_ascii=False, indent=2)
        st.download_button(
            label="Descargar JSON",
            data=json_str,
            file_name="ingresos_familiares.json",
            mime="application/json"
        )
    
    # Exportar Excel por mes
    st.subheader("Exportar por Mes")
    meses = list(datos.get('meses', {}).keys())
    if meses:
        mes_seleccionado = st.selectbox("Seleccionar mes para exportar", meses)
        
        if st.button("Exportar Mes a Excel"):
            mes_data = datos['meses'][mes_seleccionado]
            
            with pd.ExcelWriter(f'ingresos_{mes_seleccionado}.xlsx', engine='openpyxl') as writer:
                if mes_data.get('ingresos_bancarios'):
                    pd.DataFrame(mes_data['ingresos_bancarios']).to_excel(writer, sheet_name='Ingresos', index=False)
                if mes_data.get('fondos_mutuos'):
                    pd.DataFrame(mes_data['fondos_mutuos']).to_excel(writer, sheet_name='Fondos', index=False)
                if mes_data.get('propiedades'):
                    pd.DataFrame(mes_data['propiedades']).to_excel(writer, sheet_name='Propiedades', index=False)
                if mes_data.get('ajustes'):
                    pd.DataFrame(mes_data['ajustes']).to_excel(writer, sheet_name='Ajustes', index=False)
            
            with open(f'ingresos_{mes_seleccionado}.xlsx', 'rb') as f:
                st.download_button(
                    label="Descargar Excel",
                    data=f,
                    file_name=f'ingresos_{mes_seleccionado}.xlsx',
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.warning("No hay datos para exportar")


def cargar_fondos_mutuos(mes):
    st.header("Cargar Fondos Mutuos (Santander Chile)")
    
    st.info("Sube el PDF de cartola de fondos mutuos. Se detectarán automáticamente los fondos y se guardarán como activos.")
    
    archivo = st.file_uploader(
        "Seleccionar archivo PDF de fondos mutuos",
        type=['pdf']
    )
    
    if archivo:
        pdf_password = st.text_input("Password del PDF (si está encriptado)", type="password")
        
        if st.button("Extraer Fondos"):
            with st.spinner("Extrayendo fondos mutuos..."):
                archivo.seek(0)
                fondos, total_ars, fecha, total_ganancia_ars = extraer_fondos_mutuos(archivo, pdf_password)
            
            if fondos:
                st.success(f"Fondos extraídos correctamente (fecha: {fecha})")
                
                # Mostrar totales
                col1, col2 = st.columns(2)
                col1.metric("Valor Final Total (ARS)", f"${total_ars:,.0f}")
                col2.metric("Ganancia del Período (ARS)", f"${total_ganancia_ars:,.0f}", 
                           delta=f"{total_ganancia_ars:,.0f}")
                
                # Mostrar dataframe
                df_fondos = pd.DataFrame(fondos)
                st.dataframe(df_fondos[['nombre', 'moneda', 'valor_inicial', 'valor_final', 'ganancia', 'ganancia_ars']])
                
                if st.button("Guardar como Activos"):
                    datos = st.session_state.datos
                    activos = datos.get('activos', [])
                    
                    for fondo in fondos:
                        # Verificar si ya existe
                        existe = any(a.get('nombre') == fondo['nombre'] and a.get('tipo') == 'fondo_mutuo' for a in activos)
                        if not existe:
                            activos.append({
                                'id': len(activos) + 1,
                                'tipo': 'fondo_mutuo',
                                'nombre': fondo['nombre'],
                                'moneda_original': fondo['moneda'],
                                'valor_inicial': fondo['valor_inicial'],
                                'valor_final': fondo['valor_final'],
                                'valor_final_ars': fondo['valor_final_ars'],
                                'ganancia': fondo['ganancia'],
                                'ganancia_ars': fondo['ganancia_ars'],
                                'fecha': fecha,
                                'tasas': fondo['tasas']
                            })
                    
                    datos['activos'] = activos
                    
                    # Registrar ganancia del mes
                    datos.setdefault('meses', {}).setdefault(mes, {}).setdefault('ganancia_fondos', 0)
                    datos['meses'][mes]['ganancia_fondos'] = total_ganancia_ars
                    
                    guardar_datos(datos)
                    st.success(f"Fondos guardados como activos. Ganancia registrada para {mes}")
            else:
                st.error("No se pudieron extraer fondos del PDF")


@st.cache_data(ttl=3600)
def obtener_precio_adr(ticker):
    """Obtiene precio actual de un ADR desde Yahoo Finance API REST"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        params = {
            'interval': '1d',
            'range': '5d'
        }
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            return None, None, None

        data = response.json()
        result = data.get('chart', {}).get('result', [])

        if not result:
            return None, None, None

        meta = result[0].get('meta', {})
        precio = meta.get('regularMarketPrice', 0)
        moneda = meta.get('currency', 'USD')
        nombre = meta.get('shortName', ticker)

        return precio, moneda, nombre

    except Exception as e:
        print(f"Error obteniendo precio {ticker}: {e}")
        return None, None, None


@st.cache_data(ttl=86400)
def obtener_precio_adr_historico(ticker, fecha):
    """Obtiene precio de cierre de un ADR en una fecha específica"""
    try:
        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
        ts_inicio = int((fecha_obj - pd.Timedelta(days=3)).timestamp())
        ts_fin = int((fecha_obj + pd.Timedelta(days=2)).timestamp())

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        params = {
            'period1': ts_inicio,
            'period2': ts_fin,
            'interval': '1d'
        }
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        result = data.get('chart', {}).get('result', [])

        if not result:
            return None

        closes = result[0].get('indicators', {}).get('quote', [{}])[0].get('close', [])
        timestamps = result[0].get('timestamp', [])

        if not closes or not timestamps:
            return None

        ts_objetivo = int(fecha_obj.timestamp())
        mejor_precio = None
        menor_diff = float('inf')

        for ts, precio in zip(timestamps, closes):
            if precio is None:
                continue
            diff = abs(ts - ts_objetivo)
            if diff < menor_diff:
                menor_diff = diff
                mejor_precio = precio

        return mejor_precio

    except Exception as e:
        print(f"Error obteniendo precio histórico {ticker}: {e}")
        return None


def mostrar_activos():
    st.header("Activos")

    # Siempre leer fresco desde disco para tener cierres actualizados
    datos_disco = cargar_datos()
    st.session_state.datos = datos_disco
    datos = datos_disco
    activos = datos.get('activos', [])

    # Parche: inicializar precio_mes_anterior_usd en ADRs que no lo tienen
    adrs_sin_anterior = [
        a for a in activos
        if a.get('tipo') == 'adr' and not a.get('precio_mes_anterior_usd')
    ]
    if adrs_sin_anterior:
        for activo in datos_disco.get('activos', []):
            if activo.get('tipo') == 'adr' and not activo.get('precio_mes_anterior_usd'):
                activo['precio_mes_anterior_usd'] = activo.get('precio_compra_usd', 0)
        guardar_datos(datos_disco)
        st.session_state.datos = datos_disco
        activos = datos_disco.get('activos', [])

    # Separar por tipo
    fondos = [a for a in activos if a.get('tipo') == 'fondo_mutuo']
    propiedades = [a for a in activos if a.get('tipo') == 'propiedad']
    adrs = [a for a in activos if a.get('tipo') == 'adr']
    otros = [a for a in activos if a.get('tipo') not in ['fondo_mutuo', 'propiedad', 'adr']]

    # Obtener USDT/ARS actual para conversiones
    usdt_ars = obtener_usdt_ars_binance() or 1500

    # ====== RESUMEN GENERAL ======
    st.subheader("Resumen General")

    total_fondos_ars = sum(a.get('valor_final_ars', 0) for a in fondos)
    total_propiedades_ars = sum(a.get('valor_tasacion_ars', 0) for a in propiedades)
    total_adrs_ars = sum(a.get('valor_actual_ars', 0) for a in adrs)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fondos Mutuos", f"${total_fondos_ars:,.0f}")
    c2.metric("Propiedades", f"${total_propiedades_ars:,.0f}")
    c3.metric("ADRs", f"${total_adrs_ars:,.0f}")
    c4.metric("TOTAL ACTIVOS", f"${total_fondos_ars + total_propiedades_ars + total_adrs_ars:,.0f}")

    st.caption(f"Tasa USDT/ARS: {usdt_ars:,.2f}")

    # ====== TABS POR TIPO ======
    tab_fondos, tab_props, tab_adrs = st.tabs([
        f"📈 Fondos Mutuos ({len(fondos)})",
        f"🏠 Propiedades ({len(propiedades)})",
        f"📊 ADRs ({len(adrs)})"
    ])

    # ====== TAB FONDOS MUTUOS ======
    with tab_fondos:
        if fondos:
            df_fondos = pd.DataFrame(fondos)
            cols = ['nombre', 'moneda_original', 'valor_final', 'ganancia',
                    'valor_final_ars', 'ganancia_ars', 'fecha']
            available = [c for c in cols if c in df_fondos.columns]
            st.dataframe(df_fondos[available], use_container_width=True, hide_index=True)

            total_ganancia = sum(a.get('ganancia_ars', 0) for a in fondos)
            st.metric("Ganancia Total Fondos", f"${total_ganancia:,.0f}",
                      delta=f"${total_ganancia:,.0f}")
        else:
            st.info("No hay fondos mutuos. Cargalos desde 'Cargar Fondos Mutuos'.")

    # ====== TAB PROPIEDADES ======
    with tab_props:
        if propiedades:
            df_props = pd.DataFrame(propiedades)
            cols = ['nombre', 'zona', 'm2', 'valor_tasacion_usd', 'valor_tasacion_ars']
            available = [c for c in cols if c in df_props.columns]
            st.dataframe(df_props[available], use_container_width=True, hide_index=True)
        else:
            st.info("No hay propiedades. Cargalas desde 'Propiedades'.")

    # ====== TAB ADRs ======
    with tab_adrs:
        st.subheader("ADRs / Acciones")

        # ---- AGREGAR ADR ----
        with st.expander("➕ Agregar ADR", expanded=not bool(adrs)):
            TICKERS_COMUNES = [
                "", "BBAR", "GGAL", "YPF", "PAM", "SUPV", "BMA", "CRESY",
                "CEPU", "EDN", "LOMA", "TEO", "TGS", "IRS", "MELI", "GLOB",
                "(otro)"
            ]

            with st.form("form_agregar_adr", clear_on_submit=True):
                col1, col2 = st.columns(2)

                with col1:
                    ticker_sel = st.selectbox("Ticker (comunes)", TICKERS_COMUNES, index=0)
                    ticker_manual = st.text_input(
                        "Ticker manual (si no está en la lista)",
                        placeholder="Ej: AAPL, MSFT, TSLA"
                    )
                    cantidad = st.number_input("Cantidad de acciones", min_value=0.0,
                                               step=1.0, key="adr_cant")

                with col2:
                    precio_compra = st.number_input("Precio de compra (USD)",
                                                     min_value=0.0, step=0.01,
                                                     key="adr_precio")
                    fecha_compra = st.date_input("Fecha de compra", key="adr_fecha")
                    broker = st.selectbox("Broker", [
                        "Santander Chile", "IOL", "Bull Market", "Balanz",
                        "PPI", "Cocos Capital", "Otro"
                    ])

                submitted_adr = st.form_submit_button("💾 Agregar ADR", type="primary")

            if submitted_adr:
                ticker = ticker_manual.strip().upper() if ticker_manual.strip() else ticker_sel
                if not ticker or ticker == "(otro)":
                    st.warning("Ingresá un ticker válido")
                elif cantidad <= 0 or precio_compra <= 0:
                    st.warning("Cantidad y precio deben ser mayores a 0")
                else:
                    existe = any(
                        a.get('ticker') == ticker and a.get('tipo') == 'adr'
                        for a in activos
                    )
                    if existe:
                        st.warning(f"El ADR {ticker} ya existe. Editalo o eliminalo primero.")
                    else:
                        precio_actual, moneda, nombre_empresa = obtener_precio_adr(ticker)

                        if precio_actual is None:
                            st.warning(f"No se pudo obtener precio para {ticker}. Se guarda con precio de compra.")
                            precio_actual = precio_compra
                            nombre_empresa = ticker

                        valor_actual_usd = cantidad * precio_actual
                        valor_compra_usd = cantidad * precio_compra
                        ganancia_usd = valor_actual_usd - valor_compra_usd

                        nuevo_adr = {
                            'id': len(activos) + 1,
                            'tipo': 'adr',
                            'ticker': ticker,
                            'nombre': nombre_empresa or ticker,
                            'broker': broker,
                            'cantidad': cantidad,
                            'precio_compra_usd': precio_compra,
                            'fecha_compra': fecha_compra.strftime('%Y-%m-%d'),
                            'precio_actual_usd': precio_actual,
                            'precio_mes_anterior_usd': precio_compra,
                            'valor_compra_usd': valor_compra_usd,
                            'valor_actual_usd': valor_actual_usd,
                            'valor_actual_ars': valor_actual_usd * usdt_ars,
                            'ultima_actualizacion': datetime.now().strftime('%Y-%m-%d %H:%M'),
                            'dividendos': [],
                            'cierres': []
                        }

                        datos_disco = cargar_datos()
                        datos_disco.setdefault('activos', []).append(nuevo_adr)
                        guardar_datos(datos_disco)
                        st.session_state.datos = datos_disco
                        st.success(f"✅ ADR {ticker} agregado: {cantidad} acciones a USD {precio_compra:.2f}")
                        st.rerun()

        # ---- MOSTRAR ADRs ----
        if adrs:
            # Selector de mes para visualizar plusvalía
            meses_con_cierres = set()
            for a in adrs:
                for c in a.get('cierres', []):
                    meses_con_cierres.add(c.get('mes', ''))
            meses_con_cierres = sorted([m for m in meses_con_cierres if m], reverse=True)

            meses_disponibles = sorted(datos.get('meses', {}).keys(), reverse=True)
            if not meses_disponibles:
                meses_disponibles = [datetime.now().strftime('%Y-%m')]

            # Botones de acción
            col_btn1, col_btn2 = st.columns([1, 1])

            # Mes seleccionado para visualización (fuera de las columnas para acceso global)
            mes_seleccionado = st.selectbox(
                "Mes para visualizar",
                meses_disponibles,
                index=0,
                key="sel_mes_visualizar_adr"
            )
            
            with col_btn1:
                if st.button("🔄 Actualizar Cotizaciones", type="primary"):
                    datos_disco = cargar_datos()
                    activos_disco = datos_disco.get('activos', [])
                    adrs_disco = [a for a in activos_disco if a.get('tipo') == 'adr']

                    usdt_ars_actual = obtener_usdt_ars_binance() or usdt_ars

                    # Determinar mes actual para plusvalía
                    mes_actual = datetime.now().strftime('%Y-%m')

                    actualizados = 0
                    plusvalia_mes_total_usd = 0
                    plusvalia_mes_total_ars = 0

                    progress = st.progress(0)
                    for i, adr in enumerate(adrs_disco):
                        ticker = adr.get('ticker', '')
                        precio_nuevo, _, nombre = obtener_precio_adr(ticker)

                        if precio_nuevo and precio_nuevo > 0:
                            cantidad_acc = adr.get('cantidad', 0)
                            precio_compra_acc = adr.get('precio_compra_usd', 0)

                            # Precio anterior para plusvalía mensual
                            precio_anterior = adr.get('precio_mes_anterior_usd')
                            if precio_anterior is None or precio_anterior <= 0:
                                precio_anterior = adr.get('precio_actual_usd', precio_compra_acc)

                            # Plusvalía del mes para este ADR
                            plusvalia_adr_usd = (precio_nuevo - precio_anterior) * cantidad_acc
                            plusvalia_adr_ars = plusvalia_adr_usd * usdt_ars_actual

                            plusvalia_mes_total_usd += plusvalia_adr_usd
                            plusvalia_mes_total_ars += plusvalia_adr_ars

                            # Actualizar campos del ADR
                            adr['precio_mes_anterior_usd'] = adr.get('precio_actual_usd', precio_compra_acc)
                            adr['precio_actual_usd'] = precio_nuevo
                            adr['valor_actual_usd'] = cantidad_acc * precio_nuevo
                            adr['valor_actual_ars'] = cantidad_acc * precio_nuevo * usdt_ars_actual
                            adr['ganancia_total_usd'] = (precio_nuevo - precio_compra_acc) * cantidad_acc
                            adr['ganancia_total_ars'] = adr['ganancia_total_usd'] * usdt_ars_actual
                            adr['ganancia_total_pct'] = ((precio_nuevo / precio_compra_acc) - 1) * 100 if precio_compra_acc > 0 else 0
                            adr['plusvalia_mes_usd'] = plusvalia_adr_usd
                            adr['plusvalia_mes_ars'] = plusvalia_adr_ars
                            adr['plusvalia_mes_pct'] = ((precio_nuevo / precio_anterior) - 1) * 100 if precio_anterior > 0 else 0
                            adr['ultima_actualizacion'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                            if nombre:
                                adr['nombre'] = nombre
                            actualizados += 1

                        progress.progress((i + 1) / len(adrs_disco))
                        time.sleep(0.5)

                    # Guardar plusvalía del mes en datos.meses
                    datos_disco.setdefault('meses', {}).setdefault(mes_actual, {
                        'ingresos_bancarios': [], 'egresos': [], 'ajustes': [],
                        'ganancia_fondos': 0, 'plusvalia_propiedades': 0, 'plusvalia_adrs': 0
                    })
                    datos_disco['meses'][mes_actual]['plusvalia_adrs'] = plusvalia_mes_total_ars
                    datos_disco['meses'][mes_actual]['plusvalia_adrs_usd'] = plusvalia_mes_total_usd

                    guardar_datos(datos_disco)
                    st.session_state.datos = datos_disco
                    st.success(
                        f"✅ {actualizados}/{len(adrs_disco)} ADRs actualizados\n\n"
                        f"Plusvalía del mes: USD {plusvalia_mes_total_usd:,.2f} / "
                        f"ARS {plusvalia_mes_total_ars:,.0f}\n\n"
                        f"USDT/ARS: {usdt_ars_actual:,.2f}"
                    )
                    st.rerun()

            with col_btn2:
                mes_cerrar = mes_seleccionado

                if st.button("📅 Cerrar Mes (fijar precios)", type="secondary"):
                    datos_disco = cargar_datos()
                    activos_disco = datos_disco.get('activos', [])
                    adrs_disco = [a for a in activos_disco if a.get('tipo') == 'adr']

                    usdt_ars_actual = obtener_usdt_ars_binance() or usdt_ars

                    # Calcular último día del mes a cerrar
                    anio_c, mes_c = mes_cerrar.split('-')
                    ultimo_dia = calendar.monthrange(int(anio_c), int(mes_c))[1]
                    fecha_cierre = f"{anio_c}-{mes_c}-{ultimo_dia:02d}"

                    # Calcular último día del mes anterior
                    if int(mes_c) == 1:
                        anio_ant = str(int(anio_c) - 1)
                        mes_ant = '12'
                    else:
                        anio_ant = anio_c
                        mes_ant = str(int(mes_c) - 1).zfill(2)
                    ultimo_dia_ant = calendar.monthrange(int(anio_ant), int(mes_ant))[1]
                    fecha_inicio = f"{anio_ant}-{mes_ant}-{ultimo_dia_ant:02d}"

                    plusvalia_mes_total_usd = 0
                    detalle_cierre = []

                    progress = st.progress(0)
                    for i, adr in enumerate(adrs_disco):
                        ticker = adr.get('ticker', '')
                        cantidad_acc = adr.get('cantidad', 0)
                        precio_compra = adr.get('precio_compra_usd', 0)
                        fecha_compra = adr.get('fecha_compra', '')

                        # ---- PRECIO DE CIERRE DEL MES ----
                        precio_cierre = obtener_precio_adr_historico(ticker, fecha_cierre)

                        if not precio_cierre or precio_cierre <= 0:
                            precio_cierre = adr.get('precio_actual_usd', 0)

                        # ---- PRECIO INICIO DEL MES (cierre mes anterior) ----
                        precio_inicio = None

                        # 1. Buscar en historial de cierres previos
                        cierres = adr.get('cierres', [])
                        mes_anterior_key = f"{anio_ant}-{mes_ant}"
                        for cierre in cierres:
                            if cierre.get('mes') == mes_anterior_key:
                                precio_inicio = cierre.get('precio_cierre_usd')
                                break

                        # 2. Si no hay cierre previo, buscar histórico en Yahoo
                        if not precio_inicio or precio_inicio <= 0:
                            if fecha_compra and fecha_compra <= fecha_inicio:
                                precio_inicio = obtener_precio_adr_historico(ticker, fecha_inicio)

                        # 3. Si compró durante el mes a cerrar, usar precio de compra
                        if not precio_inicio or precio_inicio <= 0:
                            if fecha_compra and fecha_compra.startswith(mes_cerrar):
                                precio_inicio = precio_compra
                            elif fecha_compra and fecha_compra > fecha_inicio:
                                precio_inicio = precio_compra
                            else:
                                precio_inicio = precio_compra

                        # ---- CALCULAR PLUSVALÍA ----
                        plusvalia_adr = (precio_cierre - precio_inicio) * cantidad_acc
                        plusvalia_mes_total_usd += plusvalia_adr

                        # Rotar precio para siguiente mes
                        adr['precio_mes_anterior_usd'] = precio_cierre
                        adr['precio_actual_usd'] = precio_cierre

                        # Guardar historial
                        if 'cierres' not in adr:
                            adr['cierres'] = []

                        # Evitar duplicar cierre del mismo mes
                        adr['cierres'] = [c for c in adr['cierres'] if c.get('mes') != mes_cerrar]
                        adr['cierres'].append({
                            'mes': mes_cerrar,
                            'precio_inicio_usd': precio_inicio,
                            'precio_cierre_usd': precio_cierre,
                            'plusvalia_usd': plusvalia_adr,
                            'plusvalia_ars': plusvalia_adr * usdt_ars_actual,
                            'cantidad': cantidad_acc,
                            'fecha_calculo': datetime.now().strftime('%Y-%m-%d %H:%M')
                        })

                        detalle_cierre.append({
                            'Ticker': ticker,
                            'Cant': cantidad_acc,
                            'Precio Inicio': f"${precio_inicio:,.2f}",
                            'Precio Cierre': f"${precio_cierre:,.2f}",
                            'Plusvalía USD': f"${plusvalia_adr:,.2f}",
                        })

                        adr['ultima_actualizacion'] = datetime.now().strftime('%Y-%m-%d %H:%M')

                        progress.progress((i + 1) / len(adrs_disco))
                        time.sleep(0.5)

                    # Guardar plusvalía en el mes
                    plusvalia_mes_total_ars = plusvalia_mes_total_usd * usdt_ars_actual

                    datos_disco.setdefault('meses', {}).setdefault(mes_cerrar, {
                        'ingresos_bancarios': [], 'egresos': [], 'ajustes': [],
                        'ganancia_fondos': 0, 'plusvalia_propiedades': 0
                    })
                    datos_disco['meses'][mes_cerrar]['plusvalia_adrs'] = plusvalia_mes_total_ars
                    datos_disco['meses'][mes_cerrar]['plusvalia_adrs_usd'] = plusvalia_mes_total_usd

                    guardar_datos(datos_disco)
                    st.session_state.datos = datos_disco

                    # Mostrar detalle del cierre
                    st.success(
                        f"✅ Mes {mes_cerrar} cerrado\n\n"
                        f"Plusvalía total: USD {plusvalia_mes_total_usd:,.2f} / "
                        f"ARS {plusvalia_mes_total_ars:,.0f}"
                    )

                    df_cierre = pd.DataFrame(detalle_cierre)
                    st.dataframe(df_cierre, use_container_width=True, hide_index=True)

                    st.rerun()

            st.subheader("Cartera de ADRs")

            for adr in adrs:
                cantidad = adr.get('cantidad', 0)
                precio_compra = adr.get('precio_compra_usd', 0)
                precio_actual = adr.get('precio_actual_usd', 0)
                
                valor_actual = cantidad * precio_actual
                valor_compra = cantidad * precio_compra
                ganancia_total_usd = valor_actual - valor_compra
                ganancia_total_pct = ((precio_actual / precio_compra) - 1) * 100 if precio_compra > 0 else 0
                
                # Plusvalía mes: leer del historial de cierres del mes seleccionado
                cierres_adr = adr.get('cierres', [])
                
                # Buscar cierre del mes seleccionado
                cierre_actual = next(
                    (c for c in cierres_adr if c.get('mes') == mes_seleccionado),
                    None
                )
                if not cierre_actual and cierres_adr:
                    # Usar el último cierre disponible
                    cierre_actual = sorted(cierres_adr, key=lambda c: c.get('mes', ''))[-1]

                if cierre_actual:
                    plusvalia_mes_usd = cierre_actual.get('plusvalia_usd', 0)
                    plusvalia_mes_ars = cierre_actual.get('plusvalia_ars', 0)
                    p_anterior = cierre_actual.get('precio_inicio_usd', precio_compra)
                    plusvalia_mes_pct = ((precio_actual / p_anterior) - 1) * 100 if p_anterior > 0 else 0
                    tiene_cierre = True
                else:
                    plusvalia_mes_usd = 0
                    plusvalia_mes_ars = 0
                    plusvalia_mes_pct = 0
                    tiene_cierre = False
                
                color_total = "🟢" if ganancia_total_pct >= 0 else "🔴"
                color_mes = "🟢" if plusvalia_mes_pct >= 0 else "🔴"

                with st.container():
                    c1, c2, c3, c4, c5, c6, c7 = st.columns([1.5, 0.8, 1, 1.2, 1.5, 1.5, 0.5])

                    c1.markdown(f"**{color_total} {adr.get('ticker', '')}**")
                    c1.caption(f"{adr.get('nombre', '')}")

                    c2.metric("Cant", f"{adr.get('cantidad', 0):,.0f}")

                    c3.metric(
                        "Precio USD",
                        f"${adr.get('precio_actual_usd', 0):,.2f}",
                        delta=f"compra: ${adr.get('precio_compra_usd', 0):,.2f}"
                    )

                    c4.metric(
                        "Valor USD",
                        f"${valor_actual:,.2f}"
                    )

                    # Ganancia total (desde compra)
                    c5.metric(
                        "Gan. Total",
                        f"${ganancia_total_usd:,.2f}",
                        delta=f"{ganancia_total_pct:+.1f}% desde compra"
                    )

                    # Plusvalía del mes
                    c6.metric(
                        f"{color_mes} Plusv. Mes",
                        f"${plusvalia_mes_usd:,.2f}",
                        delta=f"{plusvalia_mes_pct:+.1f}% este mes"
                    )

                    with c7:
                        if st.button("🗑", key=f"del_adr_{adr.get('id')}"):
                            datos_disco = cargar_datos()
                            datos_disco['activos'] = [
                                a for a in datos_disco.get('activos', [])
                                if not (a.get('tipo') == 'adr' and a.get('ticker') == adr.get('ticker'))
                            ]
                            guardar_datos(datos_disco)
                            st.session_state.datos = datos_disco
                            st.success(f"ADR {adr.get('ticker')} eliminado")
                            st.rerun()

                    st.divider()

            # Totales ADRs - leer desde cierres guardados del mes seleccionado
            total_valor_usd = 0
            total_ganancia_total_usd = 0
            total_plusvalia_mes_usd = 0
            total_plusvalia_mes_ars = 0

            for adr in adrs:
                cant = adr.get('cantidad', 0)
                p_actual = adr.get('precio_actual_usd', 0)
                p_compra = adr.get('precio_compra_usd', 0)

                total_valor_usd += cant * p_actual
                total_ganancia_total_usd += (p_actual - p_compra) * cant

                # Plusvalía del mes: leer del historial de cierres
                cierres = adr.get('cierres', [])
                cierre_mes = next(
                    (c for c in cierres if c.get('mes') == mes_seleccionado),
                    None
                )
                if cierre_mes:
                    total_plusvalia_mes_usd += cierre_mes.get('plusvalia_usd', 0)
                    total_plusvalia_mes_ars += cierre_mes.get('plusvalia_ars', 0)

            total_valor_ars = total_valor_usd * usdt_ars
            total_ganancia_total_ars = total_ganancia_total_usd * usdt_ars

            st.subheader("Totales ADRs")
            t1, t2, t3 = st.columns(3)
            t1.metric("Valor Total USD", f"${total_valor_usd:,.2f}")
            t2.metric(
                "Ganancia Total (desde compra)",
                f"USD {total_ganancia_total_usd:,.2f}",
                delta=f"ARS {total_ganancia_total_ars:,.0f}"
            )
            t3.metric(
                f"Plusvalía {mes_seleccionado}",
                f"USD {total_plusvalia_mes_usd:,.2f}",
                delta=f"ARS {total_plusvalia_mes_ars:,.0f}"
            )

            # Mostrar también selector de mes para ver plusvalía histórica
            st.subheader("Plusvalía por Mes")
            todos_cierres = []
            for adr in adrs:
                for cierre in adr.get('cierres', []):
                    todos_cierres.append({
                        'Mes': cierre.get('mes', ''),
                        'Ticker': adr.get('ticker', ''),
                        'Cant': adr.get('cantidad', 0),
                        'Precio Inicio USD': cierre.get('precio_inicio_usd', 0),
                        'Precio Cierre USD': cierre.get('precio_cierre_usd', 0),
                        'Plusvalía USD': cierre.get('plusvalia_usd', 0),
                        'Plusvalía ARS': cierre.get('plusvalia_ars', 0),
                    })

            if todos_cierres:
                df_cierres = pd.DataFrame(todos_cierres)
                df_cierres = df_cierres.sort_values(['Mes', 'Ticker'], ascending=[False, True])
                st.dataframe(df_cierres, use_container_width=True, hide_index=True)

                # Resumen por mes
                st.caption("Resumen por mes")
                resumen_mes = df_cierres.groupby('Mes')[['Plusvalía USD', 'Plusvalía ARS']].sum()
                st.dataframe(resumen_mes, use_container_width=True)
            else:
                st.info("No hay cierres mensuales. Usá 'Cerrar Mes' para registrar.")

            # ---- DIVIDENDOS ----
            st.subheader("Registrar Dividendo")

            tickers_adr = [a.get('ticker', '') for a in adrs]

            with st.form("form_dividendo", clear_on_submit=True):
                cd1, cd2, cd3 = st.columns(3)
                with cd1:
                    div_ticker = st.selectbox("ADR", tickers_adr, key="div_ticker")
                with cd2:
                    div_monto_por_accion = st.number_input(
                        "Dividendo por acción (USD)",
                        min_value=0.0, step=0.01, key="div_monto"
                    )
                with cd3:
                    div_fecha = st.date_input("Fecha de pago", key="div_fecha")

                submitted_div = st.form_submit_button("💰 Registrar Dividendo")

            if submitted_div and div_ticker and div_monto_por_accion > 0:
                datos_disco = cargar_datos()

                for activo in datos_disco.get('activos', []):
                    if activo.get('tipo') == 'adr' and activo.get('ticker') == div_ticker:
                        cantidad_acc = activo.get('cantidad', 0)
                        total_div_usd = div_monto_por_accion * cantidad_acc

                        dividendo = {
                            'fecha': div_fecha.strftime('%Y-%m-%d'),
                            'monto_por_accion_usd': div_monto_por_accion,
                            'total_usd': total_div_usd,
                            'total_ars': total_div_usd * usdt_ars,
                            'cantidad_acciones': cantidad_acc
                        }

                        activo.setdefault('dividendos', []).append(dividendo)

                        mes_div = div_fecha.strftime('%Y-%m')
                        datos_disco.setdefault('meses', {}).setdefault(mes_div, {
                            'ingresos_bancarios': [], 'egresos': [], 'ajustes': [],
                            'ganancia_fondos': 0, 'plusvalia_propiedades': 0
                        })
                        datos_disco['meses'][mes_div].setdefault('ingresos_bancarios', []).append({
                            'fecha': div_fecha.strftime('%Y-%m-%d'),
                            'descripcion': f"Dividendo {div_ticker} ({cantidad_acc} acc x USD {div_monto_por_accion})",
                            'monto': total_div_usd * usdt_ars,
                            'monto_ars': total_div_usd * usdt_ars,
                            'banco': 'dividendos',
                            'categoria': 'inversion',
                            'tasas': f"USDT/ARS: {usdt_ars:.2f}",
                            'owner': 'Gustavo'
                        })

                        guardar_datos(datos_disco)
                        st.session_state.datos = datos_disco
                        st.success(
                            f"✅ Dividendo registrado: {div_ticker} "
                            f"USD {total_div_usd:,.2f} (ARS {total_div_usd * usdt_ars:,.0f})"
                        )
                        st.rerun()

            # Historial de dividendos
            todos_dividendos = []
            for adr in adrs:
                for div in adr.get('dividendos', []):
                    row = dict(div)
                    row['ticker'] = adr.get('ticker', '')
                    todos_dividendos.append(row)

            if todos_dividendos:
                st.caption("Historial de dividendos")
                df_div = pd.DataFrame(todos_dividendos)
                cols_div = ['fecha', 'ticker', 'monto_por_accion_usd', 'total_usd', 'total_ars']
                available_div = [c for c in cols_div if c in df_div.columns]
                st.dataframe(df_div[available_div], use_container_width=True, hide_index=True)

        else:
            st.info("No hay ADRs cargados. Usá el formulario de arriba para agregar.")

    # ====== OTROS ======
    if otros:
        st.subheader("Otros Activos")
        df_otros = pd.DataFrame(otros)
        st.dataframe(df_otros, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
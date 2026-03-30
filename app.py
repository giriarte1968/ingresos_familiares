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
    
    # Agregar nuevo mes
    if st.sidebar.button("+ Agregar Mes"):
        nuevo_mes = st.sidebar.text_input("Nuevo mes (YYYY-MM)")
        if nuevo_mes:
            if nuevo_mes not in st.session_state.datos.get('meses', {}):
                st.session_state.datos.setdefault('meses', {})[nuevo_mes] = {
                    'ingresos_bancarios': [],
                    'egresos': [],
                    'ganancia_fondos': 0,
                    'plusvalia_propiedades': 0,
                    'ajustes': []
                }
                guardar_datos(st.session_state.datos)
                st.rerun()
    
    # Menú principal
    menu = st.sidebar.selectbox(
        "Menú",
        ["Dashboard", "Cargar Extracto", "Cargar Fondos Mutuos", "Movimientos", "Egresos", "Propiedades", "Activos", "Ajustes", "Exportar"]
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
    
    # Total del mes
    total_mes = total_ingresos_bancarios + total_ganancia_fondos + total_plusvalia + total_ajustes
    
    # Mostrar métricas
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric("Ingresos Bancarios (ARS)", f"${total_ingresos_bancarios:,.0f}")
    col2.metric("Ganancia Fondos Mutuos", f"${total_ganancia_fondos:,.0f}", 
                delta=f"{total_ganancia_fondos:,.0f}")
    col3.metric("Plusvalía Propiedades", f"${total_plusvalia:,.0f}", 
                delta=f"{total_plusvalia:,.0f}")
    col4.metric("Ajustes", f"${total_ajustes:,.0f}", 
                delta=f"{total_ajustes:,.0f}")
    col5.metric("TOTAL MES (ARS)", f"${total_mes:,.0f}", 
                delta=f"{total_mes:,.0f}")
    
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


# Categorías para egresos
CATEGORIAS_EGRESOS = {
    'impuestos': ['arca', 'api', 'tgi', 'brassey', 'monotributo', 'afip', 'agna'],
    'servicios': ['prepaga', 'salud', 'jubil', 'caja', 'luz', 'edemsa', 'gas', 'gasnor', 'agua', 'movistar', 'flow', 'adt', 'seguro', 'seguros', 'personal'],
    'comercios': {
        'combustible': ['y PF', 'ypf', 'shell', 'axion', 'estacion', 'petro', 'oil', 'plus', 'refinor'],
        'carniceria': ['carniceria', 'carnicería', 'carne', 'fiambreria', 'polleria'],
        'panaderia': ['panaderia', 'panadería', 'pan', 'factoria'],
        'supermercado': ['supermercado', 'super', 'disco', 'coto', 'changomas', 'vea', 'jumbo', 'carrefour', 'walmart'],
        'farmacia': ['farmacia', 'farma', 'salcobrand', 'mefar', 'deluxe'],
        'pintureria': ['pintureria', 'pinturería', 'colibri', 'pintu'],
        'verduleria': ['verduleria', 'verdulería', 'verduro', 'fruteria'],
        'restaurant': ['restaurant', 'resto', 'pizza', 'burger', 'mcdonald', 'kfc', 'helado'],
        'indumentaria': ['ropa', 'indumentaria', 'zara', 'unisport', 'nike', 'adidas'],
        'ferreteria': ['ferreteria', 'ferretería', 'ferre'],
        'automovil': ['gomeri', 'mecanica', 'mecánica', 'lubricentro', 'grua'],
        'otros': []
    },
    'otros': ['transf', 'familia', 'transporte', 'taxi', 'uber', 'combis', 'otros']
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
    
    # Familia
    'sol belen iriarte rojo': {'categoria': 'otros', 'subcategoria': 'familia', 'gasto': 'Sol Belén Iriarte Rojo'},
    'tomas lautaro iriarte rojo': {'categoria': 'otros', 'subcategoria': 'familia', 'gasto': 'Tomás Lautaro Iriarte Rojo'},
    'magdalena soler': {'categoria': 'otros', 'subcategoria': 'familia', 'gasto': 'Magdalena Soler'},
    'soc': {'categoria': 'otros', 'subcategoria': 'familia', 'gasto': 'SOC'},
    
    # Peluquería (transferencia recurrente Galicia)
    'nrjx': {'categoria': 'servicios', 'subcategoria': 'peluqueria', 'gasto': 'Peluquería'},
    '20441772913': {'categoria': 'servicios', 'subcategoria': 'peluqueria', 'gasto': 'Peluquería'},
    
    # SOC (Zurcher Carlos Augusto)
    'zurcher carlos augusto': {'categoria': 'otros', 'subcategoria': 'familia', 'gasto': 'SOC'},
    'zurcher': {'categoria': 'otros', 'subcategoria': 'familia', 'gasto': 'SOC'},
    
    # Colegio Santa María (educación)
    'col s maris': {'categoria': 'servicios', 'subcategoria': 'educacion', 'gasto': 'Colegio Santa María'},
    'maris': {'categoria': 'servicios', 'subcategoria': 'educacion', 'gasto': 'Colegio Santa María'},
    
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


def categorizar_gasto(descripcion, datos=None):
    """Categoriza un gasto: 1) conocidos, 2) keywords, 3) web search"""
    
    # Limpiar descripción
    desc_limpia = ' '.join(descripcion.split())
    nombre_limpio = desc_limpia.split('  ')[0].split(' - ')[0].split('\t')[0].strip()
    nombre_lower = nombre_limpio.lower()
    
    # ========== PASO 1: Comercios conocidos (instantáneo) ==========
    for conocido, info in COMERCIOS_CONOCIDOS.items():
        if info is None:
            continue
        if conocido in nombre_lower:
            return info['categoria'], info['subcategoria'], info['gasto']
    
    # ========== PASO 2: Keywords locales (instantáneo) ==========
    for categoria, keywords in CATEGORIAS_EGRESOS.items():
        if categoria == 'comercios':
            for subcategoria, palabras in keywords.items():
                for palabra in palabras:
                    if palabra in nombre_lower:
                        return 'comercios', subcategoria, nombre_limpio.title()
        else:
            if isinstance(keywords, list):
                for palabra in keywords:
                    if palabra in nombre_lower:
                        return categoria, categoria, nombre_limpio.title()
    
    # ========== PASO 2.5: Reglas específicas familiares ==========
    if any(nombre in nombre_lower for nombre in [
        'sol belen iriarte rojo',
        'tomas lautaro iriarte rojo',
        'magdalena soler',
        'soc'
    ]):
        return 'otros', 'familia', nombre_limpio.title()

    if 'percepcion' in nombre_lower or 'percepción' in nombre_lower:
        return 'impuestos', 'impuestos', nombre_limpio.title()

    if 'uber' in nombre_lower:
        return 'servicios', 'transporte', nombre_limpio.title()
    
    # ========== PASO 3: Búsqueda web (con cache) ==========
    resultado = buscar_comercio_en_web(nombre_limpio)
    
    if resultado and len(resultado) >= 4:
        texto_resultado, confianza, cat_web, subcat_web = resultado
        
        if confianza >= 0.60 and cat_web and subcat_web:
            # Guardar en conocidos para próximas veces
            COMERCIOS_CONOCIDOS[nombre_lower] = {
                'categoria': cat_web,
                'subcategoria': subcat_web,
                'gasto': nombre_limpio.title()
            }
            return cat_web, subcat_web, nombre_limpio.title()
    
    # ========== PASO 4: Fallback ==========
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
            nuevo_mes = st.text_input("Mes (ej: 2026-03)", key="nuevo_mes_input")
            if st.button("Crear", key="crear_mes_btn") and nuevo_mes:
                if nuevo_mes not in datos.get('meses', {}):
                    datos['meses'][nuevo_mes] = {
                        'ingresos_bancarios': [],
                        'egresos': [],
                        'ajustes': [],
                        'ganancia_fondos': 0,
                        'plusvalia_propiedades': 0
                    }
                    guardar_datos(datos)
                    
                    # Marcar intención de seleccionar el nuevo mes en el próximo rerun
                    st.session_state.mes_egresos_actual = nuevo_mes
                    st.session_state["pending_mes_egresos"] = nuevo_mes

                    st.success(f"Mes {nuevo_mes} creado")
                    st.rerun()
                else:
                    st.warning("El mes ya existe")
    
    # Selectores de owner y medio de pago para los egresos
    OWNERS = ["Gustavo", "Vero"]
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
                        st.session_state.egresos_procesados_temp = gastos
                        st.success(f"Se detectaron {len(gastos)} egresos desde MercadoPago App")
                        st.rerun()
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
                        with st.expander("DEBUG: Texto PDF MercadoPago", expanded=True):
                            st.text(texto_debug)

                    if error:
                        st.error(error)
                    elif gastos:
                        st.session_state.egresos_procesados_temp = gastos
                        st.success(f"Se detectaron {len(gastos)} egresos desde MercadoPago PDF")
                        st.rerun()
                    else:
                        st.warning("No se detectaron egresos en el PDF")

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
                            st.session_state.egresos_procesados_temp = gastos_excel
                            st.success(f"Se detectaron {len(gastos_excel)} egresos desde Excel Galicia")
                            st.rerun()
                        else:
                            st.warning("No se detectaron egresos en el Excel")

                    except Exception as e:
                        st.error(f"Error procesando Excel Galicia: {e}")

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
                            st.session_state.egresos_procesados_temp = gastos
                            st.success(f"Se detectaron {len(gastos)} gastos de Bybit Tarjeta")
                            st.rerun()
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
                            st.session_state.egresos_procesados_temp = gastos
                            st.success(f"Se detectaron {len(gastos)} egresos de ICBC")
                            st.rerun()
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
                        st.session_state.egresos_procesados_temp = gastos
                        st.success(f"Se detectaron {len(gastos)} egresos desde MercadoPago App")
                        st.rerun()
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
                        # FILTRAR por período seleccionado ANTES del preview
                        gastos_filtrados = []
                        gastos_descartados = []

                        for g in gastos:
                            fecha_g = g.get('fecha', '')
                            if fecha_g and fecha_g.startswith(mes_seleccionado):
                                gastos_filtrados.append(g)
                            else:
                                gastos_descartados.append(g)

                        if gastos_descartados:
                            st.warning(
                                f"Se descartaron {len(gastos_descartados)} egresos fuera del período {mes_seleccionado}"
                            )

                        if gastos_filtrados:
                            st.session_state.egresos_procesados_temp = gastos_filtrados
                            st.success(
                                f"Se detectaron {len(gastos_filtrados)} egresos desde Binance QR para {mes_seleccionado}"
                            )
                            st.rerun()
                        else:
                            st.warning(f"No se detectaron egresos para el período {mes_seleccionado}")
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
                        st.session_state.egresos_procesados_temp = gastos
                        st.rerun()
                    else:
                        st.warning("No se detectaron gastos en el archivo")
    
    # ==================== MOSTRAR PREVIEW DE EGRESOS PROCESADOS ====================
    if st.session_state.egresos_procesados_temp:
        gastos = st.session_state.egresos_procesados_temp
        
        st.success(f"✅ {len(gastos)} egresos listos para guardar")
        
        df_preview = pd.DataFrame(gastos)[['fecha', 'gasto', 'monto', 'categoria', 'subcategoria']]
        df_preview = df_preview.rename(columns={'gasto': 'GASTO'})
        st.dataframe(df_preview, width='stretch')
        
        total = sum(g['monto'] for g in gastos)
        st.metric("Total a guardar", f"${total:,.2f} ARS")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("💾 Guardar Egresos", type="primary", width='stretch'):
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
                
                # 3.5 FILTRAR por periodo seleccionado
                mes_year, mes_month = mes_seleccionado.split('-')
                gastos_del_periodo = []
                gastos_sin_fecha = []
                gastos_otro_periodo = []
                
                for g in gastos:
                    fecha_g = g.get('fecha', '')
                    if fecha_g:
                        match_fecha = re.search(r'(\d{4})-(\d{2})', fecha_g)
                        if match_fecha:
                            g_year, g_month = match_fecha.groups()
                            if g_year == mes_year and g_month == mes_month:
                                gastos_del_periodo.append(g)
                            else:
                                gastos_otro_periodo.append(g)
                        else:
                            gastos_sin_fecha.append(g)
                    else:
                        gastos_sin_fecha.append(g)
                
                if gastos_otro_periodo:
                    st.warning(f"⚠️ {len(gastos_otro_periodo)} egresos son de otro periodo y NO se guardarán:")
                    for g in gastos_otro_periodo:
                        st.caption(f"  • {g.get('fecha', '')} - {g.get('gasto', '')} - ${g.get('monto', 0):,.2f}")
                
                if gastos_sin_fecha:
                    st.info(f"ℹ️ {len(gastos_sin_fecha)} egresos sin fecha se guardarán en {mes_seleccionado}:")
                    for g in gastos_sin_fecha:
                        st.caption(f"  • {g.get('gasto', '')} - ${g.get('monto', 0):,.2f}")
                
                gastos = gastos_del_periodo + gastos_sin_fecha
                
                if not gastos:
                    st.error(f"No hay egresos para el periodo {mes_seleccionado}")
                    st.session_state.egresos_procesados_temp = None
                    st.stop()
                
                # 3. DEBUG: guardar estado actual
                egresos_en_disco = datos_disco['meses'][mes_seleccionado]['egresos']
                debug_antes = len(egresos_en_disco)
                
                # 4. Deduplicar nuevos vs existentes
                nuevos = []
                for g in gastos:
                    duplicado = False
                    for e in egresos_en_disco:
                        mismo_gasto = e.get('gasto', '').lower() == g.get('gasto', '').lower()
                        mismo_monto = abs(e.get('monto', 0) - g.get('monto', 0)) < 0.01
                        misma_fecha = e.get('fecha', '') == g.get('fecha', '')
                        if mismo_gasto and mismo_monto and misma_fecha:
                            duplicado = True
                            break
                    if not duplicado:
                        nuevos.append(g)
                
                # 5. AGREGAR nuevos a los existentes
                egresos_en_disco.extend(nuevos)
                datos_disco['meses'][mes_seleccionado]['egresos'] = egresos_en_disco
                
                debug_despues = len(egresos_en_disco)
                
                # 6. Guardar a disco
                guardar_datos(datos_disco)
                
                # 7. Verificar que se guardó bien
                datos_verificacion = cargar_datos()
                egresos_verificacion = datos_verificacion.get('meses', {}).get(mes_seleccionado, {}).get('egresos', [])
                debug_verificacion = len(egresos_verificacion)
                
                # Guardar debug en session state para mostrar persistentemente
                st.session_state.debug_guardado = {
                    'antes': debug_antes,
                    'despues': debug_despues,
                    'verificacion': debug_verificacion,
                    'mes': mes_seleccionado
                }
                
                # 8. Actualizar session state
                st.session_state.datos = datos_verificacion
                
                # 9. Limpiar temporal
                st.session_state.egresos_procesados_temp = None
                
                if nuevos:
                    st.success(f"✅ {len(nuevos)} egresos nuevos guardados para {mes_seleccionado}")
                    if len(nuevos) < len(gastos):
                        st.info(f"ℹ️ {len(gastos) - len(nuevos)} duplicados ignorados")
                else:
                    st.warning("Todos los egresos ya existían")
                
                time.sleep(3)
                st.rerun()

        with col2:
            if st.button("❌ Cancelar", width='stretch'):
                st.session_state.egresos_procesados_temp = None
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
                            # Obtener campos del padre
                            padre_fecha = pago_original.get('fecha', '')
                            padre_owner = pago_original.get('owner', '')
                            padre_medio = pago_original.get('medio_pago', '')
                            padre_moneda = pago_original.get('moneda', 'ARS')
                            padre_fuente = pago_original.get('fuente', '')
                            
                            # Eliminar padre de egresos
                            if pago_original in egresos:
                                egresos.remove(pago_original)
                            
                            # Crear hijos
                            hijos = []
                            for sp in subpagos_rev:
                                desc_sp = sp.get('descripcion', '').strip()
                                monto_sp = sp.get('monto', 0)
                                if desc_sp and monto_sp > 0:
                                    cat, subcat, _ = categorizar_gasto(desc_sp, datos)
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
                            
                            # Agregar hijos
                            egresos.extend(hijos)
                            
                            # Persistir
                            datos.get('meses', {}).setdefault(mes_seleccionado, {})['egresos'] = egresos
                            st.session_state.datos = datos
                            guardar_datos(datos)
                            
                            # Limpiar estado temporal
                            st.session_state.pop('sp_tmp', None)
                            st.session_state.pop('sp_parent_id', None)
                            
                            st.success(f"Pago desglosado en {len(hijos)} sub-pagos.")
                            st.rerun()


def mostrar_propiedades(mes):
    st.header("Propiedades")
    
    datos = st.session_state.datos
    activos = datos.get('activos', [])
    propiedades = [a for a in activos if a.get('tipo') == 'propiedad']
    
    # Agregar propiedad (una vez)
    st.subheader("Agregar Propiedad")
    
    with st.form("agregar_propiedad"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre de la propiedad")
            tipo = st.selectbox("Tipo", ["departamento", "casa"])
            zona = st.selectbox("Zona", [
                "Centro", "Macrocentro", "Barrio Inglés", "Pichincha", "Abasto", 
                "Martin", "Facultades", "Puerto Norte", "Barrio Tigre", 
                "Rosario Norte", "Alvear", "San Martín", "General Paz",
                "Sur", "Norte", "Oeste", "Otro"
            ])
        with col2:
            m2 = st.number_input("Metros cuadrados (m²)", min_value=0)
            dormitorios = st.number_input("Dormitorios", min_value=0, max_value=10)
            baños = st.number_input("Baños", min_value=0, max_value=10)
            antiguedad = st.number_input("Antigüedad (años)", min_value=0)
        
        estado = st.selectbox("Estado", ["excelente", "bueno", "regular"])
        cochera = st.checkbox("Cochera")
        patio = st.checkbox("Patio")
        
        submitted = st.form_submit_button("Guardar Propiedad")
        
        if submitted and nombre:
            # Verificar si ya existe
            existe = any(a.get('nombre') == nombre and a.get('tipo') == 'propiedad' for a in activos)
            if existe:
                st.warning(f"La propiedad '{nombre}' ya existe")
            else:
                propiedad = {
                    'id': len(activos) + 1,
                    'tipo': 'propiedad',
                    'nombre': nombre,
                    'tipo_inmueble': tipo,
                    'zona': zona,
                    'm2': m2,
                    'dormitorios': dormitorios,
                    'baños': baños,
                    'antiguedad': antiguedad,
                    'estado': estado,
                    'cochera': cochera,
                    'patio': patio,
                    'valor_tasacion_usd': 0,
                    'valor_tasacion_ars': 0,
                    'valor_anterior_ars': 0
                }
                activos.append(propiedad)
                datos['activos'] = activos
                guardar_datos(datos)
                st.success(f"Propiedad '{nombre}' guardada como activo")
                st.rerun()
    
    # Mostrar propiedades existentes
    if propiedades:
        st.subheader("Propiedades Registradas")
        df = pd.DataFrame(propiedades)
        cols = ['nombre', 'tipo_inmueble', 'zona', 'm2', 'dormitorios', 'baños', 'antiguedad']
        available = [c for c in cols if c in df.columns]
        st.dataframe(df[available])
    
    # Actualizar tasación mensual
    st.subheader("Actualizar Tasación Mensual")
    st.info("Actualiza el valor de tasación en USD para calcular la plusvalía del mes")
    
    for prop in propiedades:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.write(f"**{prop['nombre']}** ({prop.get('zona', '')}) - {prop.get('m2', 0)}m²")
        with col2:
            nuevo_valor = st.number_input(
                f"Valor USD",
                min_value=0.0,
                value=float(prop.get('valor_tasacion_usd', 0)),
                key=f"tasacion_{prop['id']}"
            )
        with col3:
            if st.button(f"Actualizar", key=f"btn_{prop['id']}"):
                # Guardar valor anterior
                prop['valor_anterior_ars'] = prop.get('valor_tasacion_ars', 0)
                # Actualizar nuevo valor
                prop['valor_tasacion_usd'] = nuevo_valor
                prop['valor_tasacion_ars'] = nuevo_valor * 1500  # Aproximación
                
                datos['activos'] = activos
                
                # Calcular plusvalía del mes
                plusvalia = prop['valor_tasacion_ars'] - prop['valor_anterior_ars']
                datos.setdefault('meses', {}).setdefault(mes, {}).setdefault('plusvalia_propiedades', 0)
                datos['meses'][mes]['plusvalia_propiedades'] = plusvalia
                
                guardar_datos(datos)
                st.success(f"Tasación actualizada. Plusvalía: ${plusvalia:,.0f}")
                st.rerun()
    
    # Mostrar plusvalía total
    if propiedades:
        total_plusvalia = sum(
            prop.get('valor_tasacion_ars', 0) - prop.get('valor_anterior_ars', 0) 
            for prop in propiedades
        )
        st.metric("Plusvalía Total Propiedades", f"${total_plusvalia:,.0f}")


def mostrar_ajustes(mes):
    st.header("Ajustes Manuales")
    
    datos = st.session_state.datos
    ajustes = datos.get('meses', {}).get(mes, {}).get('ajustes', [])
    
    st.info("Agrega ajustes manuales como aportes en efectivo, correcciones o ajustes de cambio")
    
    with st.form("agregar_ajuste"):
        col1, col2 = st.columns(2)
        with col1:
            tipo = st.selectbox("Tipo", ["aporte_efectivo", "correccion", "ajuste_cambio"])
            descripcion = st.text_input("Descripción")
        with col2:
            monto = st.number_input("Monto", min_value=0.0)
            moneda = st.selectbox("Moneda", ["ARS", "USD", "CLP"])
        
        submitted = st.form_submit_button("Agregar Ajuste")
        
        if submitted and descripcion and monto > 0:
            ajuste = {
                'tipo': tipo,
                'descripcion': descripcion,
                'monto': monto,
                'moneda': moneda,
                'fecha': datetime.now().strftime('%Y-%m-%d')
            }
            ajustes.append(ajuste)
            datos.setdefault('meses', {}).setdefault(mes, {})['ajustes'] = ajustes
            guardar_datos(datos)
            st.success("Ajuste agregado")
            st.rerun()
    
    # Mostrar ajustes
    if ajustes:
        st.subheader("Ajustes del Mes")
        df = pd.DataFrame(ajustes)
        st.dataframe(df)
        
        total = sum(a.get('monto', 0) for a in ajustes)
        st.metric("Total Ajustes", f"${total:,.0f}")
        
        # Eliminar ajuste
        if st.button("Limpiar Ajustes"):
            datos.setdefault('meses', {}).setdefault(mes, {})['ajustes'] = []
            guardar_datos(datos)
            st.rerun()
    
    st.divider()
    st.subheader("Zona de Peligro")
    st.warning("Estas acciones son irreversibles.")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("Borrar Periodo Actual", type="primary"):
            if mes in datos.get('meses', {}):
                datos['meses'][mes] = {
                    'ingresos_bancarios': [],
                    'egresos': [],
                    'ganancia_fondos': 0,
                    'plusvalia_propiedades': 0,
                    'ajustes': []
                }
                guardar_datos(datos)
                st.success(f"Datos del periodo {mes} eliminados.")
                st.rerun()
    
    with col_b2:
        if st.button("Borrar TODOS los Datos", type="primary"):
            datos_limpios = {
                'usd_clp': st.session_state.datos.get('usd_clp', 0),
                'meses': {}
            }
            st.session_state.datos = datos_limpios
            guardar_datos(datos_limpios)
            st.success("Todos los datos fueron eliminados.")
            st.rerun()


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


def mostrar_activos():
    st.header("Activos")
    
    datos = st.session_state.datos
    activos = datos.get('activos', [])
    
    if not activos:
        st.info("No hay activos cargados. Ve a 'Cargar Fondos Mutuos' o 'Propiedades' para agregar.")
        return
    
    # Separar por tipo
    fondos = [a for a in activos if a.get('tipo') == 'fondo_mutuo']
    propiedades = [a for a in activos if a.get('tipo') == 'propiedad']
    otros = [a for a in activos if a.get('tipo') not in ['fondo_mutuo', 'propiedad']]
    
    # Totales
    total_fondos_ars = sum(a.get('valor_final_ars', 0) for a in fondos)
    total_propiedades_ars = sum(a.get('valor_actual_ars', 0) for a in propiedades)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Fondos Mutuos", f"${total_fondos_ars:,.0f}")
    col2.metric("Total Propiedades", f"${total_propiedades_ars:,.0f}")
    col3.metric("Total Activos", f"${total_fondos_ars + total_propiedades_ars:,.0f}")
    
    # Fondos Mutuos
    if fondos:
        st.subheader("Fondos Mutuos")
        df_fondos = pd.DataFrame(fondos)
        cols = ['nombre', 'moneda_original', 'valor_final', 'ganancia', 'valor_final_ars', 'ganancia_ars', 'fecha']
        available = [c for c in cols if c in df_fondos.columns]
        st.dataframe(df_fondos[available])
        
        # Total ganancia
        total_ganancia = sum(a.get('ganancia_ars', 0) for a in fondos)
        st.metric("Ganancia Total Fondos", f"${total_ganancia:,.0f}", delta=f"{total_ganancia:,.0f}")
    
    # Propiedades
    if propiedades:
        st.subheader("Propiedades")
        df_props = pd.DataFrame(propiedades)
        cols = ['nombre', 'zona', 'm2', 'valor_actual_ars']
        available = [c for c in cols if c in df_props.columns]
        st.dataframe(df_props[available])
    
    # Otros
    if otros:
        st.subheader("Otros Activos")
        df_otros = pd.DataFrame(otros)
        st.dataframe(df_otros)
    
    # Eliminar activo
    if st.button("Eliminar Activo"):
        st.info("Funcionalidad de eliminación en desarrollo")


if __name__ == "__main__":
    main()
"""
Funciones compartidas entre todos los parsers.
OCR, categorización, utilidades.
"""
import re
import os
import json
import time
import random
import numpy as np
from PIL import Image
import io


# ====================== ID ======================

def generar_id():
    """Genera un ID único"""
    ts = int(time.time() * 1000)
    rnd = ''.join(random.choice('0123456789abcdef') for _ in range(6))
    return f"ts_{ts}_{rnd}"


# ====================== COMERCIOS CONOCIDOS ======================

COMERCIOS_CONOCIDOS = {
    'miguel': {'categoria': 'comercios', 'subcategoria': 'combustible', 'gasto': 'Estación de Servicio'},
    'juan': {'categoria': 'comercios', 'subcategoria': 'carniceria', 'gasto': 'Carnicería'},
    'pepe': {'categoria': 'comercios', 'subcategoria': 'panaderia', 'gasto': 'Panadería'},
    'gge alfa park': {'categoria': 'comercios', 'subcategoria': 'restaurant', 'gasto': 'GGE Alfa Park'},
    'instituto gamma': {'categoria': 'servicios', 'subcategoria': 'salud', 'gasto': 'Instituto Gamma'},
    'gamma': {'categoria': 'servicios', 'subcategoria': 'salud', 'gasto': 'Instituto Gamma'},
    'rosati damian': {'categoria': 'comercios', 'subcategoria': 'restaurant', 'gasto': 'Pizzería Rosati'},
    'la gran argentina': {'categoria': 'comercios', 'subcategoria': 'restaurant', 'gasto': 'La Gran Argentina'},
    'sebastian montene': {'categoria': 'comercios', 'subcategoria': 'indumentaria', 'gasto': 'Indumentaria'},
    'pluspagos': {'categoria': 'servicios', 'subcategoria': 'bancos', 'gasto': 'PlusPagos'},
    'estacionamiento ocampo': {'categoria': 'servicios', 'subcategoria': 'estacionamiento', 'gasto': 'Estacionamiento Ocampo'},
    'tu quincho': {'categoria': 'comercios', 'subcategoria': 'bazar', 'gasto': 'Tu Quincho'},
    'diego rey': {'categoria': 'comercios', 'subcategoria': 'restaurant', 'gasto': 'Diego Rey'},
    'pinturerias colibri': {'categoria': 'comercios', 'subcategoria': 'pintureria', 'gasto': 'Pinturerías Colibrí'},
    'panaderia sc ii': {'categoria': 'comercios', 'subcategoria': 'panaderia', 'gasto': 'Panadería SC II'},
    'remo franco': {'categoria': 'comercios', 'subcategoria': 'indumentaria', 'gasto': 'Remo Franco SRL'},
    'epe': {'categoria': 'servicios', 'subcategoria': 'servicios_publicos', 'gasto': 'EPE (Energía)'},
    'aguas santafesinas': {'categoria': 'servicios', 'subcategoria': 'servicios_publicos', 'gasto': 'Aguas Santafesinas'},
    'movistar': {'categoria': 'servicios', 'subcategoria': 'telecomunicaciones', 'gasto': 'Movistar'},
    'personal': {'categoria': 'servicios', 'subcategoria': 'telecomunicaciones', 'gasto': 'Personal'},
    'adt': {'categoria': 'servicios', 'subcategoria': 'seguridad', 'gasto': 'ADT Seguridad'},
    'municipalidad': {'categoria': 'impuestos', 'subcategoria': 'impuestos', 'gasto': 'Municipalidad'},
    'cargo por servicio': {'categoria': 'servicios', 'subcategoria': 'bancos', 'gasto': 'Cargo Bancario'},
    'merpago*tran': {'categoria': 'servicios', 'subcategoria': 'estacionamiento', 'gasto': 'Estacionamiento Tránsito Rosario'},
    'merpago': {'categoria': 'servicios', 'subcategoria': 'estacionamiento', 'gasto': 'Estacionamiento Tránsito Rosario'},
    'correcto': None,
    'historial': None,
    'pago con': None,
    'fecha': None,
    'todos los': None,
}

CATEGORIAS_EGRESOS = {
    'impuestos': ['arca', 'api', 'tgi', 'brassey', 'monotributo', 'afip', 'agna'],
    'servicios': ['prepaga', 'salud', 'jubil', 'caja', 'luz', 'edemsa', 'gas', 'gasnor', 'agua', 'movistar', 'flow', 'adt', 'seguro', 'seguros', 'personal'],
    'comercios': {
        'combustible': ['ypf', 'shell', 'axion', 'estacion', 'petro', 'oil', 'plus', 'refinor'],
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
        'bazar': ['bazar', 'quincho', 'parrilla', 'asado'],
        'otros': []
    },
    'otros': ['transf', 'familia', 'transporte', 'taxi', 'uber', 'combis', 'otros']
}


def cargar_comercios_json():
    """Carga comercios_conocidos.json si existe"""
    try:
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'comercios_conocidos.json')
        if os.path.exists(ruta):
            with open(ruta, encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def categorizar_gasto_parser(descripcion, datos=None):
    """Categoriza un gasto"""
    desc_limpia = ' '.join(descripcion.split())
    nombre_limpio = desc_limpia.split('  ')[0].split(' - ')[0].split('\t')[0].strip()
    nombre_lower = nombre_limpio.lower()

    for conocido, info in COMERCIOS_CONOCIDOS.items():
        if info is None:
            continue
        if conocido in nombre_lower:
            return info['categoria'], info['subcategoria'], info['gasto']

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

    return 'otros', 'otros', nombre_limpio.title()


# ====================== OCR ======================

_paddle_reader = None

def get_paddle_reader():
    global _paddle_reader
    if _paddle_reader is None:
        try:
            import paddleocr
            _paddle_reader = paddleocr.PaddleOCR(use_angle_cls=True, lang='es', show_log=False)
        except Exception:
            return None
    return _paddle_reader


def imagen_a_items_paddle(archivo):
    """Lee una imagen con PaddleOCR y retorna items ordenados"""
    reader = get_paddle_reader()
    if reader is None:
        return [], "PaddleOCR no disponible"

    if hasattr(archivo, 'seek'):
        archivo.seek(0)
    if hasattr(archivo, 'read'):
        img_bytes = archivo.read()
        img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
    else:
        img = Image.open(archivo).convert('RGB')

    img_array = np.array(img)
    result = reader.ocr(img_array, cls=True)

    items = []
    if result and result[0]:
        for line in result[0]:
            if not line:
                continue
            bbox = line[0]
            x_left = bbox[0][0]
            x_right = bbox[2][0]
            items.append({
                'y': (bbox[0][1] + bbox[2][1]) / 2,
                'x_left': x_left,
                'x_center': (x_left + x_right) / 2,
                'x_right': x_right,
                'text': line[1][0].strip(),
                'conf': line[1][1]
            })

    items.sort(key=lambda i: i['y'])

    texto_debug = "\n".join(
        f"y={it['y']:.0f} x={it['x_left']:.0f}-{it['x_right']:.0f} | {it['text']}"
        for it in items
    )

    return items, texto_debug

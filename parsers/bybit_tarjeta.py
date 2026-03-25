"""
Parser para screenshots de Bybit Tarjeta Prepaga.

Formato del ticket:
    Comercio                    - MONTO ARS
    con **** NNNN                      Pago
    YYYY-MM-DD HH:MM:SS
"""
import re
import time
import random
import numpy as np
from PIL import Image
import io


def generar_id():
    ts = int(time.time() * 1000)
    rnd = ''.join(random.choice('0123456789abcdef') for _ in range(6))
    return f"ts_{ts}_{rnd}"


def get_paddle_reader():
    try:
        import paddleocr
        return paddleocr.PaddleOCR(use_angle_cls=True, lang='es', show_log=False)
    except ImportError:
        return None


def parsear_monto_bybit(texto_monto):
    """Parsea montos Bybit: '- 6.999,93 ARS' o '468,50 ARS'"""
    s = texto_monto.strip()
    s = s.replace('ARS', '').replace('-', '').strip()
    
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        parts = s.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) == 2:
            pass
        else:
            s = s.replace('.', '')
    
    try:
        return abs(float(s))
    except (ValueError, TypeError):
        return 0.0


def extraer_fecha_bybit(texto):
    """Extrae fecha de '2026-03-14 14:01:05' o '20260314'"""
    m = re.search(r'(\d{4}-\d{2}-\d{2})', texto)
    if m:
        return m.group(1)
    m = re.search(r'(\d{4})(\d{2})(\d{2})', texto)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ''


def limpiar_nombre_comercio(nombre):
    """Limpia nombres de comercio del formato Bybit"""
    nombre = nombre.strip()
    
    if 'MERPAGO' in nombre.upper():
        return 'Estacionamiento Tránsito Rosario'
    
    nombre = re.sub(r'[*]+', '', nombre)
    nombre = re.sub(r'\.{3,}', '', nombre)
    nombre = nombre.strip(' -.*')
    
    return nombre


def procesar_bybit_tarjeta(archivo, owner, medio_pago, datos, categorizar_fn=None):
    """
    Procesa screenshot de Bybit Tarjeta Prepaga.
    
    Args:
        archivo: archivo subido (st.UploadedFile)
        owner: string con el owner
        medio_pago: string con el medio de pago
        datos: diccionario de datos de la app
        categorizar_fn: función categorizar_gasto de app.py
    
    Returns:
        tuple: (lista_gastos, texto_debug, mensaje_error)
    """
    reader = get_paddle_reader()
    if reader is None:
        return [], "", "PaddleOCR no disponible"
    
    try:
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
        
        if not items:
            return [], texto_debug, "No se detectó texto en la imagen"
        
        gastos = []
        lineas_ars = []
        
        for idx, it in enumerate(items):
            if 'ARS' in it['text'].upper():
                lineas_ars.append((idx, it))
        
        for ars_idx, ars_item in lineas_ars:
            monto = parsear_monto_bybit(ars_item['text'])
            if monto < 1:
                continue
            
            y_ars = ars_item['y']
            nombre_comercio = ''
            fecha_gasto = ''
            
            for it in items:
                dist_y = abs(it['y'] - y_ars)
                
                if dist_y < 20:
                    texto_it = it['text'].strip()
                    
                    es_monto = 'ARS' in texto_it.upper()
                    es_pago = texto_it.lower() == 'pago'
                    es_tarjeta = '****' in texto_it
                    es_fecha = bool(re.match(r'^\d{4}-\d{2}-\d{2}', texto_it))
                    es_basura = texto_it.lower() in ['con', '-', 'or', 'qr']
                    
                    if not any([es_monto, es_pago, es_tarjeta, es_fecha, es_basura]):
                        if it['x_left'] < ars_item['x_left'] and len(texto_it) > 1:
                            nombre_comercio = texto_it
            
            for it in items:
                dist_y = it['y'] - y_ars
                if 10 < dist_y < 80:
                    fecha_encontrada = extraer_fecha_bybit(it['text'])
                    if fecha_encontrada:
                        fecha_gasto = fecha_encontrada
                        break
            
            if not nombre_comercio or len(nombre_comercio) < 2:
                continue
            
            nombre_lower = nombre_comercio.lower()
            if any(ig in nombre_lower for ig in ['historial', 'correcto', 'total', 'saldo', 'disponible']):
                continue
            
            nombre_limpio = limpiar_nombre_comercio(nombre_comercio)
            
            if categorizar_fn:
                cat, subcat, gasto_final = categorizar_fn(nombre_limpio, datos)
            else:
                cat, subcat, gasto_final = 'otros', 'otros', nombre_limpio.title()
            
            gastos.append({
                'fecha': fecha_gasto,
                'gasto': gasto_final,
                'monto': monto,
                'moneda': 'ARS',
                'fuente': 'Bybit Tarjeta',
                'categoria': cat,
                'subcategoria': subcat,
                'owner': owner,
                'medio_pago': medio_pago or 'Tarjeta Prepaga Bybit',
                'u_id': generar_id()
            })
        
        seen = set()
        gastos_dedup = []
        for g in gastos:
            key = (g['gasto'].lower()[:10], round(g['monto'], 2))
            if key not in seen:
                seen.add(key)
                gastos_dedup.append(g)
        
        if not gastos_dedup:
            return [], texto_debug, "No se detectaron gastos"
        
        return gastos_dedup, texto_debug, None
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], "", f"Error procesando Bybit Tarjeta: {str(e)}"

"""
Parser para screenshots de historial QR de Bybit.
SOLO captura pagos con estado "Correcto".
"""
import re
import time
import random
import io
import numpy as np
from PIL import Image


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


def parsear_monto_qr(texto):
    s = texto.strip().upper().replace('ARS', '').strip()
    s = s.replace(',', '')
    try:
        return float(s)
    except:
        return 0.0


def extraer_fecha_qr(texto):
    m = re.search(r'(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2}:\d{2})?', texto)
    if m:
        return m.group(1), m.group(2) if m.group(2) else ''
    return '', ''


def es_linea_monto_ars(texto):
    t = texto.upper()
    if 'RECIBIR' in t:
        return False
    return 'ARS' in t and bool(re.search(r'[\d,.]+\s*ARS', t))


def es_linea_fecha(texto):
    t = texto.strip().lower()
    return ('pago con qr' in t or 'enviar' in t) and bool(re.search(r'\d{4}-\d{2}-\d{2}', t))


def es_estado_correcto(texto):
    t = texto.strip().lower()
    return 'correcto' in t or 'completado' in t or 'aprobado' in t


def es_estado_error(texto):
    t = texto.strip().lower()
    return any(x in t for x in ['error', 'tiempo de espera', 'pendiente', 'rechazado', 'fallido'])


def limpiar_nombre(nombre):
    if not nombre:
        return ''
    return re.sub(r'\s+', ' ', nombre.strip())


def procesar_bybit_qr(archivo, owner, medio_pago, datos, categorizar_fn=None):
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
                y = (bbox[0][1] + bbox[2][1]) / 2
                text = line[1][0].strip()
                items.append({'y': y, 'x_left': x_left, 'x_right': x_right, 'text': text})

        items.sort(key=lambda i: i['y'])

        texto_debug = "\n".join(f"y={it['y']:.0f} | {it['text']}" for it in items)

        if not items:
            return [], texto_debug, "No se detectó texto"

        gastos = []
        procesados_y = set()

        for i, item in enumerate(items):
            texto = item['text']

            if not es_linea_monto_ars(texto):
                continue
            if item['y'] in procesados_y:
                continue

            monto = parsear_monto_qr(texto)
            if monto <= 0:
                continue

            y_monto = item['y']
            x_monto = item['x_left']
            procesados_y.add(y_monto)

            # VALIDAR ESTADO - Rango 150px
            estado_correcto = False
            estado_error = False
            hora_transaccion = ''
            
            for it in items:
                dist_y = it['y'] - y_monto
                if 0 < dist_y < 150:
                    texto_it = it['text'].strip()
                    texto_lower = texto_it.lower()
                    
                    if es_estado_correcto(texto_lower):
                        estado_correcto = True
                    if es_estado_error(texto_lower):
                        estado_error = True
                        break
                    
                    _, hora = extraer_fecha_qr(texto_it)
                    if hora:
                        hora_transaccion = hora
            
            # DESCARTAR si tiene error o no tiene estado "Correcto"
            if estado_error or not estado_correcto:
                continue

            # BUSCAR NOMBRE - Inicializar siempre
            nombre = ''
            
            for it in items:
                if abs(it['y'] - y_monto) < 18:
                    if it['x_left'] < x_monto:
                        t = it['text'].strip().lower()
                        if len(t) > 1 and 'usdt' not in t and 'recibir' not in t and 'enviar' not in t:
                            nombre = it['text'].strip()
                            break

            if not nombre:
                for it in items:
                    dist = y_monto - it['y']
                    if 0 < dist < 25:
                        t = it['text'].strip().lower()
                        if len(t) > 2 and 'usdt' not in t and 'recibir' not in t and 'enviar' not in t and 'correcto' not in t and 'error' not in t:
                            nombre = it['text'].strip()
                            break

            # BUSCAR FECHA
            fecha_completa = ''
            for it in items:
                dist_y = it['y'] - y_monto
                if 5 < dist_y < 150:
                    if es_linea_fecha(it['text']):
                        fecha, hora = extraer_fecha_qr(it['text'])
                        if fecha:
                            fecha_completa = fecha
                            if hora and not hora_transaccion:
                                hora_transaccion = hora
                        break

            # VALIDACIONES FINALES
            nombre = limpiar_nombre(nombre)

            if not nombre or len(nombre) < 2:
                continue
            if not fecha_completa:
                continue

            nlow = nombre.lower()
            if any(x in nlow for x in ['historial de pagos', 'todos los tipos', 'todos los estados', 'fecha', 'pagado']):
                continue

            if categorizar_fn:
                cat, subcat, gasto_final = categorizar_fn(nombre, datos)
            else:
                cat, subcat, gasto_final = 'otros', 'otros', nombre.title()

            unique_id = f"{fecha_completa}_{hora_transaccion}_{nombre}_{monto}"
            
            gastos.append({
                'fecha': f"{fecha_completa} {hora_transaccion}" if hora_transaccion else fecha_completa,
                'gasto': gasto_final,
                'monto': monto,
                'moneda': 'ARS',
                'fuente': 'Bybit QR',
                'categoria': cat,
                'subcategoria': subcat,
                'owner': owner,
                'medio_pago': medio_pago or 'QR Bybit',
                'u_id': generar_id(),
                '_unique_key': unique_id
            })

        # Deduplicar
        seen = set()
        gastos_dedup = []
        for g in gastos:
            key = g.get('_unique_key', '')
            if key not in seen:
                seen.add(key)
                g.pop('_unique_key', None)
                gastos_dedup.append(g)

        if not gastos_dedup:
            return [], texto_debug, "No se detectaron gastos QR"

        return gastos_dedup, texto_debug, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], "", f"Error: {str(e)}"
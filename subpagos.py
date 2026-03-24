"""
Módulo de Sub-pagos para el Gestor de Ingresos Familiares.
Maneja la extracción OCR de tickets y la división de pagos padre en sub-pagos hijos.
"""
import io
import re
import time
import random
import numpy as np
from PIL import Image


def generar_id():
    """Genera un ID único."""
    ts = int(time.time() * 1000)
    rnd = ''.join(random.choice('0123456789abcdef') for _ in range(6))
    return f"ts_{ts}_{rnd}"


def get_paddle_reader_safe():
    """Instancia PaddleOCR de forma lazy y segura."""
    try:
        from paddleocr import PaddleOCR
        reader = PaddleOCR(use_angle_cls=True, lang='es', show_log=False)
        return reader
    except Exception:
        return None


def extraer_subpagos(comprobante, datos=None):
    """
    Usa PaddleOCR para extraer sub-pagos de un ticket Santa Fe Servicios.
    Retorna (lista_de_subpagos, texto_raw).

    Patron del ticket:
      Linea 1: descripcion (MOVISTAR, ADT, EPE, etc.)
      Linea 2: IMPORTE: o EMPORTE: (etiqueta)
      Linea 3: monto (66154.05)

    Filtros: deduplicacion (4 chars desc + monto), monto < 1 (ruido).
    """
    reader = get_paddle_reader_safe()
    if reader is None:
        return [], "PaddleOCR no disponible"

    try:
        if hasattr(comprobante, 'read'):
            comprobante.seek(0)
            img_bytes = comprobante.read()
            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        else:
            img = Image.open(comprobante).convert('RGB')

        img_array = np.array(img)
        result = reader.ocr(img_array, cls=True)

        texto = ""
        if result and result[0]:
            for line in result[0]:
                if line:
                    texto += line[1][0] + "\n"

        lineas = texto.split('\n')
        sub_pagos = []
        seen = set()

        label_keywords = [
            'IMPORTE', 'EMPORTE', 'MPORTE', 'MONTO', 'TOTAL',
            'NRO.', 'NRO TRANSACC', 'NRO.TRANSACC', 'NRO TRANSACCI',
            'FECHA', 'HORA', 'SUC.', 'TERM.', 'CAJERO', 'ID:',
            'COPIA', 'APROBADA', 'FORMADEPAGOQR', 'CAJERO:',
            'NRO.REF.', 'NRO.REF'
        ]
        header_keywords = [
            'santa fe servicios', 'pago de servicios', 'copia cliente',
            'resumen', 'total desglosado'
        ]

        for i, linea in enumerate(lineas):
            linea = linea.strip()
            if not linea:
                continue

            linea_upper = linea.upper()
            linea_lower = linea.lower()

            if any(k in linea_upper for k in label_keywords):
                continue
            if any(h in linea_lower for h in header_keywords):
                continue
            if re.match(r'^[\d\s.,\-/:]+$', linea):
                continue
            if len(linea) < 2:
                continue
            if re.search(r'\d[A-Za-z]|[A-Za-z]\d', linea):
                continue

            tiene_importe = False
            for offset in range(1, 3):
                if i + offset < len(lineas):
                    sig = lineas[i + offset].strip().upper()
                    if 'IMPORTE' in sig or 'EMPORTE' in sig or 'MPORTE' in sig:
                        tiene_importe = True
                        break

            if not tiene_importe:
                continue

            monto_encontrado = None
            for offset in range(1, 4):
                if i + offset < len(lineas):
                    sig = lineas[i + offset].strip()
                    m = re.search(r'\$?\s*(\d+)\.(\d+)', sig)
                    if m:
                        try:
                            monto_encontrado = float(m.group(1) + '.' + m.group(2))
                            break
                        except ValueError:
                            pass
                    m2 = re.search(r'\$?\s*([\d,]+)', sig)
                    if m2 and monto_encontrado is None:
                        try:
                            monto_encontrado = float(m2.group(1).replace(',', '').replace('$', ''))
                            break
                        except ValueError:
                            pass

            if monto_encontrado is None or monto_encontrado < 1:
                continue

            key = (linea.lower()[:4], round(monto_encontrado, 2))
            if key in seen:
                continue
            seen.add(key)

            sub_pagos.append({
                'monto': monto_encontrado,
                'descripcion': linea.strip(),
                'fecha': ''
            })

        return sub_pagos, texto

    except Exception as e:
        return [], str(e)


def procesar_subpagos(pago_original, subpagos_rev, datos, mes_seleccionado):
    """
    Procesa la división de un pago padre en sub-pagos hijos.

    Args:
        pago_original: dict con los campos del pago padre (fecha, owner, medio_pago, fuente, moneda)
        subpagos_rev: lista de dicts con {descripcion, monto} ya revisados por el usuario
        datos: diccionario de datos (para categorizar_gasto)
        mes_seleccionado: string "YYYY-MM" del mes actual

    Returns:
        lista de hijos creados (para persistir en UI)
    """
    from app import generar_id, categorizar_gasto, guardar_datos, st

    if not pago_original or not subpagos_rev:
        return []

    padre_fecha = pago_original.get('fecha', '')
    padre_owner = pago_original.get('owner', '')
    padre_medio = pago_original.get('medio_pago', '')
    padre_moneda = pago_original.get('moneda', 'ARS')
    padre_fuente = pago_original.get('fuente', '')
    pago_id = pago_original.get('u_id', '')

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

    return hijos

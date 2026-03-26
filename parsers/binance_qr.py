"""
Parser para historial QR de Binance.
Formato:
    NOMBRE (1 o 2 líneas)     -MONTO ARS
    etiqueta opcional         (Descontado)
    FECHA HORA
    estado                    (Completado)
"""
import re
from parsers.base import (
    imagen_a_items_paddle,
    categorizar_gasto_parser,
    generar_id,
)


def parsear_monto_binance(texto):
    """
    Ejemplos:
      -713,314 ARS
      -158,883.63 ARS
      -155,381.05 ARS
      -33,524 ARS
    """
    t = texto.strip().upper()
    if 'ARS' not in t:
        return 0.0

    m = re.search(r'-\s*([\d,\.]+)\s*ARS', t)
    if not m:
        m = re.search(r'([\d,\.]+)\s*ARS', t)
        if not m:
            return 0.0
        negativo = False
    else:
        negativo = True

    s = m.group(1)

    if ',' in s and '.' in s:
        s = s.replace(',', '')
    elif ',' in s and '.' not in s:
        s = s.replace(',', '')
    elif '.' in s and ',' not in s:
        parts = s.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) == 2:
            pass
        else:
            s = s.replace('.', '')

    try:
        val = float(s)
        return -val if negativo else val
    except:
        return 0.0


def parsear_fecha_binance(texto):
    m = re.search(r'(\d{4}-\d{2}-\d{2})\s+\d{2}:\d{2}:\d{2}', texto.strip())
    if m:
        return m.group(1)

    m = re.search(r'(\d{4}-\d{2}-\d{2})', texto.strip())
    if m:
        return m.group(1)

    return ''


def es_linea_monto(texto):
    return 'ARS' in texto.upper() and bool(re.search(r'[\d,\.]+', texto))


def es_linea_fecha(texto):
    return bool(parsear_fecha_binance(texto))


def es_linea_estado(texto):
    t = texto.strip().lower()
    return 'completado' in t or 'completed' in t


def es_linea_etiqueta(texto):
    t = texto.strip().lower()
    return 'descontado' in t or 'discounted' in t


def procesar_binance_qr(archivo, owner, medio_pago, datos, categorizar_gasto_fn=None):
    items, texto_debug = imagen_a_items_paddle(archivo)

    if not items:
        return [], texto_debug, "No se pudo leer la imagen"

    gastos = []

    for idx, item in enumerate(items):
        texto = item['text'].strip()
        if not es_linea_monto(texto):
            continue

        monto = parsear_monto_binance(texto)
        if monto >= 0:
            continue

        y_monto = item['y']
        x_monto = item['x_left']

        nombre_partes = []
        for it in items:
            if it['x_right'] < x_monto:
                # mismo bloque vertical
                if -30 <= (it['y'] - y_monto) <= 65:
                    t = it['text'].strip()
                    if not es_linea_fecha(t) and not es_linea_estado(t) and not es_linea_etiqueta(t) and not es_linea_monto(t):
                        if len(t) > 1:
                            nombre_partes.append((it['y'], t))

        nombre_partes = sorted(nombre_partes, key=lambda x: x[0])

        # Unir líneas del mismo nombre
        nombre = ' '.join([p[1] for p in nombre_partes]).strip()
        nombre = re.sub(r'\s+', ' ', nombre).strip()

        # Normalizaciones específicas OCR Binance
        nombre_upper = nombre.upper()
        if 'CAJA DE PREVISION' in nombre_upper and ('SOCIAL' in nombre_upper or nombre_upper.endswith('SOC')):
            nombre = 'Caja de Previsión Social'

        fecha = ''
        for it in items:
            if 10 <= (it['y'] - y_monto) <= 100:
                f = parsear_fecha_binance(it['text'])
                if f:
                    fecha = f
                    break

        if not nombre or len(nombre) < 2:
            continue
        if not fecha:
            continue

        # Evitar nombres parciales / basura
        nombre_lower = nombre.lower().strip()
        if nombre_lower in ['social', 'soc', 'completado', 'descontado']:
            continue

        nombre_lower = nombre.lower().strip()
        if 'caja de prevision social' in nombre_lower:
            if abs(monto) >= 300000:
                cat, subcat, gasto_final = 'servicios', 'salud', 'Caja de Previsión Social'
            else:
                cat, subcat, gasto_final = 'servicios', 'jubilacion', 'Caja de Previsión Social'
        else:
            if categorizar_gasto_fn:
                cat, subcat, gasto_final = categorizar_gasto_fn(nombre, datos)
            else:
                cat, subcat, gasto_final = categorizar_gasto_parser(nombre, datos)

        gastos.append({
            'fecha': fecha,
            'gasto': gasto_final,
            'monto': abs(monto),
            'moneda': 'ARS',
            'fuente': 'Binance QR',
            'categoria': cat,
            'subcategoria': subcat,
            'owner': owner,
            'medio_pago': medio_pago or 'QR Binance',
            'u_id': generar_id()
        })

    seen = set()
    gastos_dedup = []
    for g in gastos:
        key = (
            g.get('fecha', ''),
            g.get('gasto', '').lower(),
            round(g.get('monto', 0), 2)
        )
        if key not in seen:
            seen.add(key)
            gastos_dedup.append(g)

    if not gastos_dedup:
        return [], texto_debug, "No se detectaron egresos Binance QR"

    return gastos_dedup, texto_debug, None

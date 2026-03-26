"""
Parser para capturas de app móvil MercadoPago.
Formato:
Fecha
Transferencia enviada / Compra / etc
Descripción
$ -1.700
"""
import re
from parsers.base import (
    imagen_a_items_paddle,
    categorizar_gasto_parser,
    generar_id,
)


def parsear_monto_app(texto):
    """
    Montos sin ARS:
      $ -3.000
      $ -900
      - $ 1.600
    """
    s = texto.strip()
    s = s.replace('$', '').replace(' ', '')

    # Remover signo negativo al final para float()
    if s.startswith('-'):
        negativo = True
        s = s[1:]
    else:
        negativo = False

    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        parts = s.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) == 2:
            pass
        else:
            s = s.replace('.', '')

    try:
        monto = float(s)
        return monto if not negativo else -monto
    except:
        return 0.0


def parsear_fecha_app(texto):
    """
    Fechas:
      18 feb
      27 fehrero
    """
    meses_short = {
        'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06',
        'jul': '07', 'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12',
    }
    m = re.search(r'(\d{1,2})\s+([a-z]+)', texto.lower().strip())
    if m:
        dia = m.group(1).zfill(2)
        mes_str = m.group(2)
        mes = meses_short.get(mes_str[:3])
        if mes:
            # Asumir año actual o 2026
            return f"2026-{mes}-{dia}"
    return ''


def es_linea_fecha(texto):
    return bool(parsear_fecha_app(texto))


def es_linea_monto(texto):
    return '$' in texto and bool(re.search(r'\$?\s*-?\s*[\d.,]+', texto))


def es_transferencia(texto):
    t = texto.lower()
    return 'transferencia enviada' in t or 'transferencia' in t


def es_monto(texto):
    return '$' in texto and bool(re.search(r'[\d.,]+', texto))


def procesar_mercadopago_app(archivo, owner, medio_pago, datos, categorizar_gasto_fn=None):
    """
    Procesa captura de app móvil MercadoPago.
    """
    items, texto_debug = imagen_a_items_paddle(archivo)

    if not items:
        return [], texto_debug, "No se pudo leer la imagen"

    gastos = []
    i = 0

    while i < len(items):
        item = items[i]
        y_actual = item['y']

        # Buscar fecha arriba o misma línea
        fecha = ''
        fecha_y = 9999
        for j in range(i - 3, i + 1):
            if 0 <= j < len(items):
                f = parsear_fecha_app(items[j]['text'])
                if f:
                    fecha = f
                    fecha_y = items[j]['y']
                    break

        if not fecha:
            i += 1
            continue

        # Buscar descripción entre fecha y monto
        descripcion_lines = []
        for j in range(i + 1, i + 4):
            if j < len(items):
                texto = items[j]['text'].strip().lower()
                if es_monto(items[j]['text']) or abs(items[j]['y'] - y_actual) > 50:
                    break
                if texto not in ['', 'transferencia enviada', 'compra', 'pago']:
                    descripcion_lines.append(items[j]['text'].strip())

        descripcion = ' '.join(descripcion_lines).strip()
        if not descripcion:
            i += 1
            continue

        # Buscar monto cerca
        monto = 0
        monto_y = 9999
        for j in range(i, i + 5):
            if j < len(items):
                m = parsear_monto_app(items[j]['text'])
                if m > 0 or m < -1:  # monto válido
                    if abs(items[j]['y'] - y_actual) < 40:
                        monto = m
                        monto_y = items[j]['y']
                        break

        if monto >= 0:
            i += 1
            continue

        monto_abs = abs(monto)

        cat, subcat, gasto_final = categorizar_gasto_parser(descripcion, datos)

        gastos.append({
            'fecha': fecha,
            'gasto': gasto_final,
            'monto': monto_abs,
            'moneda': 'ARS',
            'fuente': 'MercadoPago App',
            'categoria': cat,
            'subcategoria': subcat,
            'owner': owner,
            'medio_pago': medio_pago or 'Mercado Pago App',
            'u_id': generar_id()
        })

        i += 1

    seen = set()
    gastos_dedup = []
    for g in gastos:
        key = (g.get('fecha', ''), g.get('gasto', '').lower(), round(g.get('monto', 0), 2))
        if key not in seen:
            seen.add(key)
            gastos_dedup.append(g)

    if not gastos_dedup:
        return [], texto_debug, "No se detectaron egresos"

    return gastos_dedup, texto_debug, None

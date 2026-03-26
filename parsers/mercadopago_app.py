"""
Parser definitivo para capturas app MercadoPago móvil.
Optimizado para OCR real.
"""
import re
from parsers.base import (
    imagen_a_items_paddle,
    categorizar_gasto_parser,
    generar_id,
)


def parsear_monto_app(texto):
    texto = texto.strip()
    if '$' not in texto:
        return 0.0

    s = texto.replace('$', '').replace(' ', '')

    negativo = s.startswith('-')
    if negativo:
        s = s[1:]

    # Limpiar OCR raro
    s = s.replace('°', '')
    s = s.replace('o', '0')
    s = s.replace('O', '0')
    s = s.replace('s', '5') if re.match(r'^\d+\.\d+s\d*$', s) else s

    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        # Si tiene un solo punto y 2 decimales, dejarlo
        parts = s.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) == 2:
            pass
        else:
            s = s.replace('.', '')

    try:
        monto = float(s)
        return -monto if negativo else monto
    except:
        return 0.0


def parsear_fecha_app(texto):
    t = texto.strip().lower()

    m = re.search(r'(\d{1,2})\s*(de\s+)?(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)', t)
    if m:
        dia = m.group(1).zfill(2)
        mes_txt = m.group(3)[:3]
        meses = {
            'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
        }
        mes = meses.get(mes_txt)
        if mes:
            return f"2026-{mes}-{dia}"

    return ''


def normalizar_texto(texto):
    return ' '.join(texto.strip().split())


def procesar_mercadopago_app(archivo, owner, medio_pago, datos, categorizar_gasto_fn=None):
    items, texto_debug = imagen_a_items_paddle(archivo)

    if not items:
        return [], texto_debug, "No se pudo leer la imagen"

    gastos = []
    fecha_actual = ''

    # Ordenados por Y
    items = sorted(items, key=lambda x: x['y'])

    i = 0
    while i < len(items):
        texto = normalizar_texto(items[i]['text'])
        y = items[i]['y']

        # 1. detectar fecha de sección
        fecha_detectada = parsear_fecha_app(texto)
        if fecha_detectada:
            fecha_actual = fecha_detectada
            i += 1
            continue

        # 2. detectar tipo de movimiento relevante
        t_low = texto.lower()
        if 'transferencia enviada' in t_low or 'pago' == t_low or 'pago de servicio' in t_low:
            tipo_mov = texto

            # 3. buscar descripción en la línea siguiente cercana
            descripcion = ''
            monto = 0.0

            # siguiente línea útil = descripción
            j = i + 1
            while j < len(items):
                texto_j = normalizar_texto(items[j]['text'])
                if items[j]['y'] - y > 40:
                    break

                # si tiene monto, no es descripción
                if '$' not in texto_j and not parsear_fecha_app(texto_j):
                    if texto_j.lower() not in ['10resultados', 'buscar']:
                        descripcion = texto_j
                        break
                j += 1

            # 4. buscar monto en misma línea del tipo de movimiento o líneas cercanas
            for k in range(i, min(i + 3, len(items))):
                if abs(items[k]['y'] - y) <= 20:
                    m = parsear_monto_app(items[k]['text'])
                    if m < 0:
                        monto = abs(m)
                        break

            # fallback: buscar monto un poco más abajo si OCR lo separó
            if monto == 0:
                for k in range(i, min(i + 4, len(items))):
                    if items[k]['y'] - y <= 30:
                        m = parsear_monto_app(items[k]['text'])
                        if m < 0:
                            monto = abs(m)
                            break

            # solo guardar si hay fecha + descripcion + monto
            if fecha_actual and descripcion and monto > 0:
                if categorizar_gasto_fn:
                    cat, subcat, gasto_final = categorizar_gasto_fn(descripcion, datos)
                else:
                    cat, subcat, gasto_final = categorizar_gasto_parser(descripcion, datos)

                gastos.append({
                    'fecha': fecha_actual,
                    'gasto': gasto_final,
                    'monto': monto,
                    'moneda': 'ARS',
                    'fuente': 'MercadoPago App',
                    'categoria': cat,
                    'subcategoria': subcat,
                    'owner': owner,
                    'medio_pago': medio_pago or 'Mercado Pago',
                    'u_id': generar_id()
                })

        i += 1

    # Deduplicar
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
        return [], texto_debug, "No se detectaron egresos"

    return gastos_dedup, texto_debug, None

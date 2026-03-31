"""
Parser para screenshots de movimientos Banco Galicia (app o web).

Formato visual:
    FECHA (izq)          DESCRIPCION (centro)          MONTO (der)
    30/03/2026           Transferencia A Terceros       -$125.000,00

Reglas:
- Monto negativo (-$) = egreso
- Monto positivo ($) = ingreso
- Formato argentino: puntos = miles, coma = decimales
"""
import re
from parsers.base import (
    imagen_a_items_paddle,
    categorizar_gasto_parser,
    generar_id,
)


def parsear_fecha_galicia(texto):
    """
    Formatos:
      30/03/2026
      30-03-2026
      30/03/26
    Retorna: 2026-03-30
    """
    texto = texto.strip()

    # DD/MM/YYYY o DD-MM-YYYY
    m = re.match(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', texto)
    if m:
        dia = m.group(1).zfill(2)
        mes = m.group(2).zfill(2)
        anio = m.group(3)
        if 1 <= int(dia) <= 31 and 1 <= int(mes) <= 12 and 2020 <= int(anio) <= 2030:
            return f"{anio}-{mes}-{dia}"

    # DD/MM/YY
    m = re.match(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})', texto)
    if m:
        dia = m.group(1).zfill(2)
        mes = m.group(2).zfill(2)
        anio = f"20{m.group(3)}"
        if 1 <= int(dia) <= 31 and 1 <= int(mes) <= 12:
            return f"{anio}-{mes}-{dia}"

    return ''


def parsear_monto_galicia(texto):
    """
    Formato argentino:
      -$125.000,00  -> -125000.00
      $40.000,00    ->  40000.00
      -$3.500       -> -3500.00
      $1.234.567,89 ->  1234567.89

    Retorna float con signo (negativo = egreso).
    """
    t = texto.strip()

    # Detectar signo
    negativo = '-' in t

    # Limpiar todo excepto dígitos, puntos, comas
    t = re.sub(r'[^\d.,]', '', t)

    if not t:
        return 0.0

    # Formato argentino: puntos = miles, coma = decimal
    if ',' in t:
        t = t.replace('.', '').replace(',', '.')
    else:
        # Sin coma: puede ser "125.000" (miles) o "125000"
        # Si tiene punto y los dígitos después del último punto son 3 -> separador miles
        parts = t.split('.')
        if len(parts) > 1 and len(parts[-1]) == 3:
            t = t.replace('.', '')
        elif len(parts) > 1 and len(parts[-1]) == 2:
            # Podría ser decimal: 3500.50
            t = t.replace('.', '', t.count('.') - 1)
        else:
            t = t.replace('.', '')

    try:
        valor = float(t)
        return -valor if negativo else valor
    except (ValueError, TypeError):
        return 0.0


def _es_linea_fecha(texto):
    return bool(parsear_fecha_galicia(texto))


def _es_linea_monto(texto):
    t = texto.strip()
    return bool(re.search(r'[\-]?\$[\d.,]+', t)) or bool(re.search(r'[\-]?\d+\.\d{3}', t))


def _es_texto_basura(texto):
    t = texto.strip().lower()
    basura = [
        'todos los movimientos', 'fecha', 'descripcion', 'descripción',
        'monto', 'saldo', 'movimientos', 'filtrar', 'buscar', 'ver más',
        'ver mas', 'cuenta', 'caja de ahorro', 'cuenta corriente',
        'pesos', 'dolares', 'dólares', 'anterior', 'siguiente',
        'inicio', 'menú', 'menu', 'cerrar', 'salir'
    ]
    return any(b in t for b in basura) or len(t) < 2


def _agrupar_por_filas(items, tolerancia_y=20):
    """
    Agrupa items de OCR en filas por proximidad vertical.
    Retorna lista de filas, cada fila es lista de items ordenados por x.
    """
    if not items:
        return []

    filas = []
    fila_actual = [items[0]]
    y_ref = items[0]['y']

    for item in items[1:]:
        if abs(item['y'] - y_ref) <= tolerancia_y:
            fila_actual.append(item)
        else:
            fila_actual.sort(key=lambda i: i['x_left'])
            filas.append(fila_actual)
            fila_actual = [item]
            y_ref = item['y']

    if fila_actual:
        fila_actual.sort(key=lambda i: i['x_left'])
        filas.append(fila_actual)

    return filas


def _extraer_movimiento_de_fila(fila):
    """
    Dada una fila de items OCR ordenados por x_left,
    intenta extraer (fecha, descripcion, monto).
    Retorna dict o None.
    """
    if not fila:
        return None

    fecha = ''
    descripcion_parts = []
    monto = 0.0
    monto_encontrado = False

    for item in fila:
        texto = item['text'].strip()

        if not texto or _es_texto_basura(texto):
            continue

        # Intentar fecha
        if not fecha:
            f = parsear_fecha_galicia(texto)
            if f:
                fecha = f
                continue

        # Intentar monto (generalmente el más a la derecha)
        if _es_linea_monto(texto):
            m = parsear_monto_galicia(texto)
            if m != 0:
                monto = m
                monto_encontrado = True
                continue

        # Lo demás es descripción
        if texto and len(texto) > 1:
            descripcion_parts.append(texto)

    descripcion = ' '.join(descripcion_parts).strip()

    if fecha and monto_encontrado and descripcion:
        return {
            'fecha': fecha,
            'descripcion': descripcion,
            'monto': monto
        }

    return None


def _intentar_reconstruir_filas_sueltas(filas_raw, items):
    """
    Cuando OCR separa fecha/desc/monto en filas distintas,
    reconstruye agrupando por proximidad.
    """
    movimientos = []
    fechas_sueltas = []
    descs_sueltas = []
    montos_sueltos = []

    for fila in filas_raw:
        textos = [it['text'].strip() for it in fila]
        texto_unido = ' '.join(textos)

        tiene_fecha = any(parsear_fecha_galicia(t) for t in textos)
        tiene_monto = any(_es_linea_monto(t) for t in textos)

        if tiene_fecha and not tiene_monto:
            for t in textos:
                f = parsear_fecha_galicia(t)
                if f:
                    fechas_sueltas.append((f, fila[0]['y']))
                    break

        elif tiene_monto and not tiene_fecha:
            for t in textos:
                if _es_linea_monto(t):
                    m = parsear_monto_galicia(t)
                    if m != 0:
                        montos_sueltos.append((m, fila[0]['y']))
                        break

        elif not tiene_fecha and not tiene_monto:
            desc = ' '.join(t for t in textos if not _es_texto_basura(t) and len(t) > 1)
            if desc:
                descs_sueltas.append((desc, fila[0]['y']))

    # Intentar emparejar fecha+desc+monto por cercanía en Y
    usadas_desc = set()
    usados_monto = set()

    for fecha, y_fecha in fechas_sueltas:
        mejor_desc = ''
        mejor_desc_idx = -1
        mejor_dist_desc = 999

        for idx, (desc, y_desc) in enumerate(descs_sueltas):
            if idx in usadas_desc:
                continue
            dist = abs(y_desc - y_fecha)
            if dist < mejor_dist_desc and dist < 40:
                mejor_dist_desc = dist
                mejor_desc = desc
                mejor_desc_idx = idx

        mejor_monto = 0.0
        mejor_monto_idx = -1
        mejor_dist_monto = 999

        for idx, (monto, y_monto) in enumerate(montos_sueltos):
            if idx in usados_monto:
                continue
            dist = abs(y_monto - y_fecha)
            if dist < mejor_dist_monto and dist < 40:
                mejor_dist_monto = dist
                mejor_monto = monto
                mejor_monto_idx = idx

        if mejor_desc and mejor_monto != 0:
            movimientos.append({
                'fecha': fecha,
                'descripcion': mejor_desc,
                'monto': mejor_monto
            })
            if mejor_desc_idx >= 0:
                usadas_desc.add(mejor_desc_idx)
            if mejor_monto_idx >= 0:
                usados_monto.add(mejor_monto_idx)

    return movimientos


def procesar_galicia_img(archivo, owner, medio_pago, datos, categorizar_gasto_fn=None,
                         solo_egresos=True):
    """
    Procesa screenshot de movimientos Banco Galicia.

    Args:
        archivo: imagen subida
        owner: string owner
        medio_pago: string medio de pago
        datos: dict datos app
        categorizar_gasto_fn: función de categorización (de app.py)
        solo_egresos: True = solo montos negativos, False = todos

    Returns:
        tuple: (gastos, texto_debug, error)
    """
    items, texto_debug = imagen_a_items_paddle(archivo)

    if not items:
        return [], texto_debug, "No se pudo leer la imagen"

    # Filtrar basura antes de agrupar
    items_limpios = [it for it in items if not _es_texto_basura(it['text'])]

    if not items_limpios:
        return [], texto_debug, "No se detectó texto útil"

    # Agrupar en filas
    filas = _agrupar_por_filas(items_limpios)

    texto_debug += "\n\n=== FILAS AGRUPADAS ===\n"
    for idx, fila in enumerate(filas):
        textos = [it['text'] for it in fila]
        texto_debug += f"Fila {idx}: {' | '.join(textos)}\n"

    # Estrategia 1: extraer de filas completas
    movimientos = []
    filas_sin_match = []

    for fila in filas:
        mov = _extraer_movimiento_de_fila(fila)
        if mov:
            movimientos.append(mov)
        else:
            filas_sin_match.append(fila)

    # Estrategia 2: reconstruir filas sueltas
    if filas_sin_match:
        movimientos_extra = _intentar_reconstruir_filas_sueltas(filas_sin_match, items_limpios)
        movimientos.extend(movimientos_extra)

    texto_debug += f"\n=== MOVIMIENTOS DETECTADOS: {len(movimientos)} ===\n"
    for mov in movimientos:
        signo = "EGRESO" if mov['monto'] < 0 else "INGRESO"
        texto_debug += f"  {mov['fecha']} | {mov['descripcion']} | ${mov['monto']:,.2f} ({signo})\n"

    # Filtrar según tipo
    if solo_egresos:
        movimientos = [m for m in movimientos if m['monto'] < 0]
    else:
        movimientos = [m for m in movimientos if m['monto'] > 0]

    if not movimientos:
        tipo = "egresos" if solo_egresos else "ingresos"
        return [], texto_debug, f"No se detectaron {tipo}"

    # Construir gastos
    gastos = []
    for mov in movimientos:
        desc = mov['descripcion']
        monto_abs = abs(mov['monto'])

        if monto_abs < 1:
            continue

        # Si descripción es genérica, agregar monto para diferenciar
        DESCRIPCIONES_GENERICAS = [
            'transferencia a terceros',
            'transferencia',
            'debito automatico',
            'débito automático',
            'pago',
            'cargo',
        ]
        if desc.strip().lower() in DESCRIPCIONES_GENERICAS:
            desc = f"{desc} (${monto_abs:,.0f})"

        if categorizar_gasto_fn:
            cat, subcat, gasto_final = categorizar_gasto_fn(desc, datos)
        else:
            cat, subcat, gasto_final = categorizar_gasto_parser(desc, datos)

        gastos.append({
            'fecha': mov['fecha'],
            'gasto': gasto_final,
            'monto': monto_abs,
            'moneda': 'ARS',
            'fuente': 'Galicia IMG',
            'categoria': cat,
            'subcategoria': subcat,
            'owner': owner,
            'medio_pago': medio_pago or 'Banco Galicia',
            'u_id': generar_id()
        })

    # Deduplicar
    seen = set()
    gastos_dedup = []
    for g in gastos:
        key = (g['fecha'], g['gasto'].lower(), round(g['monto'], 2))
        if key not in seen:
            seen.add(key)
            gastos_dedup.append(g)

    if not gastos_dedup:
        return [], texto_debug, "No se detectaron gastos después de deduplicar"

    return gastos_dedup, texto_debug, None
"""
Parser para Resúmenes de Cuenta MercadoPago en PDF.
Formato vertical:
    Fecha
    Descripción (1 o más líneas)
    ID operación
    Valor
    Saldo
"""
import re
from parsers.base import categorizar_gasto_parser, generar_id


def parsear_fecha_mercadopago(texto):
    m = re.match(r'(\d{2})-(\d{2})-(\d{4})$', texto.strip())
    if not m:
        return ''
    dia, mes, anio = m.groups()
    return f"{anio}-{mes}-{dia}"


def parsear_monto_mercadopago(texto):
    s = texto.strip()
    s = s.replace('$', '').replace(' ', '')

    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        parts = s.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) == 2:
            pass
        else:
            s = s.replace('.', '')

    try:
        return float(s)
    except:
        return 0.0


def es_fecha(texto):
    return bool(re.match(r'^\d{2}-\d{2}-\d{4}$', texto.strip()))


def es_id_operacion(texto):
    t = texto.strip()
    return t.isdigit() and len(t) >= 8


def es_monto(texto):
    return '$' in texto and bool(re.search(r'[-\d.,]+', texto))


def limpiar_descripcion(descripcion):
    d = ' '.join(descripcion.split())
    d = d.replace('Transferencia enviada', '').strip()
    d = d.replace('Transferencia recibida', '').strip()
    d = d.replace('Pago ', '').strip()
    return d


def es_linea_basura(texto):
    t = texto.strip().lower()

    if not t:
        return True

    if re.match(r'^\d+/\d+$', t):
        return True

    if t in ['fecha', 'descripción', 'descripcion', 'valor', 'saldo']:
        return True

    if t in ['operación', 'operacion']:
        return True

    if t == 'id de la':
        return True

    if any(x in t for x in [
        'resumen de cuenta',
        'detalle de movimientos',
        'saldo inicial',
        'saldo final',
        'entradas:',
        'salidas:',
        'periodo:',
        'cvu:',
        'cuit/ cuil',
        'fecha de generación',
        'mercado libre s.r.l.',
        'encuentra nuestros canales',
        'www.mercadopago.com.ar'
    ]):
        return True

    return False


def procesar_mercadopago_pdf(archivo, owner, medio_pago, datos, categorizar_gasto_fn=None):
    try:
        import pymupdf

        if hasattr(archivo, 'seek'):
            archivo.seek(0)

        pdf_bytes = archivo.read()
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

        texto = ""
        for page in doc:
            texto += page.get_text() + "\n"
        doc.close()

        debug_lines = []
        debug_lines.append("=== TEXTO ORIGINAL ===")
        debug_lines.append(texto)

        lineas_crudas = [l.strip() for l in texto.split('\n')]
        lineas = [l for l in lineas_crudas if not es_linea_basura(l)]

        debug_lines.append("\n=== LINEAS LIMPIAS ===")
        for idx, l in enumerate(lineas):
            debug_lines.append(f"{idx:03d}: {l}")

        gastos = []
        i = 0

        while i < len(lineas):
            linea = lineas[i]

            if not es_fecha(linea):
                i += 1
                continue

            fecha = parsear_fecha_mercadopago(linea)
            debug_lines.append(f"\n[BLOQUE] Fecha detectada: {fecha} en línea {i}")

            j = i + 1
            descripcion_partes = []

            while j < len(lineas) and not es_id_operacion(lineas[j]):
                if es_fecha(lineas[j]):
                    break
                descripcion_partes.append(lineas[j])
                j += 1

            debug_lines.append(f"  Descripción partes: {descripcion_partes}")

            if j >= len(lineas):
                debug_lines.append("  -> bloque abortado: no llegó a ID")
                i += 1
                continue

            if not es_id_operacion(lineas[j]):
                debug_lines.append(f"  -> bloque abortado: no encontró ID en línea {j}, valor='{lineas[j]}'")
                i += 1
                continue

            id_operacion = lineas[j]
            debug_lines.append(f"  ID operación: {id_operacion}")
            j += 1

            if j >= len(lineas):
                debug_lines.append("  -> bloque abortado: no llegó a valor")
                i += 1
                continue

            if not es_monto(lineas[j]):
                debug_lines.append(f"  -> bloque abortado: valor inválido en línea {j}, valor='{lineas[j]}'")
                i += 1
                continue

            valor_txt = lineas[j]
            valor = parsear_monto_mercadopago(valor_txt)
            debug_lines.append(f"  Valor: {valor_txt} -> {valor}")
            j += 1

            if j >= len(lineas):
                debug_lines.append("  -> bloque abortado: no llegó a saldo")
                i += 1
                continue

            if not es_monto(lineas[j]):
                debug_lines.append(f"  -> bloque abortado: saldo inválido en línea {j}, valor='{lineas[j]}'")
                i += 1
                continue

            saldo_txt = lineas[j]
            debug_lines.append(f"  Saldo: {saldo_txt}")
            j += 1

            descripcion = limpiar_descripcion(' '.join(descripcion_partes))
            debug_lines.append(f"  Descripción limpia: {descripcion}")

            if not descripcion:
                debug_lines.append("  -> bloque descartado: descripción vacía")
                i = j
                continue

            if valor >= 0:
                debug_lines.append("  -> bloque descartado: no es egreso")
                i = j
                continue

            monto_abs = abs(valor)
            dlow = descripcion.lower()

            if 'rendimientos' in dlow:
                debug_lines.append("  -> bloque descartado: rendimiento")
                i = j
                continue

            if categorizar_gasto_fn:
                cat, subcat, gasto_final = categorizar_gasto_fn(descripcion, datos)
            else:
                cat, subcat, gasto_final = categorizar_gasto_parser(descripcion, datos)

            gastos.append({
                'fecha': fecha,
                'gasto': gasto_final,
                'monto': monto_abs,
                'moneda': 'ARS',
                'fuente': 'MercadoPago PDF',
                'categoria': cat,
                'subcategoria': subcat,
                'owner': owner,
                'medio_pago': medio_pago or 'Mercado Pago',
                'u_id': generar_id()
            })

            debug_lines.append(f"  -> egreso agregado: {fecha} | {gasto_final} | {monto_abs}")
            i = j

        seen = set()
        gastos_dedup = []
        for g in gastos:
            key = (g.get('fecha', ''), g.get('gasto', '').lower(), round(g.get('monto', 0), 2))
            if key not in seen:
                seen.add(key)
                gastos_dedup.append(g)

        debug_lines.append(f"\n=== TOTAL EGRESOS DETECTADOS: {len(gastos_dedup)} ===")

        texto_debug = "\n".join(debug_lines)

        if not gastos_dedup:
            return [], texto_debug, "No se detectaron egresos en el PDF"

        return gastos_dedup, texto_debug, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], "", f"Error procesando MercadoPago PDF: {str(e)}"

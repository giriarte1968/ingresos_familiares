"""
Parser para Resúmenes de Cuenta MercadoPago en formato PDF.
Lee texto nativo PDF, no usa OCR.
"""
import re
from parsers.base import (
    categorizar_gasto_parser,
    generar_id,
)


def parsear_monto_mercadopago(texto):
    """Ejemplos: $ -1.700,00 / $ 500,00"""
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
    except (ValueError, TypeError):
        return 0.0


def parsear_fecha_mercadopago(texto):
    """Ejemplo: 07-01-2026 -> 2026-01-07"""
    m = re.match(r'(\d{2})-(\d{2})-(\d{4})', texto.strip())
    if not m:
        return ''
    dia, mes, anio = m.groups()
    return f"{anio}-{mes}-{dia}"


def procesar_mercadopago_pdf(archivo, owner, medio_pago, datos, categorizar_gasto_fn=None):
    """Procesa Resumen de Cuenta MercadoPago PDF."""
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

        texto_debug = texto

        lineas = texto.split('\n')
        gastos = []

        # Buscar inicio de la tabla
        inicio_tabla = None
        for i, linea in enumerate(lineas):
            if 'DETALLE DE MOVIMIENTOS' in linea:
                inicio_tabla = i + 4
                break

        if inicio_tabla is None:
            return [], texto_debug, "No se encontró la tabla de movimientos"

        # Recorrer filas de la tabla
        i = inicio_tabla
        while i < len(lineas):
            linea = lineas[i].strip()

            if not linea:
                i += 1
                continue

            # Fin de la tabla
            if 'Saldo final' in linea or 'TOTAL' in linea:
                break

            # Patrón de fila válida: fecha DD-MM-AAAA
            if not re.match(r'^\d{2}-\d{2}-\d{4}', linea):
                i += 1
                continue

            partes = linea.split()
            fecha_raw = partes[0]
            fecha = parsear_fecha_mercadopago(fecha_raw)

            # Buscar monto al final
            monto_match = re.search(r'\$\s*[-\d.,]+', linea)
            if not monto_match:
                i += 1
                continue

            monto_raw = monto_match.group(0)
            monto = parsear_monto_mercadopago(monto_raw)

            # Solo egresos (monto negativo)
            if monto >= 0:
                i += 1
                continue

            monto_abs = abs(monto)

            # Limpiar descripción
            descripcion_raw = linea[len(fecha_raw):monto_match.start()].strip()
            descripcion = descripcion_raw.replace('Transferencia enviada', '').replace('Transferencia', '').replace('Compra', '').replace('Pago', '').strip()

            # Categorización
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

            i += 1

        if not gastos:
            return [], texto_debug, "No se detectaron egresos en el PDF"

        return gastos, texto_debug, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], "", f"Error procesando MercadoPago PDF: {str(e)}"

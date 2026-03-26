"""
Parser definitivo para Resúmenes MercadoPago PDF.
Funciona con estructura vertical y multi-línea.
"""
import re
from parsers.base import categorizar_gasto_parser, generar_id


def parsear_fecha_mercadopago(texto):
    m = re.match(r'(\d{2})-(\d{2})-(\d{4})', texto.strip())
    if m:
        dia, mes, anio = m.groups()
        return f"{anio}-{mes}-{dia}"
    return ''


def parsear_monto_mercadopago(texto):
    s = texto.strip().replace('$', '').replace(' ', '')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except:
        return 0.0


def es_fecha(texto):
    return bool(parsear_fecha_mercadopago(texto))


def es_id_operacion(texto):
    t = texto.strip()
    return t.isdigit() and len(t) >= 8


def es_monto(texto):
    return '$' in texto


def limpiar_descripcion(descripcion_lines):
    """Limpia y une líneas de descripción"""
    d = []
    for line in descripcion_lines:
        line = line.strip()
        if line:
            d.append(line)
    d = ' '.join(d)
    d = re.sub(r'Transferencia enviada\s+', '', d)
    d = re.sub(r'Transferencia recibida\s+', '', d)
    d = re.sub(r'\s+', ' ', d).strip()
    return d


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

        # Convertir a líneas limpias
        lineas_crudas = [l.strip() for l in texto.split('\n') if l.strip()]
        lineas = lineas_crudas[:]

        # Filtrar líneas basura conocidas
        lineas_limpias = []
        for l in lineas_crudas:
            t = l.lower()
            if any(bad in t for bad in ['/4', 'fecha', 'descripción', 'operación', 'valor', 'saldo', 'resumen de cuenta', 'detalle de movimientos', 'saldo inicial', 'saldo final', 'mercado libre', 'www.mercadopago']):
                continue
            lineas_limpias.append(l)

        gastos = []

        i = 0
        while i < len(lineas_limpias):
            linea = lineas_limpias[i]

            # Buscar fecha
            if not es_fecha(linea):
                i += 1
                continue

            fecha = parsear_fecha_mercadopago(linea)
            if not fecha:
                i += 1
                continue

            # Juntar descripción hasta encontrar ID
            descripcion_lines = []
            i += 1
            while i < len(lineas_limpias):
                linea_next = lineas_limpias[i]

                if es_id_operacion(linea_next):
                    break

                if es_fecha(linea_next):
                    i -= 1
                    break

                descripcion_lines.append(linea_next)
                i += 1

            descripcion = limpiar_descripcion(descripcion_lines)

            if not descripcion:
                i += 1
                continue

            # ID operación
            if i >= len(lineas_limpias):
                break

            id_operacion = lineas_limpias[i]
            if not es_id_operacion(id_operacion):
                i += 1
                continue
            i += 1

            # Valor
            if i >= len(lineas_limpias):
                break

            valor_txt = lineas_limpias[i]
            valor = parsear_monto_mercadopago(valor_txt)
            if not es_monto(valor_txt):
                i += 1
                continue
            i += 1

            # Saldo
            if i >= len(lineas_limpias):
                break

            saldo_txt = lineas_limpias[i]
            if not es_monto(saldo_txt):
                i += 1
                continue
            i += 1

            # Solo egresos
            if valor >= 0:
                continue

            monto_abs = abs(valor)

            if monto_abs < 1.0:
                continue

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

        # Deduplicar
        seen = set()
        gastos_dedup = []
        for g in gastos:
            key = (g.get('fecha', ''), g.get('gasto', '').lower(), round(g.get('monto', 0), 2))
            if key not in seen:
                seen.add(key)
                gastos_dedup.append(g)

        if not gastos_dedup:
            return [], texto, "No se detectaron egresos"

        return gastos_dedup, texto, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], "", f"Error: {str(e)}"

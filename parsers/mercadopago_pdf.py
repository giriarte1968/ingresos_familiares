"""
Parser para Resúmenes de Cuenta MercadoPago en PDF.
Formato detectado: extracción vertical por bloques:
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
    """
    Ejemplos:
      $ -1.700,00
      $ 500,00
      $ 2.839,60
    """
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


def es_saldo(texto):
    # saldo tiene formato igual al monto, pero aparece justo después del valor
    return es_monto(texto)


def limpiar_descripcion(descripcion):
    d = ' '.join(descripcion.split())
    d = d.replace('Transferencia enviada', '').strip()
    d = d.replace('Transferencia recibida', '').strip()
    d = d.replace('Dinero retirado misión', 'Dinero retirado misión').strip()
    d = d.replace('Dinero reservado misión', 'Dinero reservado misión').strip()
    return d


def procesar_mercadopago_pdf(archivo, owner, medio_pago, datos, categorizar_gasto_fn=None):
    """
    Procesa Resumen MercadoPago PDF con estructura vertical.
    """
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
        lineas = [l.strip() for l in texto.split('\n') if l.strip()]

        gastos = []

        i = 0
        while i < len(lineas):
            linea = lineas[i]

            # Buscar inicio de bloque por fecha
            if not es_fecha(linea):
                i += 1
                continue

            fecha = parsear_fecha_mercadopago(linea)
            if not fecha:
                i += 1
                continue

            j = i + 1
            descripcion_partes = []

            # Acumular descripción hasta encontrar ID operación
            while j < len(lineas) and not es_id_operacion(lineas[j]):
                # cortar si aparece otra fecha inesperada
                if es_fecha(lineas[j]):
                    break
                descripcion_partes.append(lineas[j])
                j += 1

            if j >= len(lineas):
                i += 1
                continue

            # ID operación
            if not es_id_operacion(lineas[j]):
                i += 1
                continue
            id_operacion = lineas[j]
            j += 1

            if j >= len(lineas):
                i += 1
                continue

            # Valor
            if not es_monto(lineas[j]):
                i += 1
                continue
            valor_txt = lineas[j]
            valor = parsear_monto_mercadopago(valor_txt)
            j += 1

            if j >= len(lineas):
                i += 1
                continue

            # Saldo
            if not es_saldo(lineas[j]):
                i += 1
                continue
            saldo_txt = lineas[j]
            j += 1

            descripcion = limpiar_descripcion(' '.join(descripcion_partes))

            if not descripcion:
                i = j
                continue

            # Solo egresos: valor negativo
            if valor >= 0:
                i = j
                continue

            monto_abs = abs(valor)

            # Filtrar cosas que no queremos como egreso real si querés
            dlow = descripcion.lower()

            # Casos especiales MercadoPago
            if 'rendimientos' in dlow:
                i = j
                continue

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

            i = j

        # Deduplicar
        seen = set()
        gastos_dedup = []
        for g in gastos:
            key = (g.get('fecha', ''), g.get('gasto', '').lower(), round(g.get('monto', 0), 2))
            if key not in seen:
                seen.add(key)
                gastos_dedup.append(g)

        if not gastos_dedup:
            return [], texto_debug, "No se detectaron egresos en el PDF"

        return gastos_dedup, texto_debug, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return [], "", f"Error procesando MercadoPago PDF: {str(e)}"

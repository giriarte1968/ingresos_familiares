"""
Parser para cartola Banco Santander Chile (PDF texto).
Basado en la lógica original de parsear_texto() que ya funcionaba.
"""
import re
from parsers.base import generar_id


def extraer_montos_chilenos(texto):
    """Extrae montos en formato chileno: 1.000.000 o 55.719"""
    montos = []
    # Formato con puntos de miles: 2.764.046 o 55.719
    patron = r'(?<!\d)(\d{1,3}(?:\.\d{3})+)(?!\d)'
    matches = re.findall(patron, texto)
    for m in matches:
        valor = m.replace('.', '')
        try:
            val = float(valor)
            if val >= 100:
                montos.append(val)
        except:
            pass
    return montos


def extraer_fecha_corta(texto):
    """Extrae DD/MM y retorna como fecha"""
    m = re.search(r'(\d{2})/(\d{2})', texto)
    if m:
        return m.group(1), m.group(2)
    return None, None


def procesar_santander_chile_pdf(archivo, owner, medio_pago, datos,
                                  categorizar_gasto_fn=None, password=None):
    try:
        import pymupdf
    except ImportError:
        return [], [], "", "PyMuPDF no disponible"

    try:
        if hasattr(archivo, 'seek'):
            archivo.seek(0)
        pdf_bytes = archivo.read()
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

        if doc.is_encrypted and password:
            doc.authenticate(password)
        elif doc.is_encrypted:
            return [], [], "", "PDF encriptado. Ingresá la password."

        texto = ""
        for page in doc:
            texto += page.get_text() + "\n"
        doc.close()

    except Exception as e:
        return [], [], "", f"Error leyendo PDF: {e}"

    # Detectar año
    anio = '2026'
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto)
    if m:
        anio = m.group(3)

    lineas = texto.split('\n')

    INGRESO_KEYWORDS = [
        'pago proveedor', 'depósito', 'deposito', 'abono',
        'transferencia recibida', 'depósito a la vista',
        'deposit', 'abonos'
    ]

    # "Transf." SIN "a" = transferencia recibida = ingreso
    # "Transf a" = transferencia enviada = egreso

    EGRESO_KEYWORDS = [
        'transf a ', 'pago a ', 'cobro', 'com.mant', 'com.',
        'seguro de', 'mantencion', 'mantención'
    ]

    texto_debug = "=== PROCESAMIENTO SANTANDER CHILE ===\n"

    ingresos = []
    en_resumen = False

    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()

        # Ignorar resumen de comisiones
        if 'Resumen de Comisiones' in linea or '****' in linea:
            en_resumen = True
            i += 1
            continue
        if 'MENSAJES' in linea or 'INFORMACION DE CUENTA' in linea:
            en_resumen = False
            i += 1
            continue
        if en_resumen:
            i += 1
            continue

        # Solo líneas con fecha DD/MM al inicio
        dia, mes_num = extraer_fecha_corta(linea)
        if not dia or not mes_num:
            i += 1
            continue

        # Verificar que empieza con la fecha
        if not re.match(r'^\d{2}/\d{2}', linea):
            i += 1
            continue

        linea_lower = linea.lower()

        # Verificar si es egreso (skip)
        es_egreso = any(kw in linea_lower for kw in EGRESO_KEYWORDS)

        # Verificar si es ingreso
        es_ingreso = any(kw in linea_lower for kw in INGRESO_KEYWORDS)

        # Caso especial: "Transf." sin "a" = ingreso recibido
        if 'transf.' in linea_lower and 'transf a' not in linea_lower:
            es_ingreso = True
            es_egreso = False

        # Si es egreso, skip
        if es_egreso and not es_ingreso:
            texto_debug += f"EGRESO (skip): {linea}\n"
            i += 1
            continue

        if not es_ingreso:
            texto_debug += f"NO MATCH: {linea}\n"
            i += 1
            continue

        # Es ingreso - buscar monto
        fecha_str = f"{anio}-{mes_num}-{dia}"

        # Extraer montos de esta línea
        montos = extraer_montos_chilenos(linea)

        # Si no hay montos en esta línea, buscar en las siguientes
        if not montos:
            for j in range(1, 5):
                if i + j >= len(lineas):
                    break
                sig = lineas[i + j].strip()
                montos_sig = extraer_montos_chilenos(sig)
                if montos_sig:
                    montos = montos_sig
                    break

        if not montos:
            texto_debug += f"INGRESO SIN MONTO: {linea}\n"
            i += 1
            continue

        # Tomar el monto correcto:
        # Si hay varios montos, el abono es generalmente el menor
        # (el mayor suele ser el saldo)
        if len(montos) >= 2:
            monto = min(montos)
        else:
            monto = montos[0]

        # Extraer descripción limpia
        desc = linea
        # Quitar fecha
        desc = re.sub(r'^\d{2}/\d{2}\s*', '', desc).strip()
        # Quitar sucursal
        for suc in ['Agustinas', 'G.Finanzas', 'G .Finanzas', 'OPER.', 'Huerfanos', 'Internet']:
            if desc.startswith(suc):
                desc = desc[len(suc):].strip()
                break
        # Quitar número de operación largo (sin puntos de miles)
        desc = re.sub(r'^\d{7,}[A-Za-z]?\s*', '', desc).strip()
        # Quitar RUT
        desc = re.sub(r'\d{1,2}\.\d{3}\.\d{3}-[\dkK]\s*', '', desc).strip()
        # Quitar montos del texto
        for m_raw in re.findall(r'\d{1,3}(?:\.\d{3})+', linea):
            desc = desc.replace(m_raw, '').strip()
        # Quitar número de documento (6 dígitos)
        desc = re.sub(r'\b\d{6}\b', '', desc).strip()
        # Limpiar espacios
        desc = re.sub(r'\s+', ' ', desc).strip()

        if not desc or len(desc) < 3:
            desc = "Ingreso Santander"

        texto_debug += f"INGRESO: {fecha_str} | {desc} | ${monto:,.0f} CLP\n"

        ingresos.append({
            'fecha': fecha_str,
            'descripcion': desc,
            'monto': monto,
            'monto_original_clp': monto,
            'banco': 'santander_chile',
            'categoria': 'transferencia',
            'tasas': None,
            'owner': owner or 'Gustavo'
        })

        i += 1

    texto_debug += f"\n=== RESULTADO ===\n"
    texto_debug += f"Ingresos detectados: {len(ingresos)}\n"
    for ing in ingresos:
        texto_debug += f"  {ing['fecha']} | {ing['descripcion']} | ${ing['monto']:,.0f} CLP\n"

    if not ingresos:
        return [], [], texto_debug, "No se detectaron ingresos"

    return ingresos, [], texto_debug, None

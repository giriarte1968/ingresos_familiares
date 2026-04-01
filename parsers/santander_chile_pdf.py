"""
Parser para cartola Banco Santander Chile (PDF texto).
Solo extrae INGRESOS (abonos, pagos proveedor, transferencias recibidas).
"""
import re
from parsers.base import generar_id


def parsear_monto_chileno(texto):
    s = texto.strip().replace('$', '').replace(' ', '')
    if '.' in s and ',' not in s:
        s = s.replace('.', '')
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def extraer_fecha_santander(texto, anio_default='2026'):
    m = re.match(r'(\d{2})/(\d{2})', texto.strip())
    if m:
        dia = m.group(1)
        mes = m.group(2)
        return f"{anio_default}-{mes}-{dia}"
    return ''


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

    lineas = texto.split('\n')

    # Detectar año del extracto
    anio = '2026'
    for linea in lineas:
        m = re.search(r'(\d{2})/(\d{2})/(\d{4})', linea)
        if m:
            anio = m.group(3)
            break

    texto_debug = "=== TODAS LAS LÍNEAS ===\n"
    for i, linea in enumerate(lineas):
        if linea.strip():
            texto_debug += f"{i:3d}: {linea}\n"

    texto_debug += "\n=== PROCESAMIENTO ===\n"

    ingresos = []
    egresos = []
    en_resumen = False

    for linea in lineas:
        linea_clean = linea.strip()

        # Ignorar resumen de comisiones (duplicado)
        if 'Resumen de Comisiones' in linea_clean or '****' in linea_clean:
            en_resumen = True
            continue
        if 'MENSAJES' in linea_clean or 'INFORMACION' in linea_clean:
            en_resumen = False
            continue
        if en_resumen:
            continue

        # Solo procesar líneas que empiezan con DD/MM
        if not re.match(r'^\d{2}/\d{2}', linea_clean):
            continue

        # Extraer fecha
        fecha_match = re.match(r'(\d{2}/\d{2})', linea_clean)
        if not fecha_match:
            continue
        fecha_raw = fecha_match.group(1)
        fecha = extraer_fecha_santander(fecha_raw, anio)

        # Extraer todos los números con formato de miles (X.XXX o X.XXX.XXX)
        montos_encontrados = re.findall(r'(\d{1,3}(?:\.\d{3})+|\d{4,})', linea_clean)
        montos = []
        for m in montos_encontrados:
            val = parsear_monto_chileno(m)
            if val >= 100:
                montos.append(val)

        if not montos:
            continue

        # El SALDO siempre es el último monto (el más grande generalmente)
        saldo = montos[-1] if len(montos) >= 2 else 0

        # Quitar saldo de la lista de montos operativos
        montos_operativos = montos[:-1] if len(montos) >= 2 else montos

        # Extraer descripción: todo entre sucursal y los montos
        # Quitar fecha y sucursal del inicio
        resto = linea_clean[5:].strip()  # Quitar DD/MM

        # Quitar sucursal
        sucursales = ['Agustinas', 'G.Finanzas', 'OPER.', 'Huerfanos', 'Internet',
                      'G .Finanzas', 'G. Finanzas']
        for suc in sucursales:
            if resto.startswith(suc):
                resto = resto[len(suc):].strip()
                break

        # Quitar número de operación del inicio (10+ dígitos o con letras)
        resto = re.sub(r'^\d{7,}[A-Za-z]?\s*', '', resto).strip()

        # Quitar RUT
        resto = re.sub(r'\d{1,2}\.\d{3}\.\d{3}-[\dkK]\s*', '', resto).strip()

        # Quitar todos los montos del texto para obtener descripción limpia
        desc = resto
        for m_str in montos_encontrados:
            desc = desc.replace(m_str, '').strip()

        # Quitar número de documento (6 dígitos sueltos)
        desc = re.sub(r'\b\d{6}\b', '', desc).strip()
        desc = re.sub(r'\s+', ' ', desc).strip()

        if not desc or len(desc) < 3:
            continue

        texto_debug += f"\nLínea: {linea_clean}\n"
        texto_debug += f"  Fecha: {fecha} | Desc: {desc} | Montos: {montos} | Saldo: {saldo}\n"

        # Clasificar: ingreso o egreso
        desc_lower = desc.lower()

        # EGRESOS claros
        es_egreso = False
        if 'transf a ' in desc_lower:
            es_egreso = True
        elif desc_lower.startswith('com.') or 'com.mant' in desc_lower:
            es_egreso = True
        elif 'cobro' in desc_lower:
            es_egreso = True
        elif 'seguro de' in desc_lower:
            es_egreso = True

        # INGRESOS claros
        es_ingreso = False
        if 'pago proveedor' in desc_lower:
            es_ingreso = True
        elif 'deposito' in desc_lower or 'depósito' in desc_lower:
            es_ingreso = True
        elif 'abono' in desc_lower:
            es_ingreso = True
        elif 'transf.' in desc_lower and 'transf a' not in desc_lower:
            es_ingreso = True

        # Si no se pudo clasificar por keywords, intentar por posición de columna
        # En el extracto Santander: si tiene monto en columna DEPOSITOS = ingreso
        # Esto se detecta porque el texto original muestra el monto más a la derecha
        if not es_egreso and not es_ingreso:
            # Default: si tiene montos operativos, es egreso
            es_egreso = True

        # Tomar el monto operativo (no el saldo)
        monto = montos_operativos[0] if montos_operativos else 0

        if monto < 100:
            continue

        texto_debug += f"  -> {'INGRESO' if es_ingreso else 'EGRESO'}: ${monto:,.0f}\n"

        if es_ingreso:
            ingresos.append({
                'fecha': fecha,
                'descripcion': desc,
                'monto': monto,
                'monto_original_clp': monto,
                'banco': 'santander_chile',
                'categoria': 'transferencia',
                'tasas': None,
                'owner': owner or 'Gustavo'
            })
        else:
            if categorizar_gasto_fn:
                cat, subcat, gasto_final = categorizar_gasto_fn(desc, datos)
            else:
                cat, subcat, gasto_final = 'otros', 'otros', desc

            egresos.append({
                'fecha': fecha,
                'gasto': gasto_final,
                'monto': monto,
                'moneda': 'CLP',
                'fuente': 'Santander Chile PDF',
                'categoria': cat,
                'subcategoria': subcat,
                'owner': owner or 'Gustavo',
                'medio_pago': medio_pago or 'Santander Chile',
                'u_id': generar_id(),
                'monto_original_clp': monto
            })

    texto_debug += f"\n=== RESULTADO ===\n"
    texto_debug += f"Ingresos: {len(ingresos)}\n"
    for i in ingresos:
        texto_debug += f"  {i['fecha']} | {i['descripcion']} | ${i['monto']:,.0f} CLP\n"
    texto_debug += f"Egresos: {len(egresos)}\n"
    for e in egresos:
        texto_debug += f"  {e['fecha']} | {e['gasto']} | ${e['monto']:,.0f} CLP\n"

    if not ingresos and not egresos:
        return [], [], texto_debug, "No se detectaron movimientos"

    return ingresos, egresos, texto_debug, None

"""
Parser para cartola Banco Santander Chile (PDF texto).
Solo extrae INGRESOS.
PyMuPDF extrae las columnas como líneas separadas.
"""
import re
from parsers.base import generar_id


def extraer_montos_chilenos(texto):
    """Extrae montos formato chileno: 2.764.046 o 55.719"""
    montos = []
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

    lineas = [l.strip() for l in texto.split('\n') if l.strip()]

    texto_debug = "=== LÍNEAS RAW ===\n"
    for idx, linea in enumerate(lineas):
        texto_debug += f"{idx:3d}: {linea}\n"

    texto_debug += "\n=== RECONSTRUCCIÓN DE MOVIMIENTOS ===\n"

    # Paso 1: Reconstruir bloques de movimiento
    # Cada movimiento empieza con DD/MM seguido de sucursal
    # Las líneas siguientes (hasta el próximo DD/MM) son parte del mismo movimiento
    bloques = []
    bloque_actual = []

    en_resumen = False

    for linea in lineas:
        if 'Resumen de Comisiones' in linea or '****' in linea:
            en_resumen = True
            continue
        if 'MENSAJES' in linea or 'INFORMACION DE CUENTA' in linea:
            en_resumen = False
            continue
        if en_resumen:
            continue

        # Ignorar headers
        if any(h in linea for h in [
            'FECHA', 'SUCURSAL', 'DESCRIPCION', 'SALDOS', 'SALDO',
            'DCTO', 'DEPOSITOS', 'CHEQUES', 'CARGOS', 'ABONOS',
            'DETALLE DE MOVIMIENTOS', 'CARTOLA', 'DESDE', 'HASTA',
            'PAGINA', 'CUENTA CORRIENTE', 'IRIARTE', 'gdiriarte',
            'BANCO SANTANDER', 'EJECUTIVO', 'TELEFONO',
            'HUERFANOS', 'dirección', 'Si su dirección', 'Nota:',
            'MENSAJES', 'SR.CLIENTE', 'INFORMESE', 'INFORMACION',
            'SALDO INICIAL', '0-000-', '0249-M', '38984',
            'En caso de', 'aprobado'
        ]):
            continue

        # ¿Es inicio de nuevo movimiento? (DD/MM + espacio + texto)
        es_inicio = bool(re.match(r'^\d{2}/\d{2}\s', linea))

        # También fechas largas DD/MM/YYYY son headers, no movimientos
        if re.match(r'^\d{2}/\d{2}/\d{4}$', linea):
            continue

        if es_inicio:
            if bloque_actual:
                bloques.append(bloque_actual)
            bloque_actual = [linea]
        else:
            if bloque_actual:
                bloque_actual.append(linea)

    if bloque_actual:
        bloques.append(bloque_actual)

    texto_debug += f"\nBloques encontrados: {len(bloques)}\n"

    # Paso 2: Procesar cada bloque
    INGRESO_KEYWORDS = [
        'pago proveedor', 'depósito', 'deposito', 'abono',
        'transferencia recibida'
    ]

    EGRESO_KEYWORDS = [
        'transf a ', 'cobro', 'com.mant', 'com.',
        'seguro de', 'mantencion', 'mantención'
    ]

    ingresos = []

    for bloque in bloques:
        texto_bloque = ' '.join(bloque).strip()
        texto_lower = texto_bloque.lower()

        # Extraer fecha
        fecha_match = re.match(r'(\d{2})/(\d{2})', bloque[0])
        if not fecha_match:
            continue
        dia = fecha_match.group(1)
        mes_num = fecha_match.group(2)
        fecha_str = f"{anio}-{mes_num}-{dia}"

        # Clasificar
        es_egreso = any(kw in texto_lower for kw in EGRESO_KEYWORDS)

        es_ingreso = any(kw in texto_lower for kw in INGRESO_KEYWORDS)

        # "Transf." sin "a" = recibida = ingreso
        if 'transf.' in texto_lower and 'transf a' not in texto_lower:
            es_ingreso = True
            es_egreso = False

        texto_debug += f"\nBloque: {texto_bloque}\n"
        texto_debug += f"  es_ingreso={es_ingreso} es_egreso={es_egreso}\n"

        if es_egreso and not es_ingreso:
            texto_debug += f"  -> EGRESO (skip)\n"
            continue

        if not es_ingreso:
            texto_debug += f"  -> NO MATCH (skip)\n"
            continue

        # Extraer montos de todo el bloque
        montos = []
        for linea_b in bloque:
            montos.extend(extraer_montos_chilenos(linea_b))

        if not montos:
            texto_debug += f"  -> INGRESO SIN MONTO (skip)\n"
            continue

        # El monto del abono: si hay varios, el menor es el monto
        # (el mayor suele ser saldo)
        if len(montos) >= 2:
            monto = min(montos)
        else:
            monto = montos[0]

        # Extraer descripción
        desc = texto_bloque
        # Quitar fecha
        desc = re.sub(r'^\d{2}/\d{2}\s*', '', desc).strip()
        # Quitar sucursal
        for suc in ['Agustinas', 'G.Finanzas', 'G .Finanzas', 'OPER.', 'Huerfanos', 'Internet']:
            if desc.startswith(suc):
                desc = desc[len(suc):].strip()
                break
        # Quitar número de operación (10+ dígitos sin puntos)
        desc = re.sub(r'\b\d{7,}[A-Za-z]?\b', '', desc).strip()
        # Quitar RUT
        desc = re.sub(r'\d{1,2}\.\d{3}\.\d{3}-[\dkK]', '', desc).strip()
        # Quitar montos
        for m_raw in re.findall(r'\d{1,3}(?:\.\d{3})+', texto_bloque):
            desc = desc.replace(m_raw, '').strip()
        # Quitar número de documento (6 dígitos)
        desc = re.sub(r'\b\d{6}\b', '', desc).strip()
        # Limpiar
        desc = re.sub(r'\s+', ' ', desc).strip()

        if not desc or len(desc) < 3:
            desc = "Ingreso Santander"

        texto_debug += f"  -> INGRESO: {fecha_str} | {desc} | ${monto:,.0f} CLP\n"

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

    texto_debug += f"\n=== RESULTADO FINAL ===\n"
    texto_debug += f"Ingresos: {len(ingresos)}\n"
    for ing in ingresos:
        texto_debug += f"  {ing['fecha']} | {ing['descripcion']} | ${ing['monto']:,.0f} CLP\n"

    if not ingresos:
        return [], [], texto_debug, "No se detectaron ingresos"

    return ingresos, [], texto_debug, None

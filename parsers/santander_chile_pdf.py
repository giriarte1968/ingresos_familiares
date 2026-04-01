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


def es_linea_movimiento(linea):
    return bool(re.match(r'^\d{2}/\d{2}\s', linea.strip()))


def clasificar_movimiento(linea):
    linea_clean = linea.strip()

    fecha_match = re.match(r'(\d{2}/\d{2})', linea_clean)
    fecha_raw = fecha_match.group(1) if fecha_match else ''

    montos_raw = re.findall(r'(?<!\d)(\d{1,3}(?:\.\d{3})*|\d{4,})(?!\d)', linea_clean)
    montos = []
    for m in montos_raw:
        val = parsear_monto_chileno(m)
        if val > 0:
            montos.append(val)

    desc = linea_clean
    if fecha_raw:
        desc = desc[5:].strip()

    sucursales = ['Agustinas', 'G.Finanzas', 'OPER.', 'Huerfanos', 'Internet']
    for suc in sucursales:
        if desc.startswith(suc):
            desc = desc[len(suc):].strip()
            break

    desc = re.sub(r'^\d{8,}\s*', '', desc)
    desc = re.sub(r'\d{1,2}\.\d{3}\.\d{3}-[\dkK]\s*', '', desc)
    desc = re.sub(r'\s+', ' ', desc).strip()

    for m in montos_raw:
        desc = desc.replace(m, '').strip()

    desc = re.sub(r'^\d{4,}\s*', '', desc).strip()

    desc_lower = desc.lower()
    tipo = None

    if 'transf a ' in desc_lower:
        tipo = 'egreso'
    elif 'com.mant' in desc_lower or 'com.' in desc_lower:
        tipo = 'egreso'
    elif 'cobro' in desc_lower:
        tipo = 'egreso'
    elif 'seguro de' in desc_lower:
        tipo = 'egreso'

    elif 'pago proveedor' in desc_lower:
        tipo = 'ingreso'
    elif 'deposito' in desc_lower or 'depósito' in desc_lower:
        tipo = 'ingreso'
    elif 'abono' in desc_lower:
        tipo = 'ingreso'
    elif 'transf.' in desc_lower and 'transf a' not in desc_lower:
        tipo = 'ingreso'

    monto = 0
    saldo = 0

    if len(montos) >= 2:
        saldo = montos[-1]
        monto = montos[-2]
    elif len(montos) == 1:
        monto = montos[0]

    return {
        'fecha_raw': fecha_raw,
        'descripcion': desc,
        'monto': monto,
        'saldo': saldo,
        'tipo_inferido': tipo,
        'montos_encontrados': montos
    }


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

    anio = '2026'
    for linea in lineas:
        m = re.search(r'(\d{2})/(\d{2})/(\d{4})', linea)
        if m:
            anio = m.group(3)
            break

    movimientos_raw = []
    texto_debug = "=== LÍNEAS DE MOVIMIENTO ===\n"

    en_resumen_comisiones = False

    for linea in lineas:
        linea_clean = linea.strip()

        if 'Resumen de Comisiones' in linea_clean:
            en_resumen_comisiones = True
            continue
        if 'MENSAJES' in linea_clean:
            en_resumen_comisiones = False
            continue
        if en_resumen_comisiones:
            continue

        if not es_linea_movimiento(linea_clean):
            continue

        mov = clasificar_movimiento(linea_clean)
        texto_debug += (
            f"{linea_clean}\n"
            f"  -> desc: {mov['descripcion']} | monto: {mov['monto']:,.0f} | "
            f"saldo: {mov['saldo']:,.0f} | tipo: {mov['tipo_inferido']}\n"
        )

        if mov['monto'] > 0 and mov['descripcion']:
            movimientos_raw.append(mov)

    texto_debug += "\n=== INFERENCIA POR SALDO ===\n"
    saldo_anterior = None

    for mov in movimientos_raw:
        if mov['tipo_inferido'] is None and mov['saldo'] > 0:
            if saldo_anterior is not None:
                if mov['saldo'] > saldo_anterior:
                    mov['tipo_inferido'] = 'ingreso'
                else:
                    mov['tipo_inferido'] = 'egreso'
                texto_debug += (
                    f"  {mov['descripcion']}: saldo {saldo_anterior:,.0f} -> "
                    f"{mov['saldo']:,.0f} = {mov['tipo_inferido']}\n"
                )

        if mov['saldo'] > 0:
            saldo_anterior = mov['saldo']

        if mov['tipo_inferido'] is None:
            mov['tipo_inferido'] = 'egreso'

    ingresos = []
    egresos = []

    for mov in movimientos_raw:
        fecha = extraer_fecha_santander(mov['fecha_raw'], anio)
        desc = mov['descripcion']
        monto = mov['monto']

        if monto < 100:
            continue

        if mov['tipo_inferido'] == 'ingreso':
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
    texto_debug += f"Ingresos: {len(ingresos)} ({sum(i['monto'] for i in ingresos):,.0f} CLP)\n"
    texto_debug += f"Egresos: {len(egresos)} ({sum(e['monto'] for e in egresos):,.0f} CLP)\n"

    if not ingresos and not egresos:
        return [], [], texto_debug, "No se detectaron movimientos"

    return ingresos, egresos, texto_debug, None

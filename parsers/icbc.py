"""
Parser para screenshots de app ICBC Argentina.
Formato actual 2026:
    LÍNEA 1: DESCRIPCIÓN                  $ -MONTO
    LÍNEA 2: DD-Mes-AAAA
"""
import re
import time
import random
import io
import numpy as np
from PIL import Image
from parsers.base import (
    imagen_a_items_paddle,
    categorizar_gasto_parser,
    generar_id,
    cargar_comercios_json,
    COMERCIOS_CONOCIDOS
)


def parsear_monto_icbc(texto):
    """
    Ejemplos:
      $ -42.386,74
      $ -4.981,49
      $ 6,60
    """
    s = texto.strip()
    s = s.replace('$', '').replace('-', '').strip()

    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        parts = s.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) == 2:
            pass
        else:
            s = s.replace('.', '')

    try:
        return abs(float(s))
    except (ValueError, TypeError):
        return 0.0


def parsear_fecha_icbc(texto):
    """
    Ejemplo:
      20-Feb-2026
    Devuelve:
      2026-02-20
    """
    m = re.match(r'(\d{1,2})-([A-Za-z]{3})-(\d{4})', texto.strip())
    if not m:
        return ''

    dia = int(m.group(1))
    mes_str = m.group(2)
    anio = int(m.group(3))

    meses = {
        'Ene': '01', 'Feb': '02', 'Mar': '03', 'Abr': '04',
        'May': '05', 'Jun': '06', 'Jul': '07', 'Ago': '08',
        'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dic': '12',
    }

    mes_num = meses.get(mes_str.title()[:3])
    if mes_num is None:
        return ''
    if not (1 <= dia <= 31 and 2020 <= anio <= 2030):
        return ''

    return f"{anio}-{mes_num}-{dia:02d}"


def procesar_icbc(archivo, owner, medio_pago, datos):
    """
    Procesa screenshot de app ICBC Argentina.

    Args:
        archivo: imagen
        owner: Gustavo/Vero/etc
        medio_pago: medio seleccionado
        datos: datos app

    Returns:
        tuple: (gastos, texto_debug, error)
    """
    items, texto_debug = imagen_a_items_paddle(archivo)

    if not items:
        return [], texto_debug, "No se pudo leer la imagen"

    comercios_json = cargar_comercios_json()
    gastos = []

    lineas_monto = []
    for idx, item in enumerate(items):
        texto = item['text']

        if '$' not in texto:
            continue
        
        # Verificar si es monto negativo (egreso) o positivo (ingreso)
        if '-' not in texto:
            # Monto positivo = ingreso, skip
            continue

        monto = parsear_monto_icbc(texto)
        if monto <= 0:
            continue

        lineas_monto.append((idx, item, monto))

    for idx_monto, item_monto, monto in lineas_monto:
        y_monto = item_monto['y']

        descripcion = ''
        for it in items:
            dist_y = abs(it['y'] - y_monto)

            if dist_y < 15:
                if it['x_right'] < item_monto['x_left']:
                    t = it['text'].strip()
                    if '$' not in t and len(t) > 2:
                        descripcion = t

        if not descripcion:
            if idx_monto > 0:
                it_arriba = items[idx_monto - 1]
                t = it_arriba['text'].strip()
                if '$' not in t and len(t) > 2:
                    descripcion = t

        fecha = ''
        if idx_monto + 1 < len(items):
            item_debajo = items[idx_monto + 1]
            fecha = parsear_fecha_icbc(item_debajo['text'])

        if not descripcion or len(descripcion) < 2:
            continue
        if not fecha:
            continue

        dlow = descripcion.lower()
        if any(kw in dlow for kw in ['liquidacion', 'reintegro', 'acreditacion', 'credito', 'transferencia push']):
            continue

        if monto < 1.0:
            continue

        if any(x in dlow for x in ['cuentas', 'movimientos', 'saldo', 'disponible']):
            continue

        if 'spotify' in dlow or 'dlocal spotify' in dlow:
            cat, subcat, g = 'servicios', 'suscripciones', 'Spotify'
        elif 'arca' in dlow or 'pago arca' in dlow:
            cat, subcat, g = 'impuestos', 'impuestos', 'Monotributo'
        elif (
            'iva' in dlow
            or 'impuesto al valor' in dlow
            or 'impuesto al valor agregado' in dlow
        ):
            cat, subcat, g = 'impuestos', 'impuestos', 'IVA'
        elif 'operaciones banel' in dlow:
            cat, subcat, g = 'servicios', 'bancos', 'Operaciones Bancarias'
        elif 'debito inmediato' in dlow:
            cat, subcat, g = 'otros', 'otros', 'Débito Inmediato'
        elif 'com rechazo' in dlow or 'rechazo deb' in dlow:
            cat, subcat, g = 'servicios', 'bancos', 'Comisión Rechazo Débito'
        elif 'transf. mobile' in dlow or 'transf mobile' in dlow:
            cat, subcat, g = 'otros', 'otros', 'Transferencia Mobile'
        elif 'sancor' in dlow:
            cat, subcat, g = 'servicios', 'seguros', 'Sancor Seguros'
        elif 'polibot' in dlow:
            cat, subcat, g = 'comercios', 'indumentaria', 'Polibot'
        elif 'havanna' in dlow:
            cat, subcat, g = 'comercios', 'restaurant', 'Havanna'
        elif 'federacion' in dlow or 'pago federacion' in dlow:
            cat, subcat, g = 'servicios', 'seguros', 'Federación Patronal'
        elif 'prev.seg' in dlow or 'pago prev.seg' in dlow:
            cat, subcat, g = 'servicios', 'seguros', 'Previsión Seguros'
        elif 'iva serv' in dlow:
            cat, subcat, g = 'impuestos', 'impuestos', 'IVA Servicios Digitales'
        elif 'percepcion' in dlow:
            cat, subcat, g = 'impuestos', 'impuestos', 'Percepción'
        elif 'netflix' in dlow or 'cpa. netflix' in dlow:
            cat, subcat, g = 'servicios', 'suscripciones', 'Netflix'
        elif 'herrero' in dlow:
            cat, subcat, g = 'comercios', 'otros', 'Herrero SRL'
        else:
            mk = next((k for k in comercios_json if k.lower() in dlow), None)
            if mk:
                cat = comercios_json[mk]['categoria']
                subcat = comercios_json[mk]['subcategoria']
                g = comercios_json[mk]['gasto']
            else:
                cat, subcat, g = categorizar_gasto_parser(descripcion, datos)

        gastos.append({
            'fecha': fecha,
            'gasto': g,
            'monto': monto,
            'moneda': 'ARS',
            'fuente': 'ICBC JPG',
            'categoria': cat,
            'subcategoria': subcat,
            'owner': owner or 'Vero',
            'medio_pago': medio_pago or 'ICBC',
            'u_id': generar_id()
        })

    if not gastos:
        return [], texto_debug, "No se detectaron gastos"

    return gastos, texto_debug, None

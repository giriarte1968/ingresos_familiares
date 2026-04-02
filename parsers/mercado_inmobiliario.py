import json
import os
from datetime import datetime

DATOS_MERCADO_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'datos_mercado.json'
)

def cargar_datos():
    if not os.path.exists(DATOS_MERCADO_FILE):
        raise FileNotFoundError("No existe datos_mercado.json")

    with open(DATOS_MERCADO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def interpolar_indice(indice, año):
    años = sorted(int(k) for k in indice.keys())

    if año in indice:
        return indice[str(año)]
    if str(int(año)) in indice and año == int(año):
        return indice[str(int(año))]

    for i in range(len(años) - 1):
        a0, a1 = años[i], años[i + 1]
        if a0 <= año <= a1:
            t = (año - a0) / (a1 - a0)
            return indice[str(a0)] + t * (indice[str(a1)] - indice[str(a0)])

    if año < años[0]:
        return indice[str(años[0])]
    return indice[str(años[-1])]

def obtener_factor_barrio(barrio, data):
    barrio = barrio.lower().replace(" ", "_")
    return data.get("factor_barrio", {}).get(barrio, data.get("factor_barrio", {}).get("default", 1.00))

def obtener_factor_piso(piso, data):
    try:
        piso = int(piso)
    except:
        piso = 1
    if piso == 0:
        return data["factores_propiedad"]["piso"]["pb"]
    elif piso <= 3:
        return data["factores_propiedad"]["piso"]["bajo"]
    elif piso <= 6:
        return data["factores_propiedad"]["piso"]["medio"]
    else:
        return data["factores_propiedad"]["piso"]["alto"]

def calcular_valor_m2(fecha, barrio, estado, calidad, piso):
    data = cargar_datos()

    indice = data["indice_mercado_rosario"]
    base_ciudad = data["metadata"]["base_ciudad_m2_2026"]

    if isinstance(fecha, str):
        fecha_dt = datetime.strptime(fecha, "%Y-%m")
    else:
        fecha_dt = fecha

    año = fecha_dt.year + (fecha_dt.month - 1) / 12

    indice_actual = interpolar_indice(indice, 2026)
    indice_fecha = interpolar_indice(indice, año)

    factor_barrio = obtener_factor_barrio(barrio, data)
    
    estado_norm = estado.lower().replace(" ", "_")
    if "estrenar" in estado_norm: estado_norm = "a_estrenar"
    if estado_norm not in data["factores_propiedad"]["estado"]:
        estado_norm = "bueno"
        
    factor_estado = data["factores_propiedad"]["estado"][estado_norm]
    
    calidad_norm = calidad.lower().strip()
    if calidad_norm not in data["factores_propiedad"]["calidad"]:
        calidad_norm = "media"
        
    factor_calidad = data["factores_propiedad"]["calidad"][calidad_norm]
    factor_piso = obtener_factor_piso(piso, data)

    valor_m2 = (
        base_ciudad
        * factor_barrio
        * (indice_fecha / indice_actual)
        * factor_estado
        * factor_calidad
        * factor_piso
    )

    return round(valor_m2, 2)


def construir_serie_historica(barrio, estado, calidad, piso, anios=10, fecha_ref=None):
    if fecha_ref is None:
        fecha_tope = datetime.now()
    else:
        if isinstance(fecha_ref, str):
            fecha_tope = datetime.strptime(fecha_ref, "%Y-%m")
        else:
            fecha_tope = fecha_ref

    anio_inicio = fecha_tope.year - anios
    fecha_cursor = datetime(anio_inicio, 1, 1)
    
    serie = []
    while fecha_cursor <= fecha_tope:
        fecha_str = fecha_cursor.strftime("%Y-%m")
        val = calcular_valor_m2(fecha_str, barrio, estado, calidad, piso)
        serie.append({
            "fecha": fecha_str,
            "valor_m2": val,
            "fuente": "modelo ajustado mercado real"
        })
        if fecha_cursor.month == 12:
            fecha_cursor = datetime(fecha_cursor.year + 1, 1, 1)
        else:
            fecha_cursor = datetime(fecha_cursor.year, fecha_cursor.month + 1, 1)
            
    return serie


def calcular_plusvalia_serie(serie, fecha_compra=None):
    if not serie or len(serie) < 2:
        return {
            'plusvalia_mensual_pct': 0,
            'plusvalia_acumulada_pct': 0,
            'tendencia': 'neutral'
        }

    ultimo = serie[-1]['valor_m2']
    penultimo = serie[-2]['valor_m2']
    plusvalia_mensual = ((ultimo / penultimo) - 1) * 100 if penultimo > 0 else 0

    if fecha_compra:
        valor_compra = None
        for s in serie:
            if s['fecha'] >= fecha_compra:
                valor_compra = s['valor_m2']
                break
        if valor_compra and valor_compra > 0:
            plusvalia_acumulada = ((ultimo / valor_compra) - 1) * 100
        else:
            primer_valor = serie[0]['valor_m2']
            plusvalia_acumulada = ((ultimo / primer_valor) - 1) * 100 if primer_valor > 0 else 0
    else:
        primer_valor = serie[0]['valor_m2']
        plusvalia_acumulada = ((ultimo / primer_valor) - 1) * 100 if primer_valor > 0 else 0

    if len(serie) >= 6:
        ultimos_6 = [s['valor_m2'] for s in serie[-6:]]
        tendencia_valor = sum(ultimos_6) / len(ultimos_6)
        if ultimo > tendencia_valor * 1.02:
            tendencia = 'alcista'
        elif ultimo < tendencia_valor * 0.98:
            tendencia = 'bajista'
        else:
            tendencia = 'neutral'
    else:
        if plusvalia_mensual > 1:
            tendencia = 'alcista'
        elif plusvalia_mensual < -1:
            tendencia = 'bajista'
        else:
            tendencia = 'neutral'

    return {
        'plusvalia_mensual_pct': round(plusvalia_mensual, 2),
        'plusvalia_acumulada_pct': round(plusvalia_acumulada, 2),
        'tendencia': tendencia,
    }


def valuar_propiedad(propiedad, fecha_ref=None):
    m2 = propiedad.get("m2", 0)
    barrio = propiedad.get("zona", "default")
    estado = propiedad.get("estado_detalle", "bueno")
    calidad = propiedad.get("calidad_edificio", "media")
    piso = propiedad.get("piso", 0)
    fecha_compra = propiedad.get("fecha_compra", None)

    fecha_ref_str = None
    if fecha_ref:
        if isinstance(fecha_ref, str):
            fecha_ref_str = fecha_ref
        elif isinstance(fecha_ref, datetime):
            fecha_ref_str = fecha_ref.strftime("%Y-%m")
    else:
        fecha_ref_str = datetime.now().strftime("%Y-%m")

    valor_m2 = calcular_valor_m2(fecha_ref_str, barrio, estado, calidad, piso)
    rango_min = valor_m2 * 0.90
    rango_max = valor_m2 * 1.10

    serie = construir_serie_historica(barrio, estado, calidad, piso, anios=10, fecha_ref=fecha_ref_str)
    plusvalia = calcular_plusvalia_serie(serie, fecha_compra)

    valor_propiedad = valor_m2 * m2

    justificacion = (
        f"Valuación desacoplada al {fecha_ref_str}. "
        f"Barrio: {barrio}. Estado: {estado}. Calidad: {calidad}. Piso: {piso}. "
        f"Rango estimado: USD {rango_min:,.0f} - {rango_max:,.0f}/m²."
    )

    return {
        'valor_m2_actual_usd': valor_m2,
        'rango_m2': f"USD {rango_min:,.0f} - {rango_max:,.0f}",
        'valor_propiedad_usd': round(valor_propiedad, 0),
        'serie_mensual_m2': serie,
        'plusvalia_mensual_pct': plusvalia['plusvalia_mensual_pct'],
        'plusvalia_acumulada_pct': plusvalia['plusvalia_acumulada_pct'],
        'tendencia': plusvalia['tendencia'],
        'factores_aplicados': {},
        'nivel_confianza': 'alto',
        'justificacion': justificacion,
        'fecha_valuacion': fecha_ref_str,
    }

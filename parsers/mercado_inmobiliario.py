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
        
    if año > años[-1]:
        # Extrapolar usando la tendencia de los últimos dos años
        if len(años) >= 2:
            pendiente = indice[str(años[-1])] - indice[str(años[-2])]
            return indice[str(años[-1])] + pendiente * (año - años[-1])

    return indice[str(años[-1])]

def obtener_factor_barrio(barrio, data):
    barrio_norm = barrio.lower().strip().replace(" ", "_")
    return data.get("factor_barrio", {}).get(barrio_norm, data.get("factor_barrio", {}).get("default", 1.00))

def obtener_factor_piso(piso, data):
    try:
        piso = int(piso)
    except:
        piso = 1
    p_fm = data["factores_propiedad"]["piso"]
    if piso == 0:
        return p_fm.get("pb", 0.95)
    elif piso <= 3:
        return p_fm.get("bajo", 1.00)
    elif piso <= 6:
        return p_fm.get("medio", 1.02)
    else:
        return p_fm.get("alto", 1.04)

def calcular_valor_m2(prop_data, fecha):
    """
    Calcula valor del m2 usando el MODELO DESACOPLADO AVANZADO (v3.0).
    """
    data = cargar_datos()
    f_p = data["factores_propiedad"]

    # Base e Índice Temporal
    indice = data["indice_mercado_rosario"]
    base_ciudad = data["metadata"]["base_ciudad_m2_2026"]

    if isinstance(fecha, str):
        fecha_dt = datetime.strptime(fecha, "%Y-%m")
    else:
        fecha_dt = fecha

    anio_decimal = fecha_dt.year + (fecha_dt.month - 1) / 12.0
    
    # Normalización al valor 'hoy' (2026 ref)
    indice_actual = interpolar_indice(indice, 2026)
    indice_fecha = interpolar_indice(indice, anio_decimal)
    factor_tiempo = (indice_fecha / indice_actual)

    # 1. Barrio
    factor_barrio = obtener_factor_barrio(prop_data.get("zona", "default"), data)
    
    # 2. Estado y Antigüedad
    # Aplicamos factor de estado directamente. 
    # La antigüedad se puede tratar como un coeficiente adicional decreciente (ej: Ross-Heidecke simplificado)
    estado_key = prop_data.get("estado_detalle", "bueno").lower().replace(" ", "_")
    if "estrenar" in estado_key: estado_key = "a_estrenar"
    factor_estado = f_p["estado"].get(estado_key, 1.00)
    
    antiguedad = prop_data.get("antiguedad", 0)
    try:
        antiguedad = int(antiguedad)
    except:
        antiguedad = 0
    # Factor depreciación empírico básico: -0.5% anual a partir de los 10 años, tope -30%
    if antiguedad > 10:
        factor_antiguedad = max(1.0 - ((antiguedad - 10) * 0.005), 0.70)
    else:
        factor_antiguedad = 1.0
        
    # 3. Características Constructivas y Funcionales
    factor_calidad = f_p["calidad"].get(prop_data.get("calidad_edificio", "media").lower(), 1.00)
    factor_piso = obtener_factor_piso(prop_data.get("piso", 0), data)
    
    # Ventilación
    vent_key = prop_data.get("ventilacion", "simple").lower().strip()
    factor_vent = f_p["ventilacion"].get(vent_key, 1.00)
    
    # Suelos
    suelo_key = prop_data.get("terminaciones_suelo", "estandar").lower().replace(" ", "_")
    factor_suelo = f_p["terminaciones_suelo"].get(suelo_key, 1.00)
    
    # Cocina
    cocina_key = prop_data.get("distribucion_cocina", "integrada").lower().replace(" ", "_")
    factor_cocina = f_p["distribucion_cocina"].get(cocina_key, 1.00)
    
    # Carpintería
    carp_key = prop_data.get("carpinteria", "estandar").lower().strip()
    factor_carp = f_p["carpinteria"].get(carp_key, 1.00)
    
    # Orientación
    orient_key = prop_data.get("orientacion", "este").lower().strip()
    factor_orient = f_p["orientacion"].get(orient_key, 1.00)
    
    # Detalles ADICIONALES (Sumatoria de porcentajes)
    detalles = prop_data.get("detalles_categoria", [])
    suma_detalles = 0
    for d in detalles:
        d_key = d.lower().replace(" ", "_")
        suma_detalles += f_p["detalles_categoria"].get(d_key, 0)
    factor_detalles = 1.0 + suma_detalles

    # FORMULA FINAL MULTIPLICATIVA
    valor_m2 = (
        base_ciudad
        * factor_barrio
        * factor_tiempo
        * factor_estado
        * factor_antiguedad
        * factor_calidad
        * factor_piso
        * factor_vent
        * factor_suelo
        * factor_cocina
        * factor_carp
        * factor_orient
        * factor_detalles
    )

    return round(valor_m2, 2)


def construir_serie_historica(propiedad_data, anios=10, fecha_ref=None):
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
        val = calcular_valor_m2(propiedad_data, fecha_str)
        serie.append({
            "fecha": fecha_str,
            "valor_m2": round(val, 0),
            "fuente": "modelo desacoplado avanzado v3.0"
        })
        if fecha_cursor.month == 12:
            fecha_cursor = datetime(fecha_cursor.year + 1, 1, 1)
        else:
            fecha_cursor = datetime(fecha_cursor.year, fecha_cursor.month + 1, 1)
            
    return serie


def calcular_plusvalia_serie(serie, fecha_compra=None):
    if not serie or len(serie) < 2:
        return {'plusvalia_mensual_pct': 0, 'plusvalia_acumulada_pct': 0, 'tendencia': 'neutral'}

    ultimo = serie[-1]['valor_m2']
    penultimo = serie[-2]['valor_m2']
    plusvalia_mensual = ((ultimo / penultimo) - 1) * 100 if penultimo > 0 else 0

    if fecha_compra:
        valor_compra_m2 = None
        for s in serie:
            if s['fecha'] >= fecha_compra:
                valor_compra_m2 = s['valor_m2']
                break
        if valor_compra_m2 and valor_compra_m2 > 0:
            plusvalia_acumulada = ((ultimo / valor_compra_m2) - 1) * 100
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
        tendencia = 'alcista' if plusvalia_mensual > 0.5 else ('bajista' if plusvalia_mensual < -0.5 else 'neutral')

    return {
        'plusvalia_mensual_pct': round(plusvalia_mensual, 2),
        'plusvalia_acumulada_pct': round(plusvalia_acumulada, 2),
        'tendencia': tendencia,
    }


def valuar_propiedad(propiedad, fecha_ref=None):
    m2 = propiedad.get("m2", 0)
    fecha_compra = propiedad.get("fecha_compra", None)

    fecha_ref_str = None
    if fecha_ref:
        if isinstance(fecha_ref, str):
            fecha_ref_str = fecha_ref
        elif isinstance(fecha_ref, datetime):
            fecha_ref_str = fecha_ref.strftime("%Y-%m")
    else:
        fecha_ref_str = datetime.now().strftime("%Y-%m")

    valor_m2 = calcular_valor_m2(propiedad, fecha_ref_str)
    rango_min = valor_m2 * 0.90
    rango_max = valor_m2 * 1.10

    serie = construir_serie_historica(propiedad, anios=10, fecha_ref=fecha_ref_str)
    plusvalia = calcular_plusvalia_serie(serie, fecha_compra)

    valor_propiedad = valor_m2 * m2

    justificacion = (
        f"Valuación avanzada v3.0 al {fecha_ref_str}. "
        f"Basado en detalles de categoría, antigüedad y modelo de mercado desacoplado. "
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
        'factores_aplicados': {}, # No es necesario para el UI actual
        'nivel_confianza': 'alto',
        'justificacion': justificacion,
        'fecha_valuacion': fecha_ref_str,
    }

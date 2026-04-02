"""
Motor de valuación inmobiliaria para Rosario, Argentina.
Calcula valor del m² en USD basado en datos de mercado,
factores de ajuste y serie histórica.
"""
import json
import os
import re
from datetime import datetime

DATOS_MERCADO_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'datos_mercado.json'
)

# ============================================================
# VALORES BASE DEL m² EN USD PARA ROSARIO (referencia 2026)
# Fuente: promedio Zonaprop, Argenprop, Reporte Inmobiliario
# ============================================================
VALOR_BASE_M2 = {
    'departamento': 1100,
    'casa': 1050,
    'local': 1300,
    'oficina': 1200,
    'terreno': 400,
}

# ============================================================
# FACTORES POR ZONA / BARRIO
# ============================================================
FACTOR_ZONA = {
    'Puerto Norte': 1.30,
    'Barrio Inglés': 1.20,
    'Centro': 1.15,
    'Macrocentro': 1.15,
    'Echesortu': 1.10,
    'Fisherton': 1.10,
    'Pichincha': 1.05,
    'Facultades': 1.05,
    'Martin': 1.00,
    'Abasto': 1.00,
    'Alvear': 1.00,
    'San Martín': 0.95,
    'General Paz': 0.95,
    'Barrio Tigre': 0.95,
    'Rosario Norte': 0.90,
    'Ruta 9': 0.85,
    'Sur': 0.80,
    'Norte': 0.85,
    'Oeste': 0.80,
    'Otro': 0.85,
}

# ============================================================
# FACTOR POR ESTADO DETALLADO
# ============================================================
FACTOR_ESTADO = {
    'a estrenar': 1.20,
    'reciclado': 1.10,
    'bueno': 1.00,
    'a refaccionar': 0.85,
}

# ============================================================
# FACTOR POR CALIDAD DEL EDIFICIO
# ============================================================
FACTOR_CALIDAD = {
    'premium': 1.25,
    'media': 1.00,
    'economica': 0.85,
}

# ============================================================
# FACTORES POR AMENITIES (acumulativos, tope +20%)
# ============================================================
FACTOR_AMENITIES = {
    'pileta': 0.05,
    'SUM': 0.03,
    'seguridad': 0.03,
    'gimnasio': 0.03,
    'sala de fiestas': 0.02,
    'lavadero': 0.02,
    'parrilla': 0.02,
    'jardin': 0.02,
}

# ============================================================
# FACTOR POR ORIENTACIÓN
# ============================================================
FACTOR_ORIENTACION = {
    'norte': 1.05,
    'noreste': 1.03,
    'noroeste': 1.02,
    'este': 1.00,
    'oeste': 0.98,
    'sur': 0.95,
    'sureste': 0.97,
    'suroeste': 0.96,
}

# ============================================================
# FACTOR POR PISO (+2% por piso, tope +20%)
# ============================================================
def factor_piso(piso):
    return min(1.0 + (piso * 0.02), 1.20)

# ============================================================
# FACTOR COCHERA
# ============================================================
FACTOR_COCHERA = 1.08

# ============================================================
# FACTOR ESPACIOS EXTERIORES (acumulativos, tope +15%)
# ============================================================
FACTOR_EXTERIORES = {
    'balcon': 0.03,
    'patio': 0.05,
    'terraza': 0.05,
    'jardin_privado': 0.04,
    'quinta': 0.03,
}

# ============================================================
# AJUSTE DE CIERRE REAL (-10% sobre precios publicados)
# ============================================================
FACTOR_CIERRE_REAL = 0.90


def cargar_datos_mercado():
    """Carga datos de mercado desde JSON persistente"""
    if os.path.exists(DATOS_MERCADO_FILE):
        try:
            with open(DATOS_MERCADO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {'series': {}, 'ultima_actualizacion': None, 'fuentes': {}}


def guardar_datos_mercado(datos):
    """Guarda datos de mercado en JSON persistente"""
    with open(DATOS_MERCADO_FILE, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def calcular_valor_m2(propiedad):
    """
    Calcula el valor del m² en USD para una propiedad.
    Retorna dict con valor_m2, factores_aplicados, rango, confianza, justificacion.
    """
    tipo = propiedad.get('tipo_inmueble', 'departamento')
    zona = propiedad.get('zona', 'Otro')
    estado = propiedad.get('estado_detalle', 'bueno')
    calidad = propiedad.get('calidad_edificio', 'media')
    piso = propiedad.get('piso', 0)
    orientacion = propiedad.get('orientacion', 'este')
    amenities = propiedad.get('amenities', [])
    cochera = propiedad.get('cochera', False)
    espacios_ext = propiedad.get('espacios_exteriores', [])

    # Valor base
    valor_base = VALOR_BASE_M2.get(tipo, 1000)

    # Factores
    fz = FACTOR_ZONA.get(zona, 0.85)
    fe = FACTOR_ESTADO.get(estado, 1.00)
    fc = FACTOR_CALIDAD.get(calidad, 1.00)
    fp = factor_piso(piso)
    fo = FACTOR_ORIENTACION.get(orientacion, 1.00)

    # Amenities (acumulativo, tope +20%)
    amen_suma = sum(FACTOR_AMENITIES.get(a, 0) for a in amenities)
    amen_suma = min(amen_suma, 0.20)
    fa = 1.0 + amen_suma

    # Exteriores (acumulativo, tope +15%)
    ext_suma = sum(FACTOR_EXTERIORES.get(e, 0) for e in espacios_ext)
    ext_suma = min(ext_suma, 0.15)
    fext = 1.0 + ext_suma

    # Cochera
    fcoch = FACTOR_COCHERA if cochera else 1.0

    # Cálculo
    valor_m2 = valor_base * fz * fe * fc * fp * fo * fa * fext * fcoch
    valor_m2_ajustado = valor_m2 * FACTOR_CIERRE_REAL

    # Rango estimado (+/- 10%)
    rango_min = valor_m2_ajustado * 0.90
    rango_max = valor_m2_ajustado * 1.10

    # Nivel de confianza (basado en cantidad de factores aplicados)
    factores_count = sum([
        1 if zona != 'Otro' else 0,
        1 if estado != 'bueno' else 0,
        1 if calidad != 'media' else 0,
        1 if piso > 0 else 0,
        1 if orientacion != 'este' else 0,
        1 if amenities else 0,
        1 if cochera else 0,
        1 if espacios_ext else 0,
    ])
    if factores_count >= 5:
        confianza = 'alto'
    elif factores_count >= 3:
        confianza = 'medio'
    else:
        confianza = 'bajo'

    # Justificación
    justificacion = (
        f"Valor base m² para {tipo} en Rosario: USD {valor_base:,.0f}. "
        f"Factor zona ({zona}): {fz:.2f}. "
        f"Factor estado ({estado}): {fe:.2f}. "
        f"Factor calidad ({calidad}): {fc:.2f}. "
        f"Factor piso ({piso}): {fp:.2f}. "
        f"Factor orientación ({orientacion}): {fo:.2f}. "
        f"Amenities: +{amen_suma*100:.0f}%. "
        f"Exteriores: +{ext_suma*100:.0f}%. "
        f"Cochera: {'+8%' if cochera else 'no'}. "
        f"Ajuste cierre real: -10%. "
        f"Rango estimado: USD {rango_min:,.0f} - {rango_max:,.0f}/m²."
    )

    factores_aplicados = {
        'zona': {'factor': fz, 'valor': zona},
        'estado': {'factor': fe, 'valor': estado},
        'calidad': {'factor': fc, 'valor': calidad},
        'piso': {'factor': fp, 'valor': piso},
        'orientacion': {'factor': fo, 'valor': orientacion},
        'amenities': {'factor': fa, 'valor': amenities},
        'exteriores': {'factor': fext, 'valor': espacios_ext},
        'cochera': {'factor': fcoch, 'valor': cochera},
        'cierre_real': {'factor': FACTOR_CIERRE_REAL, 'valor': '-10% sobre publicados'},
    }

    return {
        'valor_m2_usd': round(valor_m2_ajustado, 0),
        'rango_min': round(rango_min, 0),
        'rango_max': round(rango_max, 0),
        'factores_aplicados': factores_aplicados,
        'confianza': confianza,
        'justificacion': justificacion,
    }


def construir_serie_historica(zona, tipo, anios=10, fecha_ref=None):
    """
    Construye serie histórica mensual del m² en USD.
    Combina datos reales (si existen en datos_mercado.json) con estimaciones.
    Aplica media móvil de 3 meses para suavizar.
    Si se pasa fecha_ref (datetime), la serie se limita hasta ese mes/año.
    """
    import calendar
    datos_mercado = cargar_datos_mercado()
    clave = f"{zona}_{tipo}"

    # Fecha tope: usar fecha_ref si se proporciona, sino hoy
    if fecha_ref is None:
        fecha_tope = datetime.now()
    else:
        fecha_tope = fecha_ref

    # Si ya existe serie guardada, filtrarla hasta la fecha tope
    if clave in datos_mercado.get('series', {}):
        serie_completa = datos_mercado['series'][clave]
        tope_str = f"{fecha_tope.year}-{fecha_tope.month:02d}"
        serie = [s for s in serie_completa if s['fecha'] <= tope_str]
        if serie:
            return _suavizar_serie(serie)

    # Construir serie estimada
    anio_inicio = fecha_tope.year - anios
    mes_inicio = fecha_tope.month

    valor_base = VALOR_BASE_M2.get(tipo, 1000)
    factor_z = FACTOR_ZONA.get(zona, 0.85)
    valor_base_zona = valor_base * factor_z * FACTOR_CIERRE_REAL

    serie = []

    # Simular evolución del mercado rosarino (datos aproximados)
    # 2016-2018: crecimiento, 2019-2020: caída, 2021-2023: recuperación, 2024+: estabilización
    for anio in range(anio_inicio, fecha_tope.year + 1):
        for mes in range(1, 13):
            if anio == anio_inicio and mes < mes_inicio:
                continue
            if anio == fecha_tope.year and mes > fecha_tope.month:
                break

            fecha = f"{anio}-{mes:02d}"

            # Modelo simplificado de evolución del mercado
            if anio <= 2018:
                crecimiento = 1.03  # +3% anual
            elif anio <= 2020:
                crecimiento = 0.90  # -10% anual
            elif anio <= 2023:
                crecimiento = 1.05  # +5% anual
            else:
                crecimiento = 0.98  # -2% anual (estabilización)

            anios_transcurridos = anio - anio_inicio
            factor_tiempo = crecimiento ** anios_transcurridos

            # Variación mensual aleatoria controlada
            import hashlib
            seed = int(hashlib.md5(f"{clave}_{fecha}".encode()).hexdigest()[:8], 16)
            variacion = 1.0 + ((seed % 100) - 50) / 2500.0  # +/- 2%

            valor_m2 = valor_base_zona * factor_tiempo * variacion
            fuente = 'estimado'

            serie.append({
                'fecha': fecha,
                'valor_m2': round(valor_m2, 0),
                'fuente': fuente,
            })

    # Guardar serie completa (sin filtro de fecha_ref) para reutilización
    if 'series' not in datos_mercado:
        datos_mercado['series'] = {}
    # Solo guardar si calculamos la serie completa (sin fecha_ref o usando hoy)
    if fecha_ref is None or fecha_tope.date() >= datetime.now().date():
        datos_mercado['series'][clave] = serie
        datos_mercado['ultima_actualizacion'] = datetime.now().strftime('%Y-%m-%d')
        guardar_datos_mercado(datos_mercado)

    return _suavizar_serie(serie)


def _suavizar_serie(serie, ventana=3):
    """Aplica media móvil de N meses para suavizar saltos bruscos"""
    if len(serie) <= ventana:
        return serie

    suavizada = []
    for i in range(len(serie)):
        inicio = max(0, i - ventana + 1)
        ventana_valores = [serie[j]['valor_m2'] for j in range(inicio, i + 1)]
        promedio = sum(ventana_valores) / len(ventana_valores)

        suavizada.append({
            'fecha': serie[i]['fecha'],
            'valor_m2': round(promedio, 0),
            'fuente': serie[i]['fuente'],
        })

    return suavizada


def calcular_plusvalia_serie(serie, fecha_compra=None):
    """
    Calcula plusvalía mensual y acumulada desde una serie histórica.
    """
    if not serie or len(serie) < 2:
        return {
            'plusvalia_mensual_pct': 0,
            'plusvalia_acumulada_pct': 0,
            'tendencia': 'sin datos',
        }

    # Plusvalía mensual (último vs penúltimo)
    ultimo = serie[-1]['valor_m2']
    penultimo = serie[-2]['valor_m2']
    plusvalia_mensual = ((ultimo / penultimo) - 1) * 100 if penultimo > 0 else 0

    # Plusvalía acumulada
    if fecha_compra:
        # Buscar valor en fecha de compra
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

    # Tendencia (media móvil 6 meses)
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
    """
    Función principal: valúa una propiedad completa.
    Si se pasa fecha_ref (str 'YYYY-MM' o datetime), calcula el valor
    al último día de ese mes en lugar de usar la fecha actual.
    Retorna dict con todos los datos de valuación.
    """
    import calendar
    m2 = propiedad.get('m2', 0)
    tipo = propiedad.get('tipo_inmueble', 'departamento')
    zona = propiedad.get('zona', 'Otro')
    fecha_compra = propiedad.get('fecha_compra', None)
    valor_compra = propiedad.get('valor_compra_usd', 0)

    # Convertir fecha_ref a datetime si viene como string 'YYYY-MM'
    fecha_ref_dt = None
    if fecha_ref:
        if isinstance(fecha_ref, str):
            try:
                anio, mes = int(fecha_ref[:4]), int(fecha_ref[5:7])
                ultimo_dia = calendar.monthrange(anio, mes)[1]
                fecha_ref_dt = datetime(anio, mes, ultimo_dia)
            except Exception:
                fecha_ref_dt = None
        elif isinstance(fecha_ref, datetime):
            fecha_ref_dt = fecha_ref

    # Calcular valor m²
    resultado_m2 = calcular_valor_m2(propiedad)
    valor_m2 = resultado_m2['valor_m2_usd']

    # Construir serie histórica hasta la fecha de referencia
    serie = construir_serie_historica(zona, tipo, fecha_ref=fecha_ref_dt)

    # Calcular plusvalía
    plusvalia = calcular_plusvalia_serie(serie, fecha_compra)

    # Valor total de la propiedad
    valor_propiedad = valor_m2 * m2

    return {
        'valor_m2_actual_usd': valor_m2,
        'rango_m2': f"USD {resultado_m2['rango_min']:,.0f} - {resultado_m2['rango_max']:,.0f}",
        'valor_propiedad_usd': round(valor_propiedad, 0),
        'serie_mensual_m2': serie,
        'plusvalia_mensual_pct': plusvalia['plusvalia_mensual_pct'],
        'plusvalia_acumulada_pct': plusvalia['plusvalia_acumulada_pct'],
        'tendencia': plusvalia['tendencia'],
        'factores_aplicados': resultado_m2['factores_aplicados'],
        'nivel_confianza': resultado_m2['confianza'],
        'justificacion': resultado_m2['justificacion'],
        'fecha_valuacion': fecha_ref_dt.strftime('%Y-%m-%d') if fecha_ref_dt else datetime.now().strftime('%Y-%m-%d'),
    }

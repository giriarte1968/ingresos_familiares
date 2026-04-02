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


def cargar_indice_mercado():
    if not os.path.exists(DATOS_MERCADO_FILE):
        # Fallback al json base en caso de un error para evitar roturas
        return {2016: 0.85, 2017: 0.95, 2018: 1.00, 2019: 0.90, 2020: 0.80, 2021: 0.70, 2022: 0.68, 2023: 0.70, 2024: 0.75, 2025: 0.85, 2026: 1.00}

    with open(DATOS_MERCADO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "rosario_m2_indice" in data:
        return {int(k): v for k, v in data["rosario_m2_indice"].items()}
    else:
        return {2016: 0.85, 2017: 0.95, 2018: 1.00, 2019: 0.90, 2020: 0.80, 2021: 0.70, 2022: 0.68, 2023: 0.70, 2024: 0.75, 2025: 0.85, 2026: 1.00}


def interpolar_indice(indice, anio):
    """
    Permite obtener valores para años no exactos (ej: 2023.75)
    """
    anios = sorted(indice.keys())

    if anio in indice:
        return indice[anio]

    for i in range(len(anios) - 1):
        a0, a1 = anios[i], anios[i + 1]
        if a0 <= anio <= a1:
            t = (anio - a0) / (a1 - a0)
            return indice[a0] + t * (indice[a1] - indice[a0])

    # extrapolación simple
    if anio < anios[0]:
        return indice[anios[0]]
    return indice[anios[-1]]


def validar_serie(serie):
    """
    Validaciones clave para evitar bugs futuros
    """
    valores = [s['valor_m2'] for s in serie]
    fechas = [s['fecha'] for s in serie]

    # Convertir a dict año → promedio
    por_anio = {}
    for i, f in enumerate(fechas):
        anio = int(f.split("-")[0])
        por_anio.setdefault(anio, []).append(valores[i])

    promedio_anio = {a: sum(v) / len(v) for a, v in por_anio.items()}

    # 1. Pico en 2018
    if 2018 in promedio_anio and 2023 in promedio_anio:
        assert promedio_anio[2018] >= promedio_anio[2023], "ERROR: 2018 debería ser mayor o igual a 2023"

    # 2. Caída post 2018
    if 2020 in promedio_anio and 2018 in promedio_anio:
        assert promedio_anio[2020] <= promedio_anio[2018], "ERROR: 2020 debería ser menor que 2018"

    # 3. Valor actual coherente
    ultimo = valores[-1]
    penultimo = valores[-2] if len(valores) > 1 else ultimo
    assert abs(ultimo - penultimo) < 200, "ERROR: salto brusco en valor actual"

    # 4. Nada de valores absurdos
    for v in valores:
        assert v < 5000, "ERROR: valor m2 irreal detectado"


def construir_serie_historica(zona, tipo, anios_hist=10, fecha_ref=None):
    """
    Construye serie histórica mensual basada en índice de mercado real
    """
    if fecha_ref is None:
        fecha_tope = datetime.now()
    else:
        fecha_tope = fecha_ref

    indice = cargar_indice_mercado()

    # año tope para la valuación solicitada
    anio_actual = fecha_tope.year + (fecha_tope.month - 1) / 12.0
    indice_actual = interpolar_indice(indice, anio_actual)

    valor_base = VALOR_BASE_M2.get(tipo, 1000)
    factor_z = FACTOR_ZONA.get(zona, 0.85)

    # Este es el valor "hoy" en base 1.0 (ya que base 2026 = 1.0)
    valor_base_zona = valor_base * factor_z * FACTOR_CIERRE_REAL

    serie = []

    anio_inicio_dt = datetime.now().year - anios_hist
    if anio_inicio_dt < min(indice.keys()):
        anio_inicio_dt = min(indice.keys())

    fecha_cursor = datetime(int(anio_inicio_dt), 1, 1)

    while fecha_cursor <= fecha_tope:
        anio = fecha_cursor.year
        mes = fecha_cursor.month

        # año decimal (ej: 2023.75)
        anio_decimal = anio + (mes - 1) / 12.0

        indice_anio = interpolar_indice(indice, anio_decimal)

        # Usamos el indice 2026 (1.0) como referencia para el valor_base_zona.
        # indice_anio te da la variación relativa a ese valor base.
        indice_referencia_base = interpolar_indice(indice, datetime.now().year + (datetime.now().month-1)/12.0)
        
        valor_m2 = valor_base_zona * (indice_anio / indice_referencia_base)

        import hashlib
        clave = f"{zona}_{tipo}"
        fecha_str = fecha_cursor.strftime("%Y-%m")
        seed = int(hashlib.md5(f"{clave}_{fecha_str}".encode()).hexdigest()[:8], 16)
        variacion_micro = 1.0 + ((seed % 100) - 50) / 2500.0  # +/- 2%

        valor_m2 = valor_m2 * variacion_micro

        serie.append({
            'fecha': fecha_str,
            'valor_m2': round(valor_m2, 0),
            'fuente': 'modelo ajustado mercado real',
        })

        # avanzar mes
        if mes == 12:
            fecha_cursor = datetime(anio + 1, 1, 1)
        else:
            fecha_cursor = datetime(anio, mes + 1, 1)

    validar_serie(serie)

    return _suavizar_serie(serie)

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
    al último día de ese mes según la serie histórica del mercado.
    Retorna dict con todos los datos de valuación.
    """
    import calendar
    m2 = propiedad.get('m2', 0)
    tipo = propiedad.get('tipo_inmueble', 'departamento')
    zona = propiedad.get('zona', 'Otro')
    estado = propiedad.get('estado_detalle', 'bueno')
    calidad = propiedad.get('calidad_edificio', 'media')
    piso = propiedad.get('piso', 0)
    orientacion = propiedad.get('orientacion', 'este')
    amenities = propiedad.get('amenities', [])
    cochera = propiedad.get('cochera', False)
    espacios_ext = propiedad.get('espacios_exteriores', [])
    fecha_compra = propiedad.get('fecha_compra', None)

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

    # Construir serie histórica hasta la fecha de referencia
    serie = construir_serie_historica(zona, tipo, fecha_ref=fecha_ref_dt)

    if fecha_ref_dt and serie:
        # ── MODO HISTÓRICO ──
        # La serie ya contiene: valor_base * factor_zona * FACTOR_CIERRE_REAL
        # Necesitamos aplicar encima los factores individuales de la propiedad.
        valor_m2_serie_base = serie[-1]['valor_m2']   # valor en ese período (zona+tipo+cierre)

        # Factores que NO están en la serie (son de la propiedad, no del mercado)
        fe = FACTOR_ESTADO.get(estado, 1.00)
        fc = FACTOR_CALIDAD.get(calidad, 1.00)
        fp = factor_piso(piso)
        fo = FACTOR_ORIENTACION.get(orientacion, 1.00)
        amen_suma = min(sum(FACTOR_AMENITIES.get(a, 0) for a in amenities), 0.20)
        fa = 1.0 + amen_suma
        ext_suma = min(sum(FACTOR_EXTERIORES.get(e, 0) for e in espacios_ext), 0.15)
        fext = 1.0 + ext_suma
        fcoch = FACTOR_COCHERA if cochera else 1.0

        # Valor m² histórico ajustado con características del inmueble
        valor_m2 = round(valor_m2_serie_base * fe * fc * fp * fo * fa * fext * fcoch, 0)

        rango_min = round(valor_m2 * 0.90, 0)
        rango_max = round(valor_m2 * 1.10, 0)

        # Confianza
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
        confianza = 'alto' if factores_count >= 5 else ('medio' if factores_count >= 3 else 'bajo')

        justificacion = (
            f"Valuación histórica al {serie[-1]['fecha']}. "
            f"Valor m² de mercado ({zona}/{tipo}): USD {valor_m2_serie_base:,.0f}. "
            f"Estado ({estado}): ×{fe:.2f}. Calidad ({calidad}): ×{fc:.2f}. "
            f"Piso: ×{fp:.2f}. Amenities: +{amen_suma*100:.0f}%. "
            f"Rango estimado: USD {rango_min:,.0f} - {rango_max:,.0f}/m²."
        )
        rango_str = f"USD {rango_min:,.0f} - {rango_max:,.0f}"

    else:
        # ── MODO ACTUAL ──
        resultado_m2 = calcular_valor_m2(propiedad)
        valor_m2 = resultado_m2['valor_m2_usd']
        rango_str = f"USD {resultado_m2['rango_min']:,.0f} - {resultado_m2['rango_max']:,.0f}"
        confianza = resultado_m2['confianza']
        justificacion = resultado_m2['justificacion']

    # Calcular plusvalía
    plusvalia = calcular_plusvalia_serie(serie, fecha_compra)

    # Valor total de la propiedad
    valor_propiedad = valor_m2 * m2

    return {
        'valor_m2_actual_usd': valor_m2,
        'rango_m2': rango_str,
        'valor_propiedad_usd': round(valor_propiedad, 0),
        'serie_mensual_m2': serie,
        'plusvalia_mensual_pct': plusvalia['plusvalia_mensual_pct'],
        'plusvalia_acumulada_pct': plusvalia['plusvalia_acumulada_pct'],
        'tendencia': plusvalia['tendencia'],
        'nivel_confianza': confianza,
        'justificacion': justificacion,
        'fecha_valuacion': fecha_ref_dt.strftime('%Y-%m-%d') if fecha_ref_dt else datetime.now().strftime('%Y-%m-%d'),
    }

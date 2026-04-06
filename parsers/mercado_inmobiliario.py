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

def scrapear_m2_argenprop():
    """ Obtenemos la media en venta en la calle de Rosario """
    import requests
    from bs4 import BeautifulSoup
    import re
    url = "https://www.argenprop.com/departamentos/venta/rosario/1-dormitorio"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    tarjetas = soup.find_all("div", class_="listing__item")

    valores_m2 = []
    for tarjeta in tarjetas:
        precio_tag = tarjeta.find("p", class_="card__price")
        if not precio_tag or "USD" not in precio_tag.text:
            continue

        precio_str = re.sub(r'[^\d]', '', precio_tag.text)
        if not precio_str:
            continue
        precio = float(precio_str)

        features = tarjeta.find("ul", class_="card__main-features")
        metros = None
        if features:
            for li in features.find_all("li"):
                if "m²" in li.text and "cub" in li.text:
                    m_str = re.sub(r'[^\d]', '', li.text)
                    if m_str:
                        metros = float(m_str)
                        break

        if precio and metros and metros > 0:
            valor_m2 = precio / metros
            if 800 <= valor_m2 <= 3000:
                valores_m2.append(valor_m2)

    if not valores_m2:
        return None

    return round(sum(valores_m2) / len(valores_m2), 0)

def actualizar_base_ciudad_web():
    """ Scrapea el promedio y lo inyecta en la serie historica y metadata """
    nuevo_valor = scrapear_m2_argenprop()
    if nuevo_valor:
        data = cargar_datos()
        data["metadata"]["base_ciudad_m2_2026"] = nuevo_valor
        anio_actual = datetime.now().year
        serie = data.get("serie_historica_m2_rosario", {}).get("datos", {})
        serie[str(anio_actual)] = nuevo_valor
        if "serie_historica_m2_rosario" not in data:
            data["serie_historica_m2_rosario"] = {"datos": {}}
        data["serie_historica_m2_rosario"]["datos"][str(anio_actual)] = nuevo_valor
        with open(DATOS_MERCADO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return nuevo_valor
    return None


def scrapear_zonaprop():
    """ Obtiene precio m2 promedio de Zonaprop para departamentos en Rosario """
    import requests
    from bs4 import BeautifulSoup
    import re
    url = "https://www.zonaprop.com.ar/departamentos-venta-rosario.html"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-AR,es;q=0.9"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        valores_m2 = []
        # Zonaprop usa estructura con price y area
        items = soup.find_all("div", {"data-qa": True})
        for item in items:
            price_el = item.find(attrs={"data-qa": "posting-price"})
            area_el = item.find(attrs={"data-qa": "posting-detail-area"})
            if price_el and area_el:
                price_text = price_el.text.replace("USD", "").replace("$", "").replace(".", "").strip()
                area_text = area_el.text.replace("m²", "").replace("m2", "").strip()
                try:
                    precio = float(price_text)
                    area = float(area_text)
                    if area > 0 and precio > 0:
                        m2 = precio / area
                        if 800 <= m2 <= 3000:
                            valores_m2.append(m2)
                except ValueError:
                    continue

        if valores_m2:
            return round(sum(valores_m2) / len(valores_m2), 0)
        return None
    except Exception:
        return None


def scrapear_mercadolibre():
    """ Obtiene precio m2 promedio de MercadoLibre Inmuebles para Rosario """
    import requests
    import re
    # API publica de MercadoLibre para busquedas
    url = "https://api.mercadolibre.com/sites/MLA/search"
    params = {
        "category": "MLA1459",  # Departamentos
        "state": "AR-S",  # Santa Fe
        "city": "Rosario",
        "limit": 50
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        valores_m2 = []
        for result in data.get("results", []):
            precio = result.get("price")
            attributes = result.get("attributes", [])
            area = None
            for attr in attributes:
                if attr.get("id") in ["PROPERTY_TOTAL_AREA", "PROPERTY_AREA"]:
                    area = attr.get("value_number")
                    break
            if precio and area and area > 0:
                m2 = precio / area
                if 800 <= m2 <= 3000:
                    valores_m2.append(m2)

        if valores_m2:
            return round(sum(valores_m2) / len(valores_m2), 0)
        return None
    except Exception:
        return None


def scrapear_rosariogarage():
    """ Obtiene precio m2 promedio de RosarioGarage """
    import requests
    from bs4 import BeautifulSoup
    import re
    url = "https://www.rosariogarage.com/propiedades/departamentos/venta/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        valores_m2 = []
        # Buscar cards de propiedades con precio y superficie
        cards = soup.find_all("div", class_=re.compile(r"card|property|item", re.I))
        for card in cards:
            price_text = ""
            area_text = ""
            # Intentar encontrar precio
            price_el = card.find(class_=re.compile(r"price|precio", re.I))
            if price_el:
                price_text = price_el.text
            area_el = card.find(class_=re.compile(r"area|superficie|m2|metros", re.I))
            if area_el:
                area_text = area_el.text

            if price_text and area_text:
                precio_match = re.search(r'[\d,]+', price_text.replace(".", "").replace(",", ""))
                area_match = re.search(r'[\d,]+', area_text.replace(".", "").replace(",", ""))
                if precio_match and area_match:
                    try:
                        precio = float(precio_match.group().replace(",", ""))
                        area = float(area_match.group().replace(",", ""))
                        if area > 0 and 800 <= precio / area <= 3000:
                            valores_m2.append(precio / area)
                    except ValueError:
                        continue

        if valores_m2:
            return round(sum(valores_m2) / len(valores_m2), 0)
        return None
    except Exception:
        return None


def obtener_promedio_mercado():
    """
    Scrapea TODAS las fuentes y devuelve promedio ponderado.
    Retorna dict con resultados por fuente y promedio general.
    """
    fuentes = {
        "argenprop": scrapear_m2_argenprop,
        "zonaprop": scrapear_zonaprop,
        "mercadolibre": scrapear_mercadolibre,
        "rosariogarage": scrapear_rosariogarage,
    }

    resultados = {}
    valores_validos = []

    for nombre, func in fuentes.items():
        try:
            valor = func()
            resultados[nombre] = valor
            if valor is not None:
                valores_validos.append(valor)
        except Exception as e:
            resultados[nombre] = None

    promedio = round(sum(valores_validos) / len(valores_validos), 0) if valores_validos else None

    return {
        "fuentes": resultados,
        "promedio": promedio,
        "fuentes_exitosas": len(valores_validos),
        "total_fuentes": len(fuentes)
    }


def actualizar_datos_mercado(valor_manual=None):
    """
    Actualiza la serie historica con datos de scraping o valor manual.
    Si valor_manual es provisto, tiene prioridad sobre el scraping.

    Args:
        valor_manual: float opcional, valor ingresado manualmente por el usuario

    Returns:
        dict con resultado de la actualizacion
    """
    data = cargar_datos()
    anio_actual = datetime.now().year
    mes_actual = datetime.now().strftime("%Y-%m")

    if valor_manual is not None and valor_manual > 0:
        # Input manual tiene prioridad maxima
        nuevo_valor = round(valor_manual, 0)
        fuente = "manual"
    else:
        # Usar promedio de scraping
        resultado = obtener_promedio_mercado()
        nuevo_valor = resultado.get("promedio")
        if nuevo_valor is None:
            return {"exito": False, "error": "Ninguna fuente de scraping respondio correctamente"}
        fuente = f"scraping ({resultado['fuentes_exitosas']}/{resultado['total_fuentes']} fuentes)"

    # Actualizar metadata
    data["metadata"]["base_ciudad_m2_2026"] = nuevo_valor

    # Agregar a serie historica (sobreescribe si ya existe el año)
    if "serie_historica_m2_rosario" not in data:
        data["serie_historica_m2_rosario"] = {"datos": {}}

    data["serie_historica_m2_rosario"]["datos"][str(anio_actual)] = nuevo_valor

    # Registrar en metadata cuando fue la ultima actualizacion
    data["metadata"]["ultima_actualizacion"] = mes_actual
    data["metadata"]["fuente_ultima_actualizacion"] = fuente

    with open(DATOS_MERCADO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return {
        "exito": True,
        "valor": nuevo_valor,
        "fuente": fuente,
        "fecha": mes_actual
    }


def interpolar_precio_historico(serie_datos, año):
    """
    Interpola linealmente entre puntos reales de la serie historica.
    Si el año existe, devuelve el precio real directamente.
    Si esta fuera de rango, usa el extremo mas cercano.
    """
    años = sorted(int(k) for k in serie_datos.keys())

    año_int = int(año) if año == int(año) else año

    if str(año_int) in serie_datos and año == int(año):
        return serie_datos[str(año_int)]

    for i in range(len(años) - 1):
        a0, a1 = años[i], años[i + 1]
        if a0 <= año_int <= a1:
            if a0 == a1:
                return serie_datos[str(a0)]
            t = (año_int - a0) / (a1 - a0)
            return serie_datos[str(a0)] + t * (serie_datos[str(a1)] - serie_datos[str(a0)])

    if año_int < años[0]:
        return serie_datos[str(años[0])]

    if año_int > años[-1]:
        if len(años) >= 2:
            pendiente = serie_datos[str(años[-1])] - serie_datos[str(años[-2])]
            return serie_datos[str(años[-1])] + pendiente * (año_int - años[-1])

    return serie_datos[str(años[-1])]

def obtener_precio_base_anio(año):
    """
    Obtiene el precio base real del m2 en Rosario para un año dado.
    Usa la serie historica con interpolacion lineal.
    """
    data = cargar_datos()
    serie = data.get("serie_historica_m2_rosario", {}).get("datos", {})
    if not serie:
        return data["metadata"]["base_ciudad_m2_2026"]
    return interpolar_precio_historico(serie, año)

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
    Calcula valor del m2 usando el MODELO DESACOPLADO AVANZADO (v4.0).
    Usa precios historicos REALES del mercado de Rosario como base.
    """
    data = cargar_datos()
    f_p = data["factores_propiedad"]

    if isinstance(fecha, str):
        fecha_dt = datetime.strptime(fecha, "%Y-%m")
    else:
        fecha_dt = fecha

    anio = fecha_dt.year

    # Precio base REAL del mercado para este año
    precio_base = obtener_precio_base_anio(anio)

    # 1. Barrio
    factor_barrio = obtener_factor_barrio(prop_data.get("zona", "default"), data)

    # 2. Estado y Antigüedad
    estado_key = prop_data.get("estado_detalle", "bueno").lower().replace(" ", "_")
    if "estrenar" in estado_key: estado_key = "a_estrenar"
    factor_estado = f_p["estado"].get(estado_key, 1.00)

    antiguedad = prop_data.get("antiguedad", 0)
    try:
        antiguedad = int(antiguedad)
    except:
        antiguedad = 0
    if antiguedad > 10:
        factor_antiguedad = max(1.0 - ((antiguedad - 10) * 0.005), 0.70)
    else:
        factor_antiguedad = 1.0

    # 3. Caracteristicas Constructivas y Funcionales
    factor_calidad = f_p["calidad"].get(prop_data.get("calidad_edificio", "media").lower(), 1.00)
    factor_piso = obtener_factor_piso(prop_data.get("piso", 0), data)

    vent_key = prop_data.get("ventilacion", "simple").lower().strip()
    factor_vent = f_p["ventilacion"].get(vent_key, 1.00)

    suelo_key = prop_data.get("terminaciones_suelo", "estandar").lower().replace(" ", "_")
    factor_suelo = f_p["terminaciones_suelo"].get(suelo_key, 1.00)

    cocina_key = prop_data.get("distribucion_cocina", "integrada").lower().replace(" ", "_")
    factor_cocina = f_p["distribucion_cocina"].get(cocina_key, 1.00)

    carp_key = prop_data.get("carpinteria", "estandar").lower().strip()
    factor_carp = f_p["carpinteria"].get(carp_key, 1.00)

    orient_key = prop_data.get("orientacion", "este").lower().strip()
    factor_orient = f_p["orientacion"].get(orient_key, 1.00)

    detalles = prop_data.get("detalles_categoria", [])
    suma_detalles = 0
    for d in detalles:
        d_key = d.lower().replace(" ", "_")
        suma_detalles += f_p["detalles_categoria"].get(d_key, 0)
    factor_detalles = 1.0 + suma_detalles

    # FORMULA FINAL MULTIPLICATIVA
    valor_m2 = (
        precio_base
        * factor_barrio
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
            "fuente": "modelo v4.0 con serie historica real"
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
        f"Valuacion avanzada v4.0 al {fecha_ref_str}. "
        f"Basado en serie historica REAL de precios m2 Rosario (2000-2026) "
        f"con factores de barrio, estado, calidad y detalles constructivos. "
        f"Rango estimado: USD {rango_min:,.0f} - {rango_max:,.0f}/m2."
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

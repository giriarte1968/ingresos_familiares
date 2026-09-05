"""
SCRAPER FICHAS UP! INMOBILIARIA — WEB TOKKO BROKER
===================================================
Scrapea el inventario de VENTA de UP! Inmobiliaria (Rosario) desde su web
Tokko Broker server-rendered (upinmobiliaria.com.ar):

  - Enumeración por categoría de venta con paginación AJAX (?...&p=N)
    hasta "--NoMoreProperties--".
  - Captura de tarjetas (precio, m2, tipo, barrio, dirección, código ULA/UAP...)
    y markers (lat/lon reales por propiedad).
  - Filtro Gran Rosario (bbox GR + localidades del proyecto).
  - Apertura de la ficha completa /p/{id}-{slug} (precio real, frente, fondo,
    superficie total, descripción).

Output: cache_scraping_up_tokko.json  (fuente: "up_tokko")
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = r"C:\Users\Gustavo\ingresos_familiares_st"
OUTPUT_FILE = BASE_DIR + r"\cache_scraping_up_tokko.json"

BASE_URL = "https://www.upinmobiliaria.com.ar"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Categorías de Venta (ordenadas por relevancia). Se ignoran 404s gracefulmente.
VENTA_CATEGORIAS = [
    "/Venta",
    "/Terrenos-en-Venta",
    "/Departamentos-en-Venta",
    "/Casas-en-Venta",
    "/Countries-en-Venta",
    "/Oficinas-en-Venta",
    "/Locales-en-Venta",
    "/Campos-en-Venta",
    "/Cocheras-en-Venta",
    "/Garages-en-Venta",
]

# Paginación: mismo query string que genera el sitio (solo cambia p)
PAGINATION_QS = ("?q=&currency=ANY&min-price=&max-price=&min-roofed=&max-roofed="
                 "&min-surface=&max-surface=&min-total_surface=&max-total_surface="
                 "&min-front_measure=&max-front_measure=&min-depth_measure=&max-depth_measure="
                 "&age=&min-age=&max-age=&suites=&rooms=&credit_eligible=&is_exclusive="
                 "&tags=&operation=&locations=&location_type=&ptypes=&o=2,2&watermark=&p={page}")

# Bounding box Gran Rosario (incluye Rosario ciudad). Fuente: scraper_gran_rosario.py
GRAN_ROSARIO_BBOX = (-33.20, -32.60, -61.20, -60.30)

# Localidades del Gran Rosario (nombres que aparecen en las fichas de UP!)
GR_LOCALIDAD_KEYS = [
    "rosario", "fisherton", "funes", "roldan", "perez", "soldini", "ibarlucea",
    "granadero baigorria", "san lorenzo", "capitan bermudez", "capitán bermúdez",
    "fray luis beltran", "fray luis beltrán", "arroyo seco", "pueblo esther",
    "pinero", "piñero", "general lagos", "zavalla", "ricardone", "andino",
    "alvarez", "álvarez", "pujato", "uranga", "carcarana", "carcarañá",
    "country", "countries", "barrio cerrado", "barrios cerrados",
]

RE_MARKER = re.compile(r"add_new_marker\(\s*'(\d+)'\s*,\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)")
RE_PRICE = re.compile(r"USD\s?([\d][\d.,]*)")
RE_SUP_CARD = re.compile(r"([\d.,]+)\s*m")
RE_CODIGO = re.compile(r"([A-Z]{2,3}\d{6,})")
RE_M2_TERRENO = re.compile(r"^\s*(?:Terreno|Superficie\s*Total)\s*:?\s*([\d.,]+)\s*m", re.IGNORECASE | re.MULTILINE)
RE_M2_CUBIERTA = re.compile(r"^\s*(?:Cubierta|Superficie\s*Cubierta)\s*:?\s*([\d.,]+)\s*m", re.IGNORECASE | re.MULTILINE)
RE_FRENTE = re.compile(r"^\s*Frente\s*:?\s*([\d.,]+)\s*m", re.IGNORECASE | re.MULTILINE)
RE_FONDO = re.compile(r"^\s*Fondo\s*:?\s*([\d.,]+)\s*m", re.IGNORECASE | re.MULTILINE)


def numero_precio(val):
    """Precio: 'USD 1.200.000' -> 1200000.0 (los puntos son miles)."""
    if val is None:
        return None
    try:
        return float(val.replace(".", "").replace(",", "."))
    except (ValueError, AttributeError):
        return None


def numero_medida(val):
    """Medida superficie/frente/fondo: '54.25' -> 54.25, '1.039' -> 1039."""
    if val is None:
        return None
    try:
        s = val.strip().replace(",", ".")
        if s.count(".") == 1:
            return float(s)
        return float(s.replace(".", ""))
    except (ValueError, AttributeError):
        return None


def get(url, tries=3, timeout=25, backoff=(3, 8, 15)):
    """GET con reintentos, backoff ante 429 y log [DEBUG-UP]."""
    for intento in range(1, tries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                print(f"[DEBUG-UP] 404 {url}")
                return None
            if r.status_code == 429:
                wait = backoff[min(intento - 1, len(backoff) - 1)]
                print(f"[DEBUG-UP] 429 {url} (intento {intento}) espero {wait}s")
                time.sleep(wait)
                continue
            print(f"[DEBUG-UP] HTTP {r.status_code} {url} (intento {intento})")
        except requests.RequestException as e:
            print(f"[DEBUG-UP] ERROR {url}: {e} (intento {intento})")
        time.sleep(1 + intento)
    return None


def parse_markers(html):
    """{tokko_id: (lat, lon)} desde add_new_marker(...)"""
    markers = {}
    for m in RE_MARKER.finditer(html):
        markers[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return markers


def parse_cards(html):
    """Tarjetas <li prop-id=...> del listado."""
    cards = []
    soup = BeautifulSoup(html, "html.parser")
    for li in soup.select("li[prop-id]"):
        pid = li.get("prop-id", "").strip()
        a = li.select_one("a[href*='/p/']")
        url = a["href"] if a else None
        tipo_ub = li.select_one(".prop-desc-tipo-ub")
        direccion = li.select_one(".prop-desc-dir")
        valor = li.select_one(".prop-valor-nro")
        codref = li.select_one(".codref")
        sup_el = li.select_one(".prop-data div")
        ori_el = li.select_one(".prop-data2 div")

        tipo_ub_txt = tipo_ub.get_text(" ", strip=True) if tipo_ub else ""

        prop = {
            "id_tokko": pid,
            "url_up": (BASE_URL + url) if url else None,
            "slug": (url.split("-", 1)[1] if url and "-" in url else ""),
            "tipo_ubicacion": tipo_ub_txt,
            "direccion": direccion.get_text(" ", strip=True) if direccion else "",
            "precio_txt": valor.get_text(" ", strip=True) if valor else "",
            "codigo": codref.get_text(" ", strip=True) if codref else "",
            "sup_card": numero_medida(RE_SUP_CARD.search(sup_el.get_text(" ", strip=True)).group(1))
                       if sup_el and RE_SUP_CARD.search(sup_el.get_text(" ", strip=True)) else None,
            "orientacion": ori_el.get_text(" ", strip=True) if ori_el else "",
            "lat": None,
            "lon": None,
            "precio_usd": None,
            "m2_terreno": None,
            "m2_cubiertos": None,
            "frente_lote_m": None,
            "fondo_lote_m": None,
            "descripcion": "",
        }

        m_price = RE_PRICE.search(prop["precio_txt"])
        if m_price:
            val = numero_precio(m_price.group(1))
            if val is not None and val > 1:
                prop["precio_usd"] = val

        cards.append(prop)
    return cards


def pagina_en_gr(prop, markers):
    """¿Pertenece la propiedad al Gran Rosario? (coords > texto > bbox generico)."""
    coords = markers.get(prop["id_tokko"])
    if coords:
        lat, lon = coords
        lat_min, lat_max, lon_min, lon_max = GRAN_ROSARIO_BBOX
        if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
            return False
    texto = (prop["tipo_ubicacion"] + " " + prop["direccion"]).lower()
    return any(k in texto for k in GR_LOCALIDAD_KEYS)


def fetch_listado(path):
    """Pagina una categoría y devuelve (cards, markers)."""
    cards = []
    markers = {}
    url_pag = BASE_URL + path
    prev_ids = set()

    for page in range(1, 60):
        url = url_pag if page == 1 else url_pag + PAGINATION_QS.format(page=page)
        html = get(url)
        if html is None:
            break
        if page == 1:
            markers.update(parse_markers(html))
        nuevos = parse_cards(html)

        if page > 1 and not nuevos:
            print(f"[DEBUG-UP] FIN {path} (p={page}, sin nuevas tarjetas)")
            break
        if page == 1 and not nuevos:
            print(f"[DEBUG-UP] {path} sin resultados")
            break

        ids_actuales = {c["id_tokko"] for c in nuevos}
        if page > 1 and ids_actuales == prev_ids:
            print(f"[DEBUG-UP] {path}: página repetida en p={page} — corte")
            break
        prev_ids = ids_actuales

        cards.extend(nuevos)
        print(f"[DEBUG-UP] {path} p={page} [{len(nuevos)}] acumuladas={len(cards)} markers={len(markers)}")
        time.sleep(0.5)

    return cards, markers


def parse_detalle(html):
    """Campos de la ficha /p/{id}-{slug} a partir del texto visible."""
    datos = {"precio_usd": None, "m2_terreno": None, "m2_cubiertos": None,
             "frente_lote_m": None, "fondo_lote_m": None, "descripcion": "",
             "tipo": "", "operacion": "", "barrio": ""}

    soup = BeautifulSoup(html, "html.parser")
    texto = soup.get_text("\n", strip=True)

    m_price = RE_PRICE.search(texto)
    if m_price:
        val = numero_precio(m_price.group(1))
        # "USD1" es placeholder de precio oculto; <=1 USD no es un precio real
        if val is not None and val > 1:
            datos["precio_usd"] = val

    # Bloque SUPERFICIES Y MEDIDAS (entre esa sección y DESCRIPCION). Anclado a línea.
    m = re.search(r"SUPERFICIES Y MEDIDAS(.*?)(?:DESCRIPCI[ÓO]N|DETALLES DE LA PROPIEDAD|$)", texto, re.DOTALL | re.IGNORECASE)
    bloque = m.group(1) if m else ""

    if bloque:
        m_terr = RE_M2_TERRENO.search(bloque)
        m_cub = RE_M2_CUBIERTA.search(bloque)
        m_fren = RE_FRENTE.search(bloque)
        m_fond = RE_FONDO.search(bloque)
        if m_terr:
            datos["m2_terreno"] = numero_medida(m_terr.group(1))
        if m_cub:
            datos["m2_cubiertos"] = numero_medida(m_cub.group(1))
        if m_fren:
            datos["frente_lote_m"] = numero_medida(m_fren.group(1))
        if m_fond:
            datos["fondo_lote_m"] = numero_medida(m_fond.group(1))
    else:
        # Sin bloque estructurado: solo intento si la tarjeta ya dio superficie.
        pass

    # Descripción larga (la más larga de los párrafos del detalle)
    parrafos = [p.get_text(" ", strip=True) for p in soup.select("p, .descripcion, .property-description")]
    if parrafos:
        datos["descripcion"] = max(parrafos, key=len)

    # Tipo / operación desde el h1 del detalle ("Terreno en Venta en ...")
    h1 = soup.select_one("h1")
    if h1:
        h = h1.get_text(" ", strip=True)
        datos["tipo"] = h.split(" en ", 1)[0] if " en " in h else h

    return datos


def procesar_detalle(prop, markers):
    """Rellena la propiedad con la ficha completa."""
    if not prop["url_up"]:
        return
    html = get(prop["url_up"])
    if html is None:
        return

    coords = markers.get(prop["id_tokko"])
    if coords:
        prop["lat"], prop["lon"] = coords
    else:
        # algunos detalles embeben también markers
        for m2 in parse_markers(html).items():
            if m2[0] == prop["id_tokko"]:
                prop["lat"], prop["lon"] = m2[1]
                break
            markers[m2[0]] = m2[1]

    det = parse_detalle(html)
    if prop["precio_usd"] is None:
        prop["precio_usd"] = det["precio_usd"]
    if prop["m2_terreno"] is None:
        prop["m2_terreno"] = det["m2_terreno"]
    if prop["m2_cubiertos"] is None:
        prop["m2_cubiertos"] = det["m2_cubiertos"]
    if prop["frente_lote_m"] is None:
        prop["frente_lote_m"] = det["frente_lote_m"]
    if prop["fondo_lote_m"] is None:
        prop["fondo_lote_m"] = det["fondo_lote_m"]
    if not prop["descripcion"]:
        prop["descripcion"] = det["descripcion"][:3000] if det["descripcion"] else ""
    if det["tipo"]:
        prop["tipo"] = det["tipo"]
    print(f"[DEBUG-UP] ficha {prop['id_tokko']} precio={prop['precio_usd']} "
          f"m2terr={prop['m2_terreno']} frente={prop['frente_lote_m']} fondo={prop['fondo_lote_m']}")


def serializar(prop):
    """Mapea a payload del proyecto (convención cache_scraping_*)."""
    tipo_ub = prop["tipo_ubicacion"]
    partes = tipo_ub.split(" en ")
    tipo = prop.get("tipo") or (partes[0].strip() if partes else "")
    ub = partes[-1].strip() if len(partes) > 1 else ""
    barrio, ciudad = "", ""
    if "," in ub:
        barrio, ciudad = [x.strip() for x in ub.split(",", 1)]
    else:
        barrio = ub
    if not ciudad and barrio:
        barrio, ciudad = "", barrio
    # Normalización de ciudad
    m_paren = re.search(r"\(([^()]*?)\)", ciudad)
    if m_paren:
        ciudad = m_paren.group(1).strip()
    if ciudad.lower() == "santa fe" and barrio:
        ciudad, barrio = barrio, ""
    return {
        "id_tokko": prop["id_tokko"],
        "codigo": prop["codigo"],
        "url_up": prop["url_up"],
        "fecha_captura": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "precio": prop["precio_usd"],
        "moneda": "USD" if prop["precio_usd"] else None,
        "m2": prop["sup_card"],
        "m2_terreno": prop["m2_terreno"],
        "m2_cubiertos": prop["m2_cubiertos"],
        "frente_lote_m": prop["frente_lote_m"],
        "fondo_lote_m": prop["fondo_lote_m"],
        "sup_total_m2": prop["m2_terreno"] if prop["m2_terreno"] else prop["sup_card"],
        "tipo": tipo,
        "operacion": "venta",
        "direccion": prop["direccion"],
        "zona": barrio,
        "barrio": barrio,
        "ciudad": ciudad,
        "lat": prop["lat"],
        "lon": prop["lon"],
        "descripcion": prop["descripcion"][:1500],
        "fuente": "up_tokko",
    }


def main():
    print("[DEBUG-UP] Inicio scraping UP! / Tokko — Venta, Gran Rosario")
    todas = {}
    markers_total = {}

    for path in VENTA_CATEGORIAS:
        cards, markers = fetch_listado(path)
        if not cards:
            continue
        print(f"[DEBUG-UP] {path}: {len(cards)} cards, {len(markers)} markers")
        for c in cards:
            todas.setdefault(c["id_tokko"], c)
        markers_total.update(markers)

    print(f"[DEBUG-UP] Total únicas (pre-filtro): {len(todas)}")

    # Filtro Gran Rosario
    seleccion = {pid: p for pid, p in todas.items() if pagina_en_gr(p, markers_total)}
    print(f"[DEBUG-UP] En Gran Rosario: {len(seleccion)}")

    # Fichas completas en paralelo (poco concurrencia para evitar 429)
    with ThreadPoolExecutor(max_workers=2) as ex:
        futuros = {ex.submit(procesar_detalle, p, markers_total): pid
                   for pid, p in seleccion.items()}
        for i, f in enumerate(as_completed(futuros)):
            try:
                f.result()
            except Exception as e:
                print(f"[DEBUG-UP] ERROR ficha: {e}")
            if i % 5 == 0:
                time.sleep(1.0)

    salida = [serializar(p) for p in seleccion.values()]
    salida.sort(key=lambda p: (p["ciudad"] or "", p["zona"] or "", p["precio"] or 0))

    meta = {
        "fuente": "up_tokko",
        "agencia": "UP! Inmobiliaria (Rosario)",
        "operaciones": ["venta"],
        "rubro": "Inventario completo de fichas /p/{id}-{slug} en upinmobiliaria.com.ar (web Tokko Broker)",
        "fecha_scrape": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_fichas": len(salida),
        "gra_bbox": list(GRAN_ROSARIO_BBOX),
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "propiedades": salida}, f, ensure_ascii=False, indent=2)

    print(f"[DEBUG-UP] Guardado: {OUTPUT_FILE} ({len(salida)} propiedades)")
    por_ciudad = {}
    for p in salida:
        por_ciudad[p["ciudad"] or "?"] = por_ciudad.get(p["ciudad"] or "?", 0) + 1
    print(f"[DEBUG-UP] Por ciudad: {por_ciudad}")


if __name__ == "__main__":
    main()
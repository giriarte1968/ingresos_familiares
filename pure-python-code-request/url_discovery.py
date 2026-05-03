"""
url_discovery.py
Auto-descubrimiento de la URL de listado real de una inmobiliaria.
Estrategia en cascada:
  1. Probar rutas canónicas conocidas
  2. Crawl del sitemap.xml / robots.txt
  3. Rastrear links de la home que parezcan listados
  4. Fallback: Google Search param ?q=site:dominio+propiedades
"""

import asyncio
import re
import httpx
from urllib.parse import urljoin, urlparse
from typing import Optional

# Rutas canónicas ordenadas por frecuencia real en el mercado argentino
CANDIDATE_PATHS = [
    "/listados",
    "/propiedades",
    "/inmuebles",
    "/inmuebles/ventas",
    "/ventas",
    "/alquileres",
    "/property/",           # WordPress + plugin de real estate
    "/properties",
    "/buscar",
    "/buscar-propiedades",
    "/resultados",
    "/catalogo",
    "/emprendimientos",
    "/ficha",
    "/en-venta",
    "/departamentos",
    "/casas",
]

LISTING_KEYWORDS = re.compile(
    r"(listado|propiedad|inmueble|venta|alquiler|departamento|casa|terreno|"
    r"property|properties|buscar|resultado|catalogo|emprendimiento)",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
}


async def _get(client: httpx.AsyncClient, url: str) -> Optional[httpx.Response]:
    """GET silencioso; retorna None en error."""
    try:
        r = await client.get(url, follow_redirects=True, timeout=10)
        if r.status_code == 200:
            return r
    except Exception:
        pass
    return None


async def discover_list_url(base_url: str) -> dict:
    """
    Dado un base_url (ej. https://www.vanzini.com.ar),
    retorna un dict con:
      - list_url: la URL de listado encontrada
      - detail_link_selector: selector CSS inferido
      - engine: "http" o "playwright"
      - confidence: "high" | "medium" | "low"
    """
    base = base_url.rstrip("/")
    result = {
        "list_url": f"{base}/propiedades",  # fallback seguro
        "detail_link_selector": "a[href*='propiedad'], a[href*='inmueble'], a[href*='ficha'], a[href*='property'], a[href*='detalle']",
        "engine": "playwright",
        "confidence": "low",
    }

    async with httpx.AsyncClient(headers=HEADERS, verify=False) as client:

        # ── PASO 1: Probar rutas canónicas ──────────────────────────────────
        for path in CANDIDATE_PATHS:
            url = f"{base}{path}"
            resp = await _get(client, url)
            if resp:
                body = resp.text.lower()
                # Confirmar que la página tenga contenido de listado
                hits = len(LISTING_KEYWORDS.findall(body))
                if hits >= 3:
                    result["list_url"] = str(resp.url)  # URL final tras redirects
                    result["confidence"] = "high"
                    result["engine"] = _infer_engine(body)
                    result["detail_link_selector"] = _infer_selector(body, base)
                    return result

        # ── PASO 2: Leer sitemap.xml ────────────────────────────────────────
        for sitemap_path in ["/sitemap.xml", "/sitemap_index.xml", "/sitemap"]:
            resp = await _get(client, f"{base}{sitemap_path}")
            if resp:
                urls_in_sitemap = re.findall(r"<loc>(.*?)</loc>", resp.text)
                for u in urls_in_sitemap:
                    if LISTING_KEYWORDS.search(u):
                        result["list_url"] = u
                        result["confidence"] = "medium"
                        result["engine"] = "playwright"
                        return result

        # ── PASO 3: Crawl de la home ────────────────────────────────────────
        home_resp = await _get(client, base)
        if home_resp:
            anchors = re.findall(r'href=["\']([^"\']+)["\']', home_resp.text)
            for href in anchors:
                full = urljoin(base, href)
                # Sólo links internos
                if urlparse(full).netloc == urlparse(base).netloc:
                    if LISTING_KEYWORDS.search(href):
                        result["list_url"] = full
                        result["confidence"] = "medium"
                        result["engine"] = _infer_engine(home_resp.text)
                        result["detail_link_selector"] = _infer_selector(home_resp.text, base)
                        return result

    # ── PASO 4: Fallback ────────────────────────────────────────────────────
    return result


def _infer_engine(html_body: str) -> str:
    """Detecta si la página requiere JS (React/Vue/Angular/Next)."""
    js_signals = [
        "__NEXT_DATA__", "react-root", "ng-version",
        "__nuxt", "data-reactroot", "window.__INITIAL_STATE__",
        "Vue.config", "_next/static",
    ]
    for sig in js_signals:
        if sig in html_body:
            return "playwright"
    return "http"


def _infer_selector(html_body: str, base_url: str) -> str:
    """
    Intenta deducir el selector CSS correcto para los links de detalle
    buscando patrones comunes en el HTML.
    """
    domain = urlparse(base_url).netloc.replace("www.", "").split(".")[0]

    patterns = [
        (r'href=["\']([^"\']*(?:propiedad|ficha|inmueble|detalle|property)[^"\']*)["\']',
         "a[href*='propiedad'], a[href*='ficha']"),
        (r'class=["\'][^"\']*(?:property-card|prop-card|listing-card|card-prop)[^"\']*["\']',
         "a.property-card, a.prop-card, a.listing-card"),
        (r'class=["\'][^"\']*(?:item-prop|propiedad-item|resultado)[^"\']*["\']',
         "a.item-prop, .propiedad-item a, .resultado a"),
    ]

    for pattern, selector in patterns:
        if re.search(pattern, html_body, re.IGNORECASE):
            return selector

    # Selector ultra-genérico como último recurso
    return (
        f"a[href*='{domain}'], "
        "a[href*='propiedad'], a[href*='inmueble'], "
        "a[href*='ficha'], a[href*='property'], a[href*='detalle']"
    )


async def discover_all(agencies: list[dict]) -> list[dict]:
    """
    Recorre una lista de inmobiliarias y actualiza list_url, engine y selector.
    Retorna la lista enriquecida + un reporte de confidence.
    """
    tasks = [discover_list_url(ag["url"]) for ag in agencies]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    enriched = []
    for ag, res in zip(agencies, results):
        ag = dict(ag)  # no mutar original
        if isinstance(res, dict):
            ag["list_url"] = res["list_url"]
            ag["engine"] = res["engine"]
            ag["detail_link_selector"] = res["detail_link_selector"]
            ag["_url_confidence"] = res["confidence"]
        else:
            ag["_url_confidence"] = "error"
        enriched.append(ag)

    return enriched
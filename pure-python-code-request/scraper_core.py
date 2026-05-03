"""
scraper_core.py
Motor de scraping con:
  - Fallback automático list_url → list_url_alt → url_discovery
  - Detección de bloqueo (Cloudflare / 403 / CAPTCHA)
  - Heurística regex para precios y dimensiones
  - De-duplicación en memoria
  - Rate limiting gentil por dominio
"""

import asyncio
import re
import httpx
from urllib.parse import urljoin, urlparse
from typing import Optional
from collections import defaultdict

# ── Importar auto-descubrimiento ────────────────────────────────────────────
from url_discovery import discover_list_url

# ── Regex de extracción ─────────────────────────────────────────────────────
RE_PRICE = re.compile(
    r"(USD?[\s\$]?\s?[\d\.]+(?:[\.,]\d{3})*(?:[\.,]\d{2})?|"
    r"U\$[Ss][\s\.]*[\d\.]+(?:[\.,]\d{3})*|"
    r"\$\s?[\d\.]+(?:[\.,]\d{3})*)",
    re.IGNORECASE,
)
RE_SURFACE = re.compile(
    r"(\d+[\.,]?\d*)\s*m[²2]",
    re.IGNORECASE,
)
RE_OPERACION = re.compile(
    r"\b(venta|alquiler|alquileres|renta|rentas|compra| compra)\b",
    re.IGNORECASE,
)
RE_ANIO = re.compile(
    r"\b(año|anio|construido|construccion|del\s*(\d{4}))\b",
    re.IGNORECASE,
)
RE_ROOMS = re.compile(
    r"(\d+)\s*(?:amb(?:iente)?s?|dorm(?:itorio)?s?|hab(?:itacion)?es?)",
    re.IGNORECASE,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}

BLOCK_SIGNALS = [
    "cf-browser-verification",   # Cloudflare
    "challenge-form",            # Cloudflare challenge
    "Access denied",
    "403 Forbidden",
    "captcha",
    "robot",
    "unusual traffic",
]

# Rate limiting: 1 request por dominio cada N segundos
RATE_LIMIT_SECONDS = 1.5
_domain_locks: dict = defaultdict(asyncio.Lock)
_domain_last_call: dict = defaultdict(float)


async def _rate_limited_get(
    client: httpx.AsyncClient,
    url: str,
    retries: int = 3,
) -> Optional[httpx.Response]:
    """GET con rate limiting por dominio y reintentos exponenciales."""
    domain = urlparse(url).netloc
    async with _domain_locks[domain]:
        import time
        elapsed = time.monotonic() - _domain_last_call[domain]
        if elapsed < RATE_LIMIT_SECONDS:
            await asyncio.sleep(RATE_LIMIT_SECONDS - elapsed)
        _domain_last_call[domain] = time.monotonic()

    for attempt in range(retries):
        try:
            r = await client.get(url, follow_redirects=True, timeout=15)
            if r.status_code in (429, 503):
                wait = 2 ** attempt
                await asyncio.sleep(wait)
                continue
            return r
        except (httpx.TimeoutException, httpx.ConnectError):
            await asyncio.sleep(2 ** attempt)
        except Exception:
            break
    return None


def _is_blocked(response: httpx.Response) -> bool:
    """Detecta páginas de bloqueo/CAPTCHA."""
    if response.status_code in (403, 429, 503):
        return True
    body_lower = response.text.lower()
    return any(sig.lower() in body_lower for sig in BLOCK_SIGNALS)


def _extract_heuristic(text: str) -> dict:
    """Extracción regex sobre texto crudo (ignora estructura HTML)."""
    prices = RE_PRICE.findall(text)
    surfaces = RE_SURFACE.findall(text)
    rooms = RE_ROOMS.findall(text)
    ops = RE_OPERACION.findall(text)
    anios = RE_ANIO.findall(text)
    
    # Determinar operación
    operacion = None
    if ops:
        op = ops[0].lower()
        if 'alquiler' in op or 'rent' in op:
            operacion = 'alquiler'
        else:
            operacion = 'venta'
    
    # Extraer año de construcción
    anio_construccion = None
    for a in anios:
        match = re.search(r'\d{4}', a)
        if match:
            try:
                y = int(match.group())
                if 1900 <= y <= 2026:
                    anio_construccion = y
                    break
            except:
                pass
    
    return {
        "prices_found": prices[:5],
        "surfaces_m2": surfaces[:5],
        "rooms": rooms[:5],
        "operacion": operacion,
        "anio_construccion": anio_construccion,
    }


def _extract_links(html: str, base_url: str, selector_hint: str) -> list[str]:
    """
    Extrae links de detalle usando regex multi-estrategia.
    No usa BeautifulSoup para mantener dependencias mínimas.
    """
    # Extraer keywords del selector para armar regex
    keywords = re.findall(r"'([^']+)'", selector_hint)
    if not keywords:
        keywords = ["propiedad", "inmueble", "ficha", "property", "detalle", "listado"]

    pattern = "|".join(re.escape(k) for k in keywords)
    raw_links = re.findall(r'href=["\']([^"\']+)["\']', html)
    domain = urlparse(base_url).netloc

    seen = set()
    result = []
    for href in raw_links:
        if re.search(pattern, href, re.IGNORECASE):
            full = urljoin(base_url, href)
            if urlparse(full).netloc == domain and full not in seen:
                seen.add(full)
                result.append(full)
    return result


async def scrape_agency(
    agency: dict,
    seen_urls: set,
    max_pages: int = 3,
) -> list[dict]:
    """
    Scrapea una inmobiliaria.
    Retorna lista de dicts con datos de cada propiedad encontrada.
    """
    nombre = agency["nombre"]
    list_url = agency.get("list_url", "")
    list_url_alt = agency.get("list_url_alt")
    selector = agency.get(
        "detail_link_selector",
        "a[href*='propiedad'], a[href*='inmueble']",
    )
    results = []

    async with httpx.AsyncClient(headers=HEADERS, verify=False) as client:

        # ── Intentar list_url principal ─────────────────────────────────────
        resp = await _rate_limited_get(client, list_url)

        # ── Fallback a list_url_alt ─────────────────────────────────────────
        if (not resp or resp.status_code == 404 or _is_blocked(resp)) and list_url_alt:
            print(f"  [{nombre}] -> {list_url} bloqueado o 404, probando alt: {list_url_alt}")
            resp = await _rate_limited_get(client, list_url_alt)

        # ── Fallback a auto-descubrimiento ──────────────────────────────────
        if not resp or resp.status_code == 404 or _is_blocked(resp):
            print(f"  [{nombre}] Activando url_discovery...")
            discovery = await discover_list_url(agency["url"])
            discovered_url = discovery["list_url"]
            if discovered_url != list_url:
                resp = await _rate_limited_get(client, discovered_url)
                if resp and resp.status_code == 200:
                    list_url = discovered_url
                    selector = discovery["detail_link_selector"]
                    print(f"  [{nombre}] Discovery encontro: {discovered_url}")

        if not resp or resp.status_code != 200:
            print(f"  [{nombre}] Sin respuesta valida. Saltando.")
            return results

        if _is_blocked(resp):
            print(f"  [{nombre}] Bloqueado por anti-bot.")
            return results

        # ── Paginar y extraer links ─────────────────────────────────────────
        current_url = list_url
        for page_num in range(1, max_pages + 1):
            if page_num > 1:
                # Detectar paginación: ?page=N, /pagina/N, ?pag=N, /page/N
                next_url = _find_next_page(resp.text, current_url, page_num)
                if not next_url or next_url == current_url:
                    break
                resp = await _rate_limited_get(client, next_url)
                if not resp or resp.status_code != 200:
                    break
                current_url = next_url

            detail_links = _extract_links(resp.text, agency["url"], selector)
            print(f"  [{nombre}] Página {page_num}: {len(detail_links)} links encontrados")

            for link in detail_links:
                if link in seen_urls:
                    continue
                seen_urls.add(link)

                detail_resp = await _rate_limited_get(client, link)
                if not detail_resp or detail_resp.status_code != 200:
                    continue

                heuristic = _extract_heuristic(detail_resp.text)
                prop = {
                    "inmobiliaria": nombre,
                    "url": link,
                    **heuristic,
                }
                results.append(prop)

    print(f"  [{nombre}] Total propiedades: {len(results)}")
    return results


def _find_next_page(html: str, current_url: str, page_num: int) -> Optional[str]:
    """Detecta URL de página siguiente con patrones comunes."""
    patterns = [
        rf'href=["\']([^"\']*(?:page|pagina|pag|p)={page_num}[^"\']*)["\']',
        rf'href=["\']([^"\']*(?:/page/|/pagina/|/p/){page_num}[^"\']*)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            return urljoin(current_url, m.group(1))

    # Fallback: agregar ?page=N al current_url
    if "?" not in current_url:
        return f"{current_url}?page={page_num}"
    return None
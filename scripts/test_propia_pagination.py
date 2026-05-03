import re
import json
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL_BASE = "https://propia.com.ar/propiedades?operation=1&type=2&location_city_id=1"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(URL_BASE, timeout=30000)
    page.wait_for_timeout(4000)
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')

    cards = soup.find_all('div', class_=lambda x: x and 'card' in x.lower())
    print(f"Initial cards: {len(cards)}")
    if cards:
        print(f"First card text (200): {cards[0].text[:200]}")

    # Check for pagination controls
    nav_elements = soup.find_all(['nav', 'ul'], class_=lambda x: x and ('page' in x.lower() or 'pagination' in x.lower() or 'pagina' in x.lower()))
    for nav in nav_elements:
        print(f"Pagination nav: {nav.get('class')}, text: {nav.text[:200]}")

    # Check for "Siguiente" links / load more
    siguiente = soup.find_all(text=re.compile('siguiente|next|mas', re.IGNORECASE))
    for s in siguiente[:5]:
        parent = s.parent if s.parent else None
        grandparent = parent.parent if parent else None
        print(f"Siguiente: parent={parent and parent.name}, grandparent={grandparent and grandparent.name}")
        if parent:
            print(f"  parent class: {parent.get('class')}")
            if parent.get('href'):
                print(f"  href: {parent.get('href')}")

    # Check for data attributes that might indicate total pages
    data_attrs = soup.find_all(attrs=lambda x: x and any(k in str(x) for k in ['total', 'pages', 'page', 'count']))
    for d in data_attrs[:5]:
        print(f"Data attr: {d.get('class')}, attrs={ {k:v for k,v in d.attrs.items() if 'data' in k} }")

    # Look for nuxt data / __NUXT__
    nuxt_data = re.search(r'window\.__NUXT__\s*=\s*({.*?});', html, re.DOTALL)
    if nuxt_data:
        print(f"NUXT data found! Length: {len(nuxt_data.group(1))}")
        print(f"NUXT preview: {nuxt_data.group(1)[:500]}")

    # Look for JSON data in script tags
    scripts = soup.find_all('script')
    for s in scripts:
        text = s.string or ''
        if 'items' in text.lower() or 'properties' in text.lower() or 'listings' in text.lower():
            print(f"Script with data: {text[:300]}")

    # Try scrolling to load more - check for "load more" button
    load_more = soup.find_all(text=re.compile('ver mas|cargar mas|load more', re.IGNORECASE))
    for lm in load_more:
        print(f"Load more: parent={lm.parent.name}, attrs={lm.parent.attrs}")

    browser.close()
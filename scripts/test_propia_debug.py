import re
import json
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URLS = {
    "venta_depto": "https://propia.com.ar/propiedades?operation=1&type=2&location_city_id=1&page=1",
    "alquiler_depto": "https://propia.com.ar/propiedades?operation=2&type=2&location_city_id=1&page=1",
    "venta_casa": "https://propia.com.ar/propiedades?operation=1&type=1&location_city_id=1&page=1",
    "alquiler_casa": "https://propia.com.ar/propiedades?operation=2&type=1&location_city_id=1&page=1",
    "alquiler_ph": "https://propia.com.ar/propiedades?operation=2&type=3&location_city_id=1&page=1",
    "sin_filtros": "https://propia.com.ar/propiedades?location_city_id=1&page=1",
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for name, url in URLS.items():
        print(f"\n{'='*60}")
        print(f"URL: {name}")
        print(f"{url}")
        try:
            page.goto(url, timeout=30000)
            page.wait_for_timeout(4000)
            html = page.content()
            soup = BeautifulSoup(html, 'html.parser')

            precio_texts = soup.find_all(text=re.compile(r'U\$S|USD|\$[\d.,]+'))
            cards = soup.find_all('div', class_=lambda x: x and 'card' in x.lower())
            articles = soup.find_all('article')
            divs_white = soup.find_all('div', class_='bg-white')

            print(f"  Cards 'card': {len(cards)}, Articles: {len(articles)}, bg-white: {len(divs_white)}")
            print(f"  Precio texts (USD/$): {len(precio_texts)}")

            if cards:
                print(f"  First card class: {cards[0].get('class')}")
                print(f"  First card text (200): {cards[0].text[:200]}")
            elif precio_texts:
                print(f"  First precio text parent: {precio_texts[0].parent}")
                print(f"  First precio text (200): {precio_texts[0][:200]}")
            else:
                title = soup.find('title')
                h1 = soup.find('h1')
                print(f"  Title: {title.text if title else 'N/A'}")
                print(f"  H1: {h1.text if h1 else 'N/A'}")
                body = soup.text[:300]
                print(f"  Body preview: {body}")

        except Exception as e:
            print(f"  ERROR: {e}")

    browser.close()
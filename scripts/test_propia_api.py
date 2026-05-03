import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def log_request(request):
    if any(x in request.url.lower() for x in ['api', 'prop', 'list', 'items', 'fetch', 'graphql', 'json']):
        if '_nuxt' not in request.url and '_next' not in request.url:
            print(f"REQUEST: {request.url}")

def log_response(response):
    url = response.url
    if any(x in url.lower() for x in ['api', 'prop', 'list', 'items', 'graphql']):
        if '_nuxt' not in url and '_next' not in url and '.css' not in url and '.js' not in url:
            print(f"RESPONSE [{response.status}]: {url}")

URL_BASE = "https://propia.com.ar/propiedades?operation=1&type=2&location_city_id=1"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    page.on('request', log_request)
    page.on('response', log_response)

    page.goto(URL_BASE, timeout=30000)
    page.wait_for_timeout(3000)
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')

    # Check for Nuxt data or SSR data
    scripts = soup.find_all('script')
    for s in scripts:
        text = s.string or ''
        if 'nonce' in text or '__NUXT' in text:
            continue
        if len(text) > 500 and ('price' in text.lower() or 'precio' in text.lower() or 'items' in text.lower()):
            print(f"\nLarge script ({len(text)} chars): {text[:600]}")
            break

    # Check all response URLs for patterns
    print("\nAll non-asset responses:")
    all_urls = []
    page2 = context.new_page()
    page2.on('response', lambda r: all_urls.append(r.url) if (
        r.status != 0 and
        not any(x in r.url for x in ['.css', '.js', '.png', '.jpg', '.svg', '.woff', '.ico', '_nuxt', '_next'])
    ) else None)

    page2.goto(URL_BASE, timeout=30000)
    page2.wait_for_timeout(3000)
    for u in sorted(set(all_urls)):
        print(f"  {u}")
    page2.close()

    browser.close()
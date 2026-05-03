import re
import json
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL_BASE = "https://propia.com.ar/propiedades?operation=1&type=2&location_city_id=1"

captured_responses = []

def log_response(response):
    url = response.url
    if 'api' in url.lower() or 'json' in url.lower() or 'prop' in url.lower():
        captured_responses.append({'url': url, 'status': response.status})

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    page = context.new_page()

    page.on('response', log_response)

    page.goto(URL_BASE, timeout=30000)
    page.wait_for_timeout(4000)

    # Try scrolling to load more
    print("Scrolling to bottom...")
    for i in range(5):
        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        page.wait_for_timeout(2000)
        print(f"  Scroll {i+1}: height={page.evaluate('document.body.scrollHeight')}")

    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.find_all('div', class_=lambda x: x and 'card' in x.lower())
    print(f"Cards after scroll: {len(cards)}")

    # Try clicking "Siguiente" button if exists
    buttons = soup.find_all('button')
    sig_buttons = [b for b in buttons if b.find(string=re.compile('siguiente', re.IGNORECASE))]
    print(f"'Siguiente' buttons found: {len(sig_buttons)}")
    for sb in sig_buttons:
        attrs = sb.attrs
        print(f"  Button attrs: {attrs}")

    # Check network responses captured
    print(f"\nAPI/network responses captured: {len(captured_responses)}")
    for r in captured_responses[:10]:
        print(f"  [{r['status']}] {r['url']}")

    # Try direct API call - look for fetch patterns
    scripts = soup.find_all('script')
    for s in scripts:
        text = s.string or ''
        if 'fetch' in text.lower() or 'axios' in text.lower() or '/api/' in text:
            matches = re.findall(r'["\']([^"\']*?/api/[^"\']*?)["\']', text)
            for m in matches[:5]:
                print(f"API URL in script: {m}")

    browser.close()
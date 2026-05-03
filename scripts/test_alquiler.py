import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def test_alquiler():
    print("Test Alquiler...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Test alquiler
        url = "https://propia.com.ar/propiedades?operation=2&type=2&location_city_id=1&page=1"
        page.goto(url, timeout=15000)
        page.wait_for_timeout(3000)
        
        html = page.content()
        
        usd_prices = re.findall(r'U\$S\s*([\d.,]+)', html)
        ars_prices = re.findall(r'\$([\d.,]+)', html)
        
        print(f"Alquiler - USD: {len(usd_prices)}, ARS: {len(ars_prices)}")
        
        if usd_prices:
            print(f"USD prices: {usd_prices[:5]}")
        if ars_prices:
            print(f"ARS prices: {ars_prices[:5]}")
        
        browser.close()

if __name__ == "__main__":
    test_alquiler()
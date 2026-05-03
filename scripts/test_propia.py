import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def test_propia():
    print("Iniciando test...")
    
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navigating to propria...")
        url = "https://propia.com.ar/propiedades?operation=1&type=2&location_city_id=1&page=1"
        page.goto(url, timeout=15000)
        print("Waiting for content...")
        page.wait_for_timeout(3000)
        
        html = page.content()
        print(f"HTML length: {len(html)}")
        
        # Save HTML for inspection
        with open("test_propia.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Saved to test_propia.html")
        
        # Look for prices
        usd_prices = re.findall(r'U\$S\s*([\d.,]+)', html)
        ars_prices = re.findall(r'\$([\d.,]+)', html)
        
        print(f"USD prices found: {len(usd_prices)}")
        print(f"ARS prices found: {len(ars_prices)}")
        
        if usd_prices:
            print(f"First USD: {usd_prices[:3]}")
        if ars_prices:
            print(f"First ARS: {ars_prices[:3]}")
        
        browser.close()
    print("Done!")

if __name__ == "__main__":
    test_propia()
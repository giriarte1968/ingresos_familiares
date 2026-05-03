import re
import json
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def test_both():
    print("="*50)
    print("Testing VENTA (operation=1)")
    print("="*50)
    
    usd_pattern = r'U\$S\s*([\d.,]+)'
    ars_pattern = r'\$([\d.,]+)'
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # VENTA - Departamento
        page = browser.new_page()
        url = "https://propia.com.ar/propiedades?operation=1&type=2&location_city_id=1&page=1"
        page.goto(url, timeout=15000)
        page.wait_for_timeout(3000)
        html_v = page.content()
        
        usd_v = len(re.findall(usd_pattern, html_v))
        ars_v = len(re.findall(ars_pattern, html_v))
        
        print(f"Venta Depto - USD: {usd_v}")
        print(f"Venta Depto - ARS: {ars_v}")
        
        # ALQUILER - Departamento  
        page2 = browser.new_page()
        url2 = "https://propia.com.ar/propiedades?operation=2&type=2&location_city_id=1&page=1"
        page2.goto(url2, timeout=15000)
        page2.wait_for_timeout(3000)
        html_a = page2.content()
        
        usd_a = len(re.findall(usd_pattern, html_a))
        ars_a = len(re.findall(ars_pattern, html_a))
        
        print(f"Alquiler Depto - USD: {usd_a}")
        print(f"Alquiler Depto - ARS: {ars_a}")
        
        if "alquiler" in html_a.lower():
            print("La palabra 'alquiler' aparece en el HTML")
        
        browser.close()
        
    print("\n" + "="*50)
    print("Testing ALQUILER (operation=2) with different type")
    print("="*50)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Probar type=1 (casa) para alquiler
        page = browser.new_page()
        url = "https://propia.com.ar/propiedades?operation=2&type=1&location_city_id=1&page=1"
        page.goto(url, timeout=15000)
        page.wait_for_timeout(3000)
        html = page.content()
        
        usd_c = len(re.findall(usd_pattern, html))
        ars_c = len(re.findall(ars_pattern, html))
        
        print(f"Alquiler Casa - USD: {usd_c}")
        print(f"Alquiler Casa - ARS: {ars_c}")
        
        browser.close()

if __name__ == "__main__":
    test_both()
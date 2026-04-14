from playwright.sync_api import sync_playwright
import re

def scrapear_badaloni():
    print("="*60)
    print("SCRAPING BADALONI")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://www.badaloni.com.ar/Venta"
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        
        links = page.query_selector_all("a[href*='/p/']")
        
        props = []
        
        for i, link in enumerate(links[:30]):
            try:
                href = link.get_attribute("href")
                if not href:
                    continue
                
                # Skip if not a small property (terrenos, galpones are big)
                # Use text contains m2 but check the value
                texto = link.inner_text()
                
                # Find m2 in the text
                m2_match = re.search(r'(\d+)\s*m', texto)
                if not m2_match:
                    continue
                
                try:
                    metros = int(m2_match.group(1))
                except:
                    continue
                
                # Only small deptos like 20-250 m2
                if not (20 < metros < 250):
                    continue
                
                # The link text doesn't contain price directly - need to visit
                # But we can skip for now
                continue
                
            except Exception as e:
                continue
        
        # Alternative: Get the basic data from listing text
        # Each link has m2 visible in the list
        # We can extract from text pattern like "28 m2" in results
        
        # Parse result list - text shows "28 m2" pattern
        page_text = page.evaluate("document.body.innerText")
        
        # Find all dept patterns
        m2_deptos = re.findall(r'(\d+)\s*m[2²]?(?!\s*\d)', page_text)
        
        print(f"Possible m2 values found: {len(m2_deptos)}")
        print(f"M2s: {m2_deptos}")
        
        browser.close()
    
    print("Badaloni needs detailed visit per property - skipping for now")
    return []

def scrapear_zeballos():
    print("="*60)
    print("SCRAPING ZEBALLOS")  
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://inmobiliariazeballos.com.ar/nuestras-propiedades"
        page.goto(url, timeout=30000)
        page.wait_for_timeout(5000)
        
        html = page.content()
        
        # Save for analysis
        with open("zeballos_prop.html", "w") as f:
            f.write(html)
        
        # Search for property data
        props = re.findall(r'U?\$S?\s*([\d]+)', html)
        m2s = re.findall(r'(\d+)\s*m', html)
        
        print(f"Prices found: {len(props)}")
        print(f"M2s found: {len(m2s)}")
        
        browser.close()
    
    return []

if __name__ == "__main__":
    scrapear_badaloni()
    scrapear_zeballos()
from playwright.sync_api import sync_playwright
import re

def scrapear_zonaprop_cloudflare():
    print("Iniciando con evasion Cloudflare...")
    
    with sync_playwright() as p:
        # Configurar context con user-agent real
        context = p.chromium.launch_persistent_context(
            "",
            headless=False,
            ignore_https_errors=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        # Ir directo a la URL de busqueda
        url = "https://www.zonaprop.com.ar/departamentos-venta-rosario.html"
        print(f"Navegando a {url}...")
        
        try:
            response = page.goto(url, timeout=45000, wait_until="domcontentloaded")
            print(f"Status: {response.status if response else 'N/A'}")
        except Exception as e:
            print(f"Error al navegar: {e}")
            context.close()
            return []
        
        # Esperar a que pase el challenge (máximo 30 seg)
        print("Esperando validacion Cloudflare...")
        page.wait_for_timeout(30000)
        
        html = page.content()
        print(f"HTML: {len(html)} caracteres")
        
        # Verificar si paso el challenge
        if "Just a moment" in html or "chl_page" in html:
            print("Still blocked by Cloudflare!")
            context.close()
            return []
        
        # Buscar postings con varios selectores
        selectors = [
            "div[data-postingid]",
            "div.posting-card",
            "div[data-qa*='posting']",
            "divposting",
            "article.posting-card"
        ]
        
        props = []
        for sel in selectors:
            elementos = page.query_selector_all(sel)
            print(f"Selector '{sel}': {len(elementos)} elementos")
            if elementos:
                break
        
        context.close()
        return props

if __name__ == "__main__":
    scrapear_zonaprop_cloudflare()
from playwright.sync_api import sync_playwright
import re
import json

def scrapear_zonaprop():
    print("="*60)
    print("SCRAPING ZONAPROP (CORREGIDO)")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        print("Navegando...")
        page.goto("https://www.zonaprop.com.ar/departamentos-venta-rosario.html", timeout=60000)
        
        print("Esperando CF...")
        page.wait_for_timeout(20000)
        
        html = page.content()
        
        if "Just a moment" in html[:500]:
            print("BLOQUEADO!")
            browser.close()
            return []
        
        print("Extrayendo datos del HTML...")
        
        props = []
        
        # Método 1: buscar en postingCardLayout
        cards = page.query_selector_all(".postingCardLayout-module__posting-card-layout")
        print(f"Cards encontradas: {len(cards)}")
        
        for card in cards:
            try:
                # Solo PROPERTY (no DEVELOPMENT)
                posting_type = card.get_attribute("data-posting-type")
                if posting_type != "PROPERTY":
                    continue
                
                # Extraer precio
                precio_el = card.query_selector("[data-qa='POSTING_CARD_PRICE']")
                if not precio_el:
                    continue
                
                precio_text = precio_el.inner_text()
                # Usar regex más flexible
                precio_match = re.search(r'USD\s*([\d.,]+)', precio_text.replace(".", "").replace(",", ""))
                if not precio_match:
                    continue
                try:
                    precio = float(precio_match.group(1).replace(",", "."))
                except:
                    continue
                
                # Extraer área (m2)
                area_el = card.query_selector("[data-qa='POSTING_CARD_FEATURES']")
                metros = None
                if area_el:
                    area_text = area_el.inner_text()
                    m_match = re.search(r'(\d+)\s*m', area_text)
                    if m_match:
                        try:
                            metros = float(m_match.group(1))
                        except:
                            pass
                
                if not metros:
                    continue
                
                # Título
                titulo_el = card.query_selector("h2, h3")
                titulo = titulo_el.inner_text() if titulo_el else ""
                
                valor_m2 = precio / metros
                if 400 <= valor_m2 <= 3500:
                    props.append({
                        "precio": precio,
                        "m2": metros,
                        "valor_m2": valor_m2,
                        "titulo": titulo[:50]
                    })
            except Exception as e:
                continue
        
        browser.close()
        
        print(f"\nPropiedades extraídas: {len(props)}")
        for p in props[:15]:
            print(f"  {p['titulo'][:45]:45} | {p['m2']:5.0f}m2 | USD {p['precio']:8,.0f} | ${p['valor_m2']:.0f}/m2")
        
        if props:
            prom = sum(p['valor_m2'] for p in props) / len(props)
            print(f"\nPROMEDIO USD/m2: ${prom:.0f}")
        
        return props

if __name__ == "__main__":
    scrapear_zonaprop()
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navegando a Infomapa...")
        await page.goto("http://infomapa.rosario.gov.ar/emapa/mapa.htm")
        await page.wait_for_load_state("networkidle")
        
        print("\nFrames encontrados:")
        for frame in page.frames:
            print(f" - Name: {frame.name}, URL: {frame.url}")
            
        # Intentar encontrar el buscador catastral
        # A veces está en un frame llamado 'busquedas' o similar
        for frame in page.frames:
            content = await frame.content()
            if "Catastrales" in content:
                print(f"\n[!] Encontrado 'Catastrales' en frame: {frame.name}")
                # Imprimir forms en este frame
                forms = await frame.query_selector_all("form")
                for i, form in enumerate(forms):
                    action = await form.get_attribute("action")
                    print(f"    Form {i} Action: {action}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

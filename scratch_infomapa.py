import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Interceptar requests para ver cómo consulta los datos
        requests_intercepted = []
        
        page.on("request", lambda request: requests_intercepted.append(request.url))
        
        print("Navegando a Infomapa...")
        await page.goto("http://infomapa.rosario.gov.ar/")
        await page.wait_for_load_state("networkidle")
        
        print("Abriendo búsquedas...")
        # Intentar clickear "Búsquedas" y luego "Catastrales"
        try:
            await page.click("text=Búsquedas")
            await page.wait_for_timeout(1000)
            await page.click("text=Catastrales")
            await page.wait_for_timeout(1000)
            
            # Llenar datos (ejemplo Sección 01, Manzana 010, Gráfico 01)
            # Necesitamos ver el HTML para los selectores exactos, pero intentaremos interceptar
            # Si no funciona el click, imprimimos los requests generados al cargar
        except Exception as e:
            print(f"Error interactuando: {e}")
        
        print("Requests capturados:")
        for r in requests_intercepted:
            if "servlets" in r or "api" in r:
                print(" ->", r)
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

"""
check_extra_agencies.py
Orquestador principal. Corre el scraper sobre las 50 inmobiliarias extra
con auto-descubrimiento de URLs, fallbacks y reporte final.
"""

import asyncio
import json
from datetime import datetime

from inmobiliarias_extra_v2 import INMOBILIARIAS_EXTRA_V2
from scraper_core import scrape_agency

# ── Config ──────────────────────────────────────────────────────────────────
MAX_CONCURRENT = 5   # Paralelismo: no abusar para no ser bloqueado
MAX_PAGES = 3        # Páginas por inmobiliaria
OUTPUT_FILE = f"resultados_extra_{datetime.now().strftime('%Y%m%d_%H%M')}.json"


async def run_v2_orchestrator():
    seen_urls: set = set()
    all_results: list = []
    report: list = []
    
    # Fix encoding windows
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def run_one(agency: dict):
        async with semaphore:
            print(f"\n{'='*60}")
            print(f"[{agency['nombre']}] -> {agency['list_url']}")
            print(f"{'='*60}")
            try:
                props = await scrape_agency(agency, seen_urls, max_pages=MAX_PAGES)
                all_results.extend(props)
                report.append({
                    "nombre": agency["nombre"],
                    "url": agency["url"],
                    "list_url_used": agency["list_url"],
                    "properties_found": len(props),
                    "status": "ok" if props else "empty",
                    "notes": agency.get("notes", ""),
                })
            except Exception as e:
                print(f"  [Error] en {agency['nombre']}: {e}")
                report.append({
                    "nombre": agency["nombre"],
                    "url": agency["url"],
                    "list_url_used": agency["list_url"],
                    "properties_found": 0,
                    "status": f"error: {e}",
                })

    tasks = [run_one(ag) for ag in INMOBILIARIAS_EXTRA_V2]
    await asyncio.gather(*tasks)

    # ── Guardar resultados ────────────────────────────────────────────────
    output = {
        "generated_at": datetime.now().isoformat(),
        "total_properties": len(all_results),
        "agencies_processed": len(report),
        "agencies_with_results": sum(1 for r in report if r["properties_found"] > 0),
        "report": sorted(report, key=lambda x: x["properties_found"], reverse=True),
        "properties": all_results,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # ── Resumen en consola ────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN FINAL")
    print(f"{'='*60}")
    print(f"  Propiedades totales  : {len(all_results)}")
    print(f"  Agencias procesadas  : {len(report)}")
    print(f"  Con resultados       : {sum(1 for r in report if r['properties_found'] > 0)}")
    print(f"  Sin resultados       : {sum(1 for r in report if r['properties_found'] == 0)}")
    print(f"\n  Top 10 inmobiliarias:")
    for r in sorted(report, key=lambda x: x["properties_found"], reverse=True)[:10]:
        icon = "[OK]" if r["properties_found"] > 0 else "[X]"
        print(f"  {icon} {r['nombre']:40s} {r['properties_found']:>4} props")
    print(f"\n  Guardado en: {OUTPUT_FILE}")
    return all_results

if __name__ == "__main__":
    asyncio.run(run_v2_orchestrator())
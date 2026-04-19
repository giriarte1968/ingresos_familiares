"""
Test individual de scrapers - Para debuggear cada scraper
Ejecutar: python test_scrapers_debug.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.motor_vpp_core import (
    scrapear_argenprop, 
    scrapear_ttl, 
    scrapear_lacapital, 
    scrapear_zonaprop,
    scrapear_agencias_batch
)

import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_scraper(name, func, *args):
    print(f"\n{'='*60}")
    print(f"TESTEANDO: {name}")
    print(f"{'='*60}")
    try:
        result = func(*args)
        print(f"RESULTADO: {len(result)} propiedades")
        if result:
            print(f"Primera propiedad: {result[0]}")
        return result
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return []

print("TEST DE SCRAPERS INDIVIDUALES")
print("="*60)

# Test 1: Argenprop
props_argen = test_scraper("Argenprop Venta", scrapear_argenprop, "venta")

# Test 2: TTL
props_ttl = test_scraper("TTL Venta", scrapear_ttl, "venta")

# Test 3: La Capital
props_lc = test_scraper("La Capital Venta", scrapear_lacapital, "venta")

# Test 4: Zonaprop
props_zp = test_scraper("Zonaprop", scrapear_zonaprop)

# Test 5: Agencias
props_age = test_scraper("Agencias Batch", scrapear_agencias_batch, "venta")

# Resumen
print(f"\n{'='*60}")
print("RESUMEN TOTAL")
print(f"{'='*60}")
print(f"Argenprop: {len(props_argen)} props")
print(f"TTL: {len(props_ttl)} props")
print(f"La Capital: {len(props_lc)} props")
print(f"Zonaprop: {len(props_zp)} props")
print(f"Agencias: {len(props_age)} props")
print(f"TOTAL: {len(props_argen) + len(props_ttl) + len(props_lc) + len(props_zp) + len(props_age)} props")

# Fuentes
fuentes = {}
for p in props_argen: fuentes['argenprop'] = fuentes.get('argenprop', 0) + 1
for p in props_ttl: fuentes['ttl'] = fuentes.get('ttl', 0) + 1
for p in props_lc: fuentes['lacapital'] = fuentes.get('lacapital', 0) + 1
for p in props_zp: fuentes['zonaprop'] = fuentes.get('zonaprop', 0) + 1
for p in props_age: fuentes['agencias'] = fuentes.get('agencias', 0) + 1

print(f"\nFuentes: {fuentes}")
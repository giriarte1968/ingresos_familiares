#!/usr/bin/env python3
"""
Performance checker — mide cold-start de imports clave.

Uso: python scripts/check_performance.py

Retorna exit code 0 si todo está dentro de umbrales, 1 si no.
"""
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

UMBRALES = {
    "import_mercado_inmobiliario": 800,
    "import_location_engine": 300,
}


def main():
    all_ok = True

    # Capturar módulos precargados antes de importar proyecto
    mods_pre = set(sys.modules.keys())

    # ─── 1. Import parsers.mercado_inmobiliario ───
    t0 = time.perf_counter()
    import parsers.mercado_inmobiliario
    t = (time.perf_counter() - t0) * 1000
    ok = t <= UMBRALES["import_mercado_inmobiliario"]
    print(f"  import parsers.mercado_inmobiliario: {t:.0f}ms {'OK' if ok else 'FAIL'} (max {UMBRALES['import_mercado_inmobiliario']}ms)")
    all_ok &= ok

    # ─── 2. Import parsers.location_engine ───
    t0 = time.perf_counter()
    import parsers.location_engine
    t = (time.perf_counter() - t0) * 1000
    ok = t <= UMBRALES["import_location_engine"]
    print(f"  import parsers.location_engine: {t:.0f}ms {'OK' if ok else 'FAIL'} (max {UMBRALES['import_location_engine']}ms)")
    all_ok &= ok

    # ─── 3. Verificar que nuestras importaciones no trajeron numpy ───
    mods_nuevos = set(sys.modules.keys()) - mods_pre
    if 'numpy' in mods_nuevos:
        print(f"  [FAIL] numpy fue importado indirectamente por el proyecto")
        all_ok = False
    else:
        print(f"  numpy no importado (OK)")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())

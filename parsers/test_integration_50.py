import sys
import os
import logging

# Asegurar que el entorno reconozca las rutas del proyecto
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.motor_vpp_core import actualizar_mercado_vpp_full

if __name__ == "__main__":
    print("==================================================")
    print("INICIANDO PRUEBA DE INTEGRACIÓN VPP (50 Inmobiliarias)")
    print("==================================================")
    # Ejecutamos la función core completada
    actualizar_mercado_vpp_full()
    print("==================================================")
    print("PRUEBA FINALIZADA - Revisa cache_scraping.json")
    print("==================================================")

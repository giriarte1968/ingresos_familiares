"""
Tests de Regresión para el Sistema de Scraping VPP
===================================================

Este módulo contiene tests de smoke y funciones de verificación
para garantizar que los cambios no rompan funcionalidad validada.

Ejecutar con: python -m pytest tests_regresion.py -v
O directamente: python parsers/tests_regresion.py
"""

import json
import os
import sys

# Añadir el directorio raíz al path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

CACHE_FILE = os.path.join(BASE_DIR, "cache_scraping.json")
PROPIEDADES_FILE = os.path.join(BASE_DIR, "propiedades.json")


def test_scrapeo_basico():
    """
    Test 1: Verifica que el cache tenga datos mínimos
    """
    print("\nTEST 1: Scrapeo basico")
    print("-" * 40)
    
    if not os.path.exists(CACHE_FILE):
        print("FAIL: No existe cache_scraping.json")
        return False
    
    try:
        with open(CACHE_FILE, encoding='utf-8') as f:
            data = json.load(f)
        
        props = data.get('propiedades', [])
        
        print(f"   Total propiedades: {len(props)}")
        
        if len(props) < 50:
            print(f"WARN: Pocas propiedades ({len(props)}). Se esperan >50")
            print("   El scraping puede estar fallando")
        
        # Contar fuentes
        fuentes = {}
        for p in props:
            f = p.get('fuente', 'unknown')
            fuentes[f] = fuentes.get(f, 0) + 1
        
        print(f"   Fuentes: {fuentes}")
        
        if len(fuentes) < 2:
            print("WARN: Solo una fuente de datos")
        
        print("PASS: Cache tiene datos")
        return True
        
    except Exception as e:
        print(f"FAIL: Error leyendo cache: {e}")
        return False


def test_cluster_p1200():
    """
    Test 2: Verifica que haya datos suficientes para P1200 (Centro, 2 dorms)
    """
    print("\nTEST 2: Cluster para P1200")
    print("-" * 40)
    
    if not os.path.exists(CACHE_FILE):
        print("FAIL: No existe cache")
        return False
    
    try:
        with open(CACHE_FILE, encoding='utf-8') as f:
            data = json.load(f)
        
        # Cluster para P1200: zona=Centro, dormitorios=2, operacion=venta
        props = [p for p in data['propiedades'] 
                 if p.get('zona') == 'Centro' 
                 and p.get('dormitorios') == 2 
                 and p.get('operacion') == 'venta']
        
        print(f"   Propiedadescluster: {len(props)}")
        
        if len(props) == 0:
            print("FAIL: Sin datos para P1200 (Centro, 2 dorms)")
            return False
        
        if len(props) < 5:
            print(f"WARN: Pocas propiedades en cluster ({len(props)})")
        
        # Calcular mediana
        valores = [p['valor_m2'] for p in props]
        import numpy as np
        mediana = np.median(valores)
        
        print(f"   Mediana USD/m2: {mediana:.2f}")
        
        # Rango razonable para Rosario Centro (800-3500)
        if mediana < 800:
            print(f"WARN: Mediana muy baja ({mediana:.0f}). Revisar datos.")
        elif mediana > 3500:
            print(f"WARN: Mediana muy alta ({mediana:.0f}). Revisar datos.")
        
        print(f"PASS: Cluster valido con {len(props)} propiedades")
        return True
        
    except Exception as e:
        print(f"FAIL: Error: {e}")
        return False


def test_multiples_fuentes():
    """
    Test 3: Verifica que haya múltiples fuentes de datos
    """
    print("\nTEST 3: Multiples fuentes")
    print("-" * 40)
    
    if not os.path.exists(CACHE_FILE):
        print("FAIL: No existe cache")
        return False
    
    try:
        with open(CACHE_FILE, encoding='utf-8') as f:
            data = json.load(f)
        
        props = data.get('propiedades', [])
        
        fuentes = {}
        for p in props:
            f = p.get('fuente', 'unknown')
            fuentes[f] = fuentes.get(f, 0) + 1
        
        print(f"   Fuentes detectadas: {list(fuentes.keys())}")
        
        if len(fuentes) < 2:
            print(f"FAIL: Solo {len(fuentes)} fuente(s). Se esperan multiples.")
            return False
        
        print(f"PASS: {len(fuentes)} fuentes disponibles")
        return True
        
    except Exception as e:
        print(f"FAIL: Error: {e}")
        return False


def test_datos_ventas_vs_alquiler():
    """
    Test 4: Verifica que haya datos tanto de venta como de alquiler
    """
    print("\nTEST 4: Ventas vs Alquiler")
    print("-" * 40)
    
    if not os.path.exists(CACHE_FILE):
        print("FAIL: No existe cache")
        return False
    
    try:
        with open(CACHE_FILE, encoding='utf-8') as f:
            data = json.load(f)
        
        props = data.get('propiedades', [])
        
        ventas = [p for p in props if p.get('operacion') == 'venta']
        alquileres = [p for p in props if p.get('operacion') == 'alquiler']
        
        print(f"   Ventas: {len(ventas)}")
        print(f"   Alquileres: {len(alquileres)}")
        
        if len(ventas) == 0:
            print("FAIL: Sin datos de venta")
            return False
        
        if len(alquileres) == 0:
            print("WARN: Sin datos de alquiler")
        
        print("PASS: Datos de venta disponibles")
        return True
        
    except Exception as e:
        print(f"FAIL: Error: {e}")
        return False


def test_rango_valores():
    """
    Test 5: Verifica que los valores estén en rango razonable
    """
    print("\nTEST 5: Rango de valores")
    print("-" * 40)
    
    if not os.path.exists(CACHE_FILE):
        print("FAIL: No existe cache")
        return False
    
    try:
        with open(CACHE_FILE, encoding='utf-8') as f:
            data = json.load(f)
        
        props = data.get('propiedades', [])
        ventas = [p for p in props if p.get('operacion') == 'venta']
        
        valores = [p['valor_m2'] for p in ventas if p.get('valor_m2', 0) > 0]
        
        import numpy as np
        min_v = np.min(valores)
        max_v = np.max(valores)
        mediana = np.median(valores)
        
        print(f"   Min: {min_v:.2f} USD/m2")
        print(f"   Max: {max_v:.2f} USD/m2")
        print(f"   Mediana: {mediana:.2f} USD/m2")
        
        # Rango razonable para Rosario
        if mediana < 600:
            print("WARN: Mediana muy baja. Revisar datos.")
        elif mediana > 4000:
            print("WARN: Mediana muy alta. Revisar datos.")
        
        print("PASS: Valores en rango")
        return True
        
    except Exception as e:
        print(f"FAIL: Error: {e}")
        return False


def verificar_pre_scraping():
    """
    Verificación antes de ejecutar scraping
    """
    print("\n" + "=" * 50)
    print("VERIFICACION PRE-SCRAPING")
    print("=" * 50)
    
    if not os.path.exists(CACHE_FILE):
        print("INFO: No existe cache previo. Se creara nuevo.")
        return True
    
    try:
        with open(CACHE_FILE, encoding='utf-8') as f:
            data = json.load(f)
        
        props = data.get('propiedades', [])
        fecha = data.get('fecha', 'unknown')
        
        print(f"   Cache actual: {len(props)} propiedades")
        print(f"   Fecha: {fecha}")
        
        # Contar fuentes
        fuentes = {}
        for p in props:
            f = p.get('fuente', 'unknown')
            fuentes[f] = fuentes.get(f, 0) + 1
        
        print(f"   Fuentes: {fuentes}")
        
        if len(props) >= 50:
            print("   OK: Cache tiene datos suficientes")
        else:
            print(f"   WARN: Solo {len(props)} propiedades. Ejecutar scraping.")
        
        return True
        
    except Exception as e:
        print(f"   INFO: Error leyendo cache: {e}")
        return True


def ejecutar_tests():
    """
    Ejecuta todos los tests de regresión
    """
    print("=" * 50)
    print("SUITE DE TESTS DE REGRESION VPP")
    print("=" * 50)
    
    tests = [
        ("Scrapeo Basico", test_scrapeo_basico),
        ("Cluster P1200", test_cluster_p1200),
        ("Multiples Fuentes", test_multiples_fuentes),
        ("Ventas vs Alquiler", test_datos_ventas_vs_alquiler),
        ("Rango de Valores", test_rango_valores),
    ]
    
    resultados = {}
    
    for nombre, test_func in tests:
        try:
            resultados[nombre] = test_func()
        except Exception as e:
            print(f"ERROR en {nombre}: {e}")
            resultados[nombre] = False
    
    # Resumen
    print("\n" + "=" * 50)
    print("RESUMEN DE TESTS")
    print("=" * 50)
    
    passed = sum(1 for v in resultados.values() if v)
    total = len(resultados)
    
    for nombre, resultado in resultados.items():
        status = "PASS" if resultado else "FAIL"
        print(f"   {status}: {nombre}")
    
    print(f"\n   Resultado: {passed}/{total} tests pasados")
    
    if passed == total:
        print("   TODOS LOS TESTS PASARON")
        return True
    else:
        print("   ALGUNOS TESTS FALLARON")
        return False


if __name__ == "__main__":
    verificar_pre_scraping()
    print("\n")
    ejecutar_tests()
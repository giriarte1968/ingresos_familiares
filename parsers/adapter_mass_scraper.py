import sys
import os
import logging

# Configurar rutas para permitir importaciones desde la carpeta de scrapers nuevos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPERS_NEW_DIR = os.path.join(BASE_DIR, "pure-python-code-request")

def get_mass_properties(max_pages=3):
    """
    Ejecuta el motor de 50 inmobiliarias y retorna las propiedades para el VPP.
    """
    logger_vpp = logging.getLogger("motor_vpp")
    logger_vpp.info("Iniciando Adaptador de Scraping Masivo (50 fuentes)...")
    
    # 1. Agregar ruta al path temporalmente si no existe
    if SCRAPERS_NEW_DIR not in sys.path:
        sys.path.insert(0, SCRAPERS_NEW_DIR)
    
    try:
        # Importar dinámicamente para evitar errores si la carpeta no existe
        from main import ScrapingOrchestrator
        from config import INMOBILIARIAS
        
        # 2. Configurar y Ejecutar Orquestador
        # Usamos concurrent=True y max_workers=3 para no saturar el sistema
        orchestrator = ScrapingOrchestrator()
        
        # LOTE 1: Inmobiliarias originales (V1)
        active_inmos = [i for i in INMOBILIARIAS if i.get("activo", True) and i.get("nombre") != "INMOBILIARIAS_EXTRA"] 
        
        results_v1 = orchestrator.run(
            inmobiliarias=active_inmos,
            max_pages_per_site=max_pages,
            concurrent=True,
            max_workers=3,
            save_individual=False,
            save_combined=False
        )
        raw_props_v1 = orchestrator.all_properties
        logger_vpp.info(f"Adaptador Lote 1: Se obtuvieron {len(raw_props_v1)} propiedades brutas.")

        # LOTE 2: Inmobiliarias Extra Robustas (V2 - Asincrónico)
        raw_props_v2 = []
        try:
            from check_extra_agencies_v2 import run_v2_orchestrator
            import asyncio
            logger_vpp.info("Adaptador Lote 2: Iniciando motor asincrónico V2 para las 46 inmobiliarias extra...")
            # run_v2_orchestrator corre de forma aislada y retorna list de dicts
            raw_props_v2 = asyncio.run(run_v2_orchestrator())
            logger_vpp.info(f"Adaptador Lote 2: Se obtuvieron {len(raw_props_v2)} propiedades brutas.")
        except Exception as e2:
            logger_vpp.error(f"Error ejecutando Orquestador V2: {e2}")

        # Combincación de resultados
        raw_props = raw_props_v1 + raw_props_v2
        
        # 3. Mapear a esquema VPP core
        mapped_props = []
        for p in raw_props:
            try:
                precio = float(p.get('precio') or p.get('prices_found', [0])[0] if isinstance(p.get('prices_found'), list) and p.get('prices_found') else p.get('precio', 0))
                
                # Normalizar precio regex
                if isinstance(precio, str):
                    import re
                    precio_str = re.sub(r'[^\d]', '', precio)
                    precio = float(precio_str) if precio_str else 0

                m2_val = p.get('superficie_total') or p.get('superficie_cubierta')
                if not m2_val and isinstance(p.get('surfaces_m2'), list) and p.get('surfaces_m2'):
                    import re
                    m_str = re.sub(r'[^\d]', '', p.get('surfaces_m2')[0])
                    m2_val = float(m_str) if m_str else 0
                
                m2 = float(m2_val or 0)
                
                if precio > 0 and m2 > 0:
                    # Usar operacion detectada por scraper, o inferir de precios
                    operacion_detectada = p.get('operacion')
                    if operacion_detectada:
                        operacion = operacion_detectada
                    else:
                        # Inferir: precios muy bajos en ARS = alquiler
                        moneda = p.get('moneda', 'USD')
                        if moneda == 'ARS' and precio < 500000:
                            operacion = 'alquiler'
                        else:
                            operacion = 'venta'
                    
                    # Asignar moneda basándose en operacion
                    moneda = 'ARS' if operacion == 'alquiler' else 'USD'
                    
                    # Filtro absoluto para VENTAS USD [400, 5000]
                    if operacion == 'venta' and (precio/m2 < 400 or precio/m2 > 5000):
                        continue

                    mapped_props.append({
                        "precio": precio,
                        "m2": m2,
                        "dormitorios": int(p.get('dormitorios') or 1),
                        "valor_m2": precio / m2,
                        "direccion": p.get('ubicacion', p.get('url', 'Rosario, SF')),
                        "fuente": p.get('inmobiliaria') or p.get('fuente', 'masivo_50'),
                        "operacion": operacion,
                        "moneda": moneda,
                        "anio_construccion": p.get('anio_construccion'),
                        "zona": "Rosario"
                    })
            except Exception as e:
                continue
        
        logger_vpp.info(f"Adaptador: {len(mapped_props)} propiedades mapeadas correctamente al esquema VPP.")
        return mapped_props

    except Exception as e:
        logger_vpp.error(f"Error en Adaptador Masivo: {e}")
        return []
    finally:
        # Limpiar path (opcional, pero buena práctica)
        if SCRAPERS_NEW_DIR in sys.path:
            sys.path.remove(SCRAPERS_NEW_DIR)

if __name__ == "__main__":
    # Prueba rápida unitaria
    logging.basicConfig(level=logging.INFO)
    props = get_mass_properties(max_pages=1)
    print(f"Test: {len(props)} propiedades obtenidas.")

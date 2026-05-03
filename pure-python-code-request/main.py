"""
Sistema de Scraping Inmobiliario Rosario - Main
================================================
Punto de entrada principal para ejecutar el scraping.
Coordina la extracción de las 50 inmobiliarias top.
"""

import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import INMOBILIARIAS, SCRAPING_CONFIG, CARACTERISTICAS
from scraper import InmobiliariaScraper, RequestsScraper, SeleniumScraper
from utils import (
    logger, stats, save_json, load_json, generate_filename,
    ensure_dir, timing
)


# =============================================================================
# ORQUESTADOR PRINCIPAL
# =============================================================================

class ScrapingOrchestrator:
    """
    Orquestador principal del sistema de scraping.
    Coordina la extracción de múltiples inmobiliarias.
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or SCRAPING_CONFIG
        self.output_dir = ensure_dir(self.config["output_dir"])
        self.all_properties = []
        self.seen_urls = set()  # Seguimiento de duplicados
        self.stats_per_inmobiliaria = {}
        self.errors = []
    
    @timing
    def run(self, 
            inmobiliarias: List[Dict] = None,
            max_pages_per_site: int = 5,
            use_selenium: bool = False,
            concurrent: bool = True,
            max_workers: int = 3,
            save_individual: bool = True,
            save_combined: bool = True) -> Dict:
        """
        Ejecuta el scraping de todas las inmobiliarias.
        
        Args:
            inmobiliarias: Lista de inmobiliarias a scrapear
            max_pages_per_site: Máximo de páginas por sitio
            use_selenium: Si usar Selenium para JavaScript
            concurrent: Si ejecutar en paralelo
            max_workers: Número de workers concurrentes
            save_individual: Si guardar JSON individual por inmobiliaria
            save_combined: Si guardar JSON combinado
        
        Returns:
            Dict con resumen de la ejecución
        """
        if inmobiliarias is None:
            inmobiliarias = [i for i in INMOBILIARIAS if i.get("activo", True)]
        
        logger.info(f"\n{'#'*60}")
        logger.info(f"# SISTEMA DE SCRAPING INMOBILIARIO ROSARIO")
        logger.info(f"# Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"# Inmobiliarias a procesar: {len(inmobiliarias)}")
        logger.info(f"{'#'*60}\n")
        
        stats.reset()
        start_time = time.time()
        
        if concurrent:
            self._run_concurrent(inmobiliarias, max_pages_per_site, 
                                use_selenium, max_workers, save_individual)
        else:
            self._run_sequential(inmobiliarias, max_pages_per_site,
                                use_selenium, save_individual)
        
        # Guardar resultados combinados
        if save_combined:
            combined_file = self._save_combined()
        
        elapsed = time.time() - start_time
        
        # Generar resumen
        summary = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "inmobiliarias_processed": len(inmobiliarias),
            "total_properties": len(self.all_properties),
            "errors_count": len(self.errors),
            "errors": self.errors,
            "stats": stats.to_dict()
        }
        
        # Guardar resumen
        self._save_summary(summary)
        
        logger.info(f"\n{'#'*60}")
        logger.info(f"# SCRAPING COMPLETADO")
        logger.info(f"# Tiempo total: {elapsed:.2f} segundos")
        logger.info(f"# Propiedades totales: {len(self.all_properties)}")
        logger.info(f"# Errores: {len(self.errors)}")
        logger.info(f"{'#'*60}\n")
        
        return summary
    
    def _run_sequential(self, inmobiliarias: List[Dict], 
                        max_pages: int, use_selenium: bool,
                        save_individual: bool):
        """Ejecución secuencial (una por una)."""
        for i, inmobiliaria in enumerate(inmobiliarias, 1):
            logger.info(f"\n[{i}/{len(inmobiliarias)}] Procesando: {inmobiliaria['nombre']}")
            
            try:
                scraper = InmobiliariaScraper(inmobiliaria, self.config)
                properties = scraper.scrape(max_pages, use_selenium)
                scraper.close()
                
                if properties:
                    # Filtrar duplicados
                    unique_properties = [p for p in properties if p.get('url_propiedad') not in self.seen_urls]
                    for p in unique_properties:
                        self.seen_urls.add(p['url_propiedad'])
                    
                    self.all_properties.extend(unique_properties)
                    self.stats_per_inmobiliaria[inmobiliaria['nombre']] = len(unique_properties)
                    stats.save_property()
                    
                    if save_individual:
                        self._save_inmobiliaria(inmobiliaria['nombre'], properties)
                else:
                    self.stats_per_inmobiliaria[inmobiliaria['nombre']] = 0
                
            except Exception as e:
                error_msg = f"Error en {inmobiliaria['nombre']}: {str(e)}"
                logger.error(error_msg)
                self.errors.append({
                    "inmobiliaria": inmobiliaria['nombre'],
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                stats.add_error(str(e), inmobiliaria['nombre'])
    
    def _run_concurrent(self, inmobiliarias: List[Dict],
                        max_pages: int, use_selenium: bool,
                        max_workers: int, save_individual: bool):
        """Ejecución concurrente con ThreadPoolExecutor."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Crear futures para cada inmobiliaria
            future_to_inmobiliaria = {
                executor.submit(
                    self._scrape_single, 
                    inmobiliaria, 
                    max_pages, 
                    use_selenium,
                    save_individual
                ): inmobiliaria
                for inmobiliaria in inmobiliarias
            }
            
            # Procesar resultados conforme se completan
            for future in as_completed(future_to_inmobiliaria):
                inmobiliaria = future_to_inmobiliaria[future]
                
                try:
                    properties = future.result()
                    if properties:
                        # Filtrar duplicados
                        unique_properties = [p for p in properties if p.get('url_propiedad') not in self.seen_urls]
                        for p in unique_properties:
                            self.seen_urls.add(p['url_propiedad'])
                            
                        self.all_properties.extend(unique_properties)
                        self.stats_per_inmobiliaria[inmobiliaria['nombre']] = len(unique_properties)
                    else:
                        self.stats_per_inmobiliaria[inmobiliaria['nombre']] = 0
                        
                except Exception as e:
                    error_msg = f"Error en {inmobiliaria['nombre']}: {str(e)}"
                    logger.error(error_msg)
                    self.errors.append({
                        "inmobiliaria": inmobiliaria['nombre'],
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
    
    def _scrape_single(self, inmobiliaria: Dict, max_pages: int,
                       use_selenium: bool, save_individual: bool) -> List[Dict]:
        """Scrapea una sola inmobiliaria (para ejecución concurrente)."""
        logger.info(f"Procesando: {inmobiliaria['nombre']}")
        
        scraper = InmobiliariaScraper(inmobiliaria, self.config)
        properties = scraper.scrape(max_pages, use_selenium)
        scraper.close()
        
        if properties and save_individual:
            self._save_inmobiliaria(inmobiliaria['nombre'], properties)
        
        return properties
    
    def _save_inmobiliaria(self, nombre: str, properties: List[Dict]) -> str:
        """Guarda propiedades de una inmobiliaria en JSON."""
        # Normalizar nombre para archivo
        filename = f"{nombre.lower().replace(' ', '_').replace('.', '')}.json"
        filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.'))
        
        data = {
            "inmobiliaria": nombre,
            "fecha_extraccion": datetime.now().isoformat(),
            "total_propiedades": len(properties),
            "propiedades": properties
        }
        
        return save_json(data, filename)
    
    def _save_combined(self) -> str:
        """Guarda todas las propiedades en un JSON combinado."""
        filename = generate_filename("propiedades_rosario", "json")
        
        # Agrupar por inmobiliaria
        by_inmobiliaria = {}
        for prop in self.all_properties:
            fuente = prop.get("fuente", "desconocido")
            if fuente not in by_inmobiliaria:
                by_inmobiliaria[fuente] = []
            by_inmobiliaria[fuente].append(prop)
        
        data = {
            "titulo": "Propiedades Inmobiliarias Rosario",
            "fecha_extraccion": datetime.now().isoformat(),
            "total_propiedades": len(self.all_properties),
            "inmobiliarias_incluidas": list(by_inmobiliaria.keys()),
            "propiedades_por_inmobiliaria": {
                k: len(v) for k, v in by_inmobiliaria.items()
            },
            "propiedades": self.all_properties
        }
        
        return save_json(data, filename)
    
    def _save_summary(self, summary: Dict) -> str:
        """Guarda resumen de la ejecución."""
        filename = generate_filename("resumen_scraping", "json")
        return save_json(summary, filename)
    
    def get_properties_dataframe(self):
        """
        Convierte propiedades a DataFrame de pandas si está disponible.
        
        Returns:
            DataFrame con las propiedades o None
        """
        try:
            import pandas as pd
            return pd.DataFrame(self.all_properties)
        except ImportError:
            logger.warning("pandas no está instalado")
            return None


# =============================================================================
# FUNCIONES DE UTILIDAD PARA STREAMLIT
# =============================================================================

def scrape_single_inmobiliaria(nombre: str, max_pages: int = 5,
                               use_selenium: bool = False) -> Dict:
    """
    Scrapea una sola inmobiliaria por nombre.
    Útil para llamadas desde Streamlit.
    
    Args:
        nombre: Nombre de la inmobiliaria
        max_pages: Máximo de páginas
        use_selenium: Si usar Selenium
    
    Returns:
        Dict con resultados
    """
    # Buscar inmobiliaria
    inmobiliaria = next(
        (i for i in INMOBILIARIAS if i['nombre'].lower() == nombre.lower()),
        None
    )
    
    if not inmobiliaria:
        return {"error": f"Inmobiliaria '{nombre}' no encontrada"}
    
    scraper = InmobiliariaScraper(inmobiliaria)
    properties = scraper.scrape(max_pages, use_selenium)
    scraper.close()
    
    return {
        "inmobiliaria": nombre,
        "propiedades": properties,
        "total": len(properties)
    }


def get_available_inmobiliarias() -> List[str]:
    """Retorna lista de nombres de inmobiliarias disponibles."""
    return [i['nombre'] for i in INMOBILIARIAS if i.get("activo", True)]


def load_latest_results() -> Optional[Dict]:
    """Carga los resultados más recientes."""
    output_dir = Path(SCRAPING_CONFIG["output_dir"])
    
    if not output_dir.exists():
        return None
    
    # Buscar archivos de propiedades
    files = list(output_dir.glob("propiedades_rosario_*.json"))
    
    if not files:
        return None
    
    # Ordenar por fecha de modificación
    latest = max(files, key=lambda f: f.stat().st_mtime)
    
    return load_json(str(latest))


def get_stats_summary() -> Dict:
    """Retorna estadísticas del último scraping."""
    return stats.to_dict()


# =============================================================================
# CLI
# =============================================================================

def parse_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Sistema de Scraping Inmobiliario Rosario"
    )
    
    parser.add_argument(
        "-n", "--num-inmobiliarias",
        type=int,
        default=50,
        help="Número de inmobiliarias a procesar (default: 50)"
    )
    
    parser.add_argument(
        "-p", "--max-pages",
        type=int,
        default=5,
        help="Máximo de páginas por inmobiliaria (default: 5)"
    )
    
    parser.add_argument(
        "-s", "--selenium",
        action="store_true",
        help="Usar Selenium para sitios con JavaScript"
    )
    
    parser.add_argument(
        "-c", "--concurrent",
        action="store_true",
        default=True,
        help="Ejecutar en paralelo (default: True)"
    )
    
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=3,
        help="Número de workers concurrentes (default: 3)"
    )
    
    parser.add_argument(
        "-i", "--inmobiliaria",
        type=str,
        help="Scrapear solo una inmobiliaria específica por nombre"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="resultados",
        help="Directorio de salida (default: resultados)"
    )
    
    return parser.parse_args()


def main():
    """Función principal."""
    args = parse_args()
    
    # Configurar output
    SCRAPING_CONFIG["output_dir"] = args.output
    
    # Seleccionar inmobiliarias
    if args.inmobiliaria:
        inmobiliarias = [
            i for i in INMOBILIARIAS 
            if i['nombre'].lower() == args.inmobiliaria.lower()
        ]
        if not inmobiliarias:
            logger.error(f"Inmobiliaria '{args.inmobiliaria}' no encontrada")
            sys.exit(1)
    else:
        activas = [i for i in INMOBILIARIAS if i.get("activo", True)]
        inmobiliarias = activas[:args.num_inmobiliarias]
    
    # Crear orquestador y ejecutar
    orchestrator = ScrapingOrchestrator(SCRAPING_CONFIG)
    
    summary = orchestrator.run(
        inmobiliarias=inmobiliarias,
        max_pages_per_site=args.max_pages,
        use_selenium=args.selenium,
        concurrent=args.concurrent,
        max_workers=args.workers
    )
    
    print(f"\nScraping completado!")
    print(f"{'='*40}")
    print(f"Propiedades Únicas: {len(summary['all_properties'] if 'all_properties' in summary else summary.get('total_properties', 0))}")
    print(f"Tiempo Total: {summary['elapsed_seconds']}s")
    print(f"Errores: {summary['errors_count']}")
    print(f"{'='*40}")
    print(f"Resumen por Inmobiliaria:")
    
    # En el resumen que devuelve run(), vamos a añadir el desglose
    stats_p = getattr(orchestrator, 'stats_per_inmobiliaria', {})
    for nombre, cant in sorted(stats_p.items(), key=lambda x: x[1], reverse=True):
        print(f" - {nombre}: {cant} propiedades")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

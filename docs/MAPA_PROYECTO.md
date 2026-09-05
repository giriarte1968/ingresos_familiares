# 🗺️ MAPA DEL PROYECTO — Valu AVM ROSARIO

Este documento actúa como la guía técnica actualizada de la arquitectura y archivos del proyecto.

---

## 1. NÚCLEO DE LA APLICACIÓN (VALU)

| Archivo | Responsabilidad |
|---------|-----------------|
| `valu.py` | **Punto de entrada principal (Valu).** Router de navegación, landing page, portfolio y máquina de estados de reingreso. |
| `valu_detail_sections.py` | Secciones detalladas de UI: Cards, tabla de comparables, sliders, botón **Reporte TTL**. |
| `valu_forms.py` | Formularios de carga y modificación de atributos físicos (`tipo_balcon: terraza_servicio`). |
| `valu_design.py` | Estilos visuales CSS y componentes de diseño. |
| `gen_pdf_ttl.py` | Módulo de compilación y generación de PDF Reporte TTL mediante Playwright. |
| `parsers/mercado_inmobiliario.py` | **Motor AVM v7.** Selección Natural ($D \pm 1$), cálculo de `factor_escalera` (edificios sin ascensor) y razonamiento narrativo. |
| `parsers/motor_vpp_core.py` | Orchestrator `valuar_con_cache`, integración y profiler. |

---

## 2. PERSISTENCIA Y DATOS

| Archivo | Contenido |
|---------|-----------|
| `propiedades.json` | Base de datos principal de inmuebles y sus valuaciones oficiales en `_ultima_valuacion`. |
| `plantilla_propiedades.xlsx` | Excel maestro con los datos crudos de propiedades y desplegables sincronizados. |
| `data/valuaciones_cache.json` | Caché de ejecuciones del motor AVM. |
| `cache_scraping.json` | Base de datos de más de 20.000 muestras de mercado. |
| `cache_scraping_up_tokko.json` | Inventario Venta de UP! Inmobiliaria (Tokko), filtrado Gran Rosario (191 propiedades: `id_tokko`, precios, m², código ULA/UAP, coords). |

---

## 2b. SCRIPTS DE SCRAPING (GRAN ROSARIO)

| Script | Responsabilidad |
|--------|-----------------|
| `scripts/scraper_up_tokko.py` | Scraper de fichas UP! Inmobiliaria (`upinmobiliaria.com.ar`, template Tokko). Enumera `/Venta` + subcategorías, pagina AJAX, captura markers con coords, filtra Gran Rosario (bbox + localidades) y baja fichas `/p/{TokkoId}-{slug}` en paralelo. Salida `cache_scraping_up_tokko.json`. |
| `scripts/gen_gran_rosario_enriquecido.py` | Lista de localidades del Gran Rosario (fuente de `GRAN_ROSARIO_LOCALIDADES`). |
| `scripts/scraper_gran_rosario.py` | Bounding boxes `GRAN_ROSARIO_BBOX` / `LOCALIDADES_BBOX` usados por el scraper de UP!. |

---

## 3. SUITE DE PRUEBAS

* `tests/test_regression.py`: Suite de regresión del motor AVM y reglas hedónicas.
* `tests/test_ui_state_machine.py`: Pruebas de integración de la máquina de estados UI, persistencia y ciclo de reingreso.

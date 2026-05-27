# 🗺️ MAPA DEL PROYECTO — AVM ROSARIO

Este documento sirve como guía para que cualquier IA o desarrollador entienda la organización de los más de 150 archivos del proyecto sin tener que explorarlos uno por uno.

---

## 🛑 REGLAS Y PROTOCOLOS CRÍTICOS

Antes de tocar el código, es OBLIGATORIO consultar:
- [**Reglas de Oro**](file:///c:/Users/Gustavo/ingresos_familiares_st/docs/MEMORIA_PROYECTO.md#L33): 10 reglas inamovibles de lógica de negocio.
- [**Protocolo IA Programadora**](file:///c:/Users/Gustavo/ingresos_familiares_st/docs/MEMORIA_PROYECTO.md#L460): Pasos obligatorios para cualquier IA antes de editar.

---

## 1. NÚCLEO DEL SISTEMA (CORE)

Ubicación de la lógica principal de valuación y procesamiento.

| Archivo | Responsabilidad |
|---------|-----------------|
| `valu.py` | **Punto de entrada principal (Valu).** Aplicación moderna enfocada 100% en propiedades. |
| `valu_design.py` | Sistema de diseño premium, CSS estilo Zillow y componentes HTML. |
| `valu_forms.py` | Formularios modulares para la carga de datos de propiedades. |
| `app.py` | Punto de entrada **Legacy**. Gestión financiera e ingresos familiares. |
| `parsers/mercado_inmobiliario.py` | **El cerebro.** Motor AVM (Valuación Automatizada) y lógica de clustering. |
| `parsers/motor_vpp_core.py` | Utilidades core, integración con Binance (USDT/ARS). |
| `parsers/location_engine.py` | Motor geoespacial. Cálculo de distancias y pesos IDW. |
| `parsers/nlp_inmobiliario.py` | Análisis de descripciones libres para extracción de features. |
| `parsers/valuacion_helpers.py` | Funciones puras desacopladas del motor: `calcular_rango_venta()` (única fuente de rango), `procesar_alquiler()`, `ensamblar_metadata_resolucion()`. |
| `parsers/cluster_filters.py` | 7 helpers puros con 34 tests: filtro geográfico, percentil discreto, blend alpha, regla de percentil por edad. |
| `parsers/geocoder.py` | Integración con servicios de geocodificación. |

## 2. DATOS Y CONTEXTO (DATA)

Archivos JSON que actúan como base de datos y parámetros de configuración.

| Archivo | Contenido |
|---------|-----------|
| `cache_scraping.json` | ~10.000 propiedades scrapeadas. La fuente de verdad del mercado actual. |
| `barreras_rosario.json` | 751 LineStrings que definen límites urbanos (vías, avenidas, barrios). Incluye Av. Del Valle como barrera blanda desde 2026-05-24. |
| `anclas_rosario.json` | Puntos de referencia de precios manuales (usados como validación o fallback). |
| `comercios_conocidos.json` | Base de datos de POIs para análisis de entorno. |
| `constructoras_rosario.json` | Listado de constructoras para ajustar factor de calidad. |

## 3. SCRIPTS DE AUTOMATIZACIÓN

Scripts para validación y documentación automática.

- `scripts/auto_validate.py`: Valida tests + syntax + imports (ejecutar después de cada cambio).
- `scripts/update_docs.py`: Actualiza documentación .MD (--auto para aplicar cambios).
- `scripts/init_reminder.py`: Recordatorio de flujo de trabajo.
- `scripts/validar_coordenadas.py`: Valida coordenadas de cache contra geocoding textual. Corre bajo demanda.

## 4. MÓDULOS DE EXTRACCIÓN (SCRAPERS)

Scripts encargados de alimentar la caché desde portales inmobiliarios.

- `parsers/deep_scraper.py`: Extracción profunda de detalles.
- `parsers/scraper_propia_fresh.py`: Scraper específico para el portal Propia.
- `parsers/adapter_mass_scraper.py`: Adaptador para múltiples fuentes.

## 5. SISTEMA DE PAGOS Y FINANZAS (EXPENSES LEGACY)

El proyecto comenzó como un gestor de ingresos familiares y conserva módulos de procesamiento de pagos/OCR.

- `parsers/binance_qr.py`: Procesamiento de transacciones Binance.
- `parsers/bybit_qr.py` / `bybit_tarjeta.py`: Procesamiento de Bybit.
- `parsers/icbc.py` / `galicia_excel.py`: Parsers de resúmenes bancarios.
- `subpagos.py`: Lógica de subcategorización de gastos.

## 5. SUITE DE PRUEBAS (TESTS)

**CRÍTICO:** Antes de cualquier cambio, se deben correr estos tests.

- `tests/test_regression.py`: El más importante. Valida que las valuaciones de "Mabel" y "Ayacucho" sigan en rango.
- `parsers/tests_regresion.py`: Tests adicionales de lógica interna.
- `test_*.py` (Raíz): Archivos de prueba específicos para módulos nuevos.

## 6. SCRIPTS EXPERIMENTALES Y DEBUG

Muchos archivos en la raíz son "descartables" o de investigación.
- `check_*.py`: Verificaciones puntuales de datos o geometría.
- `debug_*.py`: Scripts para cazar bugs específicos (ej. `debug_mabel.py`).
- `verify_*.py`: Scripts de validación post-proceso.

---
> [!TIP]
> Si vas a implementar una nueva funcionalidad, busca si ya existe un `test_*.py` similar para usarlo como base.

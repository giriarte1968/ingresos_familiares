# Estado Actual del Sistema VPP (Valuación de Propiedades Personalizada)

Este documento resume el estado actual del motor de scraping y valuación de propiedades en Rosario, integrando las últimas mejoras en analítica de precios, clustering y ROI.

## 1. Módulos de Scraping (V2)

- **Portales Soportados**:
    - **Propia.com.ar**: Extracción completa de datos (precio, m2, operación, coordenadas).
    - **ArgenProp, Zonaprop, La Capital**: Integrados vía cache persistente.
- **Descubrimiento de Agencias**: `buscar_inmobiliarias.py` automatiza la búsqueda de sitios web de inmobiliarias locales para bypass de agregadores.
- **Cache de Datos**: Almacenado en `cache_scraping.json`, centralizando miles de muestras del mercado de Rosario.

## 2. Motor de Valuación (VPP v7.0)

El núcleo del sistema incluye los siguientes componentes:

### Clustering y Base de Precios
- **obtener_mediana_cluster_v2**: Clustering geográfico con radios progresivos (300m → 1500m).
- **Filtrado IQR**: outliers removidos automáticamente (percentiles 15-85 o 25-75).
- **Fecha dinámica**: usa `datetime.now()` por defecto con soporte para `fecha_ref` explícita.
- **Ventana móvil**: 180 días (configurable a 365 si <5 muestras).

### Factores de Ajuste
- **delta_anti**: depreciación por antigüedad (0.6%/año, max -30%).
- **factor_estado**: ajuste por condición (0.85 - 1.15).
- **factor_edificio**: calidad del edificio.
- **Factor Anti-Atenuación**: para propiedades >30 años (P1200 rescue).

### Barreras Geográficas
- **check_barrier_crossing**: diferenciación hard/soft.
  - **hard** (Ferrocarril): weight = 0.20 (80% penalty).
  - **soft** (Avenidas): weight = 0.90 (10% penalty).

### Valuación Híbrida
- Fórmula: `m2_equiv * m2_base * factores * (1 + NLP)`.
- Soporte para NLP con cap 3-5%.
- Cap Rate neto: 3-5% para alquiler.

## 3. Automatización

- **auto_validate.py**: Valida tests + syntax + imports automáticamente.
- **update_docs.py**: Actualiza documentación .MD.
- **Workflow**: código → validate → commit → push.

## 4. Estructura de Archivos
- `parsers/`: Lógica de procesamiento y motores de cálculo.
- `scripts/`: Utilidades de actualización y patching.
- `docs/`: Documentación técnica y funcional.
- `cache_scraping.json`: Base de datos de mercado.

---
**Actualizado por**: opencode (Agente de Mantenimiento)
**Fecha**: 2026-05-05
**Ubicación**: `ingresos_familiares_st/docs/STATUS_ACTUAL.md`

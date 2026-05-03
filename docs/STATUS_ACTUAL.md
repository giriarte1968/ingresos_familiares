# Estado Actual del Sistema VPP (Valuación de Propiedades Personalizada)

Este documento resume el estado actual del motor de scraping y valuación de propiedades en Rosario, integrando las últimas mejoras en analítica de precios, clustering y ROI.

## 1. Módulos de Scraping (V2)

- **Portales Soportados**:
    - **Propia.com.ar**: Extracción completa de datos (precio, m2, operación, coordenadas).
    - **ArgenProp, Zonaprop, La Capital**: Integrados vía cache persistente.
- **Descubrimiento de Agencias**: `buscar_inmobiliarias.py` automatiza la búsqueda de sitios web de inmobiliarias locales para bypass de agregadores.
- **Cache de Datos**: Almacenado en `cache_scraping.json`, centralizando miles de muestras del mercado de Rosario.

## 2. Motor de Valuación (VPP Enriquecido)

El núcleo del sistema ha sido actualizado con los siguientes fixes críticos (v11.2):
- **Clustering IQR**: Filtrado automático de outliers (propiedades con precios m2 fuera de los percentiles 15-85 o 25-75).
- **IDW (Inverse Distance Weighting)**: Ponderación de comparables basada en la proximidad geográfica.
- **Modelo de Ancla Dual**: Uso de precios de referencia estructurales ("Anclas") para estabilizar la valuación.
- **Fix de Antigüedad**: Aplicación del factor de depreciación/apreciación por edad de forma externa a la raíz cuadrada para mayor sensibilidad (20-30% de impacto entre nuevo y antiguo).

## 3. Análisis de Alquileres y ROI

- **Cálculo de Alquiler Estimado**: Basado en comparables de la zona y un ancla algorítmica de 4.5% Cap Rate.
- **ROI (Cap Rate Bruto)**: Cálculo automático del retorno anual en USD usando la cotización **USDT/ARS de Binance**.

## 4. Estructura de Archivos
- `parsers/`: Lógica de procesamiento y motores de cálculo.
- `scripts/`: Utilidades de actualización y patching.
- `docs/`: Documentación técnica y funcional.
- `cache_scraping.json`: Base de datos de mercado.

---
**Actualizado por**: Antigravity AI
**Fecha**: 2026-04-27
**Ubicación**: `ingresos_familiares_st/docs/STATUS_ACTUAL.md`

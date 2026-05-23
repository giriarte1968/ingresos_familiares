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

## 3. Nueva Interfaz Valu (UX Premium)
Se ha completado la transición hacia una arquitectura de frontend desacoplada:
- **Tecnología**: Streamlit + CSS Custom (Glassmorphism) + Componentes HTML5.
- **Valuación Explicable v2.0**: Razonamiento narrativo cualitativo que explica cada driver de valor en lenguaje natural (vista, calidad, estado, ventilación, piso, gas, balcón, funcionales, seguridad, edad, NLP). Sin porcentajes.
- **Historial Inmutable**: Sistema de registro por eventos (`JSONL`) que preserva cada tasación y snapshot del mercado para análisis temporal.
- **Landing Page Pública**: Página de presentación profesional inspirada en Zillow/Redfin con disclaimer de responsabilidad y onboarding para nuevos usuarios.
- **Seguimiento de Inventario**: Gestión de fechas de publicación para análisis de absorción de mercado.

## 4. Estructura de Archivos
- `valu.py`: App principal enfocada en Real Estate.
- `valu_design.py`: Design Tokens y componentes visuales.
- `valu_forms.py`: Captura de datos (45+ variables).
- `app.py`: Versión legacy / Gestión financiera.
- `parsers/`: Motores de cálculo y scraping.
- `parsers/valuacion_helpers.py`: funciones puras: `calcular_rango_venta()` (fuente única de rango), `procesar_alquiler()`, `ensamblar_metadata_resolucion()`
- `parsers/cluster_filters.py`: 7 helpers puros con 34 tests: `calcular_percentil()` (discreto, no numpy), `calcular_blend_p33()`, `seleccionar_percentil_por_edad()`, etc.
- `cache_scraping.json`: Base de datos de mercado (~50MB, gitignored).
- `data/valuaciones_cache.json`: Resultados de valuación cacheados trackeados en git para persistencia entre deploys DO.

## 5. FASE 2 — Rango Unificado ✅
- `calcular_rango_venta()` en `valuacion_helpers.py` es la única fuente de verdad para el rango de venta
- El motor `valuar_propiedad_v7()` ya no tiene lógica inline de rango; llama al helper
- El rango UI (`rango_m2`) usa el rango real del cluster, no ±10% hardcodeado
- Hardcode `rango_min = valor_venta * 0.90` y `rango_max = valor_venta * 1.10` eliminados

## 6. FASE 3 — Consolidación de Helpers ✅
- `seleccionar_percentil_por_edad()` ahora sí se llama desde producción (reemplaza inline de 15 líneas)
- `calcular_blend_p33()` ahora se usa en los 3 escenarios (conservador, mercado, optimista), no solo en blend_cons
- Los 4 helpers de cluster (`calcular_percentil`, `calcular_blend_p33`, `seleccionar_percentil_por_edad`, `calcular_rango_venta`) están 100% activos
- Sin helpers muertos — todos llamados desde producción
- **82/82 tests pasan** — baseline anclas sin cambios: Mabel $72,241 / Ayacucho $52,047 / Vera $52,062 / P1200 $137,888

---

**Actualizado por**: opencode (Agente IA)
**Fecha**: 2026-05-23
**Ubicación**: `ingresos_familiares_st/valu.py`

## 7. Persistencia entre Deploys DO ✅

- `data/valuaciones_cache.json` ahora trackeado en git → persiste en DO
- `cache_scraping.json` trackeado en git (se quitó de .gitignore)
- `_calcular_hash_scraping()` retorna `None` si el archivo no existe
- `necesita_recalcular()` omite chequeo de scraping si hash es `None`
- DO usa cache sin recálculo en cada deploy.
- `parsers/git_sync.py`: write-back de propiedades a git cuando `GIT_WRITE_TOKEN` está configurado
- ⚠️ Cada push desde DO desencadena un deploy (deploy_on_push). Las sesiones de usuario se interrumpen brevemente.

## 8. Optimización de Performance — FASE 1 ✅

### Cache persistente de Infomapa
- `_INFOMAPA_CACHE` en memoria + `data/infomapa_cache.json` en disco
- Clave por coordenadas (`{lat:.4f}_{lon:.4f}`), TTL 24h
- Se carga al importar el módulo, se persiste tras cada llamada exitosa
- **Ahorro estimado**: ~3.3s por valuación (cache hit → ~1ms)

### Cache de CSV catastral
- `_cargar_csv()` con TTL 5 min en memoria
- **Ahorro estimado**: ~110ms por valuación

### Reuso de cache_scraping
- `obtener_mediana_cluster_v2()` acepta `cache_scraping` opcional (dict precargado)
- `calcular_cap_rate_local()` acepta y propaga el mismo parámetro
- `valuar_propiedad_v7()` carga el cache UNA VEZ y lo pasa a toda la valuación
- **Ahorro estimado**: ~319ms (4 lecturas → 1)

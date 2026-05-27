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
- **Cobertura**: 751 features (263 hard + 488 soft). Av. Del Valle agregada como soft barrier el 2026-05-24 para corregir valuación de Brown 2700 (23 propiedades re-clasificadas de same_side a cross_soft).

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
**Fecha**: 2026-05-26
**Ubicación**: `ingresos_familiares_st/valu.py`

## 7. Fix Age Blend 5-7 ✅ (2026-05-26)

### Problema
`seleccionar_percentil_por_edad()` ya contemplaba `P33_age_blend` para 5–7 comparables, pero `_filtrar_por_ventana_edad()` exigía `min_con_anio=10` y segunda ventana ±20 (en vez de ±30). Con ±20 solo obtenía 4 comparables para Brown 2700 (año 2010), insuficientes para activar el blend.

### Cambios
- `min_con_anio=10` → `min_con_anio=5`
- Segunda ventana: 20 → 30
- Control flow simplificado (return on first success)
- Fallback retorna `len(pool_con_anio)` en vez de 0

### Caso Brown 2700 (2010)
| Métrica | Antes | Después |
|---------|-------|---------|
| age_filter_applied | False | True |
| n_age_filtered | 0 | 6 |
| rango_anio | — | 1980-2040 |
| percentil_usado | P33 | P33_age_blend |
| age_blend_applied | False | True |
| alpha_age_blend | — | 0.60 |
| base_principal | 2057.84 | 1763.50 |
| Comparables 1968/1975 en pool | Sí | No |

### Archivos modificados
- `parsers/mercado_inmobiliario.py` — `_filtrar_por_ventana_edad()`
- `tests/test_age_blend_filter.py` — 5 tests nuevos

## 8. Persistencia entre Deploys DO ✅

- `data/valuaciones_cache.json` ahora trackeado en git → persiste en DO
- `cache_scraping.json` trackeado en git (se quitó de .gitignore)
- `_calcular_hash_scraping()` retorna `None` si el archivo no existe
- `necesita_recalcular()` omite chequeo de scraping si hash es `None`
- DO usa cache sin recálculo en cada deploy.
- `parsers/git_sync.py`: write-back de propiedades a git cuando `GIT_WRITE_TOKEN` está configurado
- ⚠️ Cada push desde DO desencadena un deploy (deploy_on_push). Las sesiones de usuario se interrumpen brevemente.

## 9. Optimización de Performance — FASE 1 ✅

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

## 10. Infomapa Lazy-Load (On-Demand) ✅

### Problema resuelto
Infomapa era el principal cuello de botella del botón "Ver detalle":
- `infomapa` frío: ~3.9s por valuación (HTTP POST a rosario.gov.ar)
- Usuario reportaba ~30s de espera (cold start + Infomapa + Streamlit combinados)
- La consulta se ejecutaba SIEMPRE al abrir detalle, incluso si el usuario no quería ver el plano

### Solución
- `valuar_propiedad_v7(consultar_infomapa=False)` salta el bloque Infomapa completamente
- Desde la UI, el detalle se abre sin consultar Infomapa
- Botón "🔍 Consultar datos catastrales / plano" en el detalle (solo visible si no hay datos)
- Al hacer clic, se ejecuta `enriquecer_con_infomapa()`, se persiste en `valuaciones_cache.json`, y se rerunea

### Flujo
1. **Ver detalle** → apertura rápida (~2-3s), sin llamada a Infomapa
2. **Consultar catastro** (solo si el usuario hace clic) → llamada a Infomapa + cache + rerun
3. En adelante, el detalle sirve datos catastrales desde `valuaciones_cache.json`

### Archivos modificados
| Archivo | Cambio |
|---------|--------|
| `parsers/mercado_inmobiliario.py` | `consultar_infomapa` param en `valuar_propiedad_v7()` |
| `parsers/motor_vpp_core.py` | `consultar_infomapa` param en `valuar_con_cache()` |
| `valu.py` | `consultar_infomapa=False` + botón on-demand |
| `valu_detail_sections.py` | `render_catastro()` early return sin datos |

## 11. Validación de coordenadas post-scrape ✅

### Estado
`scripts/validar_coordenadas.py` disponible para correr bajo demanda. Valida cada propiedad del cache comparando coordenadas del pin scraping contra geocoding textual vía Nominatim. Discrepancias >500m se corrigen automáticamente.

### Archivos
| Archivo | Descripción |
|---------|-------------|
| `parsers/geocoder.py` | `validar_coordenadas_contra_direccion()` |
| `scripts/validar_coordenadas.py` | Script batch post-scrape |
| `tests/test_validar_coordenadas.py` | 5 tests |

Colón al 1200 corregido: -32.9337,-60.6563 → -32.9463,-60.6323

## 12. Pantallazo numérico eliminado ✅

### Problema
`mostrar_detalle_valu()` mostraba las secciones secuencialmente (~2.8s), con números apareciendo antes que mapas y catastro.

### Solución
`st.spinner()` + render directo reemplazado por `st.status(expanded=False)` que oculta todo hasta que el render completo termina, luego expande mostrando todo simultáneamente.

### Archivo modificado
| Archivo | Cambio |
|---------|--------|
| `valu.py` | `st.spinner` → `st.status(expanded=False)` wrapper

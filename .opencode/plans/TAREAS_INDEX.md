# TAREAS EJECUTADAS

| TAREA | Descripción | Commit | Fecha |
|-------|-------------|--------|-------|
| TAREA-001 | Filtro catastral por centena exacta (cuadra exacta en vez de diff <= 10) | _(pendiente)_ | 2026-05-21 |
| TAREA-002 | CTA gradiente verde + Reporte PDF valuación | `a68d775` | 2026-05-21 |
| TAREA-003 | Orden candidatos catastrales por distancia (no centena) | `7032bdf` | 2026-05-22 |
| TAREA-004 | Eliminación completa de numpy del cold start | `dea2cc9` | 2026-05-23 |
| TAREA-005 | Eliminar pantallazo numérico con st.status() | `e382a91` | 2026-05-23 |
| TAREA-006 | Reagrupar secciones del detalle en Comparables, Valuaciones, Acciones | `55ed6cf` | 2026-05-24 |
| TAREA-007 | Botones homogéneos en fila + toggle catastro en Acciones | `0683d3a` | 2026-05-24 |
| TAREA-008 | Auditar y agregar Av. del Valle como barrera blanda | `544c598` | 2026-05-24 |
| TAREA-009 | Conectar P33_age_blend para 5-7 comparables (umbral ±30 / ≥5) | _(pending)_ | 2026-05-26 |
| TAREA-010 | Validación de coordenadas post-scrape + fix Colón 1200 | `fc44149` | 2026-05-27 |
| TAREA-011 | Normalización amenities + anti doble conteo NLP | _(pendiente)_ | 2026-05-27 |
| TAREA-012 | 3-Step comparable year enrichment (token containment + intersecciones + esquina) | _(pending)_ | 2026-05-29 |
| TAREA-013 | DO valuaciones_cache persistence + guardar_resultado + try_sync fix | _(multiple)_ | 2026-05-29 |
| TAREA-014 | Restrictive comparable year enrichment (≤20m, sin esquina fallback) | `64b5b98` | 2026-05-29 |
| TAREA-015 | Enriquecimiento 3-pasos: match exacto calle+número + token ≤30m + nearest | `4999294` | 2026-05-29 |
| TAREA-016 | Persistencia DO: atomic_write_json + persistir_valuacion + branch do-state | `caa7d1f` | 2026-05-29 |
| TAREA-017 | Corrección esquinas (218 PHs) + Interpolación números faltantes (2.219 PHs) via nearest-3 IDW | `7099715` + `(pendiente)` | 2026-05-30 |
| TAREA-018 | Batch centroide masivo: centroide+reverse+interpolación+forward-verify a ~2,758 PHs | `f18c0ba` | 2026-05-30 |
| TAREA-019 | Enriquecimiento años: filtro de bloque en PASO 1+2, PASO 2 extendido a 60m | `75487da` | 2026-05-30 |
| TAREA-020 | Corrección coordenadas cache vía centroide catastral | `3c26724` | 2026-05-31 |
| TAREA-021 | Mejora `extraer_calle_numero` + re-corrección cache | `09766f5` | 2026-05-31 |
| TAREA-022 | Cap dinámico de factor_total según cluster quality | `b23dc45` | 2026-05-31 |
| TAREA-023 | Eliminar doble compensación de patio en PB | `d5b41d5` | 2026-05-31 |
| TAREA-024 | Mejora matching catastral: normalización acentos/ñ en token + fix "bis" | `ec5ad9a` | 2026-05-31 |
| TAREA-025 | PASO 3 en enriquecimiento: nearest PH misma calle por coordenadas ≤60m | `b31ca9c` | 2026-06-01 |
| TAREA-027 | Restaurar 132 bis catastro + geocoder con catastro local + map verification | _(current)_ | 2026-06-02 |
| TAREA-028 | Disposición solo-penalizaciones + Ambientes informativo en formulario y narrativa | `d3c393d` | 2026-06-03 |
| TAREA-029 | Balcón: eliminar bonus_m2, desbloquear tipo_balcon en form, recalibrar factores | _(current)_ | 2026-06-03 |
| TAREA-030 | Fix barreras duras como blandas en Puerto Norte + Fallback + Ancla | _(current)_ | 2026-06-03 |
| TAREA-031 | Fecha dinámica: date_created + 12 meses + formatos YYYY-MM/DD | `b9a3133` | 2026-06-05 |
| TAREA-032 | Puerto Norte: time-expansion en zona cerrada + ancla 2800 | _(current)_ | 2026-06-05 |
| TAREA-035 | Anclas por grilla 400m (322 microzonas, 96% cobertura, Ct dual) | `33d18ec` | 2026-06-09 |
| TAREA-038 | Pipeline de regeneración de anclas configurable (config, refactor, admin UI) | `9162203` | 2026-06-10 |
| TAREA-039 | Retro: expansión de comparables con Ct + Admin UI curva temporal | _(current)_ | 2026-06-10 |
| TAREA-040 | Preview valuation: toggles Retro/Flex muestran comps sin persistir a portfolio | _completada_ | 2026-06-11 |
| TAREA-041 | Preview valuation — `persistir_valuacion(commit=)`, `valuar_con_cache(preview=)`, toggles preview en valu.py, OR logic Retro Flexible | _completada_ | 2026-06-11 |
| TAREA-046 | Simplificación de Puerto Norte: Time-Expansion unificada con el slider Retro | _completada_ | 2026-06-12 |
| TAREA-050 | Fix P33/P50 inversion in selection UI preview | _completada_ | 2026-06-13 |
| TAREA-051 | Alinear UI percentil preview con Core Motor (granularidad completa) | _completada_ | 2026-06-13 |
| TAREA-052 | Fix "is_applied" false positive in selection UI | _completada_ | 2026-06-13 |
| TAREA-053 | Fix preview valuation leak into Portfolio | _completada_ | 2026-06-13 |
| TAREA-054 | Fix Apply Selection percentil logic in valu.py | _completada_ | 2026-06-13 |
| TAREA-055 | Show Apply Selection button even when all comparables selected | _completada_ | 2026-06-13 |
| TAREA-056 | Persistent Apply Selection (IDs) + Fix Preview Delta | _completada_ | 2026-06-13 |
| TAREA-057 | Sincronización Total Motor <-> UI (Fórmulas Premium y Barreras) | _in_progress_ | 2026-06-13 |
| TAREA-058 | Calcular precio ajustado dinámicamente en UI (sin depender del cache) | _completada_ | 2026-06-13 |
| TAREA-059 | barrier_penalty faltante en ruta principal comparables_reales | `2257b0f` | 2026-06-13 |
| TAREA-060 | Pendiente re-entry limpia (empezar desde $0) | `22464ff` | 2026-06-13 |
| TAREA-061 | Fix Pendiente re-entry detection (check preview_mode flag) | `fd63547` | 2026-06-13 |
| TAREA-062 | Live header update on checkbox change (read from sel_key) | `dbd432b` | 2026-06-13 |
| TAREA-063 | Read widget keys directly for instant header sync on checkbox | `1439df2` | 2026-06-13 |
| TAREA-064 | Fix preview/motor m² mismatch for n=5-7 when all comps selected | `c2aa127` + `4b0d951` | 2026-06-13 |
| TAREA-065 | Separar barrera del m² de comparables (solo afecta al sujeto) | _(current)_ | 2026-06-14 |
| TAREA-073 | Eliminar factores hedonicos (estado, calidad, anti, NLP) de venta. Conservar en alquiler. | _completada_ | 2026-06-20 |
| TAREA-074 | Size adjustment por macrozona. PN subzona premium. Curvas piecewise. | _completada_ | 2026-06-20 |
| TAREA-076 | Eliminar depreciación de Subfactores Display + Documentar evidencia ML | _completada_ | 2026-06-20 |
| TAREA-078 | Percentil por calidad del pool (CV) + Eliminación edad | _(current)_ | 2026-06-22 |
| TAREA-079 | UI: "Valor/m² por selección" refleja m2_base_venta del motor | `c470361` | 2026-06-23 |
| TAREA-080 | UI: columna Tipo → Publicado + eliminar tag FLEX | `c4f7259` | 2026-06-24 |
| TAREA-083 | Fix colisión checkboxes ↔ motor exclusión automática | `670f804` + _(current)_ | 2026-06-25 |
| TAREA-084 | Revertir fuente única en "Valor/m² por selección" (display_source sync) | `14dfd88` | 2026-06-25 |
| TAREA-085 | Fix "Restablecer todos" no resetea exclusión persistida | `ff6e743` | 2026-06-25 |
| TAREA-086 | Fix cambio Manual→Comparable: carga desde cache físico (v2) | _completada_ | 2026-06-27 |

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
| TAREA-023 | Eliminar doble compensación de patio en PB | _(pending)_ | 2026-05-31 |

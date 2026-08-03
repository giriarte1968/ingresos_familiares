# TAREAS EJECUTADAS

| TAREA | DescripciÃ³n | Commit | Fecha |
|-------|-------------|--------|-------|
| TAREA-001 | Filtro catastral por centena exacta (cuadra exacta en vez de diff <= 10) | _(pendiente)_ | 2026-05-21 |
| TAREA-002 | CTA gradiente verde + Reporte PDF valuaciÃ³n | `a68d775` | 2026-05-21 |
| TAREA-003 | Orden candidatos catastrales por distancia (no centena) | `7032bdf` | 2026-05-22 |
| TAREA-004 | EliminaciÃ³n completa de numpy del cold start | `dea2cc9` | 2026-05-23 |
| TAREA-005 | Eliminar pantallazo numÃ©rico con st.status() | `e382a91` | 2026-05-23 |
| TAREA-006 | Reagrupar secciones del detalle en Comparables, Valuaciones, Acciones | `55ed6cf` | 2026-05-24 |
| TAREA-007 | Botones homogÃ©neos en fila + toggle catastro en Acciones | `0683d3a` | 2026-05-24 |
| TAREA-008 | Auditar y agregar Av. del Valle como barrera blanda | `544c598` | 2026-05-24 |
| TAREA-009 | Conectar P33_age_blend para 5-7 comparables (umbral Â±30 / â‰¥5) | _(pending)_ | 2026-05-26 |
| TAREA-010 | ValidaciÃ³n de coordenadas post-scrape + fix ColÃ³n 1200 | `fc44149` | 2026-05-27 |
| TAREA-011 | NormalizaciÃ³n amenities + anti doble conteo NLP | _(pendiente)_ | 2026-05-27 |
| TAREA-012 | 3-Step comparable year enrichment (token containment + intersecciones + esquina) | _(pending)_ | 2026-05-29 |
| TAREA-013 | DO valuaciones_cache persistence + guardar_resultado + try_sync fix | _(multiple)_ | 2026-05-29 |
| TAREA-014 | Restrictive comparable year enrichment (â‰¤20m, sin esquina fallback) | `64b5b98` | 2026-05-29 |
| TAREA-015 | Enriquecimiento 3-pasos: match exacto calle+nÃºmero + token â‰¤30m + nearest | `4999294` | 2026-05-29 |
| TAREA-016 | Persistencia DO: atomic_write_json + persistir_valuacion + branch do-state | `caa7d1f` | 2026-05-29 |
| TAREA-017 | CorrecciÃ³n esquinas (218 PHs) + InterpolaciÃ³n nÃºmeros faltantes (2.219 PHs) via nearest-3 IDW | `7099715` + `(pendiente)` | 2026-05-30 |
| TAREA-018 | Batch centroide masivo: centroide+reverse+interpolaciÃ³n+forward-verify a ~2,758 PHs | `f18c0ba` | 2026-05-30 |
| TAREA-019 | Enriquecimiento aÃ±os: filtro de bloque en PASO 1+2, PASO 2 extendido a 60m | `75487da` | 2026-05-30 |
| TAREA-020 | CorrecciÃ³n coordenadas cache vÃ­a centroide catastral | `3c26724` | 2026-05-31 |
| TAREA-021 | Mejora `extraer_calle_numero` + re-correcciÃ³n cache | `09766f5` | 2026-05-31 |
| TAREA-022 | Cap dinÃ¡mico de factor_total segÃºn cluster quality | `b23dc45` | 2026-05-31 |
| TAREA-023 | Eliminar doble compensaciÃ³n de patio en PB | `d5b41d5` | 2026-05-31 |
| TAREA-024 | Mejora matching catastral: normalizaciÃ³n acentos/Ã± en token + fix "bis" | `ec5ad9a` | 2026-05-31 |
| TAREA-025 | PASO 3 en enriquecimiento: nearest PH misma calle por coordenadas â‰¤60m | `b31ca9c` | 2026-06-01 |
| TAREA-027 | Restaurar 132 bis catastro + geocoder con catastro local + map verification | _(current)_ | 2026-06-02 |
| TAREA-028 | DisposiciÃ³n solo-penalizaciones + Ambientes informativo en formulario y narrativa | `d3c393d` | 2026-06-03 |
| TAREA-029 | BalcÃ³n: eliminar bonus_m2, desbloquear tipo_balcon en form, recalibrar factores | _(current)_ | 2026-06-03 |
| TAREA-030 | Fix barreras duras como blandas en Puerto Norte + Fallback + Ancla | _(current)_ | 2026-06-03 |
| TAREA-031 | Fecha dinÃ¡mica: date_created + 12 meses + formatos YYYY-MM/DD | `b9a3133` | 2026-06-05 |
| TAREA-032 | Puerto Norte: time-expansion en zona cerrada + ancla 2800 | _(current)_ | 2026-06-05 |
| TAREA-035 | Anclas por grilla 400m (322 microzonas, 96% cobertura, Ct dual) | `33d18ec` | 2026-06-09 |
| TAREA-038 | Pipeline de regeneraciÃ³n de anclas configurable (config, refactor, admin UI) | `9162203` | 2026-06-10 |
| TAREA-039 | Retro: expansiÃ³n de comparables con Ct + Admin UI curva temporal | _(current)_ | 2026-06-10 |
| TAREA-040 | Preview valuation: toggles Retro/Flex muestran comps sin persistir a portfolio | _completada_ | 2026-06-11 |
| TAREA-041 | Preview valuation â€” `persistir_valuacion(commit=)`, `valuar_con_cache(preview=)`, toggles preview en valu.py, OR logic Retro Flexible | _completada_ | 2026-06-11 |
| TAREA-046 | SimplificaciÃ³n de Puerto Norte: Time-Expansion unificada con el slider Retro | _completada_ | 2026-06-12 |
| TAREA-050 | Fix P33/P50 inversion in selection UI preview | _completada_ | 2026-06-13 |
| TAREA-051 | Alinear UI percentil preview con Core Motor (granularidad completa) | _completada_ | 2026-06-13 |
| TAREA-052 | Fix "is_applied" false positive in selection UI | _completada_ | 2026-06-13 |
| TAREA-053 | Fix preview valuation leak into Portfolio | _completada_ | 2026-06-13 |
| TAREA-054 | Fix Apply Selection percentil logic in valu.py | _completada_ | 2026-06-13 |
| TAREA-055 | Show Apply Selection button even when all comparables selected | _completada_ | 2026-06-13 |
| TAREA-056 | Persistent Apply Selection (IDs) + Fix Preview Delta | _completada_ | 2026-06-13 |
| TAREA-057 | SincronizaciÃ³n Total Motor <-> UI (FÃ³rmulas Premium y Barreras) | _in_progress_ | 2026-06-13 |
| TAREA-058 | Calcular precio ajustado dinÃ¡micamente en UI (sin depender del cache) | _completada_ | 2026-06-13 |
| TAREA-059 | barrier_penalty faltante en ruta principal comparables_reales | `2257b0f` | 2026-06-13 |
| TAREA-060 | Pendiente re-entry limpia (empezar desde $0) | `22464ff` | 2026-06-13 |
| TAREA-061 | Fix Pendiente re-entry detection (check preview_mode flag) | `fd63547` | 2026-06-13 |
| TAREA-062 | Live header update on checkbox change (read from sel_key) | `dbd432b` | 2026-06-13 |
| TAREA-063 | Read widget keys directly for instant header sync on checkbox | `1439df2` | 2026-06-13 |
| TAREA-064 | Fix preview/motor mÂ² mismatch for n=5-7 when all comps selected | `c2aa127` + `4b0d951` | 2026-06-13 |
| TAREA-065 | Separar barrera del mÂ² de comparables (solo afecta al sujeto) | _(current)_ | 2026-06-14 |
| TAREA-073 | Eliminar factores hedonicos (estado, calidad, anti, NLP) de venta. Conservar en alquiler. | _completada_ | 2026-06-20 |
| TAREA-074 | Size adjustment por macrozona. PN subzona premium. Curvas piecewise. | _completada_ | 2026-06-20 |
| TAREA-076 | Eliminar depreciaciÃ³n de Subfactores Display + Documentar evidencia ML | _completada_ | 2026-06-20 |
| TAREA-078 | Percentil por calidad del pool (CV) + EliminaciÃ³n edad | _(current)_ | 2026-06-22 |
| TAREA-079 | UI: "Valor/mÂ² por selecciÃ³n" refleja m2_base_venta del motor | `c470361` | 2026-06-23 |
| TAREA-080 | UI: columna Tipo â†’ Publicado + eliminar tag FLEX | `c4f7259` | 2026-06-24 |
| TAREA-083 | Fix colisiÃ³n checkboxes â†” motor exclusiÃ³n automÃ¡tica | `670f804` + _(current)_ | 2026-06-25 |
| TAREA-084 | Revertir fuente Ãºnica en "Valor/mÂ² por selecciÃ³n" (display_source sync) | `14dfd88` | 2026-06-25 |
| TAREA-085 | Fix "Restablecer todos" no resetea exclusiÃ³n persistida | `ff6e743` | 2026-06-25 |
| TAREA-077 | Fix exclusiÃ³n perdida tras Guardar Valuacion Manual | _completada_ | 2026-06-28 |
| TAREA-087 | Guard preview fallido no debe pisar cache exitoso | _completada_ | 2026-06-28 |
| TAREA-088 | Fix ðŸ”„ Limpiar no borra valuaciÃ³n manual | `617b699` | 2026-06-28 |
| TAREA-089 | Preview mode no persiste valuaciÃ³n vÃ­a exclusiÃ³n restaurada | `2d948b7` | 2026-06-28 |
| TAREA-090 | Transparencia: desglose de fÃ³rmula en header | _(current)_ | 2026-06-29 |
| TAREA-091 | ValuaciÃ³n fallida no pisa cache/UV vÃ¡lido + _comp_exclusion_applied preservado + guard_restored flag + Escenario C test | `6d5b399` | 2026-06-29 |
| TAREA-086 | Fix cambio Manualâ†’Comparable: carga desde cache fÃ­sico (v2) | _completada_ | 2026-06-27 |
| TAREA-093 | VM2 core unification + flex persistence + cv_pool fix + header count fix | `e443524` | 2026-06-29 |
| TAREA-094 | Sincronizar header con exclusiÃ³n de comparables (n_propiedades, m2_microzona) | `781353e` | 2026-06-30 |
| TAREA-095 | Fix "Restablecer Todos" no respeta motor (defensa + debug + test #52) | `3d9d8d3` | 2026-06-30 |
| TAREA-096 | Header oculta valuaciÃ³n si < 3 comps | `c3dc621` | 2026-06-30 |
| TAREA-097 | Restablecer Todo como efecto visual puro | `b3d1da4` | 2026-06-30 |
| TAREA-098 | Header no cambia en modo preview | _(current)_ | 2026-07-01 |
| TAREA-099 | _official_result en primera valuaciÃ³n (gap fix) | _(current)_ | 2026-07-01 |
| TAREA-100 | Desactivar Engine Guard en preview (defensa sistÃ©mica) | _(current)_ | 2026-07-01 |
| TAREA-101 | ReconfiguraciÃ³n visual ParÃ¡metros ValuaciÃ³n Manual (5 cols, FH en %, check constructora siempre visible) | _completada_ | 2026-07-01 |
| TAREA-102 | Fallback a UV snapshot si recÃ¡lculo falla (Mabel: sin valuaciÃ³n en detalle) | _completada_ | 2026-07-01 |
| TAREA-103 | Limpiar manual_valor_usd al eliminar valuaciÃ³n manual | _completada_ | 2026-07-01 |
| TAREA-104 | Preservar retro_dias/flex_dormitorios al guardar valuaciÃ³n manual | _completada_ | 2026-07-01 |
| TAREA-105 | Fix is_applied false-positive con exclusion vacÃ­a en Retro toggle | _completada_ | 2026-07-01 |
| TAREA-106 | BotÃ³n Limpiar â†” Comparables toggle post-limpieza | _completada_ | 2026-07-01 |
| TAREA-107 | ConfiguraciÃ³n: georeferencia + aÃ±o de construcciÃ³n en Carga de Comparable | _completada_ | 2026-07-01 |
| TAREA-108 | Font-size headers +10% + eliminar botÃ³n Limpiar ValuaciÃ³n | _completada_ | 2026-07-02 |
| TAREA-109 | m2_microzona siempre cluster (RO-08) â€” Retro/Flex afectan valuaciÃ³n | `55aaf8b` | 2026-07-02 |
| TAREA-110 | Cache poisoning fix: VCC nunca persiste errores + necesita_recalcular detecta cache_envenenada | _(current)_ | 2026-07-02 |
| TAREA-111 | EstabilizaciÃ³n percentiles vÃ­a CV normalizado por macrozona + UI configurable | _completada_ | 2026-07-03 |
| TAREA-112 | Restaurar Pendiente puro + Golden Path Primera Entrada + Limpiar funcional | `900f53b` | 2026-07-03 |
| TAREA-113 | SustituciÃ³n de Tabla CT por Tasa Anual por Macrozona | 573b21 | 2026-07-04 |
| TAREA-114 | Fix flex_dormitorios=None al guardar valuaciÃ³n manual | _(current)_ | 2026-07-04 |
| TAREA-120 | Restaurar botones UI + Guardrails de regresiÃ³n | _(current)_ | 2026-07-05 |
| TAREA-122 | Fix real header leak â€” cache preview no contamina auto_valor_usd | `09973f3` | 2026-07-06 |
| TAREA-123 | Fix ðŸ”„ Limpiar borra valuaciÃ³n manual (RU-CLEAN-MANUAL-01) | _(current)_ | 2026-07-06 |
| TAREA-124 | Header independiente auto/manual + Fix n_comps gate bug (RU-HEADER-03) | _(current)_ | 2026-07-06 |
| TAREA-125 | Fix portfolio double-value + _build_rows fallback + _render_cards + Guardrail RU-PORTFOLIO-01 | _(current)_ | 2026-07-07 |
| TAREA-126 | Restaurar botones ValuaciÃ³n Manual (siempre visibles) + Renombrar a "Aplicar SelecciÃ³n"/"Limpiar" | _(current)_ | 2026-07-08 |
| TAREA-127 | Fix exclusion-applied state con 0 exclusiones (session_state) | `2135dea` | 2026-07-08 |
| TAREA-127b | Fix EXCL-RESTORE pierde _comp_exclusion_applied con lista vacÃ­a + Guardrail RU-EXCL-APPLIED-01 | `fe504ba` | 2026-07-08 |
| TAREA-128 | Desacoplar Ct del Anchor â€” ValuaciÃ³n Manual con Ct runtime | _(current)_ | 2026-07-09 |
| TAREA-135 | Limpiar preview y todos los comparables (pop _official_result incondicional) | `b189961` | 2026-07-13 |
| TAREA-136 | Eliminar bloque zombi de limpieza en valu.py | _(current)_ | 2026-07-13 |
| TAREA-137 | Fix header vacÃ­o post-Limpiar: guard pendiente no persiste como official (RO-CLEAN-03) | _(current)_ | 2026-07-14 |
| TAREA-138 | Filtro Â±10 aÃ±os fijo para comparables (usa antiquity como fuente primaria) | _(pending)_ | 2026-07-18 |
| TAREA-139 | Fix umbral min_con_anio: 10â†’3 (mÃ­nimo que el motor necesita) | _(pending)_ | 2026-07-19 |
| TAREA-140 | Transparencia en cantidad de comparables (muestra vs pool total) | `f690059` | 2026-07-20 |
| TAREA-148 | Macrozona independiente Puerto Norte con curvas planas | `3d6da94` | 2026-07-24 |
| TAREA-149 | Eliminar TASA_AJUSTE_PN hardcoded + usar ct_annual_rate real | `525844f` | 2026-07-24 |
| TAREA-150 | Ajuste fino parÃ¡metros Puerto Norte (ct=+3.5%, cv=0.339) | `2da7818` | 2026-07-24 |
| TAREA-151 | Reordenar barreras_rosario.json (soft antes que hard) | `e141789` | 2026-07-25 |
| TAREA-152 | Eliminar 10 segmentos internos de Av. Francia en Puerto Norte | `52f2184` | 2026-07-25 |
| TAREA-153 | Hacer barreras editables en UI | _(pendiente)_ | 2026-07-25 |
| TAREA-154 | RediseÃ±o UI: Tarjeta Alquiler con rango + Tarjeta Rentabilidad desglosada | _(pending)_ | 2026-07-28 |
| TAREA-155 | CT Alquiler: configuraciÃ³n editable + funciÃ³n temporal + integraciÃ³n en cluster + UI editor | `f5938b2` | 2026-07-30 |
| TAREA-156 | Refactor fÃ³rmula alquiler: eliminar GAP, cluster como primario, cap_rate como fallback | _(plan)_ | 2026-07-30 |
| TAREA-157 | CalibraciÃ³n ROI_ZONAL con factor CESO Ã— 0.75 | _(plan)_ | 2026-07-30 |
| TAREA-161 | Valor oficial m2 en valuaciÃ³n manual + ancla renaming | `276e877` | 2026-08-03 |
| TAREA-162 | DepreciaciÃ³n automÃ¡tica en Valor Oficial | _(pending)_ | 2026-08-03 |
| TAREA-163 | Fix flex_dormitorios destruye pool de comparables (two-phase search) | _(plan)_ | 2026-08-03 |

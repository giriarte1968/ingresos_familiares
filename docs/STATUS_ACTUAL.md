# 🏠 STATUS ACTUAL DEL PROYECTO — AVM Rosario

*Actualizado: 14/07/2026 (TAREA-137: RO-CLEAN-03 — fix header vacío post-Limpiar, guard pendiente no persiste como official)*

---

## 1. RESUMEN EJECUTIVO

| Dimensión | Estado |
|-----------|--------|
| Motor valuación v7 | ✅ Base puro sin factores hedónicos (TAREA-073) |
| Coordenadas cache scraping | ✅ Corregidas vía centroide catastral (TAREA-020+021+024) |
| Enriquecimiento años | ✅ 3-pasos (exacta ≤200m / token+bloque ≤30m / nearest+token+bloque ≤60m) |
| Extracción calle+num | ✅ Mejorada: limpia basura descriptiva, trailing garbage, provincia, "bis" (TAREA-021+024) |
| Matching catastral (acentos/ñ) | ✅ Normalización NFKD en `_token_contenido` (TAREA-024) |
| Persistencia DO | ✅ Atómica + branch `do-state` |
| Landing page | ✅ Navegación por teclado (PageDown/PageUp/Home/End) |
| Tests regresión | ✅ 49/49 (TAREA-137) |
| Tests persistencia | ✅ 16/16 |
| Despliegue DO | Sin redeploy loop |
| Anclas grilla 400m | 322 microzonas, 96% cobertura (TAREA-036) |
| Zonas comerciales | Martin(5) Pellegrini(8) Pichincha(4) PN(4) Abasto(3) — con filtro distancia |

---

## 2. ESTADO DEL CACHE SCRAPING

| Métrica | Cantidad |
|---------|----------|
| Propiedades totales | 9,766 |
| Anclas disponibles | 322 microzonas (grilla 400m, TAREA-035) |
| Cobertura anclas (prop ≤300m) | 96% (8.014/8.366) |
| Con lat/lon | **9,754** (99.9%) |
| Sin lat/lon | 12 (nunca las tuvo Propia) |
| Con `calle_limpia`/`numero_limpio` | **8,782** (89.9%) |
| Sin calle (no se pudo extraer) | 984 |
| PH encontrado en catastro | **7,502** (TAREA-024) |
| Sin PH en catastro | 1,280 |
| Coords corregidas acumuladas | **~3,408** (3,289 TAREA-020 + 119 TAREA-024) |
| Coords originales conservadas (≤60m) | ~4,084 |
| Error promedio actual | 31m |

---

## 2. ARQUITECTURA ACTUAL

### Flujo de valuación

```
propiedades.json → motor_vpp_core.valuar_con_cache()
    → necesita_recalcular() → valuar_propiedad_v7()
    → persistir_valuacion() [local]
        → atomic_write_json → data/valuaciones_cache.json
        → atomic_write_json → propiedades.json (_ultima_valuacion)
    → try_sync_state() [opcional, push a do-state]
```

### Enriquecimiento de años (3 pasos)

```
Paso 0: EXACTA — (calle_norm, numero) en _CATASTRO_INDEX ≤200m → ALTA
Paso 1: TOKEN — token containment + bloque ≤30m → ALTA
Paso 2: NEAREST — nearest PH + token + bloque ≤60m → MEDIA
No esquina fallback.
```

### Navegación y ciclo de vida de previews (TAREA-091.4)
```
Detalle → [cambios en slider/flex] → preview_mode=True → persistir_valuacion(commit=False)
    → valuaciones_cache.json (preview=True)
Detalle → [Volver al Portafolio] → _limpiar_estado_propiedad()
    → destruye preview de valuaciones_cache.json (si preview=True)
    → limpia Session State
    → NO toca _ultima_valuacion en propiedades.json
Re-entry → lee retro_dias/flex_dormitorios desde _ultima_valuacion (UV oficial)
    → fallback a cache del motor para UV legacy
    → controles consistentes con la UV oficial
```

### Filtro etario

```
±15 años → si ≥5 comps aplica
±30 años → si ≥5 comps aplica
Fallback → pool completo (P33)
Percentiles: 5-7→P33_age_blend / 8-9→P40 / 10-19→P45 / 20+→P50
```

---

## 3. COMPONENTES

| Archivo | Propósito |
|---------|-----------|
| `valu.py` | UI principal (Streamlit), landing, portfolio |
| `landing.py` | Landing page render + keyboard nav JS |
| `landing_content.py` | HTML sections con `data-section` |
| `parsers/mercado_inmobiliario.py` | Motor valuación v7, enriquecimiento 3-pasos |
| `parsers/valuacion_cache.py` | Cache persistente, escritura atómica |
| `parsers/git_sync.py` | Sync GitHub a `main` (try_sync) y `do-state` (try_sync_state) |
| `parsers/motor_vpp_core.py` | Wrapper valuación con caché + sync opcional |
| `parsers/valuacion_historial.py` | Historial append-only de valuaciones |
| `tests/test_persistencia_valuaciones.py` | 16 tests de persistencia |

---

## 4. PERSISTENCIA DO — BRANCH DE ESTADO

### Flujo
1. **Persistencia local atómica** (siempre):
   - `atomic_write_json()` → `data/valuaciones_cache.json`
   - `atomic_write_json()` → `propiedades.json`
2. **Sync opcional** (si hay token):
   - `try_sync_state()` → push a `do-state`

### Características
- `do-state` no dispara redeploy (DO deploya desde `main`)
- `GIT_STATE_BRANCH` configurable via env var
- `GIT_WRITE_TOKEN` requerido para push
- Fallo de sync no rompe valuación (persistencia local ya ocurrió)

### Recuperar en PC local
```bash
git fetch origin do-state
git checkout origin/do-state -- propiedades.json data/valuaciones_cache.json
```

---

## 5. TESTS

| Archivo | Estado |
|---------|--------|
| `tests/test_regression.py` | 69+ ✅ (incluye UI guardrails con mocks Streamlit) |
| `tests/test_persistencia_valuaciones.py` | 16/16 ✅ |
| `tests/test_age_blend_filter.py` | ✅ |
| `tests/test_cluster_filters.py` | ✅ |
| `tests/test_cache.py` | ✅ |

---

## 6. VALUACIONES DE REFERENCIA (TAREA-071)

| Propiedad | Valor USD | m² | $/m² (m2_base) | ALTA | Pool |
|-----------|-----------|-----|-------|------|------|
| P1200 | $125.412 | 60.0 | $2.090 | 7 | 31 |
| Brown 2750 | $306.681 | 78.0 | $3.414 | 23 | 25 |
| Mabel | $86,092 | 41.0 | $2,100 | 13 | 79 |
| Ayacucho | $43,160 | 31.5 | $1,370 | 13 | 41 |
| Vera Mujica | $64,636 | 28.0 | $2,309 | 8 | 27 |
| Entre Ríos | $73.354 | 34.0 | $2.158 | 4 | 27 |

---

## 7. PRÓXIMOS PASOS / ISSUES CONOCIDOS

1. ✅ Vera Mujica benchmark actualizado (TAREA-071)
2. ✅ Francia 250bis: valuación fallida ya no pisa cache/UV válido (TAREA-091)
3. `data/history/` directorio untracked (generado por scraping)
4. Validación manual en DO del flujo do-state
5. ⚠️ P1200 y Brown 2750 requieren recalibración con fórmula multiplicativa
6. ⚠️ Botón "Comparable" en header carga desde cache en disco, debe cargar desde resultado actual en memoria (fix pendiente TAREA-086)
7. ✅ Botón "🗑️ Limpiar Valuación" eliminado (TAREA-108) — no funcionaba correctamente
8. ✅ Botón "Aplicar Selección" restaurado visible siempre (TAREA-120)
9. ✅ "Restablecer Todas" forza recálculo preview: reselecciona checkboxes, limpia comp_excluded, setea forzar_recalculo=True (TAREA-132 overturn)
10. ✅ Botón "Aplicar Selección" visible siempre (incluso con 6/6 seleccionados) (TAREA-120)
11. ✅ UI Guardrails: tests con mocks de Streamlit protegen botones y banner (TAREA-120)
12. ✅ RU-MANUAL-SAVE-02: Save manual no contamina `auto_valor_usd` con cache preview (TAREA-122) — guardrail `_verificar_invariante_auto_valor_usd` eliminado (TAREA-NNN): detectaba falsos positivos, seteando `auto_valor_usd=0` cuando el valor legítimo coincidía con auto_result (fix TAREA-NNN)
13. ✅ RU-HEADER-02: Auto card oculto en modo manual sin `auto_valor_usd` oficial (TAREA-122)

---

## 8. COMPORTAMIENTO UI — BOTONES DE SELECCIÓN DE COMPARABLES

**Regla de oro (RO-UI-01):** "Restablecer Todas" reselecciona todos los checkboxes y limpia `comp_excluded`, y SÍ setea `forzar_recalculo=True` para que el header muestre el valor natural del pool completo. Sin embargo NO persiste ni comitea el cambio — el usuario debe confirmar con "Aplicar Selección" para persistir.

### Botones y su comportamiento

| Botón | Cuándo aparece | Qué hace | ¿Forza recálculo? |
|-------|---------------|----------|-------------------|
| "↩️ Restablecer todos" | Cuando `len(current_sel) < len(comparables)` (hay desmarcados) | Setea todos los checkboxes a True, elimina `comp_excluded`, elimina `_comp_interacted`, setea `forzar_recalculo=True` | ✅ Sí (preview) |
| "✅ Aplicar selección" | Siempre que `n_sel >= 3` y NO esté ya aplicada | Setea `comp_excluded`, `forzar_recalculo=True`, hace `st.rerun()` | ✅ Sí |
| "✅ Selección Aplicada" | Cuando la selección ya fue aplicada (`is_applied`) | Deshabilitado, solo informa | ❌ No |
| "Mínimo 3 comparables" | Cuando `n_sel < 3` | Deshabilitado, solo informa | ❌ No |
| "Guardar Valuacion Manual" | Solo cuando `usd_m2_input > 0` Y `params_changed == True` | Persiste valuación manual | ✅ Sí |

### Nota: Toggle Retro/Flex/Slider resetean selección (RO-UI-05)
Cualquier toggle de Retro (ON/OFF), Flex (ON/OFF) o cambio en el slider de meses **resetea la selección de comparables a su estado por defecto** (todos seleccionados). El pool de comparables cambia con estos parámetros y la selección previa podría referenciar IDs que ya no existen. Un mensaje `st.info()` informa al usuario.

### Flujo de banner + reset
```
[usuario desmarca comparables]
  → banner naranja: "X/Y comparables activos — N desmarcado(s). Aplicar selección para recalcular."
  → botón "↩️ Restablecer todos" disponible
[usuario click Restablecer]
  → checkboxes todos True, comp_excluded eliminado, forzar_recalculo=True, banner desaparece
  → el motor recalcula y header muestra el valor natural del pool completo (preview)
  → NO persiste — el cambio es visual hasta "Aplicar selección"
[usuario click Aplicar selección]
  → persiste exclusión, forzar_recalculo=True (ya está), st.rerun() → recalcula y guarda
```

### Cambios recientes (TAREA-120 + TAREA-122 + TAREA-132)
- **Antes:** "Aplicar Selección" desaparecía con selección completa (`else: st.write("")`).
- **Ahora:** "Aplicar Selección" visible siempre (6/6 incluido).
- **Antes:** sin test UI.
- **Ahora:** 3+ tests UI con mocks de Streamlit protegen banner, botón aplicar, guardado manual, y reset.
- **Antes:** auto card mostraba valor STALE del cache preview tras guardar manual (TAREA-121 incompleto).
- **TAREA-132:** "Restablecer todos" ahora forza recálculo (`forzar_recalculo=True`) para preview consistente, pero NO persiste. Se añadió guardrail `_is_reset_state` para inhibir restauración de exclusiones desde UV cuando el usuario elige el pool completo.
- **TAREA-133:** Se añadió RO-UI-04 (Inhibición de Restauración en Preview Fresco) con función `_should_restore_excl()` que centraliza la decisión. Cualquier acción con `preview_mode=True AND forzar=True` inhibe la restauración automática de exclusiones UV. Esto corrige el bug donde toggle Retro aplicaba directamente la exclusión previa.
- **TAREA-133 (continuación):** Se añadió RO-UI-05 (Toggle Retro/Flex resetea selección). Retro ON/OFF, Flex ON/OFF y slider resetean la selección de comparables a todos seleccionados por defecto con mensaje `st.info()` informativo.
- **TAREA-133 (corrección header):** Se añadió RO-HEADER-04. El header solo cambia con exclusión de comparables activa, no con Retro/Flex/Slider. Funciones `_tiene_exclusion_activa()` y `_should_show_preview_header()` centralizan la lógica.
- **Ahora:** RU-MANUAL-SAVE-02: Save manual NUNCA escribe `auto_valor_usd` desde `auto_result` (cache preview). Solo preserva UV existente o inicializa a 0.
- **Ahora (TAREA-NNN):** Guardrail `_verificar_invariante_auto_valor_usd` eliminado. Detectaba falsos positivos: si `auto_valor_usd == auto_result['valor_propiedad_usd']` (comportamiento NORMAL), lo trataba como contaminación y seteaba a 0, provocando auto card blank. El handler de save manual ya implementa correctamente RU-MANUAL-SAVE-02 preservando `auto_valor_usd` antes de la guardrail.
- **Antes:** sin documentación centralizada de comportamiento UI.
- **Ahora:** esta sección documenta el comportamiento de cada botón. El flujo completo paso a paso (Portfolio → Aplicar selección) está en `docs/FLUJO_UI.md` con todos los session state keys, puntos de decisión y diagrama de estados.

### Guardrails RU
- **RU-HEADER-01**: Auto card usa `n_comps_auto` (del AUTO engine), NO `n_comps` del display (que sigue a `fuente_activa`).
- **RU-HEADER-02**: Auto card oculto si `fuente_activa == 'manual'` y no hay `auto_valor_usd` oficial en UV.
- **RU-MANUAL-SAVE-02**: Save manual NO contamina `auto_valor_usd` con valor preview del cache. Guardrail `_verificar_invariante_auto_valor_usd` eliminado (TAREA-NNN): detectaba falsos positivos.
- **RU-CLEAN-MANUAL-01**: Limpiar comparables (`🔄 Limpiar`) NO borra la valuación manual. Preserva `valor_usd`, `auto_valor_usd`, `manual_valor_usd`, `fuente`, `fuente_activa`, `manual_params`, `retro_dias`, `flex_dormitorios`, `comps`, `m2_equivalentes` y `_comp_excluded`.
- **RU-HEADER-03**: La tarjeta MANUAL es independiente de la disponibilidad de comparables. El gate `< 3` comps solo oculta la tarjeta POR COMPARABLES, no la manual. `n_comps` del property card siempre refleja el auto engine.
- **RO-HEADER-04**: Header solo cambia con exclusión de comparables activa. Retro/Flex/Slider sin exclusión NO cambian el header.
- **RU-AUTO-CONTAMINATION-01**: FALLBACK-102 NUNCA usa `uv_snap['valor_usd']` cuando `uv.fuente != 'auto'`. Usa `uv_snap.get('auto_valor_usd', 0)` para evitar filtrar el valor manual al auto result.
- **RU-COMPCOUNT-CLEAN-01**: FALLBACK-102 setea `n_propiedades=0` en `resolution_metadata` cuando `uv.fuente != 'auto'`, reflejando 0 comps reales del engine post-clean. Esto oculta la auto card automáticamente.

### New Reglas de Oro — Limpieza de Comparables (RO-CLEAN)
- **RO-CLEAN-01 (Limpieza Quirúrgica)**: El botón "Limpiar" borra `_official_result`, `comps` y `auto_valor_usd` de disco. Preserva `manual_params` y resultado manual intactos. Ver test `test_clean_preserva_manual_params`.
- **RO-CLEAN-02 (Estado de Bloqueo/Gating)**: `pendiente_comparables=True` forza al motor a retornar `{valor:0, error:'pendiente'}` y salta cualquier recálculo automático. Ver test `test_pendiente_comparables_bloquea_engine`.
- **RO-CLEAN-03 (Header no se guarda con pendiente)**: `_official_result` NO se guarda si `error == 'pendiente'`. Post-engine exitoso se guarda oficial aunque esté en preview_mode. Ver test `test_official_result_no_se_guarda_si_pendiente`.
- **RO-CLEAN-04 (Unicidad de Disparador)**: Toda la lógica de limpieza reside exclusivamente en el handler del botón "Limpiar". No hay bloques de limpieza "flotantes" en el render flow. Ver test `test_clean_no_hay_zombies_fuera_del_boton`.

---

## 9. ESQUINAS — CORRECCIÓN DE DIRECCIONES VIA CENTROIDE CATASTRAL

### Problema detectado
PHs en intersecciones tienen `direccion_nominatim` incorrecta. Ej: PH 10286 tiene "Entre Ríos 411" pero su parcela catastral (SD=3) está sobre Tucumán → "Tucumán 1291".

### Métricas de detección
| Métrica | Valor |
|---------|-------|
| PHs que comparten coordenadas (esquinas) | 487 grupos, 1.182 PHs |
| PHs con coordenadas >30m del centroide catastral | 251 |
| % de esos con dirección incorrecta (muestra n=25) | 84% (21/25) |
| PHs estimados con dirección incorrecta | ~210 (~1% del total) |

### Corrección aplicada
- **Esquinas corregidas:** 218 PHs (centroide catastral → reverse-geocode → coordenadas + calle correcta)
- **Números interpolados:** 2.219 PHs (nearest-3 IDW en 146 calles con ≥20 referencias)
- **Batch centroide masivo:** +611 PHs recuperados (centroide → reverse → si número directo se acepta; si solo calle se interpola y verifica con forward-geocode <500m)
- **Total completas actual:** 18.870/21.017 (89%)
- **Pendientes:** ~1.301 PHs sin número en calles sin referencias suficientes

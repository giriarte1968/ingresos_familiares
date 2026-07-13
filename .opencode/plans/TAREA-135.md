# TAREA-135: Limpiar preview y todos los comparables que forman la valuación — Riesgo ALTO

## CONTEXTO

Tras TAREA-134 (que intentó corregir el botón "Limpiar" pero causó un loop infinito de rerun), el usuario pregunta explícitamente: **"¿Consideraste que el preview y todos los comparables que forman la valuación se limpien también?"**

### Estado actual del bloque `if clean_flag:` en `valu.py:597-635`

El bloque actual hace lo siguiente:

| # | Operación | ¿Borra comparables? | ¿Borra preview? |
|---|-----------|---------------------|-----------------|
| 1 | `cache_v.pop(prop_name, None)` | ✅ Sí — borra resultado + comps usados | ✅ Sí — borra preview del cache |
| 2 | `p.pop('_ultima_valuacion', None)` (si no tiene manual_params) | ✅ Sí — borra UV del disco | ⚠️ Sí — pero preserva si Manual |
| 3 | `st.session_state.pop('preview_mode_...')` | ❌ No aplica directo | ✅ Sí — borra flag de preview |
| 4 | `st.session_state.pop('_official_result_...')` | ✅ Sí — borra resultado oficial | ✅ Sí — borra official del header |
| 5 | `st.session_state.pop('fuente_activa_...')` | ❌ No aplica | ✅ Sí — fuerza re-lectura de fuente |
| 6 | Session state de retro/flex | ✅ Sí — borra filtros temporales | ✅ Sí |
| 7 | `comp_selection`, `comp_excluded` | ✅ Sí — borra selección/exclusión | ✅ Sí |
| 8 | `manual_preview` | ❌ Es datos manuales, se preserva | ✅ Sí — se borra post-clean |

### Problema detectado

`_official_result` se borra condicionalmente (solo si `fuente_actual != 'manual'`), lo que causa que el header muestre el resultado viejo después de limpiar para propiedades que están en estado manual. **El fix es hacer el pop incondicional.**

### Causa del bug previo (TAREA-134)

TAREA-134 movió la lógica de limpieza de UV fuera del `if clean_flag:` block, y también el `st.rerun()`. Eso causó un loop infinito de rerun porque el código se ejecutaba en cada render. La solución correcta es mantener TODO dentro del `if clean_flag:` block.

## REGLA DE ORO

- **RU-CLEAN-MANUAL-01**: Limpiar comparables NO debe tocar la valuación manual. Preserva `valor_usd`, `auto_valor_usd`, `manual_valor_usd`, `fuente`, `fuente_activa`, `manual_params`, `retro_dias`, `flex_dormitorios`, `comps`, `m2_equivalentes` y `_comp_excluded` en la UV del disco.
- **TODA la lógica dentro del `if clean_flag:` block** — no debe haber código fuera del bloque que ejecute pops o reruns, para evitar loops de rerun.
- **El pop de `_official_result` debe ser incondicional** — no depende de la fuente activa. Siempre que se limpien comparables, se limpia el resultado oficial.
- `auto_validate.py` debe pasar después del cambio.
- `pytest tests/test_regression.py` debe pasar (45+ tests).

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `valu.py` | Líneas 619-622: `_official_result` pop incondicional |
| `.opencode/plans/TAREA-135.md` | Plan creado |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar entrada |

---

### PASO 1: Unconditional `_official_result` pop

**Archivo:** `valu.py` — bloque `if clean_flag:` (líneas 618-622)

**JUSTIFICACIÓN RO:** 
- **RU-CLEAN-MANUAL-01**: El pop de `_official_result` NO afecta la UV en disco. La UV manual se preserva porque el bloque actual ya discrimina por `manual_params` en la sección de disco (líneas 608-613). El `_official_result` es SOLO session state (memoria volátil), no persistencia. El header manual se reconstruye desde la UV del disco al hacer render, no desde `_official_result`. Por lo tanto, este cambio respeta RU-CLEAN-MANUAL-01.
- **No hay loop de rerun**: Todo permanece dentro del `if clean_flag:` block. El `st.rerun()` ya está presente (línea 635) y no se duplica.

**1.1** Reemplazar el pop condicional de `_official_result` por uno incondicional:

```python
# Antes (líneas 619-622):
st.session_state.pop(f'preview_mode_{prop_name}', None)
fuente_actual = st.session_state.get(f'fuente_activa_{prop_name}', p_obj.get('_ultima_valuacion', {}).get('fuente_activa', 'auto'))
if fuente_actual != 'manual':
    st.session_state.pop(f'_official_result_{prop_name}', None)

# Después:
st.session_state.pop(f'preview_mode_{prop_name}', None)
st.session_state.pop(f'_official_result_{prop_name}', None)
```

**COMMIT:** `"fix: unconditional _official_result pop on clean comparables (TAREA-135)"`

**VERIFICAR:**
- `python scripts/auto_validate.py`
- `pytest tests/test_regression.py -v`
- Verificación manual: al hacer Limpiar en una propiedad con fuente manual, el header de comparables debe resetearse pero la tarjeta manual debe permanecer visible

---

### VALIDACION FINAL

```
☐ pytest pasa (45+ tests)
☐ auto_validate.py OK
☐ Sin loops de rerun (verificar con print DEBUG-CLEAN)
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md` (agregar entrada TAREA-135)
- `docs/STATUS_ACTUAL.md` (si aplica)
- `.opencode/plans/TAREAS_INDEX.md` (agregar entrada)

### ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-135.md`.
ID secuencial: 135 (siguiente a TAREA-134).

### ENTREGABLES

- `valu.py` modificado (pop incondicional)
- `pytest` pasando
- `auto_validate.py` OK
- Plan archivado en `.opencode/plans/TAREA-135.md`

# TAREA-137 — Fix header vacío post-Limpiar: guard pendiente no persiste como official — Riesgo BAJO

## CONTEXTO

Cuando el usuario hace clic en "🔄 Limpiar", el flujo es:

1. Botón Limpiar → `pop(_official_result)` → `pendiente_comparables=True` → `st.rerun()`
2. En el rerun, el motor detecta `pendiente_comparables=True` y retorna `{valor:0, error:'pendiente'}`
3. El **First Official auto-save** (línea 1196-1198 en `valu.py`) ve que `_official_result` no existe y **lo guarda** con el resultado pendiente (`valor=0`)
4. Cuando el usuario hace clic en "📊 Comparables", el motor calcula bien, pero `_official_result` **ya existe** (el pendiente), por lo que el First Official no lo sobreescribe
5. El header lee `_official_result` como prioridad → muestra `valor=0` → vacío

### RAÍZ DEL PROBLEMA

```python
# Línea 1196 actual:
if official_key not in st.session_state:
    st.session_state[official_key] = copy.deepcopy(resultado)
# No discrimina si resultado es un "pendiente" con error='pendiente'
```

## REGLA DE ORO

- **RO-CLEAN-03 (NUEVA):** `_official_result` en session state NO debe guardarse cuando `resultado.get('error') == 'pendiente'` — el estado pendiente es transitorio y no debe contaminar el header.
- **RO-CLEAN-01:** La limpieza quirúrgica no debe ser afectada (preserva manual_params, limpia comps y auto_valor_usd).
- **RO-CLEAN-02:** El gating `pendiente_comparables` sigue funcionando igual.
- **RO-CLEAN-04:** La lógica de limpieza sigue en el botón Limpiar exclusivamente.
- **No hay ROs existentes en peligro:** Este cambio solo afecta la persistencia en session state de un resultado transitorio. No afecta ni el motor de valuación, ni la persistencia a disco, ni la lógica de exclusión.

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu.py` (línea 1196) | Agregar guard `resultado.get('error') != 'pendiente'` en el First Official auto-save |
| `valu.py` (~línea 1173, bloque 📊 Comparables) | Forzar update de `_official_result` con el resultado real post-engine |
| `tests/test_regression.py` | Nuevo test `test_official_result_no_se_guarda_si_pendiente` |
| `docs/MEMORIA_PROYECTO.md` | Agregar RO-CLEAN-03 |
| `docs/STATUS_ACTUAL.md` | Agregar RO-CLEAN-03 a Guardrails |
| `docs/BITACORA_AGENTES.md` | Registrar decisión |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar entrada TAREA-137 |

---

### PASO 1: Fix mínimo — Guard en First Official + update post-📊 Comparables

**Archivo:** `valu.py` — bloque First Official auto-save (líneas 1192-1199)

**JUSTIFICACIÓN RO:**
- RO-CLEAN-03: Impedimos que un resultado `error='pendiente'` se guarde como `_official_result`.
- RO-CACHE-PREVIEW-03 (PENDIENTE PRESERVA PREVIEW VÁLIDO): No se viola porque `_official_result` es session state, no cache.
- RO-HEADER-04: El header sigue su lógica actual (lee `_official_result` si existe). Con el fix, `_official_result` solo existirá cuando sea un resultado real.

**1.1** En el bloque "First Official" (~línea 1196), agregar condición `resultado.get('error') != 'pendiente'`:

```python
# ANTES (línea 1196):
if official_key not in st.session_state:

# DESPUÉS:
if official_key not in st.session_state and resultado.get('error') != 'pendiente':
```

**1.2** En el bloque de "📊 Comparables" (donde se setea `act_comparables=True`), forzar update de `_official_result` con el resultado real después de que el motor calcula. Esto asegura que si el First Official no guardó nada (por el guard), el header se actualice explícitamente.

Ubicar el código post-engine donde el motor ya tiene el resultado real (alrededor de la línea ~920-950 o después del bloque `with profile_block("mostrar_detalle_valu_total", p_obj)`). Agregar:

```python
# Después de que el motor termina con resultado real
if resultado.get('error') != 'pendiente' and resultado.get('valor_propiedad_usd', 0) > 0:
    if official_key not in st.session_state:
        st.session_state[official_key] = copy.deepcopy(resultado)
        print(f"[DEBUG-OFFICIAL-FIRST] {prop_name}: official guardado post-engine (primera vez)")
```

**COMMIT:** `"fix: RO-CLEAN-03 — header vacío post-limpiar — pendiente no persiste como official_result"`

**VERIFICAR:**
- `pytest tests/test_regression.py::test_official_result_no_se_guarda_si_pendiente`
- `pytest tests/test_regression.py` (todos)
- `python scripts/auto_validate.py`

---

### PASO 2: Agregar RO-CLEAN-03 a documentación

**Archivos:** `docs/MEMORIA_PROYECTO.md`, `docs/STATUS_ACTUAL.md`

**JUSTIFICACIÓN RO:** Las reglas de oro deben reflejar la lógica vigente. RO-CLEAN-03 documenta el nuevo guard.

**COMMIT:** `"docs: agregar RO-CLEAN-03 a MEMORIA_PROYECTO y STATUS_ACTUAL"`

---

### PASO 3: Actualizar bitácora e índice

**Archivos:** `docs/BITACORA_AGENTES.md`, `.opencode/plans/TAREAS_INDEX.md`

**COMMIT:** `"chore: bitácora TAREA-137 + TAREAS_INDEX actualizado"`

---

### VALIDACION FINAL

```
☐ pytest pasa (48+ tests)
☐ test_official_result_no_se_guarda_si_pendiente pasa
☐ auto_validate.py pasa
☐ Verificación conceptual: el pending no se guarda como official
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `docs/MEMORIA_PROYECTO.md`
- `.opencode/plans/TAREAS_INDEX.md`

### ENTREGABLES

- `valu.py` modificado (guard + update post-engine)
- `tests/test_regression.py` con nuevo test
- Documentación actualizada
- Commit + push a GitHub

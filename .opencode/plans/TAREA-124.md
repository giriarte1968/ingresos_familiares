# TAREA-124: Header independiente auto/manual + Fix n_comps gate bug — Riesgo ALTO

## CONTEXTO

**Bug reportado:** Al guardar valuación manual y luego presionar "🔄 Limpiar" en comparables, el header de valuación manual desaparece.

**Causa raíz — Tres puntos de falla:**

### Punto 1 (PRIMARIO): `render_header` mezcla `n_comps` del display con el gate `< 3`

`valu_detail_sections.py:179,235`

```python
# Linea 179: n_comps viene del display (que sigue a fuente_activa)
n_comps = meta.get('n_propiedades', 0)  # ← manual_result hereda 0 del auto_result fallido

# Linea 235: gate que zerea TODO
if n_comps < 3 or (preview_mode and not ya_valuado):
    v_auto = 0
    v_manual = 0  # ← MANUAL BORRADO porque n_comps=0 < 3!
```

Cuando `fuente_activa='manual'`, `display = manual_result`. `generar_resultado_manual` (`mercado_inmobiliario.py:4098`) copia `n_propiedades` del `auto_result`. Si el auto engine falló (cache fría post-Limpiar), `n_propiedades=0`. Esto activa la condición `n_comps < 3` que zerea AMBAS tarjetas, incluyendo `v_manual`.

### Punto 2: `n_comps` en confianza del property card usa display

`valu_detail_sections.py:305,319` — La confianza y el conteo de comparables usan `n_comps` del display. Cuando `display=manual_result`, muestra "0 comparables" aunque el auto engine pueda tener datos.

### Punto 3: Clean block no preserva `comps` ni `m2_equivalentes`

`valu.py:528-531` — `manual_keys` no incluye `comps` ni `m2_equivalentes`. Esto hace que el fallback TAREA-102 (`valu.py:872`: `uv_snap.get('comps', 0) >= 3`) falle porque `comps` no está en la UV preservada.

## REGLA DE ORO

- `pytest` pasa después de cada paso
- La tarjeta MANUAL en el header es independiente de la tarjeta POR COMPARABLES
- `v_manual` solo se zerea si no hay `manual_result` válido, NO por falta de comparables
- `n_comps` del property card refleja el auto engine, no el display activo
- DEBUG flags rastrean decisión en `[DEBUG-INSUF-COMPS]`
- NO cambiar lógica de valuación ni persistencia

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_detail_sections.py:179-252` | Gate `<3` comps usa `n_comps_auto_hide`; no zerea `v_manual`; `n_comps` desde auto_result |
| `valu.py:528-531` | Agregar `'comps'`, `'m2_equivalentes'` a `manual_keys` |
| `tests/test_regression.py` | Nuevo test `test_manual_card_shows_when_auto_0_comps` |
| `docs/BITACORA_AGENTES.md` | Nueva entrada TAREA-124 |
| `.opencode/plans/TAREAS_INDEX.md` | Nueva entrada TAREA-124 |

---

### PASO 1: Fix `render_header` — desacoplar auto/manual

**Archivo:** `valu_detail_sections.py` — función `render_header` (líneas 130-323)

**1.1** `n_comps` siempre desde `auto_result`, no desde `display`:
```python
# ANTES (linea 179):
n_comps = meta.get('n_propiedades', 0)

# DESPUES:
n_comps = (auto_result.get('resolution_metadata') or {}).get('n_propiedades', 0) if auto_result else 0
```

**1.2** Gate `<3` comps usa `n_comps_auto_hide` y NO zerea `v_manual`:
```python
# ANTES (lineas 235-244):
    if n_comps < 3 or (preview_mode and not ya_valuado):
        print(f"[DEBUG-INSUF-COMPS] {nombre}: n_comps={n_comps}, preview={preview_mode}, ya_valuado={ya_valuado}, "
              f"ocultando valuación en header. v_auto_antes={v_auto}, v_manual_antes={v_manual}, "
              f"UV:auto_valor_usd={auto_valor_uv_auto}, UV:manual_valor_usd={auto_valor_uv_manual}")
        valor_usd = 0
        m2_microzona = 0
        v_auto = 0
        v_manual = 0
        m2_micro_auto = 0
        m2_line_auto = "—"

# DESPUES:
    if n_comps_auto_hide < 3 or (preview_mode and not ya_valuado):
        print(f"[DEBUG-INSUF-COMPS] {nombre}: n_comps_auto_hide={n_comps_auto_hide}, preview={preview_mode}, ya_valuado={ya_valuado}, "
              f"ocultando solo auto card (manual preservado). v_auto_antes={v_auto}, v_manual_antes={v_manual}, "
              f"UV:auto_valor_usd={auto_valor_uv_auto}, UV:manual_valor_usd={auto_valor_uv_manual}")
        valor_usd = 0
        m2_microzona = 0
        v_auto = 0
        m2_micro_auto = 0
        m2_line_auto = "—"
```

**COMMIT:** `"TAREA-124/paso1: header independiente auto/manual — gate <3 no zerea v_manual"`

**VERIFICAR:** `pytest tests/test_regression.py::test_auto_card_hidden_when_engine_failed_after_manual_save`

---

### PASO 2: Fix clean block — preservar `comps` y `m2_equivalentes`

**Archivo:** `valu.py` — bloque clean_comparables (líneas 528-531)

**2.1** Agregar `comps`, `m2_equivalentes` a `manual_keys`:
```python
# ANTES:
                                manual_keys = ('valor_usd', 'auto_valor_usd', 'manual_valor_usd',
                                               'fuente', 'fuente_activa', 'manual_params',
                                               'retro_dias', 'flex_dormitorios',
                                               '_comp_excluded', '_comp_exclusion_applied')

# DESPUES:
                                manual_keys = ('valor_usd', 'auto_valor_usd', 'manual_valor_usd',
                                               'fuente', 'fuente_activa', 'manual_params',
                                               'retro_dias', 'flex_dormitorios',
                                               'comps', 'm2_equivalentes',
                                               '_comp_excluded', '_comp_exclusion_applied')
```

**COMMIT:** `"TAREA-124/paso2: preservar comps + m2_equivalentes en clean de comparables"`

**VERIFICAR:** `pytest tests/test_regression.py::test_clean_comparables_preserves_manual_valuation`

---

### PASO 3: Nuevo test — header muestra manual cuando auto tiene 0 comps

**Archivo:** `tests/test_regression.py` — después del test TAREA-122 (linea 480 aprox.)

**3.1** Agregar test `test_manual_card_shows_when_auto_0_comps`:
- `auto_result.n_propiedades=0` (simula engine fallido post-clean)
- `manual_result.n_propiedades=0` (hereda del auto)
- UV con `valor_usd=735013`, `auto_valor_usd=0`, `fuente='manual'`
- `fuente_activa='manual'`
- Verifica: auto card oculto ("—"), manual card visible ($735,013)

**COMMIT:** `"TAREA-124/paso3: test regression — manual card visible con auto 0 comps"`

**VERIFICAR:** `pytest tests/test_regression.py::test_manual_card_shows_when_auto_0_comps`

---

### VALIDACION FINAL

```
☐ pytest tests/test_regression.py (22 tests)
☐ python scripts/auto_validate.py
☐ Test manual: Guardar manual → Limpiar → header manual visible
☐ Test manual: Sin manual → Limpiar → Pendiente normal
☐ Test manual: Auto engine OK (<3 comps) → header auto oculto, manual visible
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md` — Nueva entrada TAREA-124
- `.opencode/plans/TAREAS_INDEX.md` — Agregar entrada TAREA-124
- `docs/STATUS_ACTUAL.md` — Actualizar estado general

### ARCHIVO DE PLAN

Se guarda en `.opencode/plans/TAREA-124.md`. NO se elimina al ejecutar.

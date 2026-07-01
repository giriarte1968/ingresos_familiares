# TAREA-101 — Reconfiguración visual Parámetros Valuación Manual — Riesgo BAJO

## Contexto

La sección "Parámetros de Valuación Manual" ocupa demasiado espacio vertical:
- 3 filas separadas para 5 campos que deberían estar en una sola línea
- Factor Hedónico muestra 1.xxxx confundiendo al usuario (no es intuitivo)
- El check de "Prima de constructora" desaparece si la propiedad no tiene constructora cargada, dejando solo "Ajuste por tamaño"

## Regla de Oro

- `pytest tests/test_regression.py` pasa 57/57 después de cada paso
- El motor `generar_resultado_manual` NO cambia la lógica de cálculo
- `saved['factor_hedonico']` internamente sigue siendo decimal (1.0 = 100%)
- Los valores existentes en `propiedades.json._ultima_valuacion.manual_params.factor_hedonico` NO se rompen (sigue siendo decimal)
- `generar_resultado_manual` NO se modifica — el cambio es solo UI
- Debug flags según RO-DEBUG-FLAG-01

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_detail_sections.py` — `render_valuacion_manual` | Layout a 5 columnas en un renglón, FH en %, check de constructora siempre visible |

---

### PASO 1: Layout single-row + FH en % + check siempre visible

**Archivo:** `valu_detail_sections.py` — función `render_valuacion_manual` (líneas 1256-1378)

**1.1** Reemplazar las 3 filas de inputs por una sola fila de 5 columnas:

```python
        # Fila única: Ancla | USD/m² | Factor Hed. (%) | Inc. (±%) | Ajuste (%)
        col_a, col_b, col_c, col_d, col_e = st.columns([2, 1, 1, 1, 1])
```

**1.2** Labels cortos para ajustarse al ancho:
- "Ancla" (antes "Ancla de referencia")
- "USD/m²"
- "Factor Hed. (%)" (antes "Factor Hedonico")
- "Inc. (±%)" (antes "Incertidumbre (±%)")
- "Ajuste (%)" (antes "Ajuste porcentual (%)")

**1.3** FH en porcentaje:
- `st.number_input` value = `saved['factor_hedonico'] * 100`
- `fh = st.session_state[f'manual_fh_{nombre}'] / 100.0` (dividir por 100)

**1.4** Caption del ancla movida debajo de la fila (no dentro de columna para evitar desalineación):
```python
    if tiene_ancla:
        st.caption("Valor determinado por el ancla. Deseleccioná el ancla para editar manualmente.")
```

**1.5** Check de constructora siempre visible (quitar condición `if constr_label`):
```python
        with col_g:
            constr_check_label = f"Prima de constructora ({constr_label})" if constr_label else "Prima de constructora"
            saved['incluir_prima_const'] = st.checkbox(
                constr_check_label,
                value=saved.get('incluir_prima_const', True),
                key=f"manual_incluir_const_{nombre}",
            )
```

**1.6** Debug flags: `[DEBUG-VISUAL-101]` en el render de los nuevos campos.

**COMMIT:** `"TAREA-101: Layout single-row Parámetros Valuación Manual (5 cols, FH en %, check constructora siempre visible)"`

**VERIFICAR:** `pytest tests/test_regression.py`

---

### PASO 2: Actualizar preview HTML para FH en %

**Archivo:** `valu_detail_sections.py` — línea 1470

**2.1** Cambiar display de FH en preview HTML:
```html
<div><span style="color:#000000;font-weight:600;">FH:</span> {fh_eff*100:.1f}%</div>
```

**COMMIT:** `"TAREA-101: Preview HTML FH en %"`

**VERIFICAR:** `pytest tests/test_regression.py`

---

### VALIDACION FINAL

```
☐ pytest tests/test_regression.py (57 tests)
☐ Visual: 5 campos alineados horizontalmente en un renglón
☐ Visual: FH muestra "100.0%" para valor neutro
☐ Visual: Check de constructora visible incluso sin constructora asignada
☐ Lógica: generar_resultado_manual recibe factor_hedonico decimal (1.05, no 105)
☐ Lógica: propiedades.json existentes no se rompen
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md`

### ARCHIVO DE PLAN

`.opencode/plans/TAREA-101.md` — guardado permanentemente.

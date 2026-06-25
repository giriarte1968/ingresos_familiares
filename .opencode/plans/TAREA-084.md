## TAREA: TAREA-084 — Revertir fuente única en "Valor/m² por selección" — Riesgo BAJO

### CONTEXTO

El commit `3b60ac2` reemplazó la lectura de `m2_base_venta` del motor en `render_tabla_comparables` por un cálculo local de mediana de los comparables seleccionados. Esto introdujo una **segunda fuente de verdad** para el valor m², causando divergencia con el header:

- **Header** (`render_header` línea 137): usa `display.get('m2_base_venta', 0)` donde `display` se resuelve según `_fuente_activa` (auto_result para modo "Por Comparables", manual_result para modo "Manual").
- **Métrica** (mi cambio): usa mediana simple (P50) de `precio_m2_ajustado` de los comps seleccionados — algoritmo diferente al motor (que usa P33/P40/P45/P50 según CV).

Además, el cálculo local no considera `_fuente_activa`, por lo que en modo manual también leería el valor incorrecto.

**Referencias**: 
- TAREA-079 estableció la fuente única correcta
- TAREA-083 fixeó la colisión checkboxes/motor
- `commit 3b60ac2` introdujo la regresión

### REGLA DE ORO

- "Valor/m² por selección" debe mostrar EXACTAMENTE el mismo valor que el header en cualquier modo (auto o manual) y en cualquier estado (pre-exclusión, exclusión aplicada, re-render)
- `pytest` pasa (32 tests)
- El botón "Aplicar selección" sigue funcionando

### ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_detail_sections.py` | Reemplazar cálculo local de mediana por lectura usando la misma lógica de `display_source` que `render_header` |

---

### PASO 1: Reemplazar cálculo local por display_source

**Archivo:** `valu_detail_sections.py` — `render_tabla_comparables` (líneas 454-481)

**1.1** Eliminar el bloque de cálculo local de mediana (variables `m2_vals`, `sorted_vals`, `m2_median`, etc.)

**1.2** Implementar la misma lógica de resolución `display_source` que `render_header`:
- Si `fuente_activa == 'manual'` y `manual_result` existe → `display_source = manual_result`
- Sino → `display_source = auto_result`
- Leer `m2_base = display_source.get('m2_base_venta', 0)`

**1.3** Mostrar el valor y actualizar caption a "Valor activo • X comps..."

```python
# Antes (mi cambio incorrecto):
        m2_vals = []
        for c in comparables:
            if _get_comp_id(c) in selected_ids:
                ta = c.get('time_adjustment', 1.0)
                vm2 = c.get('precio_m2_ajustado', c.get('precio_m2', 0) * ta)
                m2_vals.append(vm2)
        if m2_vals:
            sorted_vals = sorted(m2_vals)
            n = len(sorted_vals)
            if n % 2 == 1:
                m2_median = sorted_vals[n // 2]
            else:
                m2_median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        else:
            m2_median = 0

        col_a, col_b, col_c = st.columns([1, 2, 1.2])
        with col_a:
            st.metric("Valor/m² por selección", f"${m2_median:,.0f}")
        with col_b:
            st.caption(f"Mediana de selección • {n_sel} comps seleccionados de {len(comparables)} totales")

# Después:
        auto_result = res.get('_auto_result', res)
        manual_result = res.get('_manual_result')
        fuente_activa = res.get('_fuente_activa', 'auto')

        if fuente_activa == 'manual' and manual_result:
            display_source = manual_result
        else:
            display_source = auto_result

        m2_base = display_source.get('m2_base_venta', 0)

        col_a, col_b, col_c = st.columns([1, 2, 1.2])
        with col_a:
            st.metric("Valor/m² por selección", f"${m2_base:,.0f}")
        with col_b:
            st.caption(f"Valor activo • {n_sel} comps seleccionados de {len(comparables)} totales")
```

**COMMIT:** `"fix: revert local median calc, use display_source to sync with header (TAREA-084)"`

**VERIFICAR:** `pytest tests/test_regression.py -v`

---

### VALIDACION FINAL

```
☐ pytest pasa (32 tests)
☐ "Valor/m² por selección" muestra el mismo valor que el header en modo Por Comparables
☐ "Valor/m² por selección" muestra el mismo valor que el header en modo Manual
☐ Desmarcar checkboxes → valor NO cambia (solo cambia al aplicar)
☐ Aplicar selección → valor recalculado coincide con header
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md`

### ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-084.md`.
NO se elimina al ejecutar. Sirve como registro histórico.

### ENTREGABLES

- `valu_detail_sections.py` modificado
- `pytest` pasando (32 tests)
- Sincronización header/métrica verificada en todos los escenarios
- Plan archivado en `.opencode/plans/TAREA-084.md`

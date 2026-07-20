## TAREA: TAREA-140 — Transparencia en cantidad de comparables (muestra vs pool total) — Riesgo BAJO

### CONTEXTO

Cuando el motor encuentra más comparables de los que muestra en pantalla (ej: 300 totales, 60 en pantalla), la UI no informa esta diferencia. El usuario ve "60 comparables" sin saber que la valuación se calculó con 300. Esto falta de transparencia puede generar desconfianza.

### REGLA DE ORO

- Los valores del motor NO cambian (solo se agregan metadatos al dict existente)
- `pytest` pasa después de cada paso
- No se modifica la lógica de cálculo de mediana/percentil

### UI GUARDRAILS

- El caption sobre la tabla de comparables debe informar "X de Y comparables (muestra)" cuando hay truncamiento
- Cuando total = mostrados, mostrar "Y propiedades comparables" (sin "muestra")
- El property card header debe mostrar el total, no solo los mostrados

### ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py:1626` | Agregar `n_pool_total` y `n_mostrados` al meta dict |
| `valu.py:533` | Actualizar caption de comparables |
| `valu_detail_sections.py:304` | Actualizar property card header |
| `valu_detail_sections.py:220` | Actualizar auto card m² line |

---

### PASO 1: Agregar metadatos al engine

**Archivo:** `parsers/mercado_inmobiliario.py` — función `obtener_mediana_cluster_v2()` (línea ~1626)

**JUSTIFICACIÓN RO:** Solo se agregan 2 campos al dict de metadata que ya existe. No se modifica la lógica de cálculo. Los valores del motor no cambian.

**1.1** En la línea donde se construye `meta` dict (línea ~1626), agregar `n_pool_total` y `n_mostrados`:

```python
meta = {
    'percentil_usado': percentil_usado,
    'n_raw': n_raw,
    'n_filtradas': n_filtradas,
    'n_pool_total': len(pool_final),       # NUEVO: total después de filtros
    'n_mostrados': len(comparables_reales), # NUEVO: lo que se muestra en UI
    'radio_usado': radio_usado,
    # ... resto del meta dict sin cambios
}
```

**COMMIT:** `"TAREA-140: agregar n_pool_total y n_mostrados al meta dict"`

**VERIFICAR:**
- `pytest tests/test_regression.py -x -q` (55 tests)
- `pytest tests/test_age_blend_filter.py -x -q` (9 tests)

---

### PASO 2: Actualizar caption de comparables en valu.py

**Archivo:** `valu.py` — línea 533 (caption sobre tabla)

**JUSTIFICACIÓN RO:** Cambio puramente visual en el caption. No afecta lógica de persistencia ni de cálculo.

**2.1** Reemplazar la línea del caption:

```python
# ANTES:
st.caption(f"{n_comps} propiedades comparables")

# DESPUÉS:
n_total = resultado.get('resolution_metadata', {}).get('n_pool_total', len(comparables))
n_mostrados = len(comparables)
if n_total > n_mostrados:
    st.caption(f"{n_mostrados} de {n_total} comparables (muestra)")
else:
    st.caption(f"{n_total} propiedades comparables")
```

**COMMIT:** `"TAREA-140: caption informa muestra cuando total > mostrados"`

**VERIFICAR:**
- `pytest tests/test_regression.py -x -q`
- Verificación visual: cuando pool > 60, caption debe decir "60 de 300 comparables (muestra)"

---

### PASO 3: Actualizar property card header

**Archivo:** `valu_detail_sections.py` — línea 304 (property info card)

**JUSTIFICACIÓN RO:** Cambio visual en el header. No afecta lógica de valuación.

**3.1** Modificar la línea del count_str:

```python
# ANTES:
count_str = f"({n_comps} comparables)"

# DESPUÉS:
n_total = (auto_result.get('resolution_metadata') or {}).get('n_pool_total', n_comps)
n_mostr = (auto_result.get('resolution_metadata') or {}).get('n_mostrados', n_comps)
if n_total > n_mostr:
    count_str = f"({n_total} comparables, {n_mostr} en pantalla)"
else:
    count_str = f"({n_comps} comparables)"
```

**COMMIT:** `"TAREA-140: property card muestra total + mostrados"`

**VERIFICAR:**
- `pytest tests/test_regression.py -x -q`
- Verificación visual en property card

---

### PASO 4: Actualizar auto card m² line

**Archivo:** `valu_detail_sections.py` — línea 220 (auto card m²/USD line)

**JUSTIFICACIÓN RO:** Cambio visual. El m² line ahora muestra total en vez de solo los mostrados.

**4.1** Modificar el m² line del auto card:

```python
# ANTES:
m2_line_auto = f"m²/USD en {zona}: ${m2_micro_auto:,.0f} ({n_comps_auto} comp.)" if m2_micro_auto > 0 else "—"

# DESPUÉS:
n_total_auto = (auto_result.get('resolution_metadata') or {}).get('n_pool_total', n_comps_auto)
m2_line_auto = f"m²/USD en {zona}: ${m2_micro_auto:,.0f} ({n_total_auto} comp.)" if m2_micro_auto > 0 else "—"
```

**COMMIT:** `"TAREA-140: auto card muestra total de comparables"`

**VERIFICAR:**
- `pytest tests/test_regression.py -x -q`
- Verificación visual en auto card

---

### VALIDACION FINAL

```
☐ pytest pasa (64 tests: 55 regression + 9 age_filter)
☐ Caption dice "60 de 300 comparables (muestra)" cuando pool > mostrados
☐ Caption dice "300 propiedades comparables" cuando pool = mostrados
☐ Property card muestra "(300 comparables, 60 en pantalla)"
☐ Auto card m² line muestra "(300 comp.)"
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md` — agregar entrada TAREA-140
- `.opencode/plans/TAREAS_INDEX.md` — agregar TAREA-140

### ARCHIVO DE PLAN

Plan guardado en `.opencode/plans/TAREA-140.md`

### ENTREGABLES

- 4 archivos modificados
- 64/64 tests pasando
- Verificación visual completa
- Plan archivado

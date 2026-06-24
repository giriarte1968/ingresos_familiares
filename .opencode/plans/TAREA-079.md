## TAREA: TAREA-079 — UI: valor/m² refleja motor (no cálculo independiente) — Riesgo BAJO

### CONTEXTO

"Valor/m² por selección" en `render_tabla_comparables` calculaba un percentil/MEDIA independiente
de los comps seleccionados (`p33_p50`), duplicando lógica del motor. Esto causaba inconsistencias:
para n<3 mostraba MEDIA cruda ($4,397) vs header que usa Ancla ($2,914). Incluso con `_m2_puro`
en meta, el valor seguía siendo independiente del motor.

### REGLA DE ORO

- "Valor/m² por selección" debe mostrar exactamente `m2_base_venta` (mismo valor que header)
- El botón "Aplicar selección" debe seguir funcionando
- `pytest` pasa

### ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_detail_sections.py` | Reemplazar cálculo independiente por `m2_base_venta` del motor |

---

### PASO 1: Eliminar cálculo independiente y usar m2_base_venta

**Archivo:** `valu_detail_sections.py` — `render_tabla_comparables` (líneas 385-436)

**1.1** Eliminar variables `p33_p50`, `label_short`, `_m2_puro_val`, `raw_promedio`, `original_puro`

**1.2** La métrica "Valor/m² por selección" ahora muestra `res.get('m2_base_venta', 0)`
con delta `res.get('_m2_puro_t0', 0)` (m² puro original antes de barrera, o el mismo m2_base)

**1.3** Mantener intacto el botón "Aplicar selección"

**COMMIT:** `"fix: UI valor/m² por seleccion usa m2_base_venta del motor"`

**VERIFICAR:** `pytest tests/test_regression.py`

---

### VALIDACION FINAL

```
☐ pytest pasa (32 tests)
☐ UI muestra m2_base_venta en "Valor/m² por selección"
☐ Botón "Aplicar selección" funciona
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md`

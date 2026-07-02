# TAREA-107 — Configuración: georeferencia + año de construcción en Carga de Comparable — Riesgo BAJO

## CONTEXTO

En Configuración → Comparables Manuales, el formulario de alta/edición de comparables manuales no tenía:
1. Georeferencia automática (el usuario debía ingresar lat/lon a mano)
2. Campo "Año de construcción" (dato útil para filtros etarios del motor)

Se agrega botón "📍 Geocodificar dirección" (mismo patrón que `valu_forms.py:122-138`) y campo `anio_construccion`.

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `valu.py` | 3 bloques: data_editor column + Edit form (geocode+año) + Add form (geocode+año) |
| `parsers/manual_comparables.py` | `add_manual()` y `update_manual()` persisten `anio_construccion` |

---

### PASO 1: Data editor column + column_config for anio_construccion

**Archivo:** `valu.py` L1580-1601

**1.1** Agregar `"anio_construccion"` a `_cols`

**1.2** Agregar `st.column_config.NumberColumn("Año", format="%d")` en column_config

---

### PASO 2: Geocode + anio_construccion en Edit form

**Archivo:** `valu.py` L1638-1668

**2.1** Agregar botón "📍 Geocodificar dirección" ANTES de `with st.form()`:
- Lee `calle + num` o `direccion` de session_state
- Llama `geocoding_manager()` 
- Setea lat/lon en session_state

**2.2** Agregar `st.number_input("Año de Construcción")` en `ec2`

---

### PASO 3: Geocode + anio_construccion en Add form

**Archivo:** `valu.py` L1672-1699

**3.1** Agregar botón "📍 Geocodificar dirección" ANTES de `with st.form()`

**3.2** Agregar `st.number_input("Año de Construcción")` en `ac2`

---

### PASO 4: Persistencia en manual_comparables.py

**4.1** `add_manual()`: agregar `"anio_construccion"` al entry dict (default 2000 si no viene)

**4.2** `update_manual()`: agregar `"anio_construccion"` a la actualización

---

### VALIDACION FINAL

```
☐ pytest pasa
☐ auto_validate OK
☐ Botón Geocodificar visible en Edit form → setea lat/lon
☐ Botón Geocodificar visible en Add form → setea lat/lon
☐ Año de construcción visible y persistente en add/edit/table
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md`

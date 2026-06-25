## TAREA: TAREA-080 — UI: reemplazar columna Tipo por Publicado + eliminar tag FLEX — Riesgo BAJO

### CONTEXTO

La tabla de comparables muestra columna "Tipo" (Departamento/Casa/etc.) que es redundante
cuando todos los comps son del mismo tipo. En su lugar, el usuario quiere ver `date_created`
para saber cuándo fue publicado cada comparable. También solicita eliminar el tag FLEX
(el badge púrpura que indica dormitorios flexibles).

### REGLA DE ORO

- `pytest` pasa
- Columnas de la tabla deben mantener proporciones legibles
- `date_created` debe incluirse en `comparables_reales` del motor (2 lugares)

### ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | Agregar `date_created` a `comparables_reales` (2 construcciones) |
| `valu_detail_sections.py` | Reemplazar columna Tipo → Publicado. Eliminar badge FLEX. Eliminar caption flex. |

---

### PASO 1: Agregar `date_created` a `comparables_reales` en el motor

**Archivo:** `parsers/mercado_inmobiliario.py`

**1.1** En la construcción de `comparables_reales` del early return (línea ~1155), agregar `'date_created': p.get('date_created', '')`

**1.2** En la construcción de `comparables_reales` del main path (línea ~1314), agregar `'date_created': p.get('date_created', '')`

**COMMIT:** `"feat: add date_created to comparables_reales (2 sitios)"`

**VERIFICAR:** `pytest tests/test_regression.py`

### PASO 2: Modificar UI — columna Publicado + eliminar FLEX

**Archivo:** `valu_detail_sections.py` — `render_tabla_comparables`

**2.1** Eliminar caption flex (líneas 284-287)

**2.2** Eliminar badge FLEX (líneas 370-371)

**2.3** Cabecera: cambiar ancho de columnas: eliminar Tipo (1→0), agregar Publicado (~0.9)

**2.4** Cabecera: `hdr_labels`: reemplazar 'Tipo' por 'Publicado'

**2.5** En cada fila: reemplazar `cols[6].write(str((c.get('tipo') or '')[:12])...)` por
formato de `date_created` (mostrar DD/MM/YYYY o YYYY-MM-DD)

**COMMIT:** `"fix: columna Tipo → Publicado, eliminar tag FLEX"`

**VERIFICAR:** `pytest tests/test_regression.py`

---

### VALIDACION FINAL

```
☐ pytest pasa (32 tests)
☐ Tabla muestra columna Publicado con date_created
☐ Columna Tipo eliminada
☐ Tag FLEX no aparece en badges
☐ Caption flex eliminado
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md`

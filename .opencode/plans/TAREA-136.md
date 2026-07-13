# TAREA-136: Eliminar bloque zombi de limpieza en valu.py — Riesgo BAJO

## CONTEXTO

Se detectó que el botón "📊 Comparables" dejó de funcionar correctamente. El diagnóstico reveló la existencia de un bloque de código redundante ("zombi") en `valu.py` (líneas 645-684) que ejecutaba la lógica de limpieza en cada renderizado.

Este bloque seteaba `st.session_state[f'pendiente_comparables_{prop_name}'] = True` y llamaba a `st.rerun()` incondicionalmente, anulando la acción del botón "📊 Comparables" (que intenta borrar esa misma flag para iniciar la valuación) y creando un ciclo de reinicio infinito.

La lógica de limpieza ya reside correctamente en el botón "🔄 Limpiar" (líneas 402+), por lo que el bloque en la línea 645 es código muerto y dañino.

## REGLA DE ORO

- **Cero redundancia**: No debe haber lógica de limpieza fuera del disparador explícito (botón Limpiar).
- **Estabilidad de UI**: El botón "📊 Comparables" debe liberar la flag `pendiente_comparables` y permitir que el motor de valuación se ejecute.
- `auto_validate.py` debe pasar.

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu.py` | Eliminar bloque zombi de limpieza (líneas 645-684) |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar entrada TAREA-136 |

---

### PASO 1: Eliminación del bloque zombi

**Archivo:** `valu.py` — líneas 645-684

**JUSTIFICACIÓN RO:** El bloque es redundante y viola la lógica de flujo de la aplicación al forzar un estado de "Pendiente" en cada render. Su eliminación restaura el funcionamiento del botón "📊 Comparables" sin afectar la funcionalidad de "🔄 Limpiar" (que ya está implementada en el botón correspondiente).

**1.1** Borrar el bloque que comienza en `from parsers.debug_logger import log` (línea 645) y termina en `st.rerun()` (línea 684).

**COMMIT:** `"fix: remove zombie cleaning block that blocked comparables button (TAREA-136)"`

**VERIFICAR:**
- `python scripts/auto_validate.py`
- Verificación manual: Botón "🔄 Limpiar" limpia $\rightarrow$ Botón "📊 Comparables" restaura.

---

### VALIDACION FINAL

```
☐ pytest pasa
☐ auto_validate.py OK
☐ Botón Comparables funciona correctamente
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md`

### ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-136.md`.

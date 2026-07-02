# TAREA-106 — Botón "Limpiar" ↔ "Comparables" toggle post-Limpieza — Riesgo BAJO

## CONTEXTO

Después de "🔄 Limpiar" (borra cache + UV + session state), la propiedad queda en estado Pendiente. El flujo Pendiente (`valu.py` L645-657) muestra un mensaje vacío y no hay forma de visualizar comparables sin clickear Retro/Flex.

**Solución**: Que el mismo botón haga toggle entre "🔄 Limpiar" (estado normal) y "📊 Comparables" (post-limpieza). "📊 Comparables" ejecuta el engine con ventana natural (`retro_dias=0`) y muestra los comparables en preview. No requiere `forzar_recalculo` porque el cache ya fue borrado.

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `valu.py` | Botón condicional + cleanup + bypass Pendiente early return + reset post-render |

---

### PASO 1: Implementar cambios en valu.py

**1.1** Agregar `'pendiente_comparables_'` y `'act_comparables_'` a `_PREFIJOS` (L90)

**1.2** Reemplazar botón "🔄 Limpiar" estático por lógica condicional (L358-361):
- Si `pendiente_comparables_{prop_name}` está True → mostrar "📊 Comparables (primary)"
- Si no → "🔄 Limpiar (secondary)" (comportamiento original)

**1.3** En el handler de `clean_comparables_` (L554), antes de `st.rerun()`: setear `pendiente_comparables_{prop_name} = True`

**1.4** En el bloque Pendiente early return (L645): agregar flag `act_comparables` para saltear el early return

**1.5** Antes de `mostrar_detalle_valu` (L970): resetear `pendiente_comparables` → botón vuelve a "Limpiar"

**COMMIT:** `"TAREA-106: Boton Limpiar ↔ Comparables toggle post-limpieza"`

---

### VALIDACION FINAL

```
☐ pytest pasa (59 tests)
☐ auto_validate OK
☐ Flujo: Limpiar → botón "Comparables" → click → muestra comps → botón "Limpiar"
☐ Flujo: Pendiente → Retro/Flex → botón "Limpiar" (no queda colgado "Comparables")
☐ Flujo: Navegación Portfolio → _PREFIJOS limpia claves nuevas
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md`

### ARCHIVO DE PLAN

Permanentemente en `.opencode/plans/TAREA-106.md`. NO se elimina al ejecutar.

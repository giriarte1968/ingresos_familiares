# TAREA-061: Fix Pendiente re-entry detection (check preview_mode flag)

## Problema
El fix de TAREA-060 era demasiado agresivo: en cada rerun de un Pendiente con cache (ej. checkbox deselect), limpiaba el cache y mostraba $0. Esto borraba la lista de comparables al deseleccionar uno.

## Causa
El código no distinguía entre:
- Re-entry real (usuario salió y volvió a la propiedad)
- Interacción de widgets en la misma sesión (checkbox toggle, slider)

## Solución
Agregar guard `preview_mode` al condicional de limpieza:

```python
if resultado_cacheado:
    if not st.session_state.get(f'preview_mode_{p_obj["nombre"]}', False):
        # RE-ENTRY real: preview_mode inactivo → limpiar cache, mostrar $0
        ...
    # preview_mode activo → keep cache, fall through
else:
    # Carga Natural
```

### Tabla de comportamientos

| Escenario | preview_mode | Cache | Acción |
|---|---|---|---|
| 1ra entrada (Carga Natural) | True | no existe | valuar preview |
| Widget interaction (checkbox) | True | existe | mantener cache |
| Click Volver → re-entry | False | existe | limpiar → $0 |

### Commit
`fd63547` — main

# TAREA-112 — Restaurar Pendiente puro (sin auto-run) + Limpiar funcional — Riesgo ALTO

## CONTEXTO

El hotfix de TAREA-111 introdujo un auto-run en el bloque Pendiente cuando no hay cache en disco (`if not resultado_cacheado: forzar = True`). Esto rompió dos comportamientos establecidos del proyecto:

1. **Primera entrada:** El motor corre automáticamente y crea resultados sin que el usuario haya hecho clic en "📊 Comparables" o algún control.
2. **Botón Limpiar:** Borra cache y UV, pero el auto-run recrea la valuación inmediatamente → parece que Limpiar no funciona.

La lógica correcta del proyecto (validada en `tests/test_regression.py::test_limpiar_toggle_comparables_natural` y en la documentación) es:

- **Estado Pendiente (sin UV, sin cache):** El sistema muestra mensaje "Pendiente de valuación" + mapa básico. No corre el motor.
- **Disparador:** El usuario debe hacer clic en "📊 Comparables", Retro o Flex para iniciar el motor.
- **Única excepción:** Cache envenenado (error técnico) → el sistema limpia y forza recálculo para recuperación automática (TAREA-110).

## REGLA DE ORO

- `pytest` pasa (≥63 tests)
- Primera entrada sin UV/cache → mensaje Pendiente (NO engine run)
- Post-Limpiar → mensaje Pendiente (NO engine run)
- Cache envenenado → se limpia y forza recálculo (como antes)
- Botón Limpiar → borra cache + UV + session state → Pendiente
- Botón "📊 Comparables" → corre motor en preview

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu.py` | Eliminar auto-run SIN CACHE (líneas 594-604). Mantener poisoned cache recovery. Agregar debug flag en early return. |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar entrada TAREA-112 |
| `docs/BITACORA_AGENTES.md` | Registrar decisión |

---

### PASO 1: Eliminar auto-run SIN CACHE en Pendiente block

**Archivo:** `valu.py` — bloque Pendiente (líneas 594-604)

**1.1** Eliminar el bloque `if not resultado_cacheado and not cache_valido:` que implementaba auto-run para post-Limpiar.

**1.2** Mantener intacto el bloque de poisoned cache recovery (`if resultado_cacheado and cache_preview:` con limpieza y `forzar=True`).

**1.3** Agregar debug flag `[DEBUG-FLOW] ... EARLY RETURN — Pendiente puro` en la condición de early return.

```python
# Antes (a eliminar):
                # Sin cache en disco: auto-run solo si es post-Limpiar (TAREA-111)
                if not resultado_cacheado and not cache_valido:
                    auto_run = st.session_state.get(f'pendiente_comparables_{p_obj["nombre"]}', False)
                    if auto_run:
                        print(f"[DEBUG-FLOW] {p_obj['nombre']}: SIN CACHE (post-Limpiar) — forzando engine run (preview)")
                        forzar = True
                        preview_mode = True
                        st.session_state[f'preview_mode_{p_obj["nombre"]}'] = True
                        st.session_state.pop(f'pendiente_comparables_{p_obj["nombre"]}', None)
                    else:
                        print(f"[DEBUG-FLOW] {p_obj['nombre']}: SIN CACHE (primera entrada) — NO auto-run, esperando accion usuario")

# Despues:
                # (eliminado: el auto-run SIN CACHE rompia Limpiar y violaba el flujo Pendiente)
```

**COMMIT:** `"TAREA-112: Restaurar Pendiente puro sin auto-run"`

**VERIFICAR:** `pytest tests/test_regression.py`

### VALIDACION FINAL

```
☐ pytest pasa (≥63 tests)
☐ No hay auto-run en Pendiente block
☐ Cache envenenado sigue recuperandose automaticamente
☐ Boton Limpiar → Pendiente (mensaje + mapa)
☐ Boton Comparables → corre motor
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md` (agregar entrada de la tarea ejecutada)

### ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-112.md`.
ID secuencial: 112 (posterior a TAREA-111).

### ENTREGABLES

- `valu.py` modificado (eliminar auto-run SIN CACHE)
- `pytest` pasando
- Plan archivado en `.opencode/plans/TAREA-112.md`

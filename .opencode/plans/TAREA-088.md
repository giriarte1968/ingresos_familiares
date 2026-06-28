## TAREA: TAREA-088 — Fix "🔄 Limpiar" no borra valuación manual — Riesgo BAJO

### CONTEXTO

El botón "🔄 Limpiar" en `valu.py:322` está diseñado para limpiar comparables y resetear el estado de valuación. Sin embargo, cuando la propiedad tiene una valuación manual (`manual_params` presente en `_ultima_valuacion`), el handler en `valu.py:490-498` preserva `_ultima_valuacion` intacta (solo cambia `fuente` a `'manual'`).

Al volver al Portfolio, `_cargar_resultados_cache()` en `valu_portfolio2.py:304-316` no encuentra entrada en caché (fue limpiada), pero cae al **fallback** que lee `ultima.get("valor_usd")` directamente de `propiedades.json`, mostrando el valor viejo ($738,513 en el caso de Francia 250b).

**Confirmado por debug log:**
- Line 168: `uv_fuente=manual`, `uv_keys` contiene `manual_params`
- La propiedad tenía valuación manual activa antes del click en "🔄 Limpiar"

### REGLA DE ORO

- `pytest` pasa después del cambio
- "🔄 Limpiar" ahora borra SIEMPRE `_ultima_valuacion`, incluso si hay `manual_params`
- No se afecta el motor de valuación ni la lógica de preview
- El botón "Eliminar Valuacion Manual" (valu_detail_sections.py:1523) sigue funcionando como antes (solo cambia fuente)

### ALCANCE

| Archivo | Cambio |
|---|---|
| `valu.py:490-498` | Eliminar condicional `if uv.get('manual_params')` → siempre `p.pop('_ultima_valuacion', None)` |

---

### PASO 1: Eliminar preservación de manual_params en handler "🔄 Limpiar"

**Archivo:** `valu.py` — Handler del botón "🔄 Limpiar" (líneas 490-498)

**1.1** Reemplazar el bloque condicional por un `p.pop('_ultima_valuacion', None)` incondicional.

```python
# ANTES (líneas 490-498):
                    props = cargar_propiedades()
                    for p in props:
                        if p.get('nombre') == prop_name:
                            uv = p.get('_ultima_valuacion', {})
                            if uv.get('manual_params'):
                                uv['fuente'] = 'manual'
                                uv['fuente_activa'] = 'manual'
                            else:
                                p.pop('_ultima_valuacion', None)
                            break
                    guardar_propiedades(props)

# DESPUÉS:
                    props = cargar_propiedades()
                    for p in props:
                        if p.get('nombre') == prop_name:
                            p.pop('_ultima_valuacion', None)
                            break
                    guardar_propiedades(props)
```

**COMMIT:** `"fix(TAREA-088): 🔄 Limpiar borra siempre _ultima_valuacion, incluso manual"`

**VERIFICAR:** `python scripts/auto_validate.py` + `pytest tests/test_regression.py`

---

### VALIDACION FINAL

```
☐ auto_validate.py pasa sin errores
☐ pytest tests/test_regression.py pasa
☐ Tras click "🔄 Limpiar" en propiedad con valuación manual, el Portfolio muestra "Pendiente"
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md` — Registrar decisión y fix
- `docs/STATUS_ACTUAL.md` — Actualizar estado
- `.opencode/plans/TAREAS_INDEX.md` — Agregar entrada TAREA-088

### ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-088.md`.
ID secuencial: 088 (siguiente al último en TAREAS_INDEX.md que es 087).

### ENTREGABLES

- `valu.py` modificado
- `auto_validate.py` pasando
- `pytest` pasando
- Plan archivado en `.opencode/plans/TAREA-088.md`
- Commit + push a GitHub

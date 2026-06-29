## TAREA: TAREA-089 — Preview mode no persiste valuación vía exclusión restaurada — Riesgo BAJO

### CONTEXTO

Cuando una propiedad tiene `_comp_exclusion_applied=True` en su UV (por haber clickeado "Aplicar selección" previamente), y el usuario activa Retro/Flex (preview mode), el flujo en `valu.py:744-746` setea `from_apply = True` automáticamente porque detecta la exclusión vieja en UV. Esto hace que las líneas 814-822 persistan el nuevo valor de preview a `_ultima_valuacion` con `commit=True`, sin que el usuario haya clickeado "Aplicar selección".

El motor (`valuar_con_cache` en `motor_vpp_core.py:1433`) ya usa `commit=not preview` correctamente, pero la persistencia explícita en `valu.py:822` lo salta.

### REGLA DE ORO

- `pytest` pasa después del cambio
- En preview mode (Retro/Flex activo), el valor preview NUNCA se persiste a `_ultima_valuacion`
- Cuando el usuario clickea "Aplicar selección" (path session_state), la persistencia SÍ ocurre
- El header de UI muestra correctamente el valor preview aunque no se persista
- El botón "Restablecer todos" (reset_key) sigue funcionando igual

### ALCANCE

| Archivo | Cambio |
|---|---|
| `valu.py:744` | Agregar `not preview_mode and` al `elif` de restauración desde UV |
| `valu.py:747` | Actualizar print con contexto de preview_mode |
| `valu.py:831-832` | Agregar `[DEBUG-PERSIST-SKIP]` en else de from_apply |

---

### PASO 1: Guardar from_apply=False en preview mode

**Archivo:** `valu.py` — Exclusión restoration desde UV (líneas 744-747)

**1.1** Agregar `not preview_mode and` al `elif` para evitar que `from_apply=True` se setee en preview mode.

**1.2** Actualizar el print para incluir el contexto de preview_mode.

```python
# ANTES (líneas 744-747):
                            elif p_obj.get('_ultima_valuacion', {}).get('_comp_exclusion_applied'):
                                excluded_ids = p_obj['_ultima_valuacion'].get('_comp_excluded', [])
                                from_apply = True
                                print(f"[APPLY] {prop_name}: Restaurando exclusión desde _ultima_valuacion, {len(excluded_ids)} comps excluidos")

# DESPUÉS:
                            elif not preview_mode and p_obj.get('_ultima_valuacion', {}).get('_comp_exclusion_applied'):
                                excluded_ids = p_obj['_ultima_valuacion'].get('_comp_excluded', [])
                                from_apply = True
                                print(f"[APPLY] {prop_name}: Restaurando exclusión desde _ultima_valuacion, {len(excluded_ids)} comps excluidos, preview_mode={preview_mode}")
```

**COMMIT:** `"fix(TAREA-089): preview mode no persiste valuación vía exclusión restaurada"`

**VERIFICAR:** `python scripts/auto_validate.py` + `pytest tests/test_regression.py`

---

### PASO 2: Debug flag PERSIST-SKIP

**Archivo:** `valu.py` — else de from_apply (línea 831-832)

**2.1** Agregar `[DEBUG-PERSIST-SKIP]` print cuando preview mode evita la persistencia.

```python
# ANTES (líneas 831-832):
                            else:
                                resultado['_comp_exclusion_applied'] = False

# DESPUÉS:
                            else:
                                if preview_mode:
                                    print(f"[DEBUG-PERSIST-SKIP] {prop_name}: preview activo, NO persiste (from_apply={from_apply}, excluded={excluded_ids})")
                                resultado['_comp_exclusion_applied'] = False
```

---

### VALIDACION FINAL

```
☐ auto_validate.py pasa sin errores
☐ pytest tests/test_regression.py pasa (especial atención a test_flow_manual_preserva_exclusion y test_toggle_fuente_preserva_exclusion)
☐ En UI: activar Retro en propiedad con exclusión aplicada → header muestra preview → NO persiste a propiedades.json
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md` — Agregar entrada TAREA-089

### ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-089.md`.
ID secuencial: 089.

### ENTREGABLES

- `valu.py` modificado (2 cambios)
- `auto_validate.py` pasando
- `pytest` pasando
- Plan archivado en `.opencode/plans/TAREA-089.md`
- Commit + push a estabilizar

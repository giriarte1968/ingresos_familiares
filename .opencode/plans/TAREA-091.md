## TAREA: TAREA-091 — Valuación fallida no debe pisar cache/UV válido — Riesgo BAJO

### CONTEXTO

Cuando `valuar_con_cache` recalcula con parámetros distintos a los cacheados (ej: el cache tiene Retro/Flex, pero la entrada al detalle es sin Retro), y el nuevo cálculo falla (`insuficientes_comparables`), el motor persiste el error con `commit=True` — lo que sobrescribe el `_ultima_valuacion` y el cache con `valor_usd=None`.

Esto ocurrió con Francia 250b:
- Cache tenía resultado válido ($665,387) con Retro=36, Flex=[1,2,3,4,5]
- Usuario entró al detalle sin Retro → caché params no matchean → recalcula → 0 comps → `persistir_valuacion(commit=True, valor_usd=None)` → UV y cache destruidos

El guard existente en `motor_vpp_core.py:1422-1428` solo protegía contra previews fallidos (`preview=True`). No cubría valuaciones oficiales (`preview=False`).

### REGLA DE ORO

- `pytest` pasa después del cambio
- Una valuación fallida NUNCA sobrescribe un cache/UV con `valor_usd` válido
- Si el cache tiene un resultado válido y el nuevo cálculo falla, se devuelve el resultado cacheadO (con marcador de "stale")
- Si NO hay resultado previo válido, el error se persiste normalmente
- `[DEBUG-SKIP-PERSIST]` registra cada vez que se saltea persistencia

### ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/motor_vpp_core.py:1422-1428` | Expandir guard a cualquier resultado fallido (no solo preview) |
| `parsers/motor_vpp_core.py:1427-1428` | Devolver resultado cacheadO existente cuando se saltea persist |
| `parsers/motor_vpp_core.py:1427-1428` | Agregar `[DEBUG-SKIP-PERSIST]` con contexto completo |

---

### PASO 1: Expandir guard y devolver caché

**Archivo:** `parsers/motor_vpp_core.py` — bloque guard post-valuación (líneas 1421-1436)

**1.1** Eliminar condición `preview and` — el guard debe aplicar siempre que el resultado sea fallido.

**1.2** Devolver el resultado cacheadO existente cuando se saltea persist, para que la UI muestre el valor previo.

```python
# ANTES (líneas 1421-1436):
        with profile_block("vcc_persistir_valuacion", prop):
            _vl.mark("before_persistir_valuacion")
            # Guard: failed preview should not overwrite successful cache entry
            _skip_persist = False
            if preview and (resultado.get('error') or not resultado.get('valor_propiedad_usd')):
                _existing = cache.get(nombre, {}).get('resultado_completo', {})
                if _existing.get('valor_propiedad_usd', 0) > 0 and not _existing.get('error'):
                    _skip_persist = True
                    _exist_retro = _existing.get('_cache', {}).get('retro_dias', '?')
                    print(f"[CACHE-PREVIEW-SKIP] {nombre}: preview fallido ({resultado.get('error', 'sin_valor')}) — NO se persiste, cache exitoso preservado ({_existing.get('valor_propiedad_usd'):,.0f} USD, {_exist_retro}d)")
            if not _skip_persist:
                if preview:
                    _status = 'exitoso' if resultado.get('valor_propiedad_usd') else 'fallido-sin-cache-previo'
                    print(f"[CACHE-PREVIEW-PERSIST] {nombre}: preview {_status} — persistiendo a cache")
                ok_persist = persistir_valuacion(nombre, prop, resultado, cache, commit=not preview, manual_data=manual_data)
            else:
                ok_persist = True
            _vl.mark("after_persistir_valuacion")

# DESPUÉS:
        with profile_block("vcc_persistir_valuacion", prop):
            _vl.mark("before_persistir_valuacion")
            _skip_persist = False
            if resultado.get('error') or not resultado.get('valor_propiedad_usd'):
                _existing = cache.get(nombre, {}).get('resultado_completo', {})
                if _existing.get('valor_propiedad_usd', 0) > 0 and not _existing.get('error'):
                    _skip_persist = True
                    _exist_valor = _existing.get('valor_propiedad_usd', 0)
                    _exist_error = _existing.get('error')
                    _exist_retro = _existing.get('_cache', {}).get('retro_dias', '?')
                    _exist_flex = _existing.get('_cache', {}).get('flex_dormitorios')
                    _exist_preview = _existing.get('_cache', {}).get('preview', '?')
                    _new_error = resultado.get('error', 'sin_valor')
                    _new_retro = resultado.get('_cache', {}).get('retro_dias', 0)
                    _new_flex = resultado.get('_cache', {}).get('flex_dormitorios')
                    _modo = "(preview)" if preview else "(oficial)"
                    print(f"[DEBUG-SKIP-PERSIST] {nombre}: {_modo} fallido ({_new_error}) — NO persiste. Cache previo: ${_exist_valor:,.0f} USD, retro={_exist_retro}d, flex={_exist_flex}, preview={_exist_preview}")
                    resultado = _existing
            if not _skip_persist:
                if preview:
                    _status = 'exitoso' if resultado.get('valor_propiedad_usd') else 'fallido-sin-cache-previo'
                    print(f"[CACHE-PREVIEW-PERSIST] {nombre}: preview {_status} — persistiendo a cache")
                ok_persist = persistir_valuacion(nombre, prop, resultado, cache, commit=not preview, manual_data=manual_data)
            else:
                ok_persist = True
            _vl.mark("after_persistir_valuacion")
```

**COMMIT:** `"fix(TAREA-091): valuacion fallida no pisa cache/UV valido — guard expandido"`

**VERIFICAR:** `python scripts/auto_validate.py` + `pytest tests/test_regression.py`

---

### VALIDACION FINAL

```
☐ auto_validate.py pasa
☐ pytest (47 tests) pasa
☐ En UI: al entrar a propiedad con cache valido pero params diferentes, si engine falla, se muestra el valor cacheadO (con error logueado)
☐ Log muestra [DEBUG-SKIP-PERSIST] con contexto (valor previo, params, error nuevo)
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md`

### ARCHIVO DE PLAN

Permanente en `.opencode/plans/TAREA-091.md`. ID secuencial: 091.

### ENTREGABLES

- `parsers/motor_vpp_core.py` modificado
- Tests pasando
- Commit + push a estabilizar

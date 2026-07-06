# TAREA-122 — Fix auto card leak: cache preview contamina auto_valor_usd — Riesgo ALTO

## CONTEXTO

Al guardar valuación manual, el header de "POR COMPARABLES" muestra un valor STALE del cache preview ($590K para Francia 250b) aunque el auto engine NUNCA se aplicó oficialmente.

## CAUSA RAÍZ — DOS PUNTOS DE FALLA

### Punto 1 (PRIMARIO): Save manual contamina `auto_valor_usd` con cache preview

`valu_detail_sections.py:1566-1591`

```python
auto_valor_usd = auto_result.get('valor_propiedad_usd', 0)  # ← cache preview devuelve $590K!
...
if auto_valor_usd > 0:                                        # $590K > 0 → True
    uv['auto_valor_usd'] = auto_valor_usd                     # ← CONTAMINA UV con preview!
```

La guarda `auto_valor_usd > 0` chequea si hay valor PERO NO chequea si ese valor es oficial (aplicado) o es un preview del cache. El cache preview SIEMPRE devuelve valor si hay datos, por lo que el guardado manual siempre escribe el preview en UV.

### Punto 2 (SECUNDARIO): `ocultar_auto` chequeaba `preview_mode` que es False tras save

El fix `fuente_activa == 'manual'` ya está aplicado (edición previa en línea 234), pero es insuficiente porque el Punto 1 ya contaminó `auto_valor_usd`.

## REGLA DE ORO

- `pytest` pasa después de cada paso
- `auto_valor_usd` en UV solo se actualiza cuando el AUTO ENGINE se aplica oficialmente
- El save manual NO debe contaminar `auto_valor_usd` con valores preview del cache
- DEBUG flags suficientes para rastrear el flujo

## UI GUARDRAILS

- RU-HEADER-01: Auto card usa `n_comps_auto` del auto engine, no del display (✅ ya aplicado)
- RU-HEADER-02: Auto card oculto si `fuente_activa=='manual'` y `auto_valor_usd==0` (✅ ya aplicado)
- RU-MANUAL-SAVE-02 (NUEVO): Save manual NO escribe `auto_valor_usd` desde auto_result

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_detail_sections.py:1588-1591` | Reemplazar lógica de contaminación con `uv.setdefault('auto_valor_usd', 0)` |
| `valu_detail_sections.py:1566-1573` | Agregar DEBUG: origen de auto_valor (UV/cache/preview) |
| `valu_detail_sections.py:234` | DEBUG: flag de decisión ocultar_auto (✅ ya aplicado parcialmente) |
| `tests/test_regression.py` | Actualizar test TAREA-121 para validar que save manual no contamina auto_valor_usd |
| `docs/BITACORA_AGENTES.md` | Nueva entrada TAREA-122 |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar entrada TAREA-122 |

---

### PASO 1: Fix RU-MANUAL-SAVE-02 + DEBUG flags

**Archivo:** `valu_detail_sections.py` — `render_valuacion_manual` (líneas 1566-1606) + `render_header` (línea 234)

**1.1** Reemplazar lógica contaminante:
```python
# ANTES:
auto_valor_usd = auto_result.get('valor_propiedad_usd', 0) if auto_result else 0
...
if auto_valor_usd > 0:
    uv['auto_valor_usd'] = auto_valor_usd
elif 'auto_valor_usd' not in uv:
    uv['auto_valor_usd'] = 0

# DESPUÉS:
# RU-MANUAL-SAVE-02: Preservar auto_valor_usd oficial de UV.
# El auto_result puede venir del cache preview (valor STALE no oficial).
# Solo preservar el valor existente en UV o inicializar a 0.
auto_valor_origen = 'uv_preservado' if ('auto_valor_usd' in uv and uv.get('auto_valor_usd', 0) > 0) else 'uv_init_0'
uv.setdefault('auto_valor_usd', 0)
```

**1.2** Agregar DEBUG flag `[DEBUG-MANUAL-SAVE-ORIGEN]` con origen de `auto_valor_usd`:
```python
print(f"[DEBUG-MANUAL-SAVE-ORIGEN] {nombre}: auto_valor_usd={uv['auto_valor_usd']}, "
      f"origen={auto_valor_origen}, auto_result_valor={auto_result.get('valor_propiedad_usd','N/A') if auto_result else 'NONE'}")
```

**1.3** Agregar DEBUG flag en `[DEBUG-INSUF-COMPS]` línea 246 con `fuente_activa`:
Agregar `fuente_activa={fuente_activa}` al print existente.

**COMMIT:** `"TAREA-122: RU-MANUAL-SAVE-02 + DEBUG flags — auto card leak fix"`

**VERIFICAR:** `pytest`

---

### VALIDACION FINAL

```
☐ pytest pasa (10 tests)
☐ test_auto_card_hidden_when_engine_failed_after_manual_save pasa
☐ auto_validate.py OK
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md`

### ARCHIVO DE PLAN

Se guarda en `.opencode/plans/TAREA-122.md`. NO se elimina al ejecutar.

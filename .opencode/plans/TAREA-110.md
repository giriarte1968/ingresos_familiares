# TAREA-110 — Cache poisoning fix: VCC nunca debe persistir errores

## CONTEXTO
TAREA-109 introdujo `NameError` por variable `nombre` no definida en 3 prints. Cuando el motor crasheaba con excepción, VCC (`motor_vpp_core.py:1405-1407`) creaba un dict mínimo `{'error': str(e), 'valor_propiedad_usd': 0}` sin `comparables_venta`. Si no existía caché previo bueno, este error se persistía como entry oficial. En cargas posteriores, `necesita_recalcular()` veía hashes iguales → servía el error sin llamar al motor.

## REGLA DE ORO
- `pytest tests/test_regression.py` pasa 61/61
- Caché existente con datos válidos NO debe perderse
- UI debe mostrar comparables incluso cuando el motor falla (con fallback a caché previo)
- Debug flags NUNCA deben causar NameError

## ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/valuacion_cache.py` | `necesita_recalcular()` detecta caché envenenada |
| `parsers/motor_vpp_core.py` | Exception handler incluye `comparables_venta` en error dict |
| `tests/test_regression.py` | Test cache poisoning detection + test retro bypass acepta cache_envenenada |
| `docs/BITACORA_AGENTES.md` | Registrar TAREA-110 |

---

### PASO 1: `necesita_recalcular` detecta caché envenenada

**Archivo:** `parsers/valuacion_cache.py` — `necesita_recalcular()` (L95-121)

**1.1** Agregar check post-`nombre not in cache`: si `resultado_completo` tiene `error` o `valor_propiedad_usd` falsy → `"cache_envenenada"`.

```python
    rc = entrada.get('resultado_completo', {})
    if rc.get('error') or not rc.get('valor_propiedad_usd'):
        return True, "cache_envenenada"
```

**COMMIT:** (incluido en commit final)

**VERIFICAR:** `pytest` (61/61)

---

### PASO 2: Exception handler incluye `comparables_venta`

**Archivo:** `parsers/motor_vpp_core.py` — `valuar_con_cache()` L1405-1407

**2.1** Reemplazar dict mínimo por uno con claves que espera la UI:

```python
        except Exception as e:
            logger.error(f"Error en valuar_propiedad_v7: {e}")
            resultado = {'error': str(e), 'valor_propiedad_usd': 0, 'comparables_venta': [], 'resolution_metadata': {}}
```

**COMMIT:** (incluido en commit final)

**VERIFICAR:** `pytest` (61/61)

---

### PASO 3: Test cache poisoning recovery

**Archivo:** `tests/test_regression.py`

**3.1** `test_cache_poisoning_detection`: verifica que:
- `necesita_recalcular` detecta `"cache_envenenada"`
- Cache sano con hashes correctos dice `"cache_valido"`
- `valuar_con_cache` se recupera de cache envenenada en disco

**3.2** `test_retro_bypass_respeta_cambio_dias`: acepta `"cache_envenenada"` como razón válida (además de `"parametros_cambiados"`).

**COMMIT:** (incluido en commit final)

**VERIFICAR:** `pytest` (61/61)

---

### VALIDACION FINAL

```
☐ pytest pasa (61 tests)
☐ cache_envenenada detectado correctamente
☐ Exception handler devuelve dict completo
☐ Debug flags libres de NameError
```

### DOCS A ACTUALIZAR
- `docs/BITACORA_AGENTES.md` — registrar TAREA-110
- `.opencode/plans/TAREAS_INDEX.md` — agregar entrada TAREA-110 + TAREA-108/109 faltantes

### ENTREGABLES
- `parsers/valuacion_cache.py` modificado
- `parsers/motor_vpp_core.py` modificado
- `tests/test_regression.py` modificado (1 test nuevo, 1 test actualizado)
- 61/61 tests pasando

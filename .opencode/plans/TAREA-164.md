# TAREA-164 — Fix zone change no resetea _comp_exclusion_applied — Riesgo BAJO

## CONTEXTO

Cuando el usuario cambia la zona de una propiedad (ej. "Centro" -> "Republica de la Sexta"), el boton de comparables deberia cambiar a "Aplicar seleccion" pero queda en "Seleccion aplicada". Esto ocurre porque `_limpiar_estado_propiedad()` solo limpia session state, NO limpia `_comp_exclusion_applied` de `_ultima_valuacion` en disco. `_should_restore_excl()` lee el flag viejo y lo inyecta en el resultado nuevo.

## REGLA DE ORO

- Cambios estructurales (zona, lat, lon, dormitorios) DEBEN resetear `_comp_exclusion_applied` en disco
- `pytest` pasa despues de cada paso

## PASO 1: Fix en `actualizar_propiedad()`

**Archivo:** `valu.py` linea 755-764

```python
if cambio_estructural:
    _limpiar_estado_propiedad(prop_name)
    # TAREA-164: limpiar exclusion en disco
    uv = p_obj.get('_ultima_valuacion', {})
    if uv:
        uv['_comp_exclusion_applied'] = False
        uv['_comp_excluded'] = []
    # cache clear
    cache_v = cargar_cache_valuaciones()
    cache_v.pop(prop_name, None)
    guardar_cache_valuaciones(cache_v)
```

## PASO 2: Debug flag en `_should_restore_excl()`

**Archivo:** `valu.py` linea 613-635

Agregar print con `[DEBUG-EXCL-RESTORE]` antes del return.

## PASO 3: Test de regresion

```python
def test_zone_change_resets_exclusion_applied():
    """TAREA-164: cambiar zona resetea _comp_exclusion_applied en disco."""
```

## VERIFICACION

1. `python -m pytest tests/test_regression.py -v`
2. `python scripts/auto_validate.py`
3. Probar en UI: cambiar zona -> boton debe cambiar a "Aplicar seleccion"
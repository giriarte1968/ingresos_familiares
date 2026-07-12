# TAREA-134: Corregir botón "Limpiar" de comparables (RU-CLEAN-MANUAL-01)

## 🚩 Objetivo
El botón "🔄 Limpiar" en la sección de comparables debe seguir funcionando como hasta ahora (limpiar caché, selección, session state de comparables), pero **NUNCA debe tocar la valuación manual ni su header**. Se violó la regla de oro **RU-CLEAN-MANUAL-01** porque el código borraba la UV del disco sin discriminar entre fuente auto y manual.

## 🔍 Diagnóstico (código actual en `valu.py:597-639`)

El bloque `if clean_flag:` hace 4 cosas, 3 de ellas incorrectas para fuente manual:

| # | Operación | Línea | Fuente Auto | Fuente Manual |
|---|-----------|-------|-------------|---------------|
| 1 | `cache_v.pop()` | 601 | ✅ Borrar caché | ✅ Borrar caché |
| 2 | `p.pop('_ultima_valuacion')` + `guardar_propiedades()` | 611-618 | ✅ Limpiar UV auto | ❌ **Destruye UV manual** |
| 3 | `st.session_state.pop('_official_result_...')` | 626 | ✅ Limpiar header auto | ❌ **Destruye header manual** |
| 4 | `st.session_state.pop('fuente_activa_...')` | 636 | ✅ Limpiar fuente auto | ❌ **Destruye fuente manual** |

**Causa raíz**: El código no discrimina entre fuente auto y manual. Trata ambas igual.

## 📋 Pasos de implementación

### Paso 1: Preservar UV en disco para fuente manual
**Archivo**: `valu.py`
**Líneas**: 606-618

Cambiar para que solo se borre la UV si `fuente != 'manual'`:

```python
uv_old = p.get('_ultima_valuacion', {})
tiene_manual = uv_old.get('fuente') == 'manual' or uv_old.get('fuente_activa') == 'manual'
if tiene_manual:
    print(f"[DEBUG-CLEAN] {prop_name}: UV manual preservada (RU-CLEAN-MANUAL-01)")
else:
    p.pop('_ultima_valuacion', None)
    print(f"[DEBUG-CLEAN] {prop_name}: UV auto limpiada")
```
Si es manual, NO se llama a `guardar_propiedades()` (no tocar disco).

### Paso 2: Preservar `_official_result` para fuente manual
**Archivo**: `valu.py`
**Línea**: 626

```python
if not tiene_manual:
    st.session_state.pop(f'_official_result_{prop_name}', None)
```

### Paso 3: NO borrar `fuente_activa` del session state
**Archivo**: `valu.py`
**Línea**: 636

Eliminar la línea `st.session_state.pop(f'fuente_activa_{prop_name}', None)`.
Si la fuente es auto, la línea 1004 (`st.session_state.get(f'fuente_activa_{prop_name}', uv.get('fuente_activa', 'auto'))`) usará el fallback de la UV que recién se limpió.
Si la fuente es manual, el session state retiene `'manual'` y el header se muestra correctamente.

### Paso 4: Agregar variable `tiene_manual` fuera del try
La variable `tiene_manual` se necesita en los pasos 1, 2 y 3, pero actualmente está dentro del bloque `for p in props:` dentro del `try`. Moverla a un ámbito accesible.

### Paso 5: Test de regresión
**Archivo**: `tests/test_regression.py`

Nuevo test `test_clean_comparables_preserves_manual_uv`:
1. Crear propiedad mock con `fuente: 'manual'` y `_ultima_valuacion` poblada
2. Setear `clean_comparables_{nombre} = True` en session state
3. Ejecutar la lógica del bloque `if clean_flag:` (extraída)
4. **Assert A**: UV en disco NO fue eliminada (`guardar_propiedades` no llamada)
5. **Assert B**: `_official_result` sigue en session state
6. **Assert C**: `fuente_activa` sigue en session state

### Paso 6: Verificación
- `python -m pytest tests/test_regression.py` — todos pasan
- `python scripts/auto_validate.py` — OK

## ✅ Criterios de aceptación
- [x] Botón "Limpiar" borra caché de comparables (funciona como antes)
- [x] Botón "Limpiar" **NO** toca `_ultima_valuacion` si fuente es manual
- [x] Botón "Limpiar" **NO** borra `_official_result` si fuente es manual
- [x] Botón "Limpiar" **NO** borra `fuente_activa` de session state
- [x] Header manual permanece visible después de limpiar
- [x] Test de regresión pasa y protege contra futuras violaciones

## 📝 Justificación RO
**RU-CLEAN-MANUAL-01**: Se violaba porque el código ejecutaba `p.pop('_ultima_valuacion')` incondicionalmente. Este cambio la restaura agregando un condicional que preserva la UV cuando `fuente == 'manual'`. El test de regresión `test_clean_comparables_preserves_manual_uv` blinda esta regla contra futuras regresiones.

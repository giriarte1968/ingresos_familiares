# TAREA-094 — Sincronizar header con exclusión de comparables — Riesgo BAJO

## CONTEXTO

Cuando el usuario excluye comparables vía "Aplicar selección", el motor devuelve `n_propiedades = len(pool_final)` (9 comps totales) y `m2_microzona = valor del pool completo` (ej. $2,932). El exclusion block en `valu.py:820-861` recalcula correctamente `valor_propiedad_usd` y `m2_base_venta` con la selección activa (ej. 4 comps, $2,570/m²), pero **olvida sincronizar**:

1. `resolution_metadata.n_propiedades` → header sigue mostrando `(9 comp.)` y `Confianza media` en vez de `(4 comp.)` y `Confianza baja`.
2. `m2_microzona` → la fórmula del header usa el viejo valor del pool completo (ej. `$2,932`) que no corresponde al nuevo valor (ej. `$2,570` ni suma al `$526,489` final).

### Síntomas

- Header: `$2,932 (9 comp.)` y `Confianza media (9 comparables)`
- Tabla: `4/9 activos (5 excluidos)` y footer: `4 comps selec. de 9 totales`
- Fórmula: `$2,932/m² × 160.0 m² × 1.299 + $56,000 ≠ $526,489`

### Código afectado

- `valu.py:818-839`: Exclusion block exitoso — no actualiza `_meta['n_propiedades']` ni `resultado['m2_microzona']`
- `valu_detail_sections.py:166,200-204,258,271`: Header lee `n_propiedades` y `m2_microzona` desde `resultado`

## REGLA DE ORO

- `n_propiedades` debe reflejar la cantidad de comparables **activos** (no el total del pool) cuando hay exclusiones aplicadas.
- `m2_microzona` debe reflejar el valor **efectivo** usado para el cálculo (no el valor del pool completo pre-exclusión).
- La confianza del header debe basarse en la cantidad real de comparables usados.
- `comparables_venta` y `_n_excluidos` no deben modificarse (ya están correctos).
- Los valores originales se preservan en `_original_m2_base` y `_original_valor_usd`.

## CAMBIOS

### 1. `valu.py:839` — Sync `n_propiedades` y `m2_microzona`

En el bloque de exclusión exitosa (preview not None and not fallback), después de setear `_n_excluidos`:

```python
# Sincronizar header con selección activa (TAREA-094)
_meta['n_propiedades'] = len(comps_filtrados)
resultado['m2_microzona'] = nuevo_vm2
```

### 2. Debug flag `[DEBUG-SYNC-HEADER]`

Agregar `print(f"[DEBUG-SYNC-HEADER] {prop_name}: n_propiedades={len(comps_filtrados)}, m2_microzona={nuevo_vm2}")`

### 3. `tests/test_regression.py`

Agregar `test_header_sync_on_exclusion` que verifica:
- Motor base con 9 comps tiene `n_propiedades=9` y `m2_microzona` correcto
- Después de excluir N comps vía `calcular_vm2_por_seleccion`, el resultado simulado tiene `n_propiedades = total - excluidos` y `m2_microzona = nuevo_vm2`
- La confianza es "Confianza baja" para < 8 comps

### 4. `docs/BITACORA_AGENTES.md` — Nueva entrada

### 5. `docs/STATUS_ACTUAL.md` — Actualizar fecha y conteo de tests

## TEST PLAN

### Test existente que validar
```
pytest tests/test_regression.py
```

### Test nuevo: `test_header_sync_on_exclusion`
```
python -c "from tests.test_regression import test_header_sync_on_exclusion; test_header_sync_on_exclusion()"
```

## RIESGO

BAJO. Solo actualiza metadatos de `resultado` que ya son recalculados; no toca lógica de precios ni persistencia. No viola RO-16 (MEMORIA_PROYECTO.md prioridad absoluta).

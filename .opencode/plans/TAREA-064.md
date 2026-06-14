# TAREA-064: Fix preview/motor m² mismatch for n=5-7 when all comps selected

## Problema
El preview y el Apply block mostraban un m² distinto al del header cuando todos los comparables estaban seleccionados (n=7). La causa era que el motor usa `P33_age_blend` (una mezcla compleja entre el pool filtrado por edad y el pool completo) para 5-7 comps, mientras que la UI calculaba P33 simple.

Con todos los comps seleccionados:
- Header: $3,106 (P33_age_blend del motor)
- Preview: $2,557 (P33 simple)

## Causa raíz
El Apply block en `valu.py` y la preview en `render_tabla_comparables.py` calculaban percentiles simplificados (P33/P40/P45/P50 según `seleccionar_percentil_por_edad`), pero cuando el percentil retornado es `33` y `n` está entre 5-7, el motor hace un blending entre:
- `base_age`: P33 del pool filtrado por edad
- `base_all`: P33 del pool completo
- Fórmula: `valor = alpha_age * base_age + (1 - alpha_age) * base_all`
  - n=7: alpha_age=0.75, n=6: 0.60, n=5: 0.45

La UI no replicaba este blending, produciendo un valor diferente.

## Solución
Cuando todos los comps están seleccionados (`excluded_ids` vacío), la UI saltea el recálculo y conserva el valor del motor (que ya usó P33_age_blend):

1. **`valu.py` Apply block**: `if excluded_ids:` envuelve el recálculo. Si `excluded_ids` es `[]` (todos seleccionados), no se recalcula y se mantiene `resultado['m2_base_venta']` original del motor.

2. **`render_tabla_comparables.py` preview**: Después de calcular P33/P40/P45/P50 simple, si `not excluded_ids`, se sobreescribe `p33_p50` con `res.get('m2_base_venta', p33_p50)` (el valor del motor).

### Efectos
- Todos seleccionados → header == preview == motor ($3,106)
- Algunos excluidos → preview recalcula con P33 simple sobre seleccionados
- Apply con todos seleccionados → no modifica el resultado del motor
- Apply con exclusiones → recalcula con premium formula como antes

## Archivos modificados
- `valu.py`: Indentación del bloque Apply dentro de `if excluded_ids:` check
- `valu_detail_sections.py`: Override de `p33_p50` con valor del motor cuando todos seleccionados

## Tests
- `python scripts/auto_validate.py` — OK
- `tests/test_regression.py` — OK

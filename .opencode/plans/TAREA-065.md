# TAREA-065: Separar barrera del m² de comparables (solo afecta al sujeto)

## Problema conceptual
`barrier_penalty` (×0.97) se aplicaba al precio de cada comparable que cruza una barrera geográfica. Esto es incorrecto: el precio de un comparable ya refleja su propia ubicación. La barrera debe afectar solo al sujeto en el cálculo final, no a los precios de los comparables.

## Solución
1. Quitar `_penalizacion_barrier` del `precio_m2_ajustado` de cada comparable
2. Quitar `_penalizacion_barrier` del cálculo de `precios` para P33/blend
3. Agregar `_m2_puro` al result dict (P33 sin barrera, para display)
4. Actualizar header: mostrar `m² puro`, `barrera %`, `m² ajustado`
5. Quitar badge `BARRERA` de la tabla de comparables
6. Quitar `barrier_penalty` del Apply block y preview en UI

## Archivos modificados
- `parsers/mercado_inmobiliario.py`: líneas 1143, 1284, 1295, 1382-1384, ~1540, ~1592
- `valu_detail_sections.py`: líneas 331-332, 351, 379-386, 104-143
- `valu_design.py`: hero_price con params m2_puro/barrier_pct
- `valu.py`: líneas 588, 596

## Tests
- `python scripts/auto_validate.py` — OK
- `tests/test_regression.py` — OK

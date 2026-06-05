# TAREA-032: Puerto Norte — time-expansion en zona cerrada

## Diagnóstico
Puerto Norte es una zona premium chica (15 props, solo 3 venta/2-dorm). El Tier 1 (geo search) a 500m encuentra 13 comps de Pichincha/Otro → se detiene con m² bajo. La lógica actual no distingue que esos comps son de otra zona.

## Solución
Para Puerto Norte exclusivamente:
1. Tier 1: si >80% comps son de otra zona, seguir expandiendo radio (no detenerse)
2. Tier 2: en vez de expandir radio, expandir fecha hacia atrás (365→545→730→9999 días)
3. Time adjustment: comps >1 año se ajustan con factor = 1 + (-0.045) * años_excedidos
4. Ancla: subir de 2100 a 2800

## Cambios

| Archivo | Línea | Cambio |
|---------|-------|--------|
| `data/anclas_rosario_v5_1_limpio.json` | 13 | `usd_m2`: 2100→2800 |
| `parsers/mercado_inmobiliario.py` | 935-937 | Constantes TASA_AJUSTE_PN=-0.045, VENTANAS_FECHA_PN, MIN_PN |
| `parsers/mercado_inmobiliario.py` | 1022-1028 | Tier 1: PN zone-check (no detenerse si comps otra zona) |
| `parsers/mercado_inmobiliario.py` | 1044-1071 | Tier 2 PN: time-expansion loop con _time_adjustment |
| `parsers/mercado_inmobiliario.py` | 1210 | Aplicar _time_adjustment en precios |
| `parsers/mercado_inmobiliario.py` | 3117 | Hardcoded ancla PN: 2100→2800 |
| `tests/test_regression.py` | 413 | Rango anclas 2500→2800 |

## Validación
- 39/39 tests pass
- auto_validate.py OK
- Sin cambios en otras zonas (if zona_normalizada == 'puerto norte' protege)

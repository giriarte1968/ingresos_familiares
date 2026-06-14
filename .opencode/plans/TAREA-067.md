# TAREA-067: Propagar _m2_puro y barrier_pct a resolution_metadata

## Contexto
El header mostraba formato legacy (`m²/USD en Puerto Norte: $2,968 (8 comp.)`) en
propiedades con comps que cruzan barrera porque `ensamblar_metadata_resolucion` no
incluía `_m2_puro` ni `barrier_pct` en su dict de retorno.

## Causa raíz
`ensamblar_metadata_resolucion()` crea un **nuevo dict** copiando solo un subconjunto
de `meta_venta`. Las claves `_m2_puro` y `barrier_pct` (seteadas en
`obtener_mediana_cluster_v2` línea 1607) no estaban incluidas.

Flujo:
```
obtener_mediana_cluster_v2 → meta_venta (con _m2_puro ✅, barrier_pct ✅)
  ↓
ensamblar_metadata_resolucion → nuevo dict SIN esas claves
  ↓
render_header: meta.get('barrier_pct', 0) → 0 → formato legacy
```

## Cambio
- `parsers/valuacion_helpers.py:227-228`: agregar `_m2_puro` y `barrier_pct`
  al dict de retorno de `ensamblar_metadata_resolucion`.

## Validación
- `python scripts/auto_validate.py` ✅
- Header debe mostrar formato de 3 niveles para propiedades con cruce de barrera:
  `m² puro $X | Barrera -Y% → m² ajustado $Z`

## Archivos modificados
- `parsers/valuacion_helpers.py`

# Size Adjustment por Macrozona — TAREA-074

## Justificación

El antiguo size_discount global aplicaba un castigo uniforme (-5 a -15%) a unidades
>100m² en toda la ciudad de Rosario. El análisis de 8,297 propiedades en venta del
cache_scraping (2024–2025, excluyendo basura de abril 2026) demostró que esta premisa
es incorrecta: cada macrozona tiene una relación tamaño/precio DISTINTA.

## Metodología

1. **Carga de datos**: cache_scraping.json (última versión), filtrando solo propiedades
   en USD, tipo venta, con m² y precio válidos.
2. **Asignación de macrozona**: cada propiedad se asigna a una macrozona según
   latitud/longitud usando el bbox de zonas_depreciacion.json.
3. **Bucket por tamaño**: se agrupan en S (=60m²), M (60-100m²), L (100-150m²),
   XL (=150m²).
4. **Cálculo de mediana**: se calcula la mediana de $/m² por bucket.
5. **Normalización**: se normaliza para que factor ˜ 1.0 en el tamaño mediano
   de cada macrozona.
6. **Curva piecewise linear**: se interpolan los puntos para obtener una curva
   continua.

## Datos observados

### centro_premium (n=4,293, mediana ~85m²)

| Bucket | n    | $/m²  | Factor |
|--------|------|-------|--------|
| S      | 1,404| ,814| 0.96   |
| M      | 1,180| ,875| 1.00   |
| L      | 823  | ,054| 1.09   |
| XL     | 886  | ,439| 0.77   |

**Patrón**: U invertida — L tiene PREMIO (+9%), XL tiene DESCUENTO (-23%).

### ? Puerto Norte (subzona de centro_premium)

| Bucket | n  | $/m²  | Factor |
|--------|----|-------|--------|
| S      | 287| ,733| 0.92   |
| 80-100 | 66 | ,982| 1.04   |
| 120-150| 45 | ,451| 1.29   |
| 150-200| 32 | ,651| 1.40   |
| >200   | 20 | ,631| 1.39   |

**Patrón**: MONÓTONO CRECIENTE — el $/m² AUMENTA con el tamaño.
Contradice completamente el viejo size_discount.

### macrocentro (n=1,618, mediana ~95m²)

| Bucket | n   | $/m²  | Factor |
|--------|-----|-------|--------|
| S      | 431 | ,384| 1.40   |
| M      | 429 | ,078| 1.08   |
| L      | 280 |   | 0.87   |
| XL     | 478 |   | 0.87   |

**Patrón**: ACANTILADO — unidades pequeñas tienen fuerte PREMIO (+40%),
grandes tienen fuerte DESCUENTO (-13%).

### norte (n=1,292, mediana ~148m²)

| Bucket | n   | $/m²  | Factor |
|--------|-----|-------|--------|
| S      | 109 | ,312| 1.46   |
| M      | 265 | ,338| 1.49   |
| L      | 291 |   | 1.00   |
| XL     | 627 | ,126| 1.25   |

**Patrón**: BAÑADERA — descuento en L, recuperación parcial en XL.

### oeste (n=524, mediana ~150m²)

| Bucket | n   | $/m²  | Factor |
|--------|-----|-------|--------|
| S      | 27  | ,050| 1.40   |
| M      | 121 |   | 1.05   |
| L      | 115 |   | 0.91   |
| XL     | 261 |   | 1.06   |

**Patrón**: DECLIVE SUAVE con recuperación parcial en XL.

### sur_default (n=565, mediana ~125m²)

| Bucket | n   | $/m²  | Factor |
|--------|-----|-------|--------|
| S      | 56  |   | 1.20   |
| M      | 141 |   | 1.06   |
| L      | 163 |   | 1.04   |
| XL     | 205 |   | 0.99   |

**Patrón**: PENDIENTE SUAVE — diferencias pequeñas entre buckets.

## Fórmula actualizada

`
valor_venta = m2_cubiertos × m2_microzona × size_adjustment(m2, macrozona, ancla_id) + activos
`

Donde size_adjustment interpola linealmente entre puntos definidos en
zonas_depreciacion.json para la macrozona correspondiente, con override
de subzona (Puerto Norte) si el anchor ID coincide.

## Configuración

Las curvas se almacenan en data/zonas_depreciacion.json:

`json
{
  "id": "centro_premium",
  "size_adjustment": {
    "type": "piecewise_linear",
    "points": [{"m2": 0, "factor": 0.95}, ...],
    "subzonas": {
      "puerto_norte": {
        "match_anchor_ids": ["central_argentino_puerto_norte", ...],
        "points": [{"m2": 0, "factor": 0.92}, ...]
      }
    }
  }
}
`

Se pueden editar desde la UI: Configuración ? Ajuste por Tamaño.

## Referencias

- docs/ALGORITMOS.md: fórmula general
- docs/MEMORIA_PROYECTO.md: RO-19
- data/zonas_depreciacion.json: curvas configuradas
- .opencode/plans/TAREA-074.md: plan de implementación

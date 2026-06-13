# TAREA-051: Alinear UI percentil preview con Core Motor (granularidad completa)

## Problema
La UI preview en `valu_detail_sections.py` usa un umbral binario para el percentil:
```python
p33_p50 = p50 if n_sel >= 8 else p33  # binario: P50 para ≥8, P33 para <8
```

Pero el Core Motor (`seleccionar_percentil_por_edad` en `cluster_filters.py`) tiene 5 niveles:

| n | Core Motor | UI actual |
|---|-----------|-----------|
| ≥20 | P50 | P50 |
| 10-19 | **P45** | P50 |
| 8-9 | **P40** | P50 |
| 5-7 | **P33_age_blend** | P33 |
| <5 | **P33** | P33 |

Para n=8 exactos (como en Francia 250b con todos los dorms), la UI muestra P50 ($3,592/m²) cuando el Core Motor usaría P40 ($3,213/m²), creando una diferencia de ~$379/m² que desconcierta al usuario al hacer clic en "Aplicar".

## Solución
Reemplazar la lógica binaria con `seleccionar_percentil_por_edad(True, n_sel)` importada directamente del Core Motor, y mapear el percentil numérico devuelto al índice del array ordenado.

### Código propuesto (reemplazar líneas 349-352 y 359)

```python
from parsers.cluster_filters import seleccionar_percentil_por_edad

# En lugar de la lógica binaria:
percentil, label = seleccionar_percentil_por_edad(True, n_sel)
if percentil == 50:
    perc_idx = n_sel // 2
    label_short = 'P50'
elif percentil == 45:
    perc_idx = max(0, int(n_sel * 0.45) - 1)
    label_short = 'P45'
elif percentil == 40:
    perc_idx = max(0, int(n_sel * 0.40) - 1)
    label_short = 'P40'
else:  # 33
    perc_idx = max(0, int(n_sel * 0.33) - 1)
    label_short = 'P33'

p33_p50 = precios_sorted[perc_idx]
```

Y en la etiqueta:
```python
st.caption(f"{label_short} sobre {n_sel} comps seleccionados de {len(comparables)} totales")
```

## Archivos a modificar
- `valu_detail_sections.py` — líneas 349-359: reemplazar lógica binaria con llamada a `seleccionar_percentil_por_edad`

## No modificar
- `parsers/cluster_filters.py` — la función `seleccionar_percentil_por_edad` es la fuente de verdad y no necesita cambios

## Validación
- `python scripts/auto_validate.py` → debe pasar
- Tests de regresión → deben pasar
- Test manual: Francia 250b con 8 comps → debe mostrar P40 en preview (no P50)

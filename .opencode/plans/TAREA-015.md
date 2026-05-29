# TAREA-015 — Enriquecimiento 3-pasos con match exacto (calle+número) + token ≤30m — Riesgo ALTO

## CONTEXTO

La TAREA-014 redujo la distancia máxima a 20m y eliminó la esquina fallback para evitar inflación de P1200 ($137,888 → $190,957). Pero resultó demasiado restrictiva: Brown 2750 pasó de 15 ALTA a solo 3, dejando la UI sin años estimados para la mayoría de los comparables.

La causa raíz: el scraping asigna coordenadas aproximadas (centro de cuadra), por lo que un comparable "Brown 2734" puede estar a 33-38m del PH catastral real. El token containment a 20m no alcanza.

Se descubrió que `_CATASTRO_INDEX` (índice `{(calle_norm, num): row}`) ya se construía en `cargar_catastro()` pero **nunca se consultaba** — dead code. Además, `_MAX_DIST_ADDR_MATCH = 200` estaba definido sin uso.

## SOLUCIÓN

3 pasos progresivos:

1. **Paso 0 (Match exacto)**: Consulta `_CATASTRO_INDEX` con `(calle_norm, num)`. Si la dirección catastral coincide exactamente, el año es confiable aunque la distancia sea de hasta 200m (sabemos que es el mismo edificio). → ALTA
2. **Paso 1 (Token containment ≤30m)**: Como antes, pero con distancia 30m para capturar comps con coordenadas imprecisas. → ALTA
3. **Paso 2 (Nearest + token ≤30m)**: Como antes. → MEDIA
4. Sin esquina fallback.

## CAMBIO

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | `enriquecer_anio_comparable()`: +Paso 0 exacto, default 30m |

## RESULTADOS DE SIMULACIÓN

| Propiedad | Valor USD | ALTA | MEDIA | Total |
|-----------|-----------|------|-------|-------|
| Mabel | $67,863 | 43 | 0 | 79 |
| Ayacucho | $51,154 | 31 | 0 | 43 |
| Vera Mujica | $48,873 | 24 | 0 | 27 |
| **P1200** | **$125,412** | 14 | 0 | 31 |
| Entre Rios | $77,446 | 18 | 0 | 27 |
| Brown 2750 | $306,681 | 6 | 0 | 25 |

P1200 se mantiene en $125k (vs $191k inflado con esquina). Brown sube de 3 a 6 ALTA (vs 15 con esquina, vs 3 con 20m).

## VALIDACIÓN

```
☐ pytest: 38/39 pasan (1 falla pre-existente Vera Mujica)
☐ auto_validate: syntax OK, imports OK, performance OK
☐ P1200 ~$125k (sin inflación)
☐ Brown ~$306k +6 ALTA (vs 3 con 20m)
```

## DOCS A ACTUALIZAR

- `docs/ALGORITMOS.md` — §15 actualizar a 3 pasos con match exacto
- `docs/BITACORA_AGENTES.md` — TAREA-015
- `docs/STATUS_ACTUAL.md` — §14 actualizado
- `.opencode/plans/TAREAS_INDEX.md` — TAREA-015 agregada

# TAREA: TAREA-001 — Filtro catastral por centena exacta — Riesgo BAJO

## CONTEXTO

`_match_por_direccion()` en `parsers/infomapa_api.py` usaba `diff <= 10` para filtrar candidatos catastrales.
Para Pellegrini 1200, esto permitía que Pellegrini 1195 (centena 11xx) se seleccionara como "recomendado",
a pesar de estar en una cuadra diferente. En Rosario, la centena del número define la cuadra.

## REGLA DE ORO

- No cambiar lógica de coordenadas, API, ni UI principal
- `_match_coordenadas()` no se modifica
- pytest pasa después de cada paso

## ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/infomapa_api.py` | `_match_por_direccion()` — filtro `centena_csv == centena_sujeto` |
| `parsers/infomapa_api.py` | `enriquecer_con_infomapa()` — propagar `centena_match` a candidatos |
| `valu_detail_sections.py` | `render_catastro()` — badge "Misma cuadra" / "Coordenadas" |
| `docs/DICCIONARIO_DATOS.md` | §7 — documentar campo `centena_match` |

---

## PASO 1: Filtro de centena

**Archivo:** `parsers/infomapa_api.py` — `_match_por_direccion()` (lines 112-133)

Agregar `centena_sujeto = (numero // 100) * 100` y `centena_csv = (csv_num // 100) * 100` con `if centena_csv != centena_sujeto: continue`.

**COMMIT:** Incluido en commit final.

**VERIFICAR:** P1200 no tiene dirección "exacta".

---

## PASO 2: Propagar centena_match

**Archivo:** `parsers/infomapa_api.py` — `enriquecer_con_infomapa()` (lines 175-193)

Agregar `c['centena_match'] = 'coordenadas'` a candidatos por coordenadas.
Los candidatos por dirección ya tienen `centena_match = 'exacta'` desde `_match_por_direccion()`.

---

## PASO 3: Badge en UI

**Archivo:** `valu_detail_sections.py` — `render_catastro()` (line 273-277)

Extraer formato a función `_fmt_candidato()` que muestra badge según `centena_match`.

---

## VALIDACION FINAL

```
✓ pytest pasa (39/39 regression, 152/152 total)
✓ P1200: sin candidato por dirección de 11xx
✓ Ayacucho: centena=exacta para 1805
✓ Mabel: centena=exacta para 3 de Febrero 520
```

## DOCS ACTUALIZADOS

- `docs/DICCIONARIO_DATOS.md` §7 — campo `centena_match`
- `docs/BITACORA_AGENTES.md` — entrada de la tarea
- `.opencode/plans/TAREAS_INDEX.md` — entrada TAREA-001

## ARCHIVO DE PLAN

`.opencode/plans/TAREA-001.md`

## ENTREGABLES

- `parsers/infomapa_api.py` — filtro de centena + propagación
- `valu_detail_sections.py` — badge en UI
- `docs/DICCIONARIO_DATOS.md` — schema actualizado
- `docs/BITACORA_AGENTES.md` — registro
- `.opencode/plans/TAREAS_INDEX.md` — índice

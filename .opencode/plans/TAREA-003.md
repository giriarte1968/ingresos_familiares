# TAREA: TAREA-003 — Orden candidatos catastrales por distancia (no centena) — Riesgo BAJO

## CONTEXTO

Los candidatos por coordenadas en `enriquecer_con_infomapa()` se ordenaban primero por centena (mismos → otros) y luego por distancia dentro de cada grupo. Esto causaba que entradas de calle sin número (que pasaban el filtro de centena porque `csv_num is None` → True) desplazaran a entradas con número que estaban más cerca pero en centena distinta. Caso concreto con Mabel (3 de Febrero): PH=17916 "3 de Febrero 504" a 21m quedaba fuera del top 3, mientras que PH=19899 "3 de Febrero" (sin número) a 49m entraba.

Además, el subtítulo "No solo un número: una lectura completa del activo y su contexto de mercado." en la sección "Qué recibís con Valu" de la landing page no se mostraba centrado.

## REGLA DE ORO

- No modificar lógica de valuación (`mercado_inmobiliario.py`)
- Tests de regresión deben pasar sin cambios
- El filtro de misma calle se mantiene
- Candidatos con número en distinta centena se excluyen

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `parsers/infomapa_api.py` | Cambiar orden de candidatos por coordenadas: distancia-first, excluyendo centena distinta |
| `docs/BITACORA_AGENTES.md` | Registrar análisis y cambio |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar TAREA-003 |
| `landing_content.py` o `valu_design.py` | Corregir centrado del subtítulo |

---

### PASO 1: Orden candidatos por coordenadas distancia-first

**Archivo:** `parsers/infomapa_api.py` — `enriquecer_con_infomapa()` (líneas 204-237)

**1.1** Reemplazar split `mismos/otros` (centena-first) con filtro único + top 3 por distancia:

**1.2** Eliminar bloque de relleno secundario (ya no necesario porque el filtro unificado ya captura todos los candidatos válidos)

**1.3** Simplificar `centena_match` a solo `'exacta'` y `'coordenadas'`

```python
# ANTES:
mismos = [c for c in coord_pool if _misma_calle(c) and _misma_centena(c)]
otros = [c for c in coord_pool if _misma_calle(c) and not _misma_centena(c)]
coord_candidates = (mismos + otros)[:3]
# + bloque relleno secundario (lines 227-237)

# DESPUES:
coord_candidates = [c for c in coord_pool if _misma_calle(c) and _misma_centena(c)][:3]
```

**COMMIT:** `"FIX: candidatos catastro ordenados por distancia, excluyendo centena distinta"`

**VERIFICAR:** `pytest tests/test_regression.py -x --timeout=60`

---

### PASO 2: Documentar en BITACORA y TAREAS_INDEX

**Archivos:** `docs/BITACORA_AGENTES.md`, `.opencode/plans/TAREAS_INDEX.md`

**2.1** Agregar entrada en BITACORA_AGENTES.md detallando problema, cambio y resultado

**2.2** Agregar TAREA-003 a TAREAS_INDEX.md con commit hash y fecha

---

### PASO 3: Corregir centrado subtítulo landing

**Archivo:** `landing_content.py` o `valu_design.py`

**3.1** Agregar `text-align: center` inline al `<p>` del subtítulo o en CSS

**COMMIT:** (junto con PASO 1)

---

### VALIDACION FINAL

- [x] `pytest tests/test_regression.py` pasa (39 tests)
- [x] `python scripts/auto_validate.py` pasa
- [ ] Subtítulo centrado visualmente en landing page

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md`

### ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-003.md`.
ID secuencial: 003 (último era TAREA-002).

### ENTREGABLES

- `parsers/infomapa_api.py` — orden distancia-first + exclusión centena distinta
- `docs/BITACORA_AGENTES.md` — registro detallado
- `.opencode/plans/TAREAS_INDEX.md` — entrada actualizada
- `landing_content.py` o `valu_design.py` — fix centrado
- `pytest` 39/39 pasando

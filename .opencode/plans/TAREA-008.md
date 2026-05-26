## TAREA: TAREA-008 — Auditar y agregar Av. del Valle como barrera blanda — Riesgo MEDIO

### CONTEXTO

La valuación de "Brown 2700 Pichincha" arrojó $263k–$308k vs listing de $236k (corredora).
La investigación confirmó que Av. del Valle (Aristóbulo del Valle) no figura en
`barreras_rosario.json`. Propiedades del otro lado de Av. del Valle (≈$3,000/m²)
se mezclan al 100% con propiedades de Brown St (≈$2,360/m²) porque no hay barrera
que las separe. El blend `0.70 * same_side + 0.30 * cross_soft` no se activa.

### REGLA DE ORO

- No cambiar fórmulas de blend, alpha, percentiles ni tests existentes
- `pytest tests/test_regression.py` pasa en cada paso
- No prometer impacto numérico hasta medir antes/después
- Av. del Valle debe clasificarse como `soft`, no `hard`
- La extracción por OSM debe filtrar solo segmentos de la avenida en Rosario

### ALCANCE

| Archivo | Cambio |
|---|---|
| `scripts/extract_barriers.py` | Agregar `"Del Valle"` a `nombres_clave` de barreras blandas |
| `barreras_rosario.json` | Regenerar con OSM (incluye Av. del Valle como soft) |
| `docs/ALGORITMOS.md` | Sección 7: agregar Av. del Valle como nueva barrera blanda |
| `docs/MEMORIA_PROYECTO.md` | Sección 6: registrar nueva barrera y auditoría |
| `docs/BITACORA_AGENTES.md` | Registrar decisión + resultados de auditoría |

---

### PASO 1: Agregar "Del Valle" al extractor OSM

**Archivo:** `scripts/extract_barriers.py` — línea 20

**1.1** Agregar `"Del Valle"` a la lista `nombres_clave`:

```python
nombres_clave = ['Oroño', '27 de Febrero', 'Pellegrini', 'Francia',
                 'Circunvalación', 'Lagos', 'Del Valle']
```

**1.2** Verificar que Overpass API filtre solo en Rosario (bounding box existente).

**COMMIT:** `"feat: agregar Av. del Valle a nombres_clave de barreras blandas"`

**VERIFICAR:** `python scripts/extract_barriers.py` corre sin errores y genera
`barreras_rosario.json` con features nuevas de Av. del Valle.

---

### PASO 2: Auditar Brown 2700 antes del cambio

**Archivo:** Consola Python / `valu.py`

**2.1** Ejecutar valuación de Brown 2700 con logging adicional para extraer:

- `n_same_side` = ?
- `n_cross_soft` = ? (hoy debería ser 0)
- `n_excluded_hard` = ?
- `pct_same` (P33/P40/P45/P50 según edad)
- `pct_cross` (N/A hoy porque no hay cross_soft)
- `percentil_usado` (P33? P50?)
- `valor_final` (Conservador/Mercado/Optimista)
- Lista completa de comparables con su grupo (same_side o cross_soft)

**Verificación específica:**
- Brown 2734 → debe estar en `same_side` ✅
- Av. del Valle 2700 → hoy está en `same_side` (sin barrera) → debe pasar a `cross_soft`
  después de agregar la barrera

**COMMIT:** No aplica (solo medición)

**VERIFICAR:** Salida de logging con n_same_side > 0 y todos los comparables
en same_side (hoy no hay cross_soft porque no hay barrera).

**NOTA:** Este paso es OBLIGATORIO antes del paso 3. Sin la medición previa no
podemos medir el impacto real del cambio.

---

### PASO 3: Regenerar barreras y re-evaluar

**3.1** Ejecutar `python scripts/extract_barriers.py` para regenerar
`barreras_rosario.json` con Av. del Valle incluida.

**3.2** Verificar en el JSON que las nuevas features tengan:

```json
{
  "type": "Feature",
  "geometry": { "type": "LineString", "coordinates": [...] },
  "properties": { "name": "Avenida Del Valle", "barrier_type": "soft" }
}
```

**3.3** Re-evaluar Brown 2700 con el mismo logging del Paso 2. Extraer:

- `n_same_side` (debería bajar)
- `n_cross_soft` (debería ser > 0 ahora)
- `pct_same`
- `pct_cross`
- `valor_final` (debería bajar vs Paso 2)

**3.4** Verificar:
- Brown 2734 → same_side ✅ (misma cuadra)
- Av. del Valle 2700 → cross_soft ✅ (cruza la avenida)

**COMMIT:** `"fix: regenerar barreras_rosario.json con Av. del Valle como soft"`

**VERIFICAR:** `pytest` pasa.

---

### PASO 4: Actualizar documentación

**Archivos:**
- `docs/ALGORITMOS.md` — Sección 7.1: agregar "Av. del Valle" a la tabla de
  barreras blandas.
- `docs/MEMORIA_PROYECTO.md` — Sección 6: agregar entrada con fecha, barrera,
  IDs de comparables afectados y valores antes/después.
- `docs/BITACORA_AGENTES.md` — registrar decisión y hallazgos de la auditoría.
- `.opencode/plans/TAREAS_INDEX.md` — agregar TAREA-008.
- `.opencode/plans/TAREA-008.md` — este plan.

**COMMIT:** `"docs: actualizar ALGORITMOS, MEMORIA, BITACORA con TAREA-008"`

**VERIFICAR:** Revisión visual de los .md

---

### VALIDACION FINAL

```
✅ pytest tests/test_regression.py pasa (39 tests)
✅ n_same_side registrado antes del cambio (244 same_side, 427 cross_soft)
✅ n_cross_soft = 0 para Av. del Valle antes del cambio
✅ n_cross_soft > 0 después del cambio (23 de 26 Av. del Valle → cross_soft)
✅ Av. del Valle 2700 pasa de same_side → cross_soft (23 props)
✅ Brown 2734 permanece en same_side
🔄 Valor final de Brown 2700 se acerca más al listing ($236k) — pendiente validación en UI
✅ docs actualizados
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/ALGORITMOS.md` (sección 7)
- `docs/MEMORIA_PROYECTO.md` (sección 6)
- `.opencode/plans/TAREAS_INDEX.md`
- `.opencode/plans/TAREA-008.md`

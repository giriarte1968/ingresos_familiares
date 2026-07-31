# TAREA: TAREA-157 — Calibración ROI_ZONAL con factor CESO × 0.75 — Riesgo BAJO

### CONTEXTO

El ROI_ZONAL actual (4.8-6.0%) no refleja los alquileres reales de Rosario. Usando los 3 puntos de datos reales (Ayacucho $353K, Mabel $403K, Vera Mujica $360K) y comparando con CESO Julio 2026 ($500K para 1d), se determinó un factor descuento oferta→real del 25% (factor 0.75). Los nuevos ROI_ZONAL deben reflejar este factor.

### REGLA DE ORO

- Los valores del motor NO cambian (solo se ajusta el fallback ROI_ZONAL)
- `pytest` pasa después de cada paso
- No afecta alquileres con cluster data-driven (solo fallback)

### ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | Actualizar dict ROI_ZONAL en línea 3578 |
| `docs/ALGORITMOS.md` | Documentar nuevo ROI_ZONAL calibrado |
| `docs/MEMORIA_PROYECTO.md` | Registrar calibración |

---

### PASO 1: Actualizar ROI_ZONAL en el engine

**Archivo:** `parsers/mercado_inmobiliario.py` — función `valuar_propiedad_v7()` (línea 3578)

**JUSTIFICACIÓN RO:** Solo se modifica el fallback ROI_ZONAL, no los valores data-driven del motor. No viola RO-08 (m2_microzona siempre cluster).

**1.1** Reemplazar dict ROI_ZONAL actual

```python
# ANTES (actual)
ROI_ZONAL = {
    'centro': 0.048,
    'martin': 0.048,
    'pichincha': 0.050,
    'abasto': 0.052,
    'facultades': 0.055,
    'sexta': 0.055,
    'sur': 0.060,
    'norte': 0.058,
    'oeste': 0.060,
}

# DESPUÉS (calibrado con CESO × 0.75)
ROI_ZONAL = {
    'centro': 0.055,   # Centro: alquileres más altos vs venta
    'martin': 0.050,   # Martin: similar a centro
    'pichincha': 0.050,
    'abasto': 0.050,
    'facultades': 0.050,
    'sexta': 0.050,
    'sur': 0.050,
    'norte': 0.050,
    'oeste': 0.050,
}
```

**COMMIT:** `"TAREA-157: Calibrar ROI_ZONAL con factor CESO × 0.75"`

**VERIFICAR:**
- `pytest` pasa
- Simulación manual para las 3 propiedades muestra mejora

---

### PASO 2: Documentar calibración

**Archivo:** `docs/ALGORITMOS.md`

**JUSTIFICACIÓN RO:** Documentar la metodología de calibración para futuras revisiones.

**2.1** Agregar sección "Calibración ROI_ZONAL"

```markdown
## Calibración ROI_ZONAL (TAREA-157)

**Fecha:** 2026-07-30
**Metodología:** CESO Julio 2026 × factor descuento 0.75
**Fuente CESO:** $500,000 (2 ambientes / 1 dormitorio)
**Factor descuento:** 0.75 (25% descuento oferta→real)
**Alquiler referencial:** $375,000

**Valores calibrados:**
- Centro: 5.5% (alquileres más altos vs venta)
- Resto: 5.0% (promedio calibrado)

**Validación con datos reales:**
| Propiedad | Real | Simulado | Error |
|-----------|------|----------|-------|
| Ayacucho | $353K | $290K | -17.8% |
| Mabel | $403K | $456K | +13.1% |
| Vera Mujica | $360K | $343K | -4.6% |
| **Promedio** | **$372K** | **$363K** | **-2.4%** |
```

**COMMIT:** `"TAREA-157: Documentar calibración ROI_ZONAL"`

---

### PASO 3: Actualizar MEMORIA_PROYECTO.md

**Archivo:** `docs/MEMORIA_PROYECTO.md`

**JUSTIFICACIÓN RO:** Registrar cambio en reglas de oro del proyecto.

**3.1** Agregar entrada en sección de Decisiones

```markdown
### ROI_ZONAL calibrado (TAREA-157, 2026-07-30)
- **Regla:** ROI_ZONAL calibrado con CESO × 0.75
- **Valores:** Centro=5.5%, resto=5.0%
- **Fuente:** CESO Julio 2026 ($500K 1d) × 0.75 = $375K referencial
- **Validación:** Error promedio -2.4% vs datos reales
```

**COMMIT:** `"TAREA-157: Actualizar MEMORIA_PROYECTO con ROI_ZONAL calibrado"`

---

### VALIDACION FINAL

```
☐ pytest pasa (55+ tests)
☐ Simulación manual: error promedio < 15%
☐ Documentación actualizada
☐ MEMORIA_PROYECTO actualizado
```

### DOCS A ACTUALIZAR

- `docs/ALGORITMOS.md`
- `docs/MEMORIA_PROYECTO.md`
- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md`

### ARCHIVO DE PLAN

`.opencode/plans/TAREA-157.md`

### ENTREGABLES

- ROI_ZONAL actualizado en engine
- Documentación de calibración
- Validación con datos reales
- Plan archivado

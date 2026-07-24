# TAREA-150: Ajuste fino de parámetros Puerto Norte — Riesgo BAJO

## CONTEXTO

Tras eliminar TASA_AJUSTE_PN (TAREA-149), se definieron los parámetros finales de Puerto Norte basados en análisis ML específico de la zona:

| Parámetro | Antes (calculado) | Ahora (definido) | Fuente |
|-----------|-------------------|------------------|--------|
| `ct_annual_rate` | +0.0768 | **+0.035** | Análisis ML PN-específico |
| `cv_ref` | 0.4378 | **0.339** | Compatibilidad con centro_premium |
| `bbox.lat_min` | -32.930 | **-32.932** | Ajuste geográfico |
| `bbox.lon_min` | -60.675 | **-60.672** | Ajuste geográfico |
| `by_dormitorios` | solo 2,3,default | **1,2,3,4,default** | Curvas completas |

## REGLA DE ORO

- `pytest` pasa después de cada paso
- No cambiar lógica de otras macrozonas

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `data/zonas_depreciacion.json` | Actualizar parámetros de puerto_norte |

---

## PASO 1: Actualizar parámetros de Puerto Norte

**Archivo:** `data/zonas_depreciacion.json`

**1.1** `cv_ref`: 0.4378 → 0.339
**1.2** `ct_annual_rate`: 0.0768 → 0.035
**1.3** `bbox.lat_min`: -32.930 → -32.932
**1.4** `bbox.lon_min`: -60.675 → -60.672
**1.5** Agregar curvas `by_dormitorios` para 1-dorm y 4-dorm (factor 1.0)

**COMMIT:** "TAREA-150: Ajuste fino parámetros Puerto Norte (ct=+3.5%, cv=0.339)"

---

## VALIDACION FINAL

```
☐ pytest pasa (94+ tests)
☐ ct_annual_rate = 0.035
☐ cv_ref = 0.339
☐ bbox actualizado
☐ Curvas 1,2,3,4-dorm presentes
```

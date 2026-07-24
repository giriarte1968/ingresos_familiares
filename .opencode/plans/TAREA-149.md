# TAREA-149: Eliminar TASA_AJUSTE_PN hardcoded + usar ct_annual_rate real — Riesgo MEDIO

## CONTEXTO

Puerto Norte tiene valores hardcoded que entran en conflicto con los parámetros configurables:
1. `TASA_AJUSTE_PN = -0.045` hardcodeado en mercado_inmobiliario.py línea 1121
2. `ct_annual_rate: -0.0163` en zonas_depreciacion.json (copiado de centro_premium)
3. `cv_ref: 0.339` en zonas_depreciacion.json (copiado de centro_premium)

Análisis de 229 propiedades de venta en PN revela:
- `ct_annual_rate` real: **+0.0768** (apreciación, no depreciación)
- `cv_ref` real: **0.4378**

## REGLA DE ORO

- No cambiar lógica de valuación para otras macrozonas
- `pytest` pasa después de cada paso

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `data/zonas_depreciacion.json` | Actualizar ct_annual_rate y cv_ref de puerto_norte |
| `parsers/mercado_inmobiliario.py` | Eliminar TASA_AJUSTE_PN y branch PN específico |

---

## PASO 1: Actualizar valores reales en zonas_depreciacion.json

**Archivo:** `data/zonas_depreciacion.json`

**1.1** Cambiar `ct_annual_rate` de `-0.0163` a `0.0768`
**1.2** Cambiar `cv_ref` de `0.339` a `0.4378`

**COMMIT:** "TAREA-149: ct_annual_rate y cv_ref reales para Puerto Norte"

---

## PASO 2: Eliminar TASA_AJUSTE_PN y branch PN

**Archivo:** `parsers/mercado_inmobiliario.py`

**JUSTIFICACIÓN RO:** Eliminar hardcoded que entra en conflicto con el sistema configurable. El flujo normal de CT ya maneja todas las zonas.

**2.1** Eliminar línea 1121-1122: `TASA_AJUSTE_PN = -0.045`

**2.2** Eliminar líneas 1240-1274: todo el `if zona_normalizada == 'Puerto Norte':` branch

**2.3** Eliminar la condición `zona_normalizada != 'Puerto Norte'` de la línea 1198 (Tier 1 bypass)

**COMMIT:** "TAREA-149: Eliminar TASA_AJUSTE_PN hardcoded, usar flujo CT estándar"

---

## PASO 3: Ejecutar pytest

```
python -m pytest tests/test_zonas_manager.py tests/test_regression.py -v
```

**VERIFICAR:**
- 39 zonas tests pasan
- 55 regression tests pasan
- Ningún test de PN falla

---

## VALIDACION FINAL

```
☐ pytest pasa (94+ tests)
☐ ct_annual_rate = 0.0768 en zonas_depreciacion.json
☐ cv_ref = 0.4378 en zonas_depreciacion.json
☐ TASA_AJUSTE_PN eliminado de mercado_inmobiliario.py
☐ Branch PN específico eliminado
☐ Tier 1 bypass eliminado
```

## DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md`

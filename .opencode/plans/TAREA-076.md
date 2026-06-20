# TAREA-076 — Eliminar Depreciación de Subfactores Display + Documentar Justificación ML

## CONTEXTO

El bloque "Subfactores de Referencia" en Valuación Manual mostraba 5 factores: Estado, Calidad, Depreciación, Amenities, NLP. El usuario señaló que la Depreciación (fórmula -0.6%/año × antigüedad) es falsa para Rosario — no existe ese valor en el mercado local.

### Evidencia ML (confirmada en TAREA-073)

| Análisis | Hallazgo |
|----------|----------|
| **XGBoost (R²=0.839)** | lat+lon = 80% importancia. Edad ni siquiera fue feature relevante. |
| **RF por macrozona** | centro_premium: -0.18%/año (baja), norte: +0.06%/año (aprecia!), oeste: -0.85%/año |
| **Grid RF (40×40 celdas)** | Controlando por ubicación exacta: Mabel +0.2% en 55 años. Efecto edad = confounding con ubicación. |
| **Conclusión TAREA-073** | Edad es confounding effect. Estado/calidad son double premiums sobre el anchor. Todos los factores hedónicos eliminados de venta. |

## DECISIÓN

- La depreciación NO existe como factor de mercado independiente en Rosario (ML confirmado)
- Estado, Calidad, Amenities, NLP SÍ tienen sentido como referencia porque son observables específicos de la propiedad
- Se elimina Depreciación de `calcular_factores_display()` y de la UI de Subfactores
- Se documenta la evidencia ML ampliamente en ALGORITMOS.md y MEMORIA_PROYECTO.md

## REGLA DE ORO

- `calcular_factores()` sigue retornando 1.0 (sin cambios)
- `_calcular_factores_rental()` no se toca
- 38 tests existentes pasan sin cambios
- auto_validate pasa antes del commit

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `.opencode/plans/TAREA-076.md` | (nuevo) Plan de tarea |
| `docs/ALGORITMOS.md` | Nueva sección "Depreciación en Rosario: Evidencia ML" |
| `docs/MEMORIA_PROYECTO.md` | Nueva RO-20: Depreciación no es factor de mercado |
| `parsers/mercado_inmobiliario.py` | Eliminar anti/antigüedad de `calcular_factores_display()` |
| `valu_detail_sections.py` | Eliminar columna Depreciación (5 → 4 columnas) |
| `main_valu_detail_sections.py` | Idem |
| `docs/BITACORA_AGENTES.md` | Registrar TAREA-076 |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar TAREA-076 |

## IMPLEMENTACIÓN

### PASO 1: Documentar justificación en ALGORITMOS.md

Agregar sección "17. Depreciación en Rosario: Evidencia ML" con:
- Resultados de XGBoost (80% ubicación, edad no es feature relevante)
- RF por macrozona (tabla completa)
- Grid RF por celda (+0.2% en 55 años para Mabel)
- Conclusión: edad es confounding effect con ubicación
- Diferencia entre factores de mercado (depreciación) y factores de propiedad (estado/calidad/amenities/NLP)

### PASO 2: Actualizar MEMORIA_PROYECTO.md

Agregar RO-20: "Depreciación no es factor de mercado en Rosario. Edad es confounding effect con ubicación. No mostrar como referencia en UI."

### PASO 3: Eliminar depreciación de calcular_factores_display()

- Remover cálculo de antigüedad, tasa zonal, delta_anti, factor_anti
- Remover antigüedad y depreciación del return dict
- Mantener: estado, calidad, amenities, NLP

### PASO 4: Eliminar columna Depreciación de UI

- valu_detail_sections.py: 5 columnas → 4 columnas (sin Depreciación)
- main_valu_detail_sections.py: idem
- Ajustar caption de factor combinado (ya no incluye anti)

### PASO 5: auto_validate + tests + commit + push

--- 

**Generado por**: OpenCode
**Fecha**: 2026-06-20

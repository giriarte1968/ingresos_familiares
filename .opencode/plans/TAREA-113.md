# TAREA: TAREA-113 — Sustitución de Tabla CT por Tasa Anual por Macrozona — Riesgo MEDIO

### CONTEXTO

El análisis rolling de USD/m² reveló que la tabla CT universal (`config/anclas_config.json`) es direccionalmente incorrecta para la mayoría de las macrozonas. Mientras la tabla asume una subida constante (~+10%/año), los datos reales muestran tendencias negativas en USD (especialmente en Centro Premium y Norte), lo que causa una inflación artificial de precios en comparables retroactivos (Salto Mabel).

### REGLA DE ORO

- No modificar la estructura de `anclas_config.json` para mantener compatibilidad con el generador de anclas.
- Mantener el fallback a la tabla universal si la macrozona no tiene tasa configurada.
- `pytest` debe pasar después de la implementación.
- Implementar flags de debug `[DEBUG-CT]` para rastrear la tasa y el factor final.

### ALCANCE

| Archivo | Cambio |
|---|---|
| `data/zonas_depreciacion.json` | Agregar `ct_annual_rate` por macrozona |
| `parsers/time_adjustment.py` | Reemplazar interpolación de tabla por fórmula exponencial: $(1 + \text{tasa})^{\frac{\text{meses}}{12}}$ |
| `parsers/mercado_inmobiliario.py` | Pasar `macrozona_id` a la función `calcular_ct` |
| `docs/ALGORITMOS.md` | Actualizar sección de Ajuste Temporal (Ct) |

---

### PASO 1: Configuración de Tasas
**Archivo:** `data/zonas_depreciacion.json`
1. Agregar `ct_annual_rate` basado en análisis rolling:
   - centro_premium: -0.0411
   - macrocentro: -0.0006
   - norte: -0.0665
   - oeste: -0.1949
   - sur_default: 0.0305
   - resto_rosario: -0.02

**COMMIT:** `"TAREA-113: Agregar tasas anuales de CT por macrozona"`
**VERIFICAR:** JSON válido

---

### PASO 2: Lógica de Cálculo
**Archivo:** `parsers/time_adjustment.py`
1. Implementar `get_ct_rate(macrozona_id)`
2. Modificar `calcular_ct(meses, es_nuevo_flag, macrozona_id)` para usar la fórmula exponencial.
3. Agregar `print(f"[DEBUG-CT] mz={macrozona_id} m={meses} tasa={tasa} ct={ct}")`

**COMMIT:** `"TAREA-113: Implementar cálculo de CT basado en tasa anual exponencial"`
**VERIFICAR:** `pytest`

---

### PASO 3: Integración en Motor
**Archivo:** `parsers/mercado_inmobiliario.py`
1. En `obtener_mediana_cluster_v2`, pasar `zona_resol` a `calcular_ct`.

**COMMIT:** `"TAREA-113: Vincular motor de cluster con tasa de CT por macrozona"`
**VERIFICAR:** `pytest` / Prueba visual Mabel

---

### PASO 4: Documentación
**Archivo:** `docs/ALGORITMOS.md`
1. Actualizar descripción de Ct: de "Interpolación de tabla" a "Crecimiento compuesto anual por macrozona".

**COMMIT:** `"TAREA-113: Documentar nueva lógica de Ct en ALGORITMOS.md"`

---

### VALIDACION FINAL
```
☐ pytest pasa (63+ tests)
☐ No hay saltos artificiales en comparables retroactivos de Centro Premium
☐ Logs [DEBUG-CT] muestran tasas correctas
```

### DOCS A ACTUALIZAR
- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md`
- `docs/ALGORITMOS.md`

### ENTREGABLES
- Sistema de CT dinámico por macrozona.
- Documentación actualizada.
- Plan archivado.

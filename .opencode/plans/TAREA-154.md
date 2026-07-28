# TAREA: TAREA-154 — Rediseño UI: Tarjeta Alquiler con rango + Tarjeta Rentabilidad desglosada — Riesgo BAJO

### CONTEXTO

Las tarjetas de métricas de inversión en `render_metricas()` (valu_detail_sections.py:505-544) muestran información incompleta y con etiquetas confusas:
- **Alquiler**: Muestra rango en una línea, sin rango explícito con prefijo "Rango:".
- **Cap Rate Neto**: Nombre técnico poco intuitivo para el usuario final.
- **No hay desglose** de costos del propietario (expensas extraordinarias, mantenimiento, vacancia).

El usuario solicita:
1. Tarjeta Alquiler mejorada con formato de rango explícito.
2. Tarjeta Rentabilidad renombrada y expandida con desglose de costos del propietario.

### REGLA DE ORO

- Los valores del motor **NO cambian** — solo se modifica la presentación UI.
- `python scripts/auto_validate.py` debe pasar después de cada paso.
- Tests de regresión existentes deben seguir pasando.

### UI GUARDRAILS

No se requieren tests de mock porque los cambios son puramente visuales (labels, layout, contenido de tarjetas). No se agregan/quitan botones ni se altera la lógica de persistencia.

### ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_detail_sections.py` | Reescribir `render_metricas()` (líneas 505-544): renombrar labels, mostrar rango de alquiler con prefijo, agregar tarjeta de rentabilidad desglosada con costos del propietario |

---

### PASO 1: Rediseñar tarjeta Alquiler con rango explícito

**Archivo:** `valu_detail_sections.py` — función `render_metricas()` (líneas 505-544)

**JUSTIFICACIÓN RO:** Este cambio es puramente visual. No modifica la lógica de cálculo de alquiler, cap rate ni ningún valor del motor. Solo cambia cómo se presentan los datos existentes en la UI.

**1.1** Reemplazar la lógica de formateo del alquiler (líneas 526-529) para mostrar:
- Valor principal: `$ <valor> ARS / mes   USD <valor_usd>`
- Segunda línea: `Rango: $<min> – $<max>`

**1.2** Calcular `alq_usd` usando el `dolar` que ya está disponible como parámetro.

**1.3** Cambiar el label de "Alquiler Estimado" a "Alquiler" (más corto).

```python
# Línea ~526-529: reemplazar formateo actual
alq_usd = int(alq_ars / dolar) if dolar > 0 else 0
alq_min_usd = int(alq_min / dolar) if dolar > 0 else 0
alq_max_usd = int(alq_max / dolar) if dolar > 0 else 0

# Tarjeta Alquiler con rango
with m1:
    if alq_min > 0 and alq_max > 0:
        st.markdown(metric_card(
            "",
            "Alquiler",
            f"${alq_ars:,.0f} ARS / mes   USD {alq_usd:,}",
            f"Rango: ${alq_min:,.0f} – ${alq_max:,.0f}",
        ), unsafe_allow_html=True)
    else:
        st.markdown(metric_card(
            "",
            "Alquiler",
            f"${alq_ars:,.0f} ARS / mes   USD {alq_usd:,}",
            "Sin datos de rango",
        ), unsafe_allow_html=True)
```

**COMMIT:** `"TAREA-154: Tarjeta Alquiler con rango explícito ARS + USD"`

**VERIFICAR:**
- `python scripts/auto_validate.py`
- Verificación visual: la tarjeta muestra "Alquiler" con valor ARS/USD y rango en segunda línea

---

### PASO 2: Renombrar "Cap Rate Neto" → "Rentabilidad neta"

**Archivo:** `valu_detail_sections.py` — función `render_metricas()` (línea 535)

**JUSTIFICACIÓN RO:** Cambio cosmético de label. No altera el cálculo de cap_rate ni ningún valor del motor.

**2.1** Cambiar el label de "Cap Rate Neto" a "Rentabilidad neta" en la tarjeta `m2`.

```python
# Línea 535: reemplazar label
st.markdown(metric_card(
    "",
    "Rentabilidad neta",
    f"{cap*100:.1f}% anual",
    f"Cierre est: ${valor_usd*0.92:,.0f} USD",
    border_color="#16A34A"
), unsafe_allow_html=True)
```

**COMMIT:** `"TAREA-154: Renombrar Cap Rate Neto → Rentabilidad neta"`

**VERIFICAR:**
- `python scripts/auto_validate.py`
- Verificación visual: tarjeta muestra "Rentabilidad neta" en vez de "Cap Rate Neto"

---

### PASO 3: Agregar tarjeta de Rentabilidad desglosada con costos del propietario

**Archivo:** `valu_detail_sections.py` — función `render_metricas()`

**JUSTIFICACIÓN RO:** Este paso agrega una nueva sección visual debajo de las 3 tarjetas de métricas. No modifica la lógica de cálculo existente. Los costos se calculan a partir de datos ya disponibles en `prop` y `res`.

**3.1** Después del bloque de las 3 columnas (m1, m2, m3), agregar una nueva sección completa con:

**Rentabilidad bruta** = `cap_rate * 100` (anual)
**Rentabilidad neta** = `cap_rate * 100 * 0.92` (aproximación: 8% de impuestos/costos operativos sobre renta)

**Costos del propietario:**
- **Expensas extraordinarias**: `prop.get('expensas_ars', 0)` — si no hay dato, mostrar "Sin datos"
- **Mantenimiento estimado**: `alq_ars * 0.065` (6.5% del alquiler como estimación de mantenimiento)
- **Vacancia estimada (4%)**: `alq_ars * 0.04`

**3.2** Renderizar con HTML inline usando `st.markdown(unsafe_allow_html=True)` para controlar el formato exacto:

```python
# Después de las 3 columnas m1/m2/m3, agregar:
st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

# Tarjeta de Rentabilidad de la inversión
expensas = prop.get('expensas_ars', 0)
mantenimiento = int(alq_ars * 0.065) if alq_ars > 0 else 0
vacancia = int(alq_ars * 0.04) if alq_ars > 0 else 0
cap_rate_pct = cap * 100
cap_rate_neto_pct = cap_rate_pct * 0.92

rentabilidad_html = f"""
<div style="background:white;border-radius:16px;padding:20px 24px;box-shadow:0 4px 12px rgba(0,0,0,0.08);margin-top:8px;">
    <div style="font-size:14px;font-weight:700;color:#1A2B5C;margin-bottom:12px;">Rentabilidad de la inversión</div>
    <div style="display:flex;gap:32px;margin-bottom:16px;">
        <div>
            <div style="color:#6B7280;font-size:12px;">Rentabilidad bruta</div>
            <div style="color:#1A2B5C;font-size:18px;font-weight:700;">{cap_rate_pct:.1f}% anual</div>
        </div>
        <div>
            <div style="color:#6B7280;font-size:12px;">Rentabilidad neta</div>
            <div style="color:#16A34A;font-size:18px;font-weight:700;">{cap_rate_neto_pct:.1f}% anual</div>
        </div>
    </div>
    <div style="border-top:1px solid #E5E7EB;padding-top:12px;">
        <div style="color:#6B7280;font-size:12px;font-weight:600;margin-bottom:8px;">Costos del propietario:</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 24px;font-size:13px;color:#374151;">
            <div>Expensas extraordinarias:</div><div style="text-align:right;">$ {expensas:,.0f} ARS/mes</div>
            <div>Mantenimiento estimado:</div><div style="text-align:right;">$ {mantenimiento:,.0f} ARS/mes</div>
            <div>Vacancia estimada (4%):</div><div style="text-align:right;">$ {vacancia:,.0f} ARS/mes</div>
        </div>
    </div>
</div>
"""
st.markdown(rentabilidad_html, unsafe_allow_html=True)
```

**COMMIT:** `"TAREA-154: Tarjeta Rentabilidad desglosada con costos del propietario"`

**VERIFICAR:**
- `python scripts/auto_validate.py`
- Verificación visual: aparece tarjeta completa con "Rentabilidad de la inversión", bruta, neta, y desglose de 3 costos

---

### PASO 4: Actualizar docs y commit final

**Archivo:** `.opencode/plans/TAREAS_INDEX.md`, `docs/BITACORA_AGENTES.md`

**JUSTIFICACIÓN RO:** Documentación obligatoria post-cambio (RO-EXEC-02).

**4.1** Agregar entrada de TAREA-154 en TAREAS_INDEX.md.

**4.2** Registrar en BITACORA_AGENTES.md el cambio de UI en `render_metricas()`.

**COMMIT:** `"TAREA-154: Actualizar docs post-cambio UI alquiler/rentabilidad"`

**VERIFICAR:**
- Archivos de documentación actualizados

---

### VALIDACION FINAL

```
☐ python scripts/auto_validate.py pasa
☐ Tarjeta "Alquiler" muestra: $ <ARS> ARS / mes   USD <USD> + Rango: $<min> – $<max>
☐ Tarjeta "Rentabilidad neta" reemplaza "Cap Rate Neto"
☐ Nueva tarjeta "Rentabilidad de la inversión" con bruta, neta y 3 costos
☐ No se alteraron cálculos del motor (cap_rate, alquiler_estimado_ars, etc.)
☐ TAREAS_INDEX.md actualizado con TAREA-154
☐ BITACORA_AGENTES.md actualizado
```

### DOCS A ACTUALIZAR

- `.opencode/plans/TAREAS_INDEX.md` (agregar entrada TAREA-154)
- `docs/BITACORA_AGENTES.md` (registrar cambio UI)

### ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-154.md`.
NO se elimina al ejecutar. Sirve como registro histórico.

### ENTREGABLES

- Archivo `valu_detail_sections.py` modificado (función `render_metricas`)
- `python scripts/auto_validate.py` pasando
- Verificación visual completa
- Plan archivado en `.opencode/plans/TAREA-154.md`

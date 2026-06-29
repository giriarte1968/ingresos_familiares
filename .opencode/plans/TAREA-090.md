## TAREA: TAREA-090 — Transparencia: desglose de fórmula en header — Riesgo BAJO

### CONTEXTO

El usuario notó que al cambiar los comparables (Retro), el precio/m² en la tabla subía pero la valuación final no cambiaba. Esto generaba confusión porque el motor usa una fórmula compleja (cluster + size adjustment + activos) que no es visible. Para resolverlo, se agrega un desglose en el header que muestra:

`$1,716/m² × 42.3 m²_eq × 1.155 ajuste + $5,000 extras = $83,851`

Así el usuario ve que cada componente SÍ cambia, pero se compensan.

### REGLA DE ORO

- `pytest` pasa después del cambio
- La fórmula mostrada en el header debe ser matemáticamente correcta: `valor = m2_base × m2_eq × size_discount + activos`
- No se altera ningún valor de valuación
- El breakdown solo aparece si hay datos suficientes (m2_base > 0 y m2_eq > 0)

### ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py:3631-3632` | Agregar `size_discount` y `valor_activos_total` al resultado dict |
| `valu_detail_sections.py:159-162` | Leer nuevos campos en `render_header` |
| `valu_detail_sections.py:219` | Agregar línea de desglose en el HTML del header |

---

### PASO 1: Backend — exponer size_discount y activos

**Archivo:** `parsers/mercado_inmobiliario.py` (líneas 3631-3632)

**1.1** Agregar `size_discount` (calculado en línea 3324) al resultado dict.
**1.2** Agregar `valor_activos_total` (calculado en línea 3369-3370) al resultado dict.

```python
'm2_base_venta': round(m2_base_venta, 2),
'size_discount': round(size_discount, 4),
'valor_activos_total': round(valor_activos['total'], 2),
```

### PASO 2: UI — mostrar desglose en header

**Archivo:** `valu_detail_sections.py` — función `render_header`

**2.1** Leer `size_discount`, `valor_activos_total`, `m2_equivalentes` del display.
**2.2** Agregar línea HTML con el breakdown.

```python
# Lectura de nuevos campos (línea 160-162):
size_discount = display.get('size_discount', 1.0)
activos_total = display.get('valor_activos_total', 0)
m2_equiv_display = display.get('m2_equivalentes', 0)

# Línea HTML agregada (línea 219):
<div style="font-size:10px;color:rgba(255,255,255,0.5);margin-top:4px;">
  {'${:,.0f}/m² × {} m² × {} ajuste + ${:,.0f} extras = ${:,.0f}'.format(...)}
</div>
```

### VERIFICAR

- `python scripts/auto_validate.py`
- `pytest tests/test_regression.py`
- Ver visual: el header muestra el desglose debajo del precio

---

### VALIDACION FINAL

```
☐ auto_validate.py pasa
☐ pytest (47 tests) pasa
☐ En UI: el header POR COMPARABLES muestra línea de desglose con la fórmula
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md`

### ARCHIVO DE PLAN

Permanente en `.opencode/plans/TAREA-090.md`. ID secuencial: 090.

### ENTREGABLES

- `mercado_inmobiliario.py` modificado
- `valu_detail_sections.py` modificado
- Tests pasando
- Commit + push

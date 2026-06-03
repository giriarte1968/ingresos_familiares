# TAREA-029 — Balcón: eliminar bonus_m2, desbloquear tipo_balcon, recalibrar factores — Riesgo MEDIO

## CONTEXTO

`tipo_balcon` está硬codeado a `'ninguno'` en el form (`valu_forms.py:392` y `app.py:3508`), haciendo que `factor_balcon` y `bonus_m2` estén efectivamente desactivados para el usuario. Además, `bonus_m2` en `calcular_m2_equivalentes` duplica el valor de los m² semicubiertos que ya entran en `m2_equiv` con coeficiente 0.45.

| Capa | Dónde | Qué suma |
|---|---|---|
| `m2_semi × 0.45` | `m2_equiv` | Valor base de los m² semicubiertos |
| `bonus_m2` | `m2_equiv` | +5% (corrido) / +10% (L) de los mismos m² |
| `factor_balcon` | `f_estructural` | +2% a +6% sobre el total |

## REGLA DE ORO

- `pytest` pasa después de cada paso
- Mabel tiene `tipo_balcon: 'corrido'` — su valor puede cambiar (aceptado)
- Ayacucho, Vera Mujica, Entre Ríos sin cambios (no tienen tipo_balcon → ninguno)
- SumaCruda clamp (±40%) y AMENITY_TOTAL_CAP intactos

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_forms.py` | Agregar `tipo_balcon` selectbox |
| `parsers/mercado_inmobiliario.py` | Eliminar `bonus_m2` de `calcular_m2_equivalentes` |
| `parsers/mercado_inmobiliario.py` | Actualizar coeficientes de `factor_balcon` |
| `app.py` | Reemplazar hardcodeo por lectura de prop_inicial |
| `docs/DICCIONARIO_DATOS.md` | Actualizar tabla factor_balcon |
| `tests/test_regression.py` | Ajustar rango de Mabel |

---

### PASO 1: Crear plan + actualizar índice

**Archivos:** `.opencode/plans/TAREA-029.md`, `.opencode/plans/TAREAS_INDEX.md`

---

### PASO 2: Eliminar `bonus_m2` de `calcular_m2_equivalentes()`

**Archivo:** `parsers/mercado_inmobiliario.py` — función `calcular_m2_equivalentes` (L1655-1661, L1706)

Eliminar bloque bonus_m2 y su variable base_bonus_balcon. Sacar bonus_m2 de la suma m2_equiv.

---

### PASO 3: Actualizar coeficientes de `factor_balcon`

**Archivo:** `parsers/mercado_inmobiliario.py` — L1967-1976

| tipo_balcon | Antes | Después |
|---|---|---|
| `terraza` | 1.06 | 1.09 |
| `L` | 1.05 | 1.07 |
| `corrido` | 1.02 | 1.035 |
| `frances` | 0.98 | 0.98 |
| `ninguno` | 1.00 | 1.00 |

---

### PASO 4: Agregar `tipo_balcon` al formulario

**Archivo:** `valu_forms.py` — Sección Funcionalidad + dict data

Agregar selectbox con opciones: ninguno, corrido, L, frances, terraza.
Reemplazar hardcodeo `'balcon': False, 'tipo_balcon': 'ninguno'` por `'tipo_balcon': tipo_balcon`.

---

### PASO 5: Fix `app.py`

**Archivo:** `app.py:3508`

Reemplazar `'balcon': False, 'tipo_balcon': 'ninguno'` por `'tipo_balcon': prop_inicial.get('tipo_balcon', 'ninguno')`.

---

### PASO 6: Ajustar test Mabel

**Archivo:** `tests/test_regression.py` — `test_mabel_venta`

Re-valuar Mabel, ajustar rango al nuevo valor.

---

### PASO 7: Actualizar documentación

**Archivo:** `docs/DICCIONARIO_DATOS.md`

Actualizar tabla factor_balcon, eliminar bonus_m2 de la documentación.

---

### VALIDACION FINAL

```
☐ pytest pasa (39+ tests)
☐ Mabel valor actualizado dentro del nuevo rango
☐ Ayacucho, Vera Mujica, Ente Ríos sin cambios
☐ Formulario muestra selector tipo_balcon
☐ auto_validate.py OK
```

### DOCS A ACTUALIZAR

- `docs/DICCIONARIO_DATOS.md`
- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md`
- `.opencode/plans/TAREA-029.md`

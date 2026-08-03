# TAREA-162 — Depreciación automática en Valor Oficial — Riesgo BAJO

## CONTEXTO

Cuando el analista selecciona "Valor oficial" como fuente del m², se usa el precio oficial de la zona (ej. Centro 3D: $2,122/m²) **sin ajuste por antigüedad**. Este precio es la mediana de publicaciones de toda la zona, que incluye propiedades nuevas y viejas.

Para una propiedad de 1971 (55 años), el precio real debería ser inferior a la mediana porque los edificios viejos se transan con descuento. En el motor automático esto se resuelve con filtro de edad (±10 años) y P33, pero en "Valor oficial" no hay ninguno de estos mecanismos.

**Ejemplo Mitre1473:** $2,122/m² × 0.78 (factor anti) = $1,655/m² → valor $340,930 vs $437,132 actual.

## REGLA DE ORO

- Los valores del motor automático NO cambian (solo afecta manual + valor oficial)
- La depreciación SOLO se aplica cuando `fuente_m2 == "Valor oficial"`
- El factor de depreciación se calcula con la misma fórmula que `_calcular_factores_rental()` (ya validada)
- `pytest` pasa después de cada paso

## UI GUARDRAILS

- Mostrar "Depreciación: XX% (XX años × X.X%/año)" como caption debajo del USD/m² oficial
- El valor en el number_input DEBE reflejar el precio ya depreciado
- Transparencia: el analyst debe ver tanto el precio original como el ajustado

## ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | Aplicar `factor_anti` en `generar_resultado_manual()` cuando `fuente_m2 == "Valor oficial"` |
| `valu_detail_sections.py` | Mostrar depreciación acumulada en UI + precio ajustado |
| `tests/test_regression.py` | Test que verifique que oficial × factor_anti = valor correcto |

---

## PASO 1: Lógica de depreciación en `generar_resultado_manual()`

**Archivo:** `parsers/mercado_inmobiliario.py` — función `generar_resultado_manual()` (línea ~4126)

**JUSTIFICACIÓN RO:** No se viola RO-073 (factores hedónicos eliminados de venta) porque este no es un factor hedónico genérico — es un ajuste específico por fuente de datos (oficial = precio de publicación zona-level, no transacción). El motor automático no lo necesita porque filtra por edad; el manual con oficial no tiene ese filtro.

**1.1** Importar `obtener_tasa_depreciacion_macrozona` al inicio de la función

**1.2** Después de calcular `usd_m2`, detectar si `fuente_m2 == "Valor oficial"` y calcular `factor_anti`

**1.3** Aplicar `usd_m2_ajustado = usd_m2 * factor_anti` al cálculo del valor

**1.4** Guardar `delta_anti`, `factor_anti`, `usd_m2_original` en el resultado para transparencia

```python
# Después de la línea donde se obtiene usd_m2 (línea ~4137):
usd_m2 = manual_params.get('usd_m2', 0)
fuente_m2 = manual_params.get('fuente_m2', 'Ancla del cluster')

# ─── Depreciación por antigüedad (solo Valor Oficial) ───
factor_anti = 1.0
delta_anti = 0.0
usd_m2_original = usd_m2
if fuente_m2 == 'Valor oficial':
    try:
        from parsers.zonas_manager import obtener_tasa_depreciacion_macrozona
        _tasa_zonal, _ = obtener_tasa_depreciacion_macrozona(prop)
        anio_constr = prop.get('anio_construccion', 0)
        if anio_constr and anio_constr > 0:
            antiguedad = 2026 - int(anio_constr)
            delta_anti_raw = max(-0.60, -(_tasa_zonal * antiguedad))
            UMBRAL_PENALIZACION_SEVERA = -0.18
            FACTOR_ATENUACION = 0.35
            if delta_anti_raw < UMBRAL_PENALIZACION_SEVERA:
                exceso = delta_anti_raw - UMBRAL_PENALIZACION_SEVERA
                delta_anti = UMBRAL_PENALIZACION_SEVERA + (exceso * FACTOR_ATENUACION)
            else:
                delta_anti = delta_anti_raw
            factor_anti = max(0.40, 1.0 + delta_anti)
            usd_m2 = round(usd_m2 * factor_anti, 2)
    except Exception:
        pass
```

**1.5** Actualizar el cálculo del subtotal para usar `usd_m2` (ya ajustado)

**1.6** Agregar campos al `result` dict:
```python
'delta_anti': round(delta_anti, 4),
'factor_anti': round(factor_anti, 4),
'usd_m2_original': round(usd_m2_original, 2),
'usd_m2_ajustado': round(usd_m2, 2) if factor_anti != 1.0 else None,
```

**COMMIT:** `"feat: depreciación automática en Valor Oficial (TAREA-162)"`

**VERIFICAR:**
- `pytest` pasa
- Test nuevo `test_fuente_m2_oficial_depreciacion` verifica el cálculo

---

## PASO 2: UI — Mostrar depreciación acumulada

**Archivo:** `valu_detail_sections.py` — bloque "Valor oficial" (línea ~2004)

**JUSTIFICACIÓN RO:** Cambio visual puro. No altera lógica de persistencia ni el motor automático.

**2.1** Calcular `antigüedad` y `delta_anti` en el UI para mostrar caption

**2.2** Actualizar caption debajo del number_input con el desglose

```python
# En el bloque "elif fuente_sel == 'Valor oficial':", después del st.caption de fuente:
try:
    from parsers.zonas_manager import obtener_tasa_depreciacion_macrozona
    _tasa_z, _ = obtener_tasa_depreciacion_macrozona(prop)
    _anio = prop.get('anio_construccion', 0)
    if _anio and _tasa_z:
        _anti = 2026 - int(_anio)
        _delta_raw = max(-0.60, -(_tasa_z * _anti))
        _umbral = -0.18
        _atenuacion = 0.35
        if _delta_raw < _umbral:
            _exceso = _delta_raw - _umbral
            _delta = _umbral + (_exceso * _atenuacion)
        else:
            _delta = _delta_raw
        _factor = max(0.40, 1.0 + _delta)
        _ajustado = float(usd_oficial_val) * _factor
        st.caption(
            f"Depreciación: {_delta*100:+.1f}% ({_anti} años × {_tasa_z*100:.1f}/año). "
            f"Valor ajustado: USD {int(_ajustado):,}/m²"
        )
except Exception:
    pass
```

**COMMIT:** `"feat: UI muestra depreciación acumulada en Valor Oficial (TAREA-162)"`

**VERIFICAR:**
- `pytest` pasa
- Verificación visual: Mitre1473 muestra "Depreciación: -22.0% (55 años × 0.4/año). Valor ajustado: USD 1,655/m²"

---

## PASO 3: Test de regresión

**Archivo:** `tests/test_regression.py`

**JUSTIFICACIÓN RO:** Test que valida que el cálculo de depreciación es correcto para valor oficial.

**3.1** Agregar test `test_fuente_m2_oficial_depreciacion`

```python
@pytest.mark.core
def test_fuente_m2_oficial_depreciacion():
    """TAREA-162: Valor oficial aplica depreciación por antigüedad."""
    from parsers.mercado_inmobiliario import generar_resultado_manual
    from parsers.location_engine import obtener_precio_oficial
    from parsers.zonas_manager import obtener_tasa_depreciacion_macrozona

    prop = {
        'nombre': 'test_deprec',
        'tipo_inmueble': 'departamento',
        'zona': 'Centro',
        'direccion': 'Mitre 1473',
        'lat': -32.9544, 'lon': -60.6416,
        'm2': 206, 'm2_cubiertos': 206,
        'dormitorios': 3,
        'anio_construccion': 1971,
    }

    oficial = obtener_precio_oficial('Centro', 3)
    usd_m2_original = oficial['usd_m2']  # 2122

    # Calcular factor_anti esperado
    _tasa_z, _ = obtener_tasa_depreciacion_macrozona(prop)
    antiguedad = 2026 - 1971  # 55
    delta_anti_raw = max(-0.60, -(_tasa_z * antiguedad))
    factor_anti = max(0.40, 1.0 + delta_anti_raw)
    usd_m2_esperado = round(usd_m2_original * factor_anti, 2)

    manual_params = {
        'ancla_id': '_oficial',
        'usd_m2': float(usd_m2_original),
        'factor_hedonico': 1.0,
        'incertidumbre_pct': 10.0,
        'ajuste_pct': 0.0,
        'incluir_prima_const': False,
        'fuente_m2': 'Valor oficial',
    }

    result = generar_resultado_manual(prop, manual_params)
    assert result.get('factor_anti') == round(factor_anti, 4), \
        f"factor_anti debe ser {factor_anti:.4f}, got {result.get('factor_anti')}"
    assert result.get('m2_base_venta') == usd_m2_esperado, \
        f"m2_base_venta debe ser {usd_m2_esperado}, got {result.get('m2_base_venta')}"
    assert result.get('delta_anti') != 0, "delta_anti debe ser distinto de 0"
    print(f"[T-DEPREC-OFICIAL] OK — anti={antiguedad}y, tasa={_tasa_z}, factor={factor_anti:.4f}, m2={usd_m2_esperado}")
```

**COMMIT:** `"test: depreciación automática en Valor Oficial (TAREA-162)"`

**VERIFICAR:**
- `pytest tests/test_regression.py -v` — 57 tests pasan

---

## VALIDACIÓN FINAL

```
☐ pytest pasa (57 tests)
☐ Mitre1473 Valor oficial muestra precio depreciado
☐ Caption muestra desglose de depreciación
☐ Valor oficial sin año de construcción NO aplica depreciación (factor_anti=1.0)
☐ Ancla del cluster NO se afecta por depreciación
```

## DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md`

## ARCHIVO DE PLAN

`.opencode/plans/TAREA-162.md`

## ENTREGABLES

- `parsers/mercado_inmobiliario.py` modificado
- `valu_detail_sections.py` modificado
- `tests/test_regression.py` con test nuevo
- 57 tests pasando
- Plan archivado en `.opencode/plans/TAREA-162.md`

# TAREA-030: Fix barreras duras en Puerto Norte + Fallback cluster + Ancla

## Diagnóstico
Francia 250 bis (`lat -32.9304159, lon -60.6620818`) queda **entre dos vías de tren** (vía sur `~-32.93087`, vía norte `~-32.9296`). Las 73 propiedades dentro de 500m están **todas fuera de esa franja** → cualquier línea sujeto-comparable cruza una vía → `excluded_hard` para TODAS → `same_side=0, cross_soft=0` → pool vacío → `n_v=0` → fallback ancla con valor incorrecto.

**Solución**: No tocar coordenadas (son correctas). Corregir la regla.

---

## Cambios

### Archivo: `parsers/mercado_inmobiliario.py`

#### PASO 1 — Barreras blandas por zona (líneas ~1090-1119)

Donde hoy se aplican barreras, agregar lógica post-`separar_por_barreras`:

```python
        same_side = barreras_result['same_side']
        cross_soft = barreras_result['cross_soft']
        excluded_hard = barreras_result['excluded_hard']

        # === PASO 1: Convertir excluded_hard → cross_soft para zonas urbanas densas ===
        # En Rosario, las vías del tren no aíslan mercados (ej: Puerto Norte,
        # Centro). No tiene sentido excluir 73/73 comparables por 50m de vía.
        ZONAS_BARRERA_BLANDA = ['Puerto Norte', 'Refinería', 'Centro', 'Alberto Olmedo']
        if zona_normalizada in ZONAS_BARRERA_BLANDA and excluded_hard:
            for comp in excluded_hard:
                comp['_penalizacion_barrier'] = 0.97
                cross_soft.append(comp)
            excluded_hard = []
            logger.info(f"[BARRERA_BLANDA] {zona_normalizada}: {len(cross_soft)} props reconvertidas (penalización 0.97)")

        # === PASO 2: Si aún no hay comparables, fallback con excluded_hard ===
        if not same_side and not cross_soft and len(excluded_hard) >= 5:
            for comp in excluded_hard:
                comp['_penalizacion_barrier'] = 0.97
                cross_soft.append(comp)
            excluded_hard = []
            logger.info(f"[BARRERA_FALLBACK] {len(cross_soft)} props usadas vía fallback (penalización 0.97)")
```

#### PASO 1b — Aplicar penalización en precios (líneas ~1165, ~1236-1243)

```python
# Línea 1165 actual:
#   precios = [p['valor_m2'] for p in pool_final]
# Reemplazar con:
        precios = [p['valor_m2'] * p.get('_penalizacion_barrier', 1.0) for p in pool_final]
```

```python
# Líneas 1236-1243 actual:
#   for p in pool_final:
#       val = p.get('valor_m2', 0)
# Reemplazar con:
        for p in pool_final:
            penalty = p.get('_penalizacion_barrier', 1.0)
            val = p.get('valor_m2', 0) * penalty
```

#### PASO 3 — Ancla correcta para Puerto Norte (líneas ~3093-3098)

```python
    # Fallback a ancla
    antiguedad = ANIO_ACTUAL - anio_const
    
    # Puerto Norte: forzar rio_puerto_norte (2100) y NO depreciar si es a estrenar
    if zona_txt.lower() in ('puerto norte',) or 'puerto norte' in str(prop.get('zona', '')).lower():
        valor_ancla_geo = 2100
        ancla_seleccionada = 'rio_puerto_norte'
        if prop.get('estado_detalle') == 'a estrenar' and anio_const >= 2020:
            factor_deprec = 1.0
        else:
            factor_deprec = max(0.5, 1.0 - (antiguedad * 0.006))
    else:
        factor_deprec = max(0.5, 1.0 - (antiguedad * 0.006))
    
    m2_base_venta = valor_ancla_geo * factor_deprec
    metodo_origen = "Ancla (fallback)"
```

---

## Validación

1. `python scripts/auto_validate.py`
2. `python -m pytest tests/ -v` (especialmente `test_regression.py`)
3. Valuar Francia 250 bis (dorm=1, depto, venta) → verificar:
   - `n_comparables_total > 0` (esperado ~73)
   - `m2_base_venta` en rango ~1.800-2.100 USD/m²
   - `resolution = GEO` y `confidence` no `BAJA`
4. Valuar Mabel (Barrio Martin) → verificar no regresión (~$76.293)
5. Valuar Ayacucho 1800 → verificar no regresión

---

## Commit

```
git commit -m "fix: barreras duras como blandas en Puerto Norte + fallback + ancla

- B + C: Las vías del tren en zonas urbanas densas (Puerto Norte, Centro)
  ahora son barreras blandas (penalización 3% en vez de exclusión total).
- Fallback robusto: si todas cruzan barrera dura, se usan con 0.97.
- Ancla Puerto Norte: fuerza rio_puerto_norte (2100 USD/m²) en fallback,
  sin depreciación si es a estrenar post-2020."
```

---

## Documentación a actualizar

- [ ] `docs/BITACORA_AGENTES.md` — registro del fix de barreras
- [ ] `docs/ALGORITMOS.md` — actualizar sección de barreras si corresponde
- [ ] `.opencode/plans/TAREAS_INDEX.md` — marcar TAREA-030 como ejecutada

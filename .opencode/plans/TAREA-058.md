# TAREA-058: Calcular precio ajustado dinámicamente en UI (sin depender del cache)

## Problema
El preview y el Apply Selection leían `precio_m2_ajustado` directamente del cache:
```python
c.get('precio_m2_ajustado', c.get('precio_m2', 0))
```
El cache guardaba este campo sin incluir `barrier_penalty` (por ser anterior a TAREA-057). Como resultado:
- Preview n=2: `($3,213 + $5,574)/2 = $4,394` ❌ (vs motor `$4,262`)
- Badge BARRERA no se mostraba a menos que el cache se regenerara

## Solución
Calcular el precio ajustado desde los componentes individuales, replicando la fórmula del motor (`mercado_inmobiliario.py:1383`):
```python
val = p.get('valor_m2', 0) * penalty * ta
```

Implementación en la UI:
```python
precios = [c.get('precio_m2', 0) * c.get('time_adjustment', 1.0) * c.get('barrier_penalty', 1.0) for c in comps]
```

Esto funciona para cualquier n (n<3 usa MEDIA, n≥3 usa percentiles) y no depende del contenido del cache.

## Archivos modificados
- `valu_detail_sections.py:342`
- `valu.py:568`

## Validacion
- `python scripts/auto_validate.py` -> OK
- Tests de regresion -> OK
- Preview n=2: `$4,262` (coincide con header)
- Badge BARRERA visible aunque cache sea viejo
- Apply Selection recalcula con la misma formula

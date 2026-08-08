# Análisis: Ajuste por Tipo de Dormitorio (Interdepartamento)

**Fecha**: 2026-07-26
**Estado**: Análisis guardado, pendiente de implementación

## Problema

Cuando se usan comparables de distintos dormitorios (ej: 1-dorm comps para sujeto 3-dorm), hay diferencias sistemáticas de precio_m2 que varían por zona. El sistema actual NO ajusta por esta diferencia.

## Datos del Análisis

### Ratios de precio_m2 por dormitorio (baseline = 2-dorm)

| Zona | 1-dorm | 2-dorm | 3-dorm | 4-dorm | 5-dorm |
|------|--------|--------|--------|--------|--------|
| **Puerto Norte** | 1.069 | 1.000 | **1.404** | 0.541 | — |
| **Centro** | 0.922 | 1.000 | 0.984 | 0.716 | 0.636 |
| **Norte** | **1.469** | 1.000 | 1.104 | 0.984 | 1.124 |
| **Oeste** | **1.614** | 1.000 | 0.999 | 1.026 | 0.856 |
| **Sur** | 1.134 | 1.000 | 0.948 | 1.030 | 1.038 |

### Impacto: Error al usar comps de dorm incorrecto

| Sujeto | Zona | Usando 1-dorm | Usando 2-dorm |
|--------|------|---------------|---------------|
| 3-dorm | Puerto Norte | **-21.9%** | **-28.7%** |
| 3-dorm | Norte | **+33.1%** | -9.1% |
| 3-dorm | Oeste | **+61.5%** | +0.1% |
| 3-dorm | Centro | -6.3% | +1.7% |

## Solución Propuesta

### 1. Almacenamiento en zonas_depreciacion.json

Agregar `dorm_type_ratios` en cada macrozona:

```json
{
  "id": "puerto_norte",
  "dorm_type_ratios": {
    "baseline": 2,
    "ratios": {
      "1": 1.069,
      "2": 1.000,
      "3": 1.404,
      "4": 0.541
    }
  }
}
```

### 2. Función de ajuste en mercado_inmobiliario.py

```python
def calcular_dorm_type_adjustment(dorm_comp, dorm_sujeto, macrozona_id):
    """
    Retorna ratio para ajustar precio_m2 del comp al nivel del sujeto.
    Ej: comp=1-dorm, sujeto=3-dorm, ratio=1.313 → multiplica precio por 1.313
    """
    config = _cargar_dorm_type_config()
    mz_config = config.get(macrozona_id, {})
    ratios = mz_config.get('ratios', {})
    baseline = mz_config.get('baseline', 2)
    
    if not ratios or dorm_comp == dorm_sujeto:
        return 1.0
    
    # Normalizar相对于 baseline
    ratio_comp = ratios.get(str(dorm_comp), 1.0)
    ratio_sujeto = ratios.get(str(dorm_sujeto), 1.0)
    
    if ratio_comp > 0:
        return ratio_sujeto / ratio_comp
    return 1.0
```

### 3. Integración en _precio_ajustado()

```python
def _precio_ajustado(c, macrozona_id=None, ancla_id=None, dormitorios_sujeto=None):
    precio = c.get('precio_m2', c.get('valor_m2', 0))
    adj = c.get('time_adjustment', 1.0)
    raw_val = precio * adj
    
    m2_comp = c.get('m2') or c.get('m2_cubiertos', 0)
    dorms_comp = c.get('dormitorios')
    
    # Size adjustment (existente)
    adj_size = calcular_size_adjustment(m2_comp, macrozona_id, ancla_id=ancla_id, dormitorios=dorms_comp)
    norm_val = raw_val / adj_size if adj_size > 0 else raw_val
    
    # NUEVO: Dorm type adjustment
    if dormitorios_sujeto and dorms_comp and dorms_comp != dormitorios_sujeto:
        adj_dorm = calcular_dorm_type_adjustment(dorms_comp, dormitorios_sujeto, macrozona_id)
        norm_val *= adj_dorm
    
    return norm_val
```

### 4. Parámetro dormitorios_sujeto

El `dormitorios_sujeto` ya está disponible en `obtener_mediana_cluster_v2()` como parámetro `dormitorios`. Se pasa a `_precio_ajustado()`.

### 5. Calcular ratios desde datos

Los ratios se calculan usando medianas de precio_m2 por dormitorio dentro de cada macrozona, usando solo datos con CT aplicado y antigüedad ±10 años.

## Archivos a Modificar

1. `data/zonas_depreciacion.json` — agregar `dorm_type_ratios` por macrozona
2. `parsers/mercado_inmobiliario.py` — nueva función `calcular_dorm_type_adjustment()` + modificar `_precio_ajustado()`
3. `parsers/cluster_filters.py` — pasar `dormitorios_sujeto` a `_precio_ajustado()` en `calcular_percentil()` y `calcular_blend_p33()`

## Dependencias

- TAREA-146 (size adjustment by dormitorios) ya implementada
- CT ajustado por dormitorio (TAREA-147) ya implementado
- Los ratios se calculan desde los mismos datos CT-adjusted

## Notas

- Los ratios varían MUCHO por zona (Oeste: 1-dorm +61%, Centro: 1-dorm -8%)
- Puerto Norte tiene el mayor spread (3-dorm +40% vs 2-dorm)
- La implementación es similar a size_adjustment pero con ratios fijos por dormitorio
- Se recomienda recalcular ratios periódicamente (ej: cada vez que se actualiza cache_scraping)

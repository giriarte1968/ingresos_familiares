# TAREA: CT Alquiler — Integración al Sistema

## CONTEXTO
El análisis de tendencia temporal de alquileres (scripts/ct_alquiler_analysis.py) derivó un CT de +23.6% anual desde nuestro scraping, con fuentes oficiales (IPEC +39.9%, ICL +32.6%, CESO +32.1%). Se recomienda +30.1% anual como CT blend. Actualmente el CT de venta se usa para alquileres viejos, lo cual es incorrecto porque los mercados se mueven en direcciones opuestas.

## REGLA DE ORO
- Los valores del motor de CT alquiler NO pueden hardcodearse — siempre vienen de zonas_depreciacion.json
- El CT alquiler es INDEPENDIENTE del CT venta
- La fórmula debe ser visible en pantalla para el analista
- Los valores deben ser editables por macrozona Y por dormitorios

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `data/zonas_depreciacion.json` | Agregar `ct_alquiler_rate` y `ct_alquiler_by_dormitorios` por macrozona |
| `parsers/time_adjustment.py` | Agregar `get_ct_alquiler_rate()` y `calcular_ct_alquiler()` |
| `parsers/mercado_inmobiliario.py` | Aplicar CT alquiler en el cluster de alquiler |
| `valu.py` | UI editor CT alquiler + fórmula visible |

---

## PASO 1: Config CT alquiler en zonas_depreciacion.json

**Archivo:** `data/zonas_depreciacion.json`

Agregar a cada macrozona:
```json
"ct_alquiler_rate": 0.3014,
"ct_alquiler_by_dormitorios": {
  "1": 0.2934,
  "2": 0.5021,
  "3": 0.6470
},
"ct_alquiler_fuente": "Scraping propio (60%) + IPEC (40%)",
"ct_alquiler_fecha": "2026-07-30"
```

**COMMIT:** `"config: add ct_alquiler rates per macrozona from scraping analysis"`

---

## PASO 2: Funciones CT alquiler en time_adjustment.py

**Archivo:** `parsers/time_adjustment.py`

```python
def get_ct_alquiler_rate(macrozona_id=None, dormitorios=None):
    """Retorna tasa anual CT alquiler desde zonas_depreciacion.json.
    Si se especifica dormitorios, usa la tasa específica.
    Si no, usa la tasa general de la macrozona."""
    
def calcular_ct_alquiler(meses, macrozona_id=None, dormitorios=None):
    """Calcula CT para alquiler: (1 + tasa_alquiler)^(meses/12)"""
```

**COMMIT:** `"feat(ct_alquiler): add calcular_ct_alquiler function"`

---

## PASO 3: Integrar CT alquiler en cluster de alquiler

**Archivo:** `parsers/mercado_inmobiliario.py`

En `obtener_mediana_cluster_v2()`, cuando `operacion='alquiler'`, usar `calcular_ct_alquiler()` en vez de `calcular_ct()`:

```python
# ACTUAL (line ~1336):
p['_time_adjustment'] = calcular_ct(m, es_nuevo(p), macrozona_id=macrozona_id_ct)

# NUEVO:
if operacion == 'alquiler':
    p['_time_adjustment'] = calcular_ct_alquiler(m, macrozona_id=macrozona_id_ct, dormitorios=dormitorios)
else:
    p['_time_adjustment'] = calcular_ct(m, es_nuevo(p), macrozona_id=macrozona_id_ct)
```

**COMMIT:** `"feat(ct_alquiler): apply rental CT to alquiler comparables"`

---

## PASO 4: UI editor CT alquiler

**Archivo:** `valu.py`

Agregar expander "📈 CT Alquiler" con:
1. Tabla editable por macrozona (ct_alquiler_rate general)
2. Sub-tabla por dormitorios (1d, 2d, 3d)
3. Fuentes oficiales como referencia (IPEC, ICL, CESO)
4. Fórmula visible: `CT_alquiler = (1 + tasa)^(meses/12)`
5. Botón guardar

**COMMIT:** `"feat(ct_alquiler): editable UI with formula display"`

---

## VALIDACION FINAL
```
☐ python scripts/auto_validate.py pasa
☐ El CT alquiler se aplica correctamente a alquileres >180 días
☐ El CT venta NO se aplica a alquileres
☐ La fórmula es visible en la UI
☐ Los valores son editables y se guardan en JSON
```

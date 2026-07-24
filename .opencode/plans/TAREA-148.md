# TAREA-148: Macrozona Independiente Puerto Norte — Riesgo MEDIO

## CONTEXTO

Puerto Norte actualmente es subzona de `centro_premium` con `skip_size_adj: true`. Este es un workaround que:
1. No refleja la realidad del mercado (3-dorm plano ~$3,000/m²)
2. Usa una subzona con `match_anchor_ids` que limita la cobertura
3. No permite curvas específicas por dormitorio

**Evidencia de datos reales (311 props):**
- 3-dorm: ~$3,000/m² para todos los tamaños (plano)
- 2-dorm: creciente $1,351→$3,821 (small→large)

**Solución:** Crear macrozona independiente `"puerto_norte"` con curvas planas.

## REGLA DE ORO

- Curvas de normalización deben reflejar datos reales de $/m² por tamaño
- No cambiar lógica de resolución de zonas existentes (solo agregar nueva)
- `pytest` pasa después de cada paso

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `data/zonas_depreciacion.json` | Eliminar PN de centro_premium, crear macrozona independiente |
| `tests/test_zonas_manager.py` | Agregar tests de resolución textual y bbox para PN |

---

## PASO 1: Crear macrozona puerto_norte

**Archivo:** `data/zonas_depreciacion.json`

**JUSTIFICACIÓN RO:** Este cambio NO viola ninguna regla de oro. Solo reorganiza la configuración de zonas sin modificar la lógica de valuación.

**1.1** Eliminar `"puerto norte"` y `"puertonorte"` de `centro_premium.zonas_match_textual` (líneas 17-18)

**1.2** Eliminar subzona `"puerto_norte"` de `centro_premium.subzonas` (líneas 100-119)

**1.3** Crear nueva macrozona `"puerto_norte"` al inicio del array `macrozonas` (antes de `centro_premium`):

```json
{
  "id": "puerto_norte",
  "nombre": "Puerto Norte",
  "ct_annual_rate": -0.0163,
  "bbox": {
    "lat_min": -32.930,
    "lat_max": -32.918,
    "lon_min": -60.675,
    "lon_max": -60.655
  },
  "zonas_match_textual": ["puerto norte", "puertonorte"],
  "points": [
    {"m2": 0, "factor": 1.0},
    {"m2": 250, "factor": 1.0}
  ],
  "by_dormitorios": {
    "2": [
      {"m2": 0, "factor": 1.0},
      {"m2": 250, "factor": 1.0}
    ],
    "3": [
      {"m2": 0, "factor": 1.0},
      {"m2": 250, "factor": 1.0}
    ],
    "default": [
      {"m2": 0, "factor": 1.0},
      {"m2": 250, "factor": 1.0}
    ]
  }
}
```

**COMMIT:** `"TAREA-148: Macrozona independiente Puerto Norte con curvas planas"`

---

## PASO 2: Agregar tests de resolución

**Archivo:** `tests/test_zonas_manager.py`

**JUSTIFICACIÓN RO:** Tests verifican que la nueva zona se resuelve correctamente. No cambian lógica de valuación.

**2.1** Agregar test de resolución textual:

```python
def test_puerto_norte_textual(self):
    """Propiedad con zona 'Puerto Norte' resuelve a macrozona puerto_norte"""
    prop = {"zona": "Puerto Norte", "lat": -32.924, "lon": -60.666}
    result = resolver_macrozona(prop)
    assert result["macrozona"]["id"] == "puerto_norte"
    assert result["confianza"] == "ALTA"
```

**2.2** Agregar test de resolución bbox:

```python
def test_puerto_norte_bbox(self):
    """Propiedad sin texto pero con coords dentro de Puerto Norte resuelve por bbox"""
    prop = {"lat": -32.9244, "lon": -60.6662}
    result = resolver_macrozona(prop)
    assert result["macrozona"]["id"] == "puerto_norte"
    assert result["confianza"] == "MEDIA"
```

**2.3** Agregar test de que Puerto Norte NO resuelve a centro_premium:

```python
def test_puerto_norte_no_centro_premium(self):
    """Puerto Norte ya no es parte de centro_premium"""
    prop = {"zona": "Puerto Norte"}
    result = resolver_macrozona(prop)
    assert result["macrozona"]["id"] != "centro_premium"
```

**COMMIT:** `"TAREA-148: Tests resolución Puerto Norte"`

---

## VALIDACION FINAL

```
☐ pytest pasa (55+ tests)
☐ Propiedades con zona "Puerto Norte" resuelven a nueva macrozona
☐ Factor size_adjustment = 1.0 para todos los tamaños
☐ Propiedades con zona "Centro" siguen resolviendo a centro_premium
```

## DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md` (agregar entrada)
- `docs/STATUS_ACTUAL.md` (actualizar estado de Puerto Norte)
- `.opencode/plans/TAREAS_INDEX.md` (agregar TAREA-148)

## ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-148.md`.
NO se elimina al ejecutar. Sirve como registro histórico.

## ENTREGABLES

- Lista de archivos modificados
- `pytest` pasando
- Verificación funcional completa
- Plan archivado en `.opencode/plans/TAREA-148.md`

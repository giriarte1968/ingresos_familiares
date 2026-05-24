# TAREA: TAREA-004 — Eliminar dependencia de numpy del cold start — Riesgo BAJO

### CONTEXTO

El cold start de la app en DO tarda ~12s debido a la carga de numpy (arrastrado por `mercado_inmobiliario.py` y `location_engine.py`). Aunque numpy ya se movió a lazy import dentro de `valuar_propiedad_v7()`, sigue siendo una dependencia que:

1. Se importa al hacer la primera valuación (~12s pagados ahí)
2. En `location_engine.py` está importado pero **nunca se usa**
3. En `mercado_inmobiliario.py` solo se usa para `np.median()` y `np.percentile()` — operaciones trivialmente reemplazables con Python puro

### REGLA DE ORO

- `pytest tests/test_regression.py tests/test_cluster_filters.py` pasa después de cada paso
- Los valores numéricos de valuación NO cambian
- La app funciona sin numpy instalado (opcional, no se fuerza su remoción)
- No se toca ninguna lógica de negocio, cluster, age blend, cap rate

### ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/location_engine.py` | Eliminar `import numpy as np` y `from sklearn.cluster import DBSCAN` (no usados) |
| `parsers/mercado_inmobiliario.py` | Agregar `_calcular_mediana()` y `_calcular_percentil_linear()`; reemplazar 19 calls a np.median/np.percentile; eliminar `globals()['np'] = np` de funciones |

---

### PASO 1: Limpiar location_engine.py de imports muertos

**Archivo:** `parsers/location_engine.py` — líneas 1-5

**1.1** Eliminar:
```python
import numpy as np
from sklearn.cluster import DBSCAN
```
COMMIT: "clean: eliminar imports de numpy y sklearn de location_engine.py (no usados)"

VERIFICAR: python scripts/auto_validate.py

---

### PASO 2: Agregar helpers _calcular_mediana y _calcular_percentil_linear
Archivo: parsers/mercado_inmobiliario.py — insertar al inicio del archivo, después de los imports existentes

**2.1** Agregar helpers (después de línea 10, antes de los imports de cluster_filters):

```python
def _calcular_mediana(precios):
    """Pure Python median - equivalente a np.median()."""
    if not precios:
        return 0.0
    s = sorted(precios)
    n = len(s)
    if n % 2 == 1:
        return float(s[n // 2])
    return (s[n // 2 - 1] + s[n // 2]) / 2.0


def _calcular_percentil_linear(precios, q):
    """Pure Python percentile con interpolación lineal - equivalente a np.percentile(..., q)."""
    if not precios:
        return 0.0
    s = sorted(precios)
    n = len(s)
    if n == 1:
        return float(s[0])
    idx = q / 100.0 * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return float(s[-1])
    frac = idx - lo
    return float(s[lo] * (1 - frac) + s[hi] * frac)
```
COMMIT: "feat: agregar _calcular_mediana y _calcular_percentil_linear helpers"

VERIFICAR: pytest tests/test_regression.py tests/test_cluster_filters.py

---

### PASO 3: Reemplazar np.median y np.percentile en obtener_mediana_cluster()
Archivo: parsers/mercado_inmobiliario.py — función obtener_mediana_cluster (líneas 263-340)

**3.1** Eliminar el lazy import de numpy del comienzo de la función:

```python
    # Lazy numpy import for direct calls
    if 'np' not in globals():
        import numpy as np
        globals()['np'] = np
```
**3.2** Reemplazar todas las ocurrencias:

| Línea actual | Reemplazar con |
|---|---|
| return float(np.median(precios)), len(precios) | return _calcular_mediana(precios), len(precios) |
| mediana_raw = np.median(precios) | mediana_raw = _calcular_mediana(precios) |
| return float(np.median(precios_ordenados)), len(precios_ordenados) | return _calcular_mediana(precios_ordenados), len(precios_ordenados) |
| q1 = np.percentile(precios_ordenados, 25) | q1 = _calcular_percentil_linear(precios_ordenados, 25) |
| q3 = np.percentile(precios_ordenados, 75) | q3 = _calcular_percentil_linear(precios_ordenados, 75) |
| return float(np.median(precios_filtrados)), len(precios_filtrados) | return _calcular_mediana(precios_filtrados), len(precios_filtrados) |

COMMIT: "refactor: reemplazar np.median/np.percentile en obtener_mediana_cluster()"

VERIFICAR: pytest tests/test_regression.py tests/test_cluster_filters.py

---

### PASO 4: Reemplazar np.median y np.percentile en obtener_mediana_cluster_v2()
Archivo: parsers/mercado_inmobiliario.py — función obtener_mediana_cluster_v2 (líneas 511+)

**4.1** Eliminar el lazy import de numpy si existe en esta función.

**4.2** Reemplazar ocurrencias (líneas 804, 816, 826, 836-837, 843, 884-887, 1006):

| Línea actual | Reemplazar con |
|---|---|
| return float(np.median(precios)), len(precios), { | return _calcular_mediana(precios), len(precios), { |
| mediana_raw = np.median(precios) | mediana_raw = _calcular_mediana(precios) |
| return float(np.median(precios)), len(precios), { (en fallback IQR) | return _calcular_mediana(precios), len(precios), { |
| q1 = np.percentile(precios_ordenados, 25) | q1 = _calcular_percentil_linear(precios_ordenados, 25) |
| q3 = np.percentile(precios_ordenados, 75) | q3 = _calcular_percentil_linear(precios_ordenados, 75) |
| return float(np.median(precios)), len(precios), { (sin filtrados) | return _calcular_mediana(precios), len(precios), { |
| p25_cluster = float(np.percentile(precios_todos, 25)) | p25_cluster = _calcular_percentil_linear(precios_todos, 25) |
| p33_cluster = float(np.percentile(precios_todos, 33)) | p33_cluster = _calcular_percentil_linear(precios_todos, 33) |
| p50_cluster = float(np.median(precios_todos)) | p50_cluster = _calcular_mediana(precios_todos) |
| p75_cluster = float(np.percentile(precios_todos, 75)) | p75_cluster = _calcular_percentil_linear(precios_todos, 75) |
| valor = float(np.median(precios_filtrados)) | valor = _calcular_mediana(precios_filtrados) |

COMMIT: "refactor: reemplazar np.median/np.percentile en obtener_mediana_cluster_v2()"

VERIFICAR: pytest tests/test_regression.py tests/test_cluster_filters.py

---

### PASO 5: Eliminar lazy import de numpy en valuar_propiedad_v7()
Archivo: parsers/mercado_inmobiliario.py — función valuar_propiedad_v7 (línea 2484)

**5.1** Eliminar:

```python
    import numpy as np
    globals()['np'] = np
```
(Reemplazar solo esas 2 líneas, dejando el from parsers.profiler import StepLedger intacto)

COMMIT: "clean: eliminar lazy import de numpy de valuar_propiedad_v7() - ya no se necesita"

VERIFICAR: pytest tests/test_regression.py tests/test_cluster_filters.py

---

### VALIDACION FINAL
- [ ] pytest tests/test_regression.py tests/test_cluster_filters.py pasa
- [ ] python scripts/auto_validate.py pasa
- [ ] No quedan referencias a np. en parsers/mercado_inmobiliario.py
- [ ] No quedan referencias a numpy/sklearn en parsers/location_engine.py
- [ ] Cold start de valuación sin numpy: landing <0.1s, portfolio <0.5s, detalle ~2-3s

### DOCS A ACTUALIZAR
- docs/BITACORA_AGENTES.md
- docs/STATUS_ACTUAL.md
- .opencode/plans/TAREAS_INDEX.md (agregar entrada TAREA-004)

### ARCHIVO DE PLAN
El plan se guarda permanentemente en .opencode/plans/TAREA-004.md.

### ENTREGABLES
- parsers/location_engine.py — sin imports de numpy/sklearn
- parsers/mercado_inmobiliario.py — sin referencias a numpy, con helpers puros
- pytest pasando
- Plan archivado en .opencode/plans/TAREA-004.md

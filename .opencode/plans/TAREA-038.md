# TAREA-038 — Pipeline de regeneración de anclas configurable — Riesgo ALTO

## CONTEXTO

Actualmente las 322 anclas grid están fijas en `data/anclas_rosario_v5_1_limpio.json`. El generador (`scripts/generar_anclas_grid.py`) tiene paths, parámetros y zona_centroides hardcodeados. No hay forma de:
- Regenerar anclas desde la UI tras un scraping nuevo
- Mantener múltiples versiones de anclas y seleccionar cuál está activa
- Ajustar parámetros (grid_size, min_props, Ct_factors) sin editar código
- Invalidar caché automáticamente al activar nuevas anclas

## REGLA DE ORO

- `pytest tests/test_regression.py` pasa después de cada paso
- `python scripts/auto_validate.py` pasa después de cada paso
- El archivo de anclas activo se lee desde `config/anclas_config.json → active_anchor_file`
- Cada regeneración produce un archivo timestamped (`data/anclas_v7_AAAAMMDD_HHMMSS.json`)
- El archivo de producción original nunca se sobreescribe directamente
- La caché de valuaciones se invalida (bump `cache_version`) al activar nuevas anclas

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `config/anclas_config.json` | **Nuevo** — configuración centralizada del generador + runtime |
| `scripts/generar_anclas_grid.py` | **Refactor** — leer desde config, output timestamped |
| `parsers/motor_vpp_core.py` | **Modificar** — leer `active_anchor_file` desde config |
| `parsers/location_engine.py` | **Modificar** — leer `active_anchor_file` desde config |
| `parsers/valuacion_cache.py` | **Modificar** — leer `CACHE_VERSION` desde config |
| `valu.py` | **Modificar** — pestaña "Anclas" en admin UI |
| `docs/ALGORITMOS.md` | **Actualizar** — sección de pipeline regeneración |
| `docs/POST_SCRAPING.md` | **Actualizar** — paso opcional regeneración post-scraping |
| `docs/BITACORA_AGENTES.md` | **Actualizar** — registro de TAREA-038 |
| `.opencode/plans/TAREAS_INDEX.md` | **Actualizar** — entrada TAREA-038 |

---

### PASO 1: Crear `config/anclas_config.json`

**Archivo:** `config/anclas_config.json` — nuevo

**1.1** Crear directorio `config/` y archivo con todos los parámetros del generador + runtime:

```json
{
  "generator": {
    "grid_size_m": 400,
    "min_props_per_cell": 5,
    "ct_factors": { "usado": 1.12, "nuevo": 0.95 },
    "city_center": { "lat": -32.92776, "lon": -60.69769 },
    "output_dir": "data",
    "output_prefix": "anclas_v7_",
    "noise_tokens": ["planta baja", "piso", "dormitorio", "departamento", "casa", "cochera", "duplex", "local", "oficina", "ph", "monoambiente", "ambiente", "baño", "cocina", "living", "comedor", "suite", "hall", "lavadero", "terraza", "patio", "balcon", "jardin", "garage", "quincho", "pileta", "parrilla", "sum", "gimnasio", "laundry", "rooftop"],
    "noise_patterns": ["\\b\\d+\\b", "\\b(de|la|del|el|los|las|en|y|al|con|por|para|sin|entre)\\b"]
  },
  "zones": {
    "martin":       { "lat": -32.9500, "lon": -60.6525, "radio": 1500 },
    "pellegrini":   { "lat": -32.9551, "lon": -60.6507, "radio": 1500 },
    "puerto_norte": { "lat": -32.9250, "lon": -60.6660, "radio": 1200 },
    "pichincha":    { "lat": -32.9373, "lon": -60.6581, "radio": 1200 },
    "abasto":       { "lat": -32.9589, "lon": -60.6453, "radio": 1200 },
    "centro":       { "lat": -32.940,  "lon": -60.649,  "radio": 1500 }
  },
  "runtime": {
    "active_anchor_file": "data/anclas_rosario_v5_1_limpio.json",
    "cache_version": "v6_pn_comparables",
    "cache_ttl_minutes": 60
  }
}
```

**1.2** Crear función helper `load_anclas_config()` en `parsers/motor_vpp_core.py` que lea el config y lo devuelva como dict. Usar `functools.lru_cache` con TTL para evitar lecturas repetitivas en disco.

**COMMIT:** `"TAREA-038-paso1: config/anclas_config.json + load_anclas_config()"`

**VERIFICAR:** `python -c "from parsers.motor_vpp_core import load_anclas_config; cfg = load_anclas_config(); print(cfg['runtime']['active_anchor_file'])"`

---

### PASO 2: Refactor `scripts/generar_anclas_grid.py`

**Archivo:** `scripts/generar_anclas_grid.py`

**2.1** Reemplazar constantes hardcodeadas por lectura de `config/anclas_config.json` (sección `generator` + `zones`).

**2.2** Output escribir a `data/anclas_v7_AAAAMMDD_HHMMSS.json` en vez de fijo. Generar también archivo `.latest` con la ruta del último generado (para el preview en UI).

**2.3** Agregar CLI overrides con `argparse`:
- `--grid-size` (default: del config)
- `--min-props` (default: del config)
- `--output` (default: timestamped)

**2.4** Al final del script, imprimir resumen:
```
=== RESUMEN GENERACIÓN ===
Output: data/anclas_v7_20260610_143022.json
Anclas generadas: 322
Cobertura (props ≤300m): 96.2%
Anclas con zona comercial: 187 (58.1%)
Anclas sin zona (macrozona): 135 (41.9%)
```

**2.5** Mover la tabla Ct y constantes de factor al config (ya están en `config.ct_factors`).

**COMMIT:** `"TAREA-038-paso2: refactor generar_anclas_grid.py con config + output timestamped"`

**VERIFICAR:** `cd C:\Users\Gustavo\ingresos_familiares_st && python scripts/generar_anclas_grid.py --grid-size 400 --min-props 5`

---

### PASO 3: Modificar runtime para leer `active_anchor_file` del config

**Archivo:** `parsers/motor_vpp_core.py`

**3.1** Reemplazar:
```python
ANCLAS_FILE = os.path.join(BASE_DIR, "data", "anclas_rosario_v5_1_limpio.json")
```
Por:
```python
def _get_anclas_file():
    cfg = load_anclas_config()
    return os.path.join(BASE_DIR, cfg['runtime']['active_anchor_file'])

ANCLAS_FILE = _get_anclas_file()
```

**Archivo:** `parsers/location_engine.py`

**3.2** Modificar `cargar_anclas(path=None)`:
```python
from parsers.motor_vpp_core import load_anclas_config

def cargar_anclas(path=None):
    if path is None:
        cfg = load_anclas_config()
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), cfg['runtime']['active_anchor_file'])
    ...
```

**Archivo:** `valu.py`

**3.3** Reemplazar `ANCLAS_PATH` hardcodeado (línea 590):
```python
from parsers.motor_vpp_core import load_anclas_config
_cfg = load_anclas_config()
ANCLAS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), _cfg['runtime']['active_anchor_file'])
```

**Archivo:** `parsers/valuacion_cache.py`

**3.4** Reemplazar:
```python
CACHE_VERSION = "v6_pn_comparables"
```
Por:
```python
from parsers.motor_vpp_core import load_anclas_config
_cfg = load_anclas_config()
CACHE_VERSION = _cfg['runtime']['cache_version']
```

**COMMIT:** `"TAREA-038-paso3: runtime lee active_anchor_file y cache_version desde config"`

**VERIFICAR:** `python scripts/auto_validate.py && pytest tests/test_regression.py`

---

### PASO 4: Admin UI — Pestaña "Anclas"

**Archivo:** `valu.py` — reemplazar sección "📍 Administrar Zonas (Anclas)" (líneas 589-695)

**4.1** Reemplazar el expander actual por una pestaña completa `st.tabs()` o expander con sub-secciones:

```
### ⚙️ Pipeline de Anclas

#### 1. Archivos Disponibles
[lista de data/anclas_v7_*.json + anclas_rosario_v5_1_limpio.json]
Actual activo: anclas_rosario_v5_1_limpio.json [ACTIVO]
[ACTIVAR] botón junto a cada archivo no-activo

#### 2. Generar Nuevas Anclas
[Grid size:] [Min props:] [button: GENERAR]
→ Preview: "Nuevas anclas: 322, cobertura: 96.2%"
→ Top 20 cambios vs actual
→ [ACTIVAR NUEVAS ANCLAS] (copia path a config + bump cache_version + rerun)

#### 3. Editar Config
[editor inline de config/anclas_config.json]

#### 4. Editor de Anclas (existente)
[tabla data_editor + guardar]
```

**4.2** Lógica de activación:
- Al hacer clic en "Activar": escribir `active_anchor_file` en `config/anclas_config.json`
- Incrementar `cache_version` (ej: cambiar sufijo con timestamp)
- Llamar `cargar_anclas_cached(force_reload=True)`
- Mostrar `st.success()` y `st.rerun()`

**4.3** Preview de cobertura: leer el nuevo archivo y calcular:
- `anclas_count` = len(anclas)
- `coverage` = % de props en cache_scraping.json a ≤300m de alguna ancla
- Comparación con actual: top 20 diferencias absolutas de USD/m²

**COMMIT:** `"TAREA-038-paso4: admin UI pestaña Anclas con regeneración + activación"`

**VERIFICAR:** Iniciar UI con `streamlit run valu.py` y probar pestaña Anclas en admin.

---

### PASO 5: Actualizar documentación

**5.1** `docs/ALGORITMOS.md`: agregar sección "7. Pipeline de Regeneración de Anclas":
- Arquitectura: config → generador → archivo timestamped → activación
- Cómo leer config desde runtime
- Cómo funciona la activación (cambio de active_anchor_file + bump cache_version)

**5.2** `docs/POST_SCRAPING.md`: agregar paso opcional:
> **PASO 3 (opcional) — Regenerar anclas**: desde Admin UI → pestaña Anclas → "Generar Nuevas Anclas". Revisar preview de cobertura. Si es满意, hacer clic en "Activar".

**5.3** `docs/BITACORA_AGENTES.md`: registrar TAREA-038

**5.4** `.opencode/plans/TAREAS_INDEX.md`: agregar entrada TAREA-038

**COMMIT:** `"TAREA-038-paso5: docs pipeline regeneración + post-scraping"`

**VERIFICAR:** Revisar visualmente cada documento actualizado.

---

## VALIDACION FINAL

```
☐ auto_validate.py OK
☐ pytest test_regression.py (39/39)
☐ python scripts/generar_anclas_grid.py genera archivo timestamped en data/
☐ Activar nuevas anclas desde UI cambia active_anchor_file en config
☐ Al activar, caché se invalida (cache_version cambia)
☐ UI muestra lista de archivos disponibles con indicador de activo
☐ Preview de cobertura se muestra antes de activar
```

## DOCS A ACTUALIZAR

- `docs/ALGORITMOS.md`: nueva sección pipeline regeneración
- `docs/POST_SCRAPING.md`: paso opcional regeneración
- `docs/BITACORA_AGENTES.md`: registro de TAREA-038
- `.opencode/plans/TAREAS_INDEX.md`: entrada TAREA-038

## ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-038.md`.
NO se elimina al ejecutar.

## ENTREGABLES

- `config/anclas_config.json` con todos los parámetros
- `scripts/generar_anclas_grid.py` refactorizado (lee config, output timestamped, CLI args)
- Runtime modificado para leer active_anchor_file + cache_version desde config
- Admin UI con pestaña Anclas funcional (listar, generar preview, activar, editar config)
- Documentación actualizada
- `pytest` pasando
- `auto_validate` pasando

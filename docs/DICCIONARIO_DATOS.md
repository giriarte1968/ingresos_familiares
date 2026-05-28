# 📖 DICCIONARIO DE DATOS — AVM ROSARIO

Este documento detalla la estructura de los archivos de datos críticos para evitar errores de tipo o campos faltantes durante el desarrollo.

---

## 1. `cache_scraping.json`

Es el archivo más grande y crítico. Contiene el "universo" de propiedades comparables.

### Estructura de Raíz
- `fecha`: ISO string de la última actualización global.
- `status`: String descriptivo de la versión de la caché (ej. "propia_api_browser_cleaned_v2").
- `propiedades`: Lista de objetos `Propiedad`.

### Conceptos de Valuación (Percentiles)
- **percentil_venta_p33**: Percentil 33 del cluster de comparables limpio (post-IQR). Se usa como precio base por m² para operaciones de venta como proxy de antigüedad por falta de año de construcción en comparables. NO es la mediana.
- **percentil_alquiler_p50**: Mediana (percentil 50) del cluster de comparables limpio. Se usa como precio base por m² para operaciones de alquiler debido a la homogeneidad del mercado.

### Objeto `Propiedad`
| Campo | Tipo | Descripción |
|-------|------|-------------|

### Objeto `Propiedad`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `precio` | float | Precio de lista. |
| `moneda` | string | "USD" o "ARS". |
| `m2` | float | Superficie total informada (a veces cubiertos, a veces total). |
| `dormitorios` | int | Cantidad de habitaciones. |
| `tipo` | string | "Departamento", "Casa", "Cochera", etc. |
| `operacion` | string | "venta" o "alquiler". |
| `lat` / `lon` | float | Coordenadas geográficas (CRÍTICO para clustering). |
| `valor_m2` | float | Calculado como `precio / m2`. |
| `fuente` | string | Portal de origen (ej. "propia", "argenprop"). |
| `url` | string | Link a la publicación original. |
| `date_updated` | string | ISO de la última vez que se vio activa la propiedad. |
| `anio_construccion` (comparable) | int/null | Campo actualmente NO disponible o no confiable en la caché. Razón del uso de P33 en venta. |
| `anio_construccion` (objetivo) | int | Campo SÍ disponible para propiedades propias. Usado para calcular `delta_anti` individual. |

---

## 2. `barreras_rosario.json`

Archivo GeoJSON que contiene las "barreras duras y blandas" que afectan la valuación.

### Estructura
Es un `FeatureCollection` donde cada `Feature` es un `LineString`.

### Propiedades de la Barrera
- `barrier_type`:
    - `hard`: Ferrocarril, Circunvalación → Exclusión total (weight *= 0.20 en IDW)
    - `soft`: Avenidas principales → Penalización suave (weight *= 0.90 en IDW)
- `name`: Nombre descriptivo (ej. "Ferrocarril", "Bulevar 27 de Febrero")

### Pesos Implementados (2026-05)
| Tipo | peso IDW | Efecto en Cluster |
| :--- | :--- | :--- |
| hard | 0.20 | Excluir propiedad |
| soft | 0.90 | Mantener propiedad |

---

## 3. `anclas_rosario.json`

Puntos de referencia manuales para calibración.

- `lat` / `lon`: Ubicación del ancla.
- `precio_m2_base`: Valor esperado para una propiedad "estándar" en ese punto exacto.
- `zona`: Nombre del barrio o microzona.

---

## 4. `constructoras_rosario.json`

Diccionario simple para ajustar la calidad del edificio.

- **Key:** Nombre de la constructora (ej. "Fundar", "MSR").
- **Value:** Factor de ajuste (ej. 1.10 para +10% de valor por marca).

---

## 4b. Normalización de `estado_detalle` vs `calidad_edificio` (TAREA 2026-05-20)

Regla aplicada en `calcular_factores()` vía helper `normalizar_estado_y_calidad(prop)`:

- `estado_detalle = "premium"` → se normaliza a estado `"excelente"` (factor 1.05)
- `calidad_edificio` se promueve a `"premium"` solo si estaba vacío o `"media"`
- Si `calidad_edificio` ya tenía otro valor (ej. `"alta"`), se respeta sin cambios

### Factor de Estado (nueva tabla, sin premium)

| Clave | Factor | Descripción |
|-------|--------|-------------|
| `malo` | 0.85 | Estado de conservación deficiente |
| `regular` | 0.92 | Estado regular |
| `bueno` | 1.00 | Estado normal (neutro) |
| `muy_bueno` | 1.03 | Buen estado de conservación |
| `excelente` | 1.05 | Excelente estado |
| `a_estrenar` | 1.08 | Propiedad nueva sin uso |

### Factor de Calidad (nueva tabla, con premium)

| Clave | Factor | Descripción |
|-------|--------|-------------|
| `baja` | 0.95 | Calidad constructiva baja |
| `media` | 1.00 | Calidad estándar (neutro) |
| `alta` | 1.04 | Calidad superior |
| `excelente` | 1.06 | Calidad excelente |
| `premium` | 1.08 | Calidad premium (categoría, no estado) |

### Factor de Ventilación (suavizado)

| Clave | Factor | Descripción |
|-------|--------|-------------|
| `simple` | 0.95 | Ventilación simple (antes 0.90) |
| `doble` | 1.00 | Doble ventilación (neutro) |
| `cruzada` | 1.05 | Ventilación cruzada (antes 1.10) |

---

## 5. Parámetros de Atenuación Dinámica y Guardrails (V13.0)

- `UMBRAL_PENALIZACION` (float): Límite de castigo por antigüedad antes de aplicar atenuación agresiva (ej. -0.15).
- `FACTOR_EXCESO` (float): Factor de reducción para el castigo que excede el umbral (ej. 0.10).
- `ATENUACION_BASE` (float): Atenuación aplicada a castigos leves (ej. 1.00).
- `SUMA_CRUDA_MIN` / `SUMA_CRUDA_MAX` (float): Rango permitido para la suma de factores aditivos ($[-0.40, +0.40]$).
- `FACTOR_MIN` / `FACTOR_MAX` (float): Rango permitido para el factor total de valuación ($[0.70, 1.35]$).
- `delta_anti_efectivo` (float): El $\Delta$ de antigüedad final después de aplicar la lógica de saturación.
- `factor_raw` (float): Factor calculado linealmente antes de aplicar el clamp final.
- `factor_total` (float): Factor final acotado usado para multiplicar el $m2\_base$.
- `UMBRAL_PENALIZACION_SEVERA` (float): Umbral de activación de atenuación para propiedades $>30$ años (valor: -0.18).
- `FACTOR_ATENUACION` (float): Factor de reducción del exceso de antigüedad (valor: 0.35).
- `NLP_CAP_1_DORM` (float): Cap máximo de NLP para propiedades de 1 dormitorio (valor: 0.03 = +3%).
- `NLP_CAP_2PLUS_DORM` (float): Cap máximo de NLP para propiedades de 2+ dormitorios (valor: 0.05 = +5%).
- `delta_anti_raw` (float): Depreciación lineal calculada antes de atenuación.
- `delta_anti_efectivo` (float): Depreciación después de aplicar atenuación (solo para props $>30$ años).
- `m2_base_venta` (float): Precio base por m² del cluster v2 para operación de venta (percentil: P33).
- `m2_base_alquiler` (float): Precio base por m² del cluster v2 para operación de alquiler (percentil: P50).
- `percentil_usado` (string): Percentil utilizado del cluster (P33 para venta, P50 para alquiler).
- `resolution_metadata` (dict): Metadata de resolución del cluster (n_propiedades, radio_usado, zonaresol, method).

---

## 6. Campos de Cap Rate Data-Driven (v8.1)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `cap_rate` | float | Cap Rate anual derivado del mercado local (ratio alquiler/venta). |
| `cap_rate_min` | float | Rango mínimo del Cap Rate (±8-15% según confianza). |
| `cap_rate_max` | float | Rango máximo del Cap Rate. |
| `alquiler_rango` | dict | Rango de alquiler: `{min, mid, max}` en ARS. |
| `es_fallback_alquiler` | bool | True si no hay datos locales y se usó ROI zonal estimado. |
| `confianza_alquiler` | str | ALTA/MEDIA/BAJA basada en cantidad de comparables de alquiler. |
| `metodo_alquiler` | str | 'mercado_local' o 'roi_zonal_fallback'. |
| `cap_rate_info` | dict | Metadata del cálculo: n_venta, n_alquiler, venta_m2_base, alq_m2_base. |

---

## 6. Esquema Canónico de Superficies y Año

### Campos UI (4 campos exactos - Opción A)
| Campo | Tipo | Descripción | Coeficiente |
|-------|------|-------------|-------------|
| `m2_cubiertos` | float | Superficie cubierta habitable | 100% |
| `m2_semicubiertos` | float | Balcón, terraza techada | 45% |
| `m2_descubiertos_propios` | float | Patio propio, jardín escriturado | 0.25 (0.30 si ≥20m²) |
| `m2_descubiertos_comun_exclusivo` | float | Balcón descubierto, terasa común uso exclusivo | 0.15 (0.20 si ≥20m²) |

### Campos de Superficies (legado/compatibilidad)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `m2_descubiertos` | float | Patio, jardín, terreza abierta (m²). Legacy. |
| `m2_comunes` | float | Áreas comunes del edificio (m²). |
| `m2` | float | Superficie "publicable/mercado" (deprecated). |

### Campo de Año
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `anio_construccion` | int | Año de construcción del edificio. |

### Reglas de Uso
- **MODO LEGADO**: Si `m2_descubiertos_propios` y `m2_descubiertos_comun_exclusivo` son None → usar `m2_descubiertos`.
- **MODO GRANULAR**: Usar coeficientes diferenciados para propios vs comun_exclusivo.
- **m2**: Eliminado del UI (solo retrocompatibilidad).

---

## 7. `valuaciones_historial.jsonl`

Archivo append-only que registra cada evento de valuación. Formato: una línea JSON por evento.

### Estructura del Registro
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | string | ID único del evento (`val_YYYYMMDD_HHMMSS_Nombre`). |
| `timestamp` | string | ISO string del momento del cálculo. |
| `propiedad` | string | Nombre de la propiedad valuada. |
| `razon_recalculo` | string | `primera_vez`, `scraping_actualizado`, `propiedad_modificada`, etc. |
| `snapshot_propiedad` | dict | Copia completa de los atributos físicos de la propiedad en ese momento. |
| `snapshot_mercado` | dict | Variables de entorno: Dólar, m² base, n_comparables, hash_scraping. |
| `resultado` | dict | Valores finales calculados (venta, alquiler, cap_rate). |

### Snapshot de Mercado (Detalle)
- `hash_scraping`: Primeros 12 caracteres del hash MD5 de `cache_scraping.json`.
- `archivo_scraping`: Nombre del snapshot guardado en `data/scraping_history/`.
- `dolar_binance`: Cotización USDT/ARS usada.
- `m2_base_venta`: Precio base del cluster detectado.

---

## 7b. `resultado.audit_log` — Log Técnico de Auditoría (TAREA 2026-05-20)

Cada valuación genera un `audit_log` estructurado en `resultado['audit_log']`.

### Estructura completa

| Sección | Campos principales |
|---------|-------------------|
| `timestamp` | ISO timestamp de la valuación |
| `motor_version` | Versión del motor ('v7.0') |
| `nombre` | Nombre de la propiedad |
| `propiedad` | inputs: nombre, zona, tipo, dirección, lat/lon, año, dorms, estado, calidad, piso, ventilación, etc. |
| `superficies` | m2_cubiertos, m2_semi, m2_descubiertos, m2_equiv |
| `cluster_venta` | n_total_cluster, n_con_anio, age_filter, percentil_usado, p33_same/cross, bases, comparables_usados[] |
| `factores` | estado, calidad, depreciacion, suma_cruda, f_estructural, nlp_bruto, nlp_cap_aplicado, es_ventana3 |
| `venta` | valor_conservador/mercado/optimista, spread, m2_base, m2_base_source |
| `alquiler` | metodo_alquiler, cap_rate, rango alquiler, size_discount, es_fallback |
| `final` | valor_venta, valor_realizable, alquiler, plusvalia, cap_rates |
| `resolution_metadata` | Copia de la metadata de resolución del cluster |

### Persistencia

Los audit_logs se guardan en `data/history/audit_logs/` con formato:
```
YYYY-MM-DD_HH-MM-SS__Nombre_Propiedad.json
```

Se acceden desde la aplicación en **Configuración → Auditoría Técnica**.

---

## 7. `resultado.catastro_detalle` (Infomapa)

Agregado a valuación vía `enriquecer_con_infomapa()`.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `candidatos` | `list[dict]` | Lista de PHs candidatos dentro del radio de tolerancia |
| `candidatos[].ph` | `str` | Número de carpeta PH |
| `candidatos[].year` | `str` | Año de construcción |
| `candidatos[].direccion_nominatim` | `str` | Dirección del CSV |
| `candidatos[].seccion` | `str` | Sección catastral |
| `candidatos[].manzana` | `str` | Manzana catastral |
| `candidatos[].grafico` | `str` | Gráfico catastral |
| `candidatos[].distancia` | `float` | Distancia en grados decimales desde la propiedad |
| `candidatos[].recomendado` | `bool` | `True` si coincide con la dirección de la propiedad |
| `candidatos[].centena_match` | `str` | Tipo: `'exacta'` (misma cuadra por dirección), `'coordenadas'` (por proximidad geográfica) |
| `imagenes_disponibles` | `dict` | Mapa `PH → list[{ruta, url}]` con las imágenes del plano |

---

---

## 8. `rosario_avm_full.csv`

Catastro de PHs con años de construcción del Infomapa. Generado por `scripts/completar_catastral.py` desde JSONs de secciones + geometría oficial.

### Estructura

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `ph` | int | Número de carpeta PH (identificador único catastral) |
| `year` | float | Año de construcción |
| `seccion` | str | Sección catastral (completado vía point-in-polygon contra geometría oficial) |
| `manzana` | str | Manzana catastral |
| `grafico` | str | Gráfico catastral (parcela) |
| `division` | str | División catastral (mayormente vacío) |
| `latitud` | float | Coordenada geográfica (obtenida del Infomapa) |
| `longitud` | float | Coordenada geográfica |
| `direccion_nominatim` | str | Dirección textual (obtenida vía Nominatim reverse geocoding) |

### Notas
- ~21,017 PHs. 21,016/21,017 tienen seccion/manzana/grafico completos.
- Fuente de verdad: `data/geometry/parcelas_seccion*_json.csv` (274k polígonos oficiales del catastro).
- Usado por `parsers/mercado_inmobiliario.py` → `cargar_catastro()` y `parsers/infomapa_api.py`.

**Generado por**: Antigravity (IA de Desarrollo)
**Fecha**: 2026-05-27

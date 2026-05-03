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
    - `hard`: Peso = 0 (los comparables no pueden cruzar esta línea).
    - `soft`: Peso atenuado por un factor β.
    - `attractor`: Genera un plus de valor por cercanía.
- `name`: Nombre descriptivo (ej. "Vías FFCC Mitre").

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

## 5. Parámetros de Atenuación Dinámica y Guardrails (V13.0)

- `UMBRAL_PENALIZACION` (float): Límite de castigo por antigüedad antes de aplicar atenuación agresiva (ej. -0.15).
- `FACTOR_EXCESO` (float): Factor de reducción para el castigo que excede el umbral (ej. 0.10).
- `ATENUACION_BASE` (float): Atenuación aplicada a castigos leves (ej. 1.00).
- `SUMA_CRUDA_MIN` / `SUMA_CRUDA_MAX` (float): Rango permitido para la suma de factores aditivos ($[-0.40, +0.40]$).
- `FACTOR_MIN` / `FACTOR_MAX` (float): Rango permitido para el factor total de valuación ($[0.70, 1.35]$).
- `delta_anti_efectivo` (float): El $\Delta$ de antigüedad final después de aplicar la lógica de saturación.
- `factor_raw` (float): Factor calculado linealmente antes de aplicar el clamp final.
- `factor_total` (float): Factor final acotado usado para multiplicar el $m2\_base$.

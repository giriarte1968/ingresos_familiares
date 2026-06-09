# TAREA-035 — Generación de Anclas por Grilla Espacial 400m — Riesgo ALTO

## CONTEXTO

Las 117 anclas artesanales de `anclas_rosario_v5_1_limpio.json` tienen cobertura insuficiente (46% de propiedades a ≤300m) y las 36 anclas `v3_heredada` están 40-50% sobreestimadas respecto al mercado actual. Además, `rio_puerto_norte` estaba 2.8km fuera de su posición real.

El nuevo sistema reemplaza las anclas artesanales por una grilla regular de 400m × 400m sobre toda la ciudad, generando 322 microzonas con cobertura del 96%.

## REGLA DE ORO

- El archivo `anclas_rosario_v5_1_limpio.json` se renombra a `.bak`, no se elimina
- El nuevo archivo mantiene la ruta/nombre `anclas_rosario_v5_1_limpio.json` para que el pipeline existente lo lea sin cambios de código
- Todos los campos requeridos por `valuar_propiedad_v7()` se conservan (id, lat, lon, usd_m2, fecha_calibracion, fuente, n_zonal)
- Los tests de regresión deben pasar (pueden requerir actualización de rangos de anclas)
- El script generador queda documentado en `scripts/generar_anclas_grid.py`

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `data/anclas_rosario_v5_1_limpio.json` | Renombrar a `.bak`, reemplazar con 322 anclas grid |
| `.opencode/plans/TAREA-035.md` | Crear este plan |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar entrada de TAREA-035 |
| `docs/ALGORITMOS.md` | Agregar sección 6: Generación de Anclas por Grilla |
| `docs/STATUS_ACTUAL.md` | Actualizar estado y métricas |
| `docs/BITACORA_AGENTES.md` | Registrar cambio |
| `docs/MAPA_PROYECTO.md` | Actualizar si aplica |
| `scripts/generar_anclas_grid.py` | Script generador (nuevo) |
| `data/anclas_rosario_v6_cluster.json` | Archivo intermedio (generado, no versionado) |

---

### PASO 1: Crear script generador documentado

**Archivo:** `scripts/generar_anclas_grid.py`

**1.1** Script autónomo que:
- Lee `cache_scraping.json` (8.366 props válidas de venta)
- Calcula Ct para cada propiedad según segmento (nuevo/usado)
- Asigna cada propiedad a una celda de grilla 400m × 400m
- Para cada celda con ≥5 props: calcula centroide (promedio lat/lon de props reales) y mediana de lista_hoy
- Genera nombre = `calle1_calle2_macrozona` (calles más frecuentes en la celda)
- Asigna macrozona (centro/norte/sur/oeste) por posición geográfica
- Escribe `anclas_rosario_v6_cluster.json` (archivo intermedio)

**1.2** Logging de estadísticas: distribución de valores, cobertura, comparación vs viejas

### PASO 2: Respaldo y reemplazo del archivo de anclas

**2.1** Renombrar `data/anclas_rosario_v5_1_limpio.json` → `data/anclas_rosario_v5_1_limpio.json.bak`

**2.2** Copiar `data/anclas_rosario_v6_cluster.json` → `data/anclas_rosario_v5_1_limpio.json`

### PASO 3: Verificar pipeline existente

**3.1** Ejecutar `python scripts/auto_validate.py`

**3.2** Ejecutar `pytest tests/test_regression.py`

**3.3** Verificar que `valuar_propiedad_v7()` lee el nuevo archivo correctamente (mismos campos requeridos)

### PASO 4: Actualizar documentación

**4.1** `docs/ALGORITMOS.md`: nueva sección "6. Generación de Anclas por Grilla Espacial"

**4.2** `docs/STATUS_ACTUAL.md`: actualizar cobertura de anclas (46% → 96%), número de anclas (117 → 322), fuente

**4.3** `docs/BITACORA_AGENTES.md`: registrar la tarea completa

**4.4** `.opencode/plans/TAREAS_INDEX.md`: agregar entrada TAREA-035

---

## LÓGICA DE GENERACIÓN DE ANCLAS (para documentación)

### Algoritmo: Grid Espacial 400m con Ct Dual

```
Entrada: cache_scraping.json (8.366 propiedades venta con lat/lon)
         TABLA_CT (curva de ajuste temporal)
         FACTOR_USADO = 1.12 (usado aprecia 12% más que el índice general)
         FACTOR_NUEVO = 0.95 (nuevo aprecia 5% menos)

1. Para cada propiedad:
   a. Calcular meses desde listado hasta fecha_ref (2026-06-01)
   b. Calcular Ct_base = interpolar(TABLA_CT, meses)
   c. Determinar si es nuevo o usado por texto (keywords: "a estrenar", "pozo", etc.)
   d. Si usado: Ct = 1.0 + (Ct_base - 1.0) × FACTOR_USADO
      Si nuevo: Ct = 1.0 + (Ct_base - 1.0) × FACTOR_NUEVO
   e. lista_hoy = valor_m2 × Ct

2. Asignar a grilla:
   dlat = 400m / 111000 (grados latitud)
   dlon = 400m / (111320 × cos(lat_centro)) (grados longitud)
   ix = floor((lon - lon_min) / dlon)
   iy = floor((lat - lat_min) / dlat)

3. Para cada celda con ≥5 propiedades:
   a. Centroide: lat = avg(lat_props), lon = avg(lon_props)
   b. Valor: mediana de lista_hoy de las props en la celda
   c. Nombre: dos calles más frecuentes (limpias de ruido) + macrozona
   d. Macrozona por posición geográfica (distancia y dirección desde centro)

4. Output: 322 anclas con id, lat, lon, usd_m2, fecha_calibracion, fuente, n_zonal
```

### Tabla Ct

La tabla base representa el movimiento del mercado de departamentos en Rosario:

| Meses | Ct_base | Ct_usado (×1.12) | Ct_nuevo (×0.95) |
|-------|---------|-------------------|-------------------|
| 0 | 1.000 | 1.000 | 1.000 |
| 3 | 1.011 | 1.012 | 1.010 |
| 6 | 1.033 | 1.037 | 1.031 |
| 12 | 1.105 | 1.118 | 1.100 |
| 18 | 1.207 | 1.232 | 1.197 |
| 24 | 1.235 | 1.263 | 1.223 |
| 30 | 1.267 | 1.299 | 1.254 |
| 36 | 1.254 | 1.284 | 1.241 |
| 42 | 1.203 | 1.227 | 1.193 |
| 48 | 1.173 | 1.194 | 1.164 |
| 54 | 1.152 | 1.170 | 1.144 |
| 60 | 1.131 | 1.147 | 1.124 |
| 66 | 1.105 | 1.118 | 1.100 |
| 72 | 1.067 | 1.075 | 1.064 |
| 78 | 1.027 | 1.030 | 1.026 |
| ≥83 | 1.000 | 1.000 | 1.000 |

### Cobertura

| Métrica | Viejas (117) | Nuevas (322) |
|---------|-------------|--------------|
| Props ≤300m de ancla | 3.815 (46%) | 8.014 (96%) |
| Anclas v3_heredada sobreestimadas 40-50% | 12 | 0 |
| Anclas con nombre por calle | parcial | 100% |

### Naming

Formato: `calle_principal_calle_secundaria_macrozona`

Limpieza de calles:
- Se eliminan tokens de ruido: "duplex", "casa", "departamento", "cochera", "dormitorio", artículos, preposiciones, digitos sueltos
- Se eliminan tokens mixtos (letras+números) que no sean calles tipo "3_de_febrero"
- Top 2 calles más frecuentes en la celda → nombre

### Macrozona

Asignación por posición geográfica relativa al centro de la ciudad (-32.92776, -60.69769):
- Centro: radio < 1.5km desde el centro
- Norte: al norte del centro, cerca del río (corredor ribereño)
- Sur: al sur del centro, cerca del río
- Oeste: tierra adentro (al oeste del centro)

---

### PASO 5: Commit

```
git add data/anclas_rosario_v5_1_limpio.json.bak
git add data/anclas_rosario_v5_1_limpio.json
git add scripts/generar_anclas_grid.py
git add docs/ALGORITMOS.md docs/STATUS_ACTUAL.md docs/BITACORA_AGENTES.md
git add .opencode/plans/TAREA-035.md .opencode/plans/TAREAS_INDEX.md
git commit -m "TAREA-035: Reemplazo anclas artesanales por grilla 400m (322 anclas, 96% cobertura)
```

---

## VALIDACION FINAL

```
☐ auto_validate.py OK
☐ pytest test_regression.py (39/39)
☐ 322 anclas en el archivo nuevo
☐ Nicho de cobertura: 96% vs 46% anterior
☐ Valores de macrozona dentro de rangos esperados
☐ Centro ~$1.900, Norte ~$1.700, Sur ~$970, Oeste ~$1.180 (verificando contra MeLi+UdeSA)
```

## DOCS A ACTUALIZAR

- `docs/ALGORITMOS.md`: nueva sección de generación de anclas
- `docs/STATUS_ACTUAL.md`: métricas de cobertura
- `docs/BITACORA_AGENTES.md`: registro de TAREA-035
- `.opencode/plans/TAREAS_INDEX.md`: entrada de TAREA-035

## ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-035.md`.
NO se elimina al ejecutar.

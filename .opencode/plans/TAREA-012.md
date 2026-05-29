# TAREA-012 — Reemplazo de enriquecimiento de año: token containment + intersecciones + esquina — Riesgo MEDIO

## CONTEXTO

El actual `enriquecer_anio_comparable()` (líneas 487-561 de `parsers/mercado_inmobiliario.py`) usa matching por **primer token** de la dirección, lo que falla cuando:

- La dirección del comparable es "Av. del Valle al 2700" → primer token "av" no matchea "avenida" ni "aristobulo" del catastro → **NONE** (~14/25 sin año)
- La dirección tiene intersecciones como "Santiago y Brown" → solo usa el primer token antes del espacio, ignora "Brown"
- No hay fallback para direcciones complejas

La simulación V7.1 mostró que el nuevo algoritmo de 3 pasos eleva la cobertura de ~11/25 a **27/33 (82%)** con ALTA/MEDIA.

## REGLA DE ORO

- `pytest tests/test_age_enrichment.py` debe pasar después de cada paso
- `python scripts/auto_validate.py` debe pasar
- El formato de retorno de `enriquecer_anio_comparable()` debe mantener compatibilidad: dict con `anio_estimado`, `ph_match`, `distancia_m`, `confianza`, `match_calle`, `direccion_catastro`
- El `_filtrar_por_diccionario` solo se aplica al subset bbox (~15-20 filas), NUNCA a las 20K filas del catastro completo (performance)
- No cambiar la firma `enriquecer_anio_comparable(comp, max_dist_m=50)`

## ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | 3 helpers nuevos + reemplazo de `enriquecer_anio_comparable` + carga de `calles_rosario.json` |
| `docs/ALGORITMOS.md` | Documentar 3 pasos del nuevo enriquecimiento |
| `docs/BITACORA_AGENTES.md` | Registrar la tarea |
| `docs/STATUS_ACTUAL.md` | Actualizar estado |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar entrada TAREA-012 |

---

### PASO 1: Carga del street dictionary + helpers de matching

**Archivo:** `parsers/mercado_inmobiliario.py`

**1.1** Agregar variable global y carga lazy de `calles_rosario.json` después de la línea 441 (`_MAX_DIST_ADDR_MATCH`):

```python
_CALLES_ROSARIO = None
_CALLES_DICT_FILTER_CACHE = {}
```

**1.2** Agregar bloque de carga al final de `cargar_catastro()` o en un bloque `if _CALLES_ROSARIO is None` dentro de los helpers. La ruta: `os.path.join(os.path.dirname(__file__), '..', 'data', 'calles_rosario.json')`

**1.3** Insertar 3 helpers entre `cargar_catastro()` (termina ~linea 484) y `enriquecer_anio_comparable()` (empieza ~linea 487):

```python
def _token_contenido(comp_tokens, csv_tokens):
    if not comp_tokens or not csv_tokens:
        return False
    it = iter(csv_tokens)
    for ct in comp_tokens:
        if not ct:
            continue
        found = False
        for csv_t in it:
            if ct == csv_t or (len(ct) >= 2 and len(csv_t) > len(ct) and csv_t.startswith(ct)):
                found = True
                break
        if not found:
            return False
    return True

def _filtrar_calle_diccionario(cn):
    global _CALLES_ROSARIO, _CALLES_DICT_FILTER_CACHE
    if _CALLES_ROSARIO is None:
        _calles_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'calles_rosario.json')
        if os.path.exists(_calles_path):
            with open(_calles_path, encoding='utf-8') as f:
                _CALLES_ROSARIO = json.load(f)
    if not cn or not _CALLES_ROSARIO:
        return ''
    if cn in _CALLES_DICT_FILTER_CACHE:
        return _CALLES_DICT_FILTER_CACHE[cn]
    tokens = cn.split()
    best = None
    best_score = -1
    for longitud in range(len(tokens), 0, -1):
        for inicio in range(len(tokens) - longitud + 1):
            sub = tokens[inicio:inicio+longitud]
            for calle in _CALLES_ROSARIO:
                calle_tokens = calle.split()
                it2 = iter(calle_tokens)
                exact = 0; prefix = 0; ok = True
                for st in sub:
                    found = False
                    for ct2 in it2:
                        if st == ct2:
                            exact += 1; found = True; break
                        elif len(st) >= 2 and len(ct2) > len(st) and ct2.startswith(st):
                            prefix += 1; found = True; break
                    if not found:
                        ok = False; break
                if ok:
                    score = longitud * 1000 + exact * 10 + prefix
                    if score > best_score:
                        best_score = score; best = ' '.join(sub)
    if best is None:
        validos = [t for t in tokens if len(t) >= 3 and any(
            t == ct for calle in _CALLES_ROSARIO for ct in calle.split())]
        best = ' '.join(validos)
    _CALLES_DICT_FILTER_CACHE[cn] = best if best else ''
    return _CALLES_DICT_FILTER_CACHE[cn]

def _extraer_interseccion(direccion):
    if not isinstance(direccion, str) or not direccion.strip():
        return []
    s = direccion.lower().strip()
    for sep in [' y ', ' - ', ' e ', ' esq ', ' esq. ', ' esq, ', ' esquina ']:
        if sep in s:
            partes = s.split(sep, 1)
            res = []
            for p in partes:
                p = p.strip()
                if p:
                    cn, num = extraer_calle_numero(p)
                    if cn:
                        cn2 = _filtrar_calle_diccionario(cn)
                        if cn2:
                            res.append((cn2, num))
            return res
    cn, num = extraer_calle_numero(direccion)
    if cn:
        cn2 = _filtrar_calle_diccionario(cn)
        if cn2:
            return [(cn2, num)]
    return []
```

**VERIFICAR:** `python -c "from parsers.mercado_inmobiliario import _token_contenido, _filtrar_calle_diccionario, _extraer_interseccion; print('OK')"`

---

### PASO 2: Reemplazar `enriquecer_anio_comparable()`

**Archivo:** `parsers/mercado_inmobiliario.py` — reemplazar líneas 487-561

La nueva función mantiene la misma firma y estructura de retorno. Implementa 3 pasos:

1. **Paso 1 (Token containment + ≤50m):** Para cada calle de la intersección parseada, busca el PH más cercano en el bbox donde `_token_contenido(comp_tokens, csv_tokens)` sea True y distancia ≤50m → ALTA (<30m) / MEDIA (30-50m)
2. **Paso 2 (Fallback nearest PH + token validation):** Encuentra el PH absoluto más cercano en bbox. Si <30m → ALTA. Si 30-50m + token match → MEDIA. Si no hay token match → descarta MEDIA.
3. **Paso 3 (Esquina fallback):** Si el nearest PH está ≤30m y no hubo token match en paso 2 → MEDIA (match_calle=False).

```python
def enriquecer_anio_comparable(comp, max_dist_m=50):
    catastro = cargar_catastro()
    if catastro is None:
        return None
    lat = comp.get('lat') or comp.get('latitud')
    lon = comp.get('lon') or comp.get('longitud')
    dir_comp = comp.get('direccion', comp.get('address', ''))
    if not lat or not lon:
        return None
    try:
        lat, lon = float(lat), float(lon)
    except (ValueError, TypeError):
        return None
    
    calles = _extraer_interseccion(dir_comp)
    if not calles:
        return None
    
    bbox = 0.001
    cercanos = catastro[
        (catastro['latitud'].between(lat - bbox, lat + bbox)) &
        (catastro['longitud'].between(lon - bbox, lon + bbox))
    ]
    if cercanos.empty:
        return None
    
    # Pre-normalizar bbox (SOLO ~15-20 filas)
    cercanos_norm = []
    for _, row in cercanos.iterrows():
        cn, num = extraer_calle_numero(str(row.get('direccion_nominatim', '')))
        cn_filt = _filtrar_calle_diccionario(cn) if cn else ''
        cercanos_norm.append({
            'row': row,
            'cn': cn_filt,
            'tokens': cn_filt.split() if cn_filt else []
        })
    
    # Paso 1: Token containment + ≤50m
    for cn, num in calles:
        if not cn:
            continue
        comp_tokens = cn.split()
        best_d = float('inf')
        best_row = None
        for entry in cercanos_norm:
            if not entry['tokens']:
                continue
            if _token_contenido(comp_tokens, entry['tokens']):
                r = entry['row']
                d = calcular_distancia_km(lat, lon, r['latitud'], r['longitud']) * 1000
                if d < best_d:
                    best_d = d
                    best_row = r
        if best_row is not None and best_d <= max_dist_m:
            conf = 'ALTA' if best_d < 30 else 'MEDIA'
            return {
                'anio_estimado': int(best_row['year']),
                'ph_match': str(best_row.get('ph', '?')),
                'distancia_m': round(best_d, 1),
                'confianza': conf,
                'match_calle': True,
                'direccion_catastro': str(best_row.get('direccion_nominatim', ''))
            }
    
    # Paso 2: Nearest PH absoluto + token validation para MEDIA
    mejor_dist = float('inf')
    mejor_row = None
    for entry in cercanos_norm:
        r = entry['row']
        d = calcular_distancia_km(lat, lon, r['latitud'], r['longitud']) * 1000
        if d < mejor_dist:
            mejor_dist = d
            mejor_row = r
    
    conf = None
    if mejor_row is not None and mejor_dist <= max_dist_m:
        if mejor_dist < 30:
            conf = 'ALTA'
        else:
            csv_tokens = []
            for entry in cercanos_norm:
                if entry['row']['ph'] == mejor_row['ph']:
                    csv_tokens = entry['tokens']
                    break
            match = any(
                _token_contenido(cn.split(), csv_tokens)
                for cn, _ in calles if cn
            ) if csv_tokens else False
            if match:
                conf = 'MEDIA'
        if conf:
            return {
                'anio_estimado': int(mejor_row['year']),
                'ph_match': str(mejor_row.get('ph', '?')),
                'distancia_m': round(mejor_dist, 1),
                'confianza': conf,
                'match_calle': True,
                'direccion_catastro': str(mejor_row.get('direccion_nominatim', ''))
            }
    
    # Paso 3: Esquina fallback — nearest ≤30m → MEDIA
    if mejor_dist <= 30:
        return {
            'anio_estimado': int(mejor_row['year']),
            'ph_match': str(mejor_row.get('ph', '?')),
            'distancia_m': round(mejor_dist, 1),
            'confianza': 'MEDIA',
            'match_calle': False,
            'direccion_catastro': str(mejor_row.get('direccion_nominatim', ''))
        }
    
    return None
```

**COMMIT:** `"TAREA-012: Replace enriquecer_anio_comparable with 3-step token containment + intersections + esquina"`

**VERIFICAR:**
- `pytest tests/test_age_enrichment.py -v`
- `python -c "executado de prueba unitaria de los 3 pasos"`

---

### PASO 3: Actualizar documentación

**3.1** `docs/ALGORITMOS.md` — Agregar sección de enriquecimiento de 3 pasos con pseudocódigo

**3.2** `docs/BITACORA_AGENTES.md` — Registrar decisión técnica

**3.3** `docs/STATUS_ACTUAL.md` — Actualizar estado

**3.4** `.opencode/plans/TAREAS_INDEX.md` — Agregar línea:

```
| TAREA-012 | Enriquecimiento 3-pasos: token containment + intersecciones + esquina | _(pendiente)_ | 2026-05-28 |
```

---

### VALIDACION FINAL

```
☐ pytest tests/test_age_enrichment.py pasa (26 tests)
☐ python scripts/auto_validate.py pasa
☐ python simular_valuacion_v3.py produce ~27/33 enriquecidos
☐ Valor Brown 2700 se mantiene ~$306,681 o cambia justificadamente
```

### ENTREGABLES

- `parsers/mercado_inmobiliario.py` modificado
- `docs/ALGORITMOS.md` actualizado
- `docs/BITACORA_AGENTES.md` actualizado
- `docs/STATUS_ACTUAL.md` actualizado
- `tests/test_age_enrichment.py` verificado (26 tests pasan)
- `.opencode/plans/TAREA-012.md` archivado
- `.opencode/plans/TAREAS_INDEX.md` actualizado

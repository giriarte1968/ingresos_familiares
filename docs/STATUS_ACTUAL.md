# 🏠 STATUS ACTUAL DEL PROYECTO — AVM Rosario

*Actualizado: 27/06/2026 (Fix persist cache preview + RO-CACHE-PREVIEW)*

---

## 1. RESUMEN EJECUTIVO

| Dimensión | Estado |
|-----------|--------|
| Motor valuación v7 | ✅ Base puro sin factores hedónicos (TAREA-073) |
| Coordenadas cache scraping | ✅ Corregidas vía centroide catastral (TAREA-020+021+024) |
| Enriquecimiento años | ✅ 3-pasos (exacta ≤200m / token+bloque ≤30m / nearest+token+bloque ≤60m) |
| Extracción calle+num | ✅ Mejorada: limpia basura descriptiva, trailing garbage, provincia, "bis" (TAREA-021+024) |
| Matching catastral (acentos/ñ) | ✅ Normalización NFKD en `_token_contenido` (TAREA-024) |
| Persistencia DO | ✅ Atómica + branch `do-state` |
| Landing page | ✅ Navegación por teclado (PageDown/PageUp/Home/End) |
| Tests regresión | ✅ 40/40 (RO-CACHE-PREVIEW-01 a 03: persist preview + Pendiente preserva válido) |
| Tests persistencia | ✅ 16/16 |
| Despliegue DO | Sin redeploy loop |
| Anclas grilla 400m | 322 microzonas, 96% cobertura (TAREA-036) |
| Zonas comerciales | Martin(5) Pellegrini(8) Pichincha(4) PN(4) Abasto(3) — con filtro distancia |

---

## 2. ESTADO DEL CACHE SCRAPING

| Métrica | Cantidad |
|---------|----------|
| Propiedades totales | 9,766 |
| Anclas disponibles | 322 microzonas (grilla 400m, TAREA-035) |
| Cobertura anclas (prop ≤300m) | 96% (8.014/8.366) |
| Con lat/lon | **9,754** (99.9%) |
| Sin lat/lon | 12 (nunca las tuvo Propia) |
| Con `calle_limpia`/`numero_limpio` | **8,782** (89.9%) |
| Sin calle (no se pudo extraer) | 984 |
| PH encontrado en catastro | **7,502** (TAREA-024) |
| Sin PH en catastro | 1,280 |
| Coords corregidas acumuladas | **~3,408** (3,289 TAREA-020 + 119 TAREA-024) |
| Coords originales conservadas (≤60m) | ~4,084 |
| Error promedio actual | 31m |

---

## 2. ARQUITECTURA ACTUAL

### Flujo de valuación

```
propiedades.json → motor_vpp_core.valuar_con_cache()
    → necesita_recalcular() → valuar_propiedad_v7()
    → persistir_valuacion() [local]
        → atomic_write_json → data/valuaciones_cache.json
        → atomic_write_json → propiedades.json (_ultima_valuacion)
    → try_sync_state() [opcional, push a do-state]
```

### Enriquecimiento de años (3 pasos)

```
Paso 0: EXACTA — (calle_norm, numero) en _CATASTRO_INDEX ≤200m → ALTA
Paso 1: TOKEN — token containment + bloque ≤30m → ALTA
Paso 2: NEAREST — nearest PH + token + bloque ≤60m → MEDIA
No esquina fallback.
```

### Filtro etario

```
±15 años → si ≥5 comps aplica
±30 años → si ≥5 comps aplica
Fallback → pool completo (P33)
Percentiles: 5-7→P33_age_blend / 8-9→P40 / 10-19→P45 / 20+→P50
```

---

## 3. COMPONENTES

| Archivo | Propósito |
|---------|-----------|
| `valu.py` | UI principal (Streamlit), landing, portfolio |
| `landing.py` | Landing page render + keyboard nav JS |
| `landing_content.py` | HTML sections con `data-section` |
| `parsers/mercado_inmobiliario.py` | Motor valuación v7, enriquecimiento 3-pasos |
| `parsers/valuacion_cache.py` | Cache persistente, escritura atómica |
| `parsers/git_sync.py` | Sync GitHub a `main` (try_sync) y `do-state` (try_sync_state) |
| `parsers/motor_vpp_core.py` | Wrapper valuación con caché + sync opcional |
| `parsers/valuacion_historial.py` | Historial append-only de valuaciones |
| `tests/test_persistencia_valuaciones.py` | 16 tests de persistencia |

---

## 4. PERSISTENCIA DO — BRANCH DE ESTADO

### Flujo
1. **Persistencia local atómica** (siempre):
   - `atomic_write_json()` → `data/valuaciones_cache.json`
   - `atomic_write_json()` → `propiedades.json`
2. **Sync opcional** (si hay token):
   - `try_sync_state()` → push a `do-state`

### Características
- `do-state` no dispara redeploy (DO deploya desde `main`)
- `GIT_STATE_BRANCH` configurable via env var
- `GIT_WRITE_TOKEN` requerido para push
- Fallo de sync no rompe valuación (persistencia local ya ocurrió)

### Recuperar en PC local
```bash
git fetch origin do-state
git checkout origin/do-state -- propiedades.json data/valuaciones_cache.json
```

---

## 5. TESTS

| Archivo | Estado |
|---------|--------|
| `tests/test_regression.py` | 40/40 ✅ (RO-CACHE-PREVIEW-01 a 03) |
| `tests/test_persistencia_valuaciones.py` | 16/16 ✅ |
| `tests/test_age_blend_filter.py` | ✅ |
| `tests/test_cluster_filters.py` | ✅ |
| `tests/test_cache.py` | ✅ |

---

## 6. VALUACIONES DE REFERENCIA (TAREA-071)

| Propiedad | Valor USD | m² | $/m² (m2_base) | ALTA | Pool |
|-----------|-----------|-----|-------|------|------|
| P1200 | $125.412 | 60.0 | $2.090 | 7 | 31 |
| Brown 2750 | $306.681 | 78.0 | $3.414 | 23 | 25 |
| Mabel | $86,092 | 41.0 | $2,100 | 13 | 79 |
| Ayacucho | $43,160 | 31.5 | $1,370 | 13 | 41 |
| Vera Mujica | $64,636 | 28.0 | $2,309 | 8 | 27 |
| Entre Ríos | $73.354 | 34.0 | $2.158 | 4 | 27 |

---

## 7. PRÓXIMOS PASOS / ISSUES CONOCIDOS

1. ✅ Vera Mujica benchmark actualizado (TAREA-071)
2. `data/history/` directorio untracked (generado por scraping)
3. Validación manual en DO del flujo do-state
4. ⚠️ P1200 y Brown 2750 requieren recalibración con fórmula multiplicativa
5. ⚠️ Botón "Comparable" en header carga desde cache en disco, debe cargar desde resultado actual en memoria (fix pendiente TAREA-086)

---

## 8. ESQUINAS — CORRECCIÓN DE DIRECCIONES VIA CENTROIDE CATASTRAL

### Problema detectado
PHs en intersecciones tienen `direccion_nominatim` incorrecta. Ej: PH 10286 tiene "Entre Ríos 411" pero su parcela catastral (SD=3) está sobre Tucumán → "Tucumán 1291".

### Métricas de detección
| Métrica | Valor |
|---------|-------|
| PHs que comparten coordenadas (esquinas) | 487 grupos, 1.182 PHs |
| PHs con coordenadas >30m del centroide catastral | 251 |
| % de esos con dirección incorrecta (muestra n=25) | 84% (21/25) |
| PHs estimados con dirección incorrecta | ~210 (~1% del total) |

### Corrección aplicada
- **Esquinas corregidas:** 218 PHs (centroide catastral → reverse-geocode → coordenadas + calle correcta)
- **Números interpolados:** 2.219 PHs (nearest-3 IDW en 146 calles con ≥20 referencias)
- **Batch centroide masivo:** +611 PHs recuperados (centroide → reverse → si número directo se acepta; si solo calle se interpola y verifica con forward-geocode <500m)
- **Total completas actual:** 18.870/21.017 (89%)
- **Pendientes:** ~1.301 PHs sin número en calles sin referencias suficientes

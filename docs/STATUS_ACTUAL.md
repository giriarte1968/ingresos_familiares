# ðŸ  STATUS ACTUAL DEL PROYECTO â€” AVM Rosario

*Actualizado: 09/06/2026 (TAREA-036: Filtro distancia zona comercial)*

---

## 1. RESUMEN EJECUTIVO

| DimensiÃ³n | Estado |
|-----------|--------|
| Motor valuaciÃ³n v7 | âœ… Operativo (cap dinÃ¡mico por cluster TAREA-022) |
| Coordenadas cache scraping | âœ… Corregidas vÃ­a centroide catastral (TAREA-020+021+024) |
| Enriquecimiento aÃ±os | âœ… 3-pasos (exacta â‰¤200m / token+bloque â‰¤30m / nearest+token+bloque â‰¤60m) |
| ExtracciÃ³n calle+num | âœ… Mejorada: limpia basura descriptiva, trailing garbage, provincia, "bis" (TAREA-021+024) |
| Matching catastral (acentos/Ã±) | âœ… NormalizaciÃ³n NFKD en `_token_contenido` (TAREA-024) |
| Persistencia DO | âœ… AtÃ³mica + branch `do-state` |
| Landing page | âœ… NavegaciÃ³n por teclado (PageDown/PageUp/Home/End) |
| Tests regresiÃ³n | âœ… 39/39 |
| Tests persistencia | âœ… 16/16 |
| Despliegue DO | Sin redeploy loop |
| Anclas grilla 400m | 322 microzonas, 96% cobertura (TAREA-036) |
| Zonas comerciales | Martin(5) Pellegrini(8) Pichincha(4) PN(4) Abasto(3) — con filtro distancia |

---

## 2. ESTADO DEL CACHE SCRAPING

| MÃ©trica | Cantidad |
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
| Coords originales conservadas (â‰¤60m) | ~4,084 |
| Error promedio actual | 31m |

---

## 2. ARQUITECTURA ACTUAL

### Flujo de valuaciÃ³n

```
propiedades.json â†’ motor_vpp_core.valuar_con_cache()
    â†’ necesita_recalcular() â†’ valuar_propiedad_v7()
    â†’ persistir_valuacion() [local]
        â†’ atomic_write_json â†’ data/valuaciones_cache.json
        â†’ atomic_write_json â†’ propiedades.json (_ultima_valuacion)
    â†’ try_sync_state() [opcional, push a do-state]
```

### Enriquecimiento de aÃ±os (3 pasos)

```
Paso 0: EXACTA â€” (calle_norm, numero) en _CATASTRO_INDEX â‰¤200m â†’ ALTA
Paso 1: TOKEN â€” token containment + bloque â‰¤30m â†’ ALTA
Paso 2: NEAREST â€” nearest PH + token + bloque â‰¤60m â†’ MEDIA
No esquina fallback.
```

### Filtro etario

```
Â±15 aÃ±os â†’ si â‰¥5 comps aplica
Â±30 aÃ±os â†’ si â‰¥5 comps aplica
Fallback â†’ pool completo (P33)
Percentiles: 5-7â†’P33_age_blend / 8-9â†’P40 / 10-19â†’P45 / 20+â†’P50
```

---

## 3. COMPONENTES

| Archivo | PropÃ³sito |
|---------|-----------|
| `valu.py` | UI principal (Streamlit), landing, portfolio |
| `landing.py` | Landing page render + keyboard nav JS |
| `landing_content.py` | HTML sections con `data-section` |
| `parsers/mercado_inmobiliario.py` | Motor valuaciÃ³n v7, enriquecimiento 3-pasos |
| `parsers/valuacion_cache.py` | Cache persistente, escritura atÃ³mica |
| `parsers/git_sync.py` | Sync GitHub a `main` (try_sync) y `do-state` (try_sync_state) |
| `parsers/motor_vpp_core.py` | Wrapper valuaciÃ³n con cachÃ© + sync opcional |
| `parsers/valuacion_historial.py` | Historial append-only de valuaciones |
| `tests/test_persistencia_valuaciones.py` | 16 tests de persistencia |

---

## 4. PERSISTENCIA DO â€” BRANCH DE ESTADO

### Flujo
1. **Persistencia local atÃ³mica** (siempre):
   - `atomic_write_json()` â†’ `data/valuaciones_cache.json`
   - `atomic_write_json()` â†’ `propiedades.json`
2. **Sync opcional** (si hay token):
   - `try_sync_state()` â†’ push a `do-state`

### CaracterÃ­sticas
- `do-state` no dispara redeploy (DO deploya desde `main`)
- `GIT_STATE_BRANCH` configurable via env var
- `GIT_WRITE_TOKEN` requerido para push
- Fallo de sync no rompe valuaciÃ³n (persistencia local ya ocurriÃ³)

### Recuperar en PC local
```bash
git fetch origin do-state
git checkout origin/do-state -- propiedades.json data/valuaciones_cache.json
```

---

## 5. TESTS

| Archivo | Estado |
|---------|--------|
| `tests/test_regression.py` | 100/101 âœ… (1 preexistente: Vera Mujica benchmark) |
| `tests/test_persistencia_valuaciones.py` | 16/16 âœ… |
| `tests/test_age_blend_filter.py` | âœ… |
| `tests/test_cluster_filters.py` | âœ… |
| `tests/test_cache.py` | âœ… |

---

## 6. VALUACIONES DE REFERENCIA

| Propiedad | Valor USD | mÂ² | $/mÂ² (m2_base) | ALTA | Pool |
|-----------|-----------|-----|-------|------|------|
| P1200 | $125.412 | 60.0 | $2.090 | 7 | 31 |
| Brown 2750 | $306.681 | 78.0 | $3.414 | 23 | 25 |
| Mabel | $66.694 | 41.0 | $1.627 | 13 | 79 |
| Ayacucho | $51.154 | 31.5 | $1.624 | 13 | 41 |
| Vera Mujica | $48.873 | 28.0 | $1.745 | 8 | 27 |
| Entre RÃ­os | $73.354 | 34.0 | $2.158 | 4 | 27 |

---

## 7. PRÃ“XIMOS PASOS / ISSUES CONOCIDOS

1. âš ï¸ Vera Mujica benchmark desactualizado (test_regression)
2. `data/history/` directorio untracked (generado por scraping)
3. ValidaciÃ³n manual en DO del flujo do-state

## 8. ESQUINAS â€” CORRECCIÃ“N DE DIRECCIONES VIA CENTROIDE CATASTRAL

### Problema detectado
PHs en intersecciones tienen `direccion_nominatim` incorrecta. Ej: PH 10286 tiene "Entre RÃ­os 411" pero su parcela catastral (SD=3) estÃ¡ sobre TucumÃ¡n â†’ "TucumÃ¡n 1291".

### MÃ©tricas de detecciÃ³n
| MÃ©trica | Valor |
|---------|-------|
| PHs que comparten coordenadas (esquinas) | 487 grupos, 1.182 PHs |
| PHs con coordenadas >30m del centroide catastral | 251 |
| % de esos con direcciÃ³n incorrecta (muestra n=25) | 84% (21/25) |
| PHs estimados con direcciÃ³n incorrecta | ~210 (~1% del total) |

### CorrecciÃ³n aplicada
- **Esquinas corregidas:** 218 PHs (centroide catastral â†’ reverse-geocode â†’ coordenadas + calle correcta)
- **NÃºmeros interpolados:** 2.219 PHs (nearest-3 IDW en 146 calles con â‰¥20 referencias)
- **Batch centroide masivo:** +611 PHs recuperados (centroide â†’ reverse â†’ si nÃºmero directo se acepta; si solo calle se interpola y verifica con forward-geocode <500m)
- **Total completas actual:** 18.870/21.017 (89%)
- **Pendientes:** ~1.301 PHs sin nÃºmero en calles sin referencias suficientes

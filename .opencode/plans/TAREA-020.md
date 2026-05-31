# TAREA-020 — Corrección de coordenadas del cache scraping vía centroide catastral

## CONTEXTO

Las coordenadas de `cache_scraping.json` (~9.766 propiedades) provienen del geocoder de los portales (Zonaprop/Argenprop), que asigna coordenadas al centro de cuadra. Esto causa dos problemas:

1. **Error promedio de 124m** vs la ubicación real del PH en catastro
2. **58% de las coordenadas** tienen error >60m (umbral PASO 2 para enriquecimiento de año)
3. **Comparables no fidedignos**: la distancia UI mostrada al sujeto valuado es incorrecta

## REGLA DE ORO

- Backup de `cache_scraping.json` antes de modificar
- Solo reemplazar coordenadas cuando error >60m detectado vs centroide catastral
- No modificar el motor de valuación ni el enriquecimiento de años
- `pytest` debe pasar después del cambio

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `data/geometry/parcelas_seccion*_json.csv` | (21 archivos) Leer geometría de parcelas, precomputar centroides |
| `cache_scraping.json` | Reemplazar lat/lon de propiedades con error >60m por centroide del PH matching |
| `scripts/corregir_coords_cache.py` | Nuevo script: backup → cargar geometría → matchear → corregir → guardar |
| `docs/BITACORA_AGENTES.md` | Registro de la tarea |
| `docs/STATUS_ACTUAL.md` | Actualizar sección de fuentes de datos |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar TAREA-020 |

## MÉTODO

```
Por cada propiedad en cache_scraping.json:
  1. extraer_calle_numero(direccion) → (cn, num)
  2. Buscar PH más cercano en catastro (exacto o por bloque)
  3. Obtener (seccion, manzana, grafico) del PH
  4. Cargar parcela desde geometría → calcular centroide
  5. Si distancia cache vs centroide >60m → reemplazar con centroide
```

## ESTIMACIÓN

| Métrica | Valor |
|---------|-------|
| Propiedades en cache | 9.766 |
| Con (calle, num) válido | 8.774 (90%) |
| Resolubles vía catastro (PH match) | ~2.445 únicos |
| Correcciones esperadas (>60m) | ~734 (30% de resolubles) |
| Calls a Nominatim | **0** |

## RESULTADOS ESPERADOS

- Enriquecimiento de año más preciso (coordenadas correctas → PASO 2 captura más matches)
- Distancias UI más fidedignas
- Cero regresiones en valores de valuación (solo cambian coordenadas, no el motor)

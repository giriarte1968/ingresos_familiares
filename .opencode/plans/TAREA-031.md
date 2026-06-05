# TAREA-031: Fecha dinámica — últimos 12 meses con date_created

## Diagnóstico
La valuación usaba `date_updated` para filtrar comparables, con ventana 180→365 días de dos pasos. Las fechas de referencia (fecha_ref) tenían tres problemas:
1. Campo incorrecto: `date_updated` en vez de `date_created`
2. Formato: `YYYY-MM` (ej. `'2026-05'`) rompía `strptime('%Y-%m-%d')` → el filtro caía en `except: return props` (sin filtro)
3. Hardcoded `'2026-04'` en `valuar_propiedad_smart`
4. Llamada alquiler en `valuar_propiedad_v7` no pasaba `fecha_ref`

## Solución
1. `date_updated` → `date_created` (con fallback a `date_updated` si no existe)
2. Aceptar `YYYY-MM-DD` y `YYYY-MM` en `filtrar_por_fecha`
3. Ventana fija 365 días (eliminar fallback 180)
4. Reemplazar hardcoded `'2026-04'` con `datetime.now()`
5. Pasar `fecha_ref` en la llamada alquiler

---

## Cambios

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py:941` | `filtrar_por_fecha`: `date_updated`→`date_created`, acepta `YYYY-MM` y `YYYY-MM-DD` |
| `parsers/mercado_inmobiliario.py:994` | `aplicar_filtro_fecha`: ventana fija 365 días |
| `parsers/mercado_inmobiliario.py:1502` | `valuar_propiedad_smart`: `'2026-04'` → `datetime.now()` |
| `parsers/mercado_inmobiliario.py:3161` | Alquiler en `valuar_propiedad_v7`: agregar `fecha_ref=fecha_ref` |

---

## Validación

1. `python scripts/auto_validate.py`
2. `python -m pytest tests/ -v`
3. Valuar una propiedad desde UI con fecha `2026-05` → verificar que filtra con `date_created`

---

## Documentación a actualizar

- [ ] `docs/BITACORA_AGENTES.md`
- [ ] `.opencode/plans/TAREAS_INDEX.md`

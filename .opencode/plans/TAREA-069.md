# TAREA-069: Sincronización Absoluta — Limpiar preview no comprometido al entrar

## Objetivo
Garantizar que una propiedad Pendiente se muestre **siempre vacía** al entrar,
eliminando cualquier residuo de previsualizaciones no comprometidas (Retro/Flex/
Selección), sin importar la ruta de navegación o el estado de flags de sesión.

## Causa Raíz Definitiva
El flag `forzar_recalculo` se filtraba entre sesiones de navegación, causando que
el Pendiente block se saltara el cleanup. Intentos previos de limpiar flags de
sesión (`preview_mode`, `retro_active`) fallaron porque los leaks ocurrían por
distintas rutas de entrada (`?prop=` handler, sidebar nav).

El sistema anterior verificaba condiciones de sesión (`forzar`/`retro_btn_clicked`)
que resultaron no confiables como guardianes del bloque Pendiente.

## Solución: Cache Inspection (Fuente de Verdad)
En lugar de depender de flags de sesión, se inspecciona DIRECTAMENTE el archivo
de cache (`valuaciones_cache.json`) para determinar si el resultado guardado fue
comprometido o es un preview.

**Regla absoluta:**
- Si `resultado_completo._cache.preview == True` → el resultado NUNCA fue comprometido
  (el usuario jamás presionó "Aplicar cambios" que llama a `persistir_valuacion(commit=True)`)
  → **limpiar cache y mostrar vacío**
- Si `_cache.preview == False` → el resultado fue comprometido, conservar

Esto se aplica SIEMPRE que se entra al bloque Pendiente, independientemente de
`forzar` o `retro_btn_clicked`. La limpieza del cache de preview no comprometido
es incondicional.

## Cambios

### 1. Pendiente block — `valu.py:500-522`
- Eliminar dependencia de `forzar` y `retro_btn_clicked` como guardianes
- Agregar inspección directa del cache: si `resultado_completo._cache.preview == True`,
  limpiar el cache incondicionalmente
- Solo se salta el cleanup (y se muestra vacío) si es un re-entry pasivo
  (`not forzar and not retro_btn_clicked`)

### 2. "← Volver al Portafolio" — `valu.py:645-651`
- Agregar pops de `retro_active`, `flex_active`, `manual_preview` adicionales
  al pop existente de `preview_mode`

### 3. Query param handler — `valu.py:1178-1186`
- Mantener la limpieza de estado de sesión al entrar por `?prop=Nombre`

## Flujo de Verificación
1. Pendiente en Portfolio "Sin valuación" → click → **vacío**
2. Retro toggle → preview → Volver → "Sin valuación" → click → **vacío**
3. Retro toggle → Aplicar cambios → Portfolio → muestra valor → click → **valor comprometido**
4. Retro toggle → Aplicar selección → Volver → "Sin valuación" → click → **vacío**
5. Limpiar valuación → "Sin valuación" → click → **vacío**

## Archivos modificados
- `valu.py` (Pendiente block, Volver button)

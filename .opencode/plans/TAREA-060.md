# TAREA-060: Pendiente re-entry limpia (empezar desde $0)

## Problema
Al re-entrar a una propiedad Pendiente que tenía preview cacheado, se mostraba el valor viejo del cache en lugar de empezar limpio ($0). El usuario quería: "empezar limpio".

## Causa
El bloque `if resultado_cacheado` en `valu.py:498` simplemente caía al flujo normal, donde `valuar_con_cache` encontraba el cache preview y lo retornaba. No limpiaba el estado previo.

## Solución
- Al detectar re-entry a Pendiente con cache preview, se **elimina la entrada del cache** y se muestra el detalle con `resultado={}` ($0), con un mensaje informativo.
- Se agregó `guardar_cache_valuaciones` al import de línea 420 para que esté disponible en el nuevo flujo.
- La Carga Natural (primera entrada sin cache) no se modifica.

## Commit
`<pending>`

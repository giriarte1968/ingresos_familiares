# TAREA-046: Simplificación de Puerto Norte (Time-Expansion Slider Unificado)

## Objetivo
Eliminar el algoritmo histórico y cableado de ventanas fijas para Puerto Norte (`VENTANAS_FECHA_PN = [365, 545, 730, 9999]`), unificando su comportamiento temporal con el del resto de Rosario. 
- En modo Natural (Retro OFF), Puerto Norte usará la ventana estándar de 180 días, pudiendo entrar "en blanco" si no hay comparables frescos (forzando al analista a activar Retro).
- En modo Retro (Retro ON), la ventana temporal será estrictamente gobernada por el slider (`180 + retro_meses * 30`).
- Se mantendrá la frontera cerrada (radio 1500m fijo sin expansión) para evitar la contaminación de datos con Pichincha.
- Se mantendrá el ajuste por depreciación temporal del `-4.5% anual` para comparables mayores a 180 días.

## Archivos a Modificar
- `parsers/mercado_inmobiliario.py`: Reemplazar el loop progresivo de PN por una consulta directa gobernada por `dias_ventana = 180 + retro_dias * 30` y actualizar el tracker `window_dias_usado`.

## Criterios de Aceptación
1. El slider de meses funciona de manera 100% reactiva para Francia 250b (Puerto Norte).
2. Si Retro está desactivado, Francia 250b entra en blanco ("insuficientes comparables") si no hay nada en los últimos 180 días.
3. El caption "ventana de X días" en la UI coincide exactamente con el valor real usado por el motor.
4. `auto_validate.py` pasa sin errores.

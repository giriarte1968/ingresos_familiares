# TAREA-147: Completar Curvas by_dormitorios (CT-adjusted) — Riesgo MEDIO

## CONTEXTO

Las curvas de size adjustment en zonas_depreciacion.json tienen 2 problemas:
1. Solo centro_premium y macrocentro tienen curvas by_dormitorios
2. Las curvas existentes fueron generadas SIN CT
3. Las curvas genericas mezclan todos los dormitorios

Analisis CT-adjustado de 21,828 propiedades revela patrones distintos por dormitorio.

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| data/zonas_depreciacion.json | Agregar by_dormitorios a 5 macrozonas + actualizar 2 existentes |

## PROCEDIMIENTO

1. Generar puntos de curva CT-adjusted para cada zona/dorm
2. Fallback a generica para dorms con datos insuficientes
3. Actualizar zonas_depreciacion.json
4. Validar con pytest y auto_validate

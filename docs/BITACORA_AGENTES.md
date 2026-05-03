# 📝 BITÁCORA DE AGENTES — AVM ROSARIO

Este documento es el "diario de trabajo". Cada agente de IA que trabaje en este proyecto debe registrar aquí el progreso para que el siguiente sepa exactamente dónde retomar.

---

## 🏗️ TAREA ACTUAL: Sincronización UI y Estabilidad de Fórmula (VPP)
**Estado:** Finalizado ✅
**Agente:** OpenCode (Gemma 4)
**Objetivo:** Resolver divergencia de precios UI vs Python y blindar la fórmula de valuación.

### Acciones Realizadas:
1. **Sincronización de Fecha**: Implementado el paso de `fecha_ref` desde la UI hasta el cluster en `obtener_mediana_cluster`, asegurando que ambos entornos filtren el mismo subconjunto de datos.
2. **Guard RO-12**: Implementado `_verificar_imports()` en `app.py` para bloquear el arranque si se detectan llamadas a `calcular_valor_vpp` (motor obsoleto).
3. **Fix de Caché (RO-13)**: Implementado control de TTLs por entorno (`APP_ENV`). En `development`, TTL=0 para evitar visualización de datos obsoletos.
4. **Sustitución de Sqrt por Clamps (V13.0)**: Eliminada la raíz cuadrada (`sqrt`) del cálculo del factor final para evitar compresiones no lineales difíciles de calibrar. Se implementaron clamps explícitos sobre la `SumaCruda` ($[-0.4, 0.4]$) y el `FactorTotal` ($[0.7, 1.35]$) para evitar la sobreinflación de precios por acumulación de factores positivos.
5. **Atenuación Dinámica (V12.4)**: Implementada lógica de saturación no lineal para el $\Delta \text{Antigüedad}$ en Venta P33. Se reemplazó el factor $K$ lineal por una función por tramos (Piecewise) para evitar la doble penalización en propiedades antiguas.
6. **Sincronización de Contexto**: Actualizados los tests de regresión para usar `fecha_ref="2026-04"`, eliminando la divergencia de $10k USD causada por el uso de promedios históricos en los tests vs datos actuales en la UI.
7. **Validación**: Ejecutados tests de regresión; confirmada convergencia de valores.
8. **Blindaje de Docs**: Actualizada `MEMORIA_PROYECTO.md` con **RO-15**, **RO-16** y **BUG-14**. Actualizado `ALGORITMOS.md` y `DICCIONARIO_DATOS.md` con la nueva lógica de atenuación y guardrails.

### Próximos Pasos (ROADMAP):
- [ ] Crear `GUIA_INSTALACION.md` con dependencias y requerimientos de entorno.
- [ ] Implementar los tests de regresión faltantes mencionados en la Memoria (Sección 11).
- [ ] Validar la guía de instalación en un entorno limpio.

---

## 📜 HISTORIAL DE SESIONES ANTERIORES
... (preserved)

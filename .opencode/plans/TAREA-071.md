# TAREA-071: Nueva Fórmula Multiplicativa de Valuación (ML-Based)

## Objetivo
Transicionar el motor de valuación de un modelo hedónico aditivo a un modelo multiplicativo basado en ML, eliminando factores de ruido y priorizando los drivers principales (Base, Tamaño, Edad, Calidad).

## Fórmula
Valor = m2_microzona * Size Discount * Factor Antigüedad * Factor Calidad/Estado * m2_equivalentes

## Pasos
1. [ ] Refactorizar calcular_factores en parsers/mercado_inmobiliario.py para eliminar factores de ruido (Vista, Piso, Ubicación, Gas, Balcón, etc.) y retornar solo multiplicadores puros de Edad y Calidad/Estado.
2. [ ] Implementar el cálculo multiplicativo final en aluar_propiedad_v7 (reemplazando el uso de suma_cruda).
3. [ ] Integrar calcular_size_discount_venta en el flujo principal.
4. [ ] Actualizar generar_razonamiento_valuacion para reflejar la nueva lógica multiplicativa.
5. [ ] Ejecutar tests de regresión, analizar el drift de precios y actualizar los valores de referencia en 	ests/test_regression.py.
6. [ ] Registrar cambios en docs/BITACORA_AGENTES.md y actualizar ALGORITMOS.md.

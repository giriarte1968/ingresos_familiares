# TAREA-057: Sincronización Total Motor <-> UI (Fórmulas Premium y Barreras)

## Problemas Detectados
1. **Barreras Geográficas Invisibles**: El motor aplica una penalización por barrera (ej. 3%) que afecta el m2 base, pero la tabla de comparables no lo muestra ni lo incluye en el precio ajustado, creando una discrepancia visual entre la tabla y el header.
2. **Error de Mediana (n=2)**: La UI usaba indexación entera (`n//2`) que devolvía el valor más alto en lugar del promedio cuando n=2, difiriendo de la matemática del motor.
3. **Recálculo Manual "Depreciado"**: El "Aplicar Selección" ignoraba los factores premium (+35%) y activos (cocheras), resultando en valores abruptamente bajos.
4. **Bucle de Carga Natural**: El guard de caché dependía de `comparables_venta`, provocando `st.rerun()` infinitos en propiedades Pendientes sin comparables, reseteando los widgets.

## Solución

### 1. `parsers/mercado_inmobiliario.py`
- Modificar la creación de comparables para que `precio_m2_ajustado` incluya `_time_adjustment * _penalizacion_barrier`.
- Agregar `barrier_penalty` al diccionario del comparable.
- Asegurar que `comparables_venta` se devuelvan incluso en caso de `insuficientes_comparables` para permitir visualización y selección.

### 2. `valu_detail_sections.py`
- Implementar `_calcular_mediana_local(precios_list)` para promediar medianas en n par.
- Agregar badge **BARRERA (X%)** en la tabla de comparables.
- Ajustar la métrica de selección para comparar P33 contra `m2_base_venta` (base vs base) en lugar de `valor_m2_actual_usd`.

### 3. `valu.py`
- **Botón Retro**: Agregar `key` estable.
- **Guard Carga Natural**: Cambiar `if resultado_cacheado.get('comparables_venta'):` por `if resultado_cacheado:`.
- **Fórmula de Recálculo Premium**:
  - Usar `_calcular_mediana_local` para P50.
  - Extraer multiplicador implícito: `mult = (valor_orig - valor_activos) / (m2_eq * m2_base_orig)`.
  - Nuevo valor: `(m2_eq * nuevo_vm2 * mult) + valor_activos`.
  - Actualizar `valor_m2_actual_usd` como `nuevo_valor / m2_eq`.

## Validación
- Header m² $\leftrightarrow$ Tabla m² (Suma de penalizaciones).
- P50 para n=2 $\leftrightarrow$ Promedio matemático.
- "Aplicar Selección" $\leftrightarrow$ Valor coherente con factores premium.
- Widgets persistentes en propiedades Pendientes.

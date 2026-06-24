## TAREA: TAREA-081 — Sistema de Valuación Híbrida: Sincronización Auto-Manual + Auditoría de Divergencia — Riesgo MEDIO

### CONTEXTO

Actualmente, la valuación automática y la manual coexisten como alternativas independientes y ciegas entre sí. El objetivo es transformarlas en un sistema de soporte de decisiones donde el motor propone un marco de mercado y el tasador aplica su criterio experto sobre ese marco, documentando las desviaciones.

### REGLA DE ORO

- **Transparencia**: El PDF debe mostrar ambos valores (Auto y Manual) si ambos existen.
- **Justificación**: Cualquier divergencia >10% en el valor manual requiere un `motivo` obligatorio.
- **Sincronización**: La valuación manual debe basarse en el contexto actual del motor (retro/flex activo).
- **Bloqueo de PDF**: No se permite exportar PDF si hay divergencia >5% y el `motivo` está vacío.

### ALCANCE TÉCNICO

#### 1. Motor de Valuación (`parsers/mercado_inmobiliario.py`)
- `generar_resultado_manual()`: Modificar firma para aceptar `auto_result` opcional. Copiar `comparables_venta`, `mapa_html`, `retro_activo` y `total_dias_ventana`.
- `manual_params`: Expandir para incluir `motivo`, `fecha_guardado`, `valor_auto_snapshot`.

#### 2. Interfaz de Usuario (`valu_detail_sections.py` & `valu.py`)
- **Lógica de Carga**: Calcular siempre `resultado_auto`. Si hay `manual_params`, calcular `resultado_manual`.
- **Header**: Toggle pills + alertas divergencia + staleness warning.
- **Formulario Manual**: motivo, validación (Δ>10% obligatorio), línea base viva del motor.

#### 3. Informe PDF
- Opción B: mostrar ambos valores + Δ + motivo.
- Hard block: Δ>5% + motivo vacío → no exportar.

### PASOS

1. Motor: modificar `generar_resultado_manual`
2. valu.py: orquestación paralela + fuente_activa
3. Header: toggle + alertas
4. Manual form: motivo + validación
5. PDF: ambos valores + hard block
6. Validación: tests + auto_validate

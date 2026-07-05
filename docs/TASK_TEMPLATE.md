# Formato TAREA — Template para cambios estructurados

Cada cambio significativo debe documentarse en este formato antes de implementar.
Los planes se guardan permanentemente en `.opencode/plans/TAREA-NNN.md` con ID secuencial.

## INDICE DE TAREAS EJECUTADAS

Ver `.opencode/plans/TAREAS_INDEX.md` para el listado completo.

---

## TAREA: TAREA-NNN — [Nombre corto] — Riesgo [BAJO/MEDIO/ALTO]

### CONTEXTO

Problema actual que motiva el cambio, con referencias a código y comportamiento observado.

### REGLA DE ORO

- Condiciones que NO deben violarse bajo ningun concepto
- `pytest` pasa despues de cada paso
- Los valores del motor NO cambian (si aplica)
- etc.

### UI GUARDRAILS (OBLIGATORIO si el cambio afecta la UI)

Si el cambio modifica componentes de UI (botones, banners, visibilidad, formularios):

1. **Agregar tests con mocks de Streamlit** en `tests/test_regression.py` que verifiquen:
   - Visibilidad de botones en todos los estados (selección total, parcial, sin selección)
   - Comportamiento del banner informativo
   - Estados disabled/enabled de botones críticos
2. Nombrar los tests con prefijo `test_ui_` para identificarlos
3. Usar `unittest.mock.patch` para simular `streamlit.button`, `streamlit.info`, etc.
4. Verificar que los tests pasen ANTES y DESPUÉS del cambio de código

### ALCANCE

| Archivo | Cambio |
|---|---|
| `ruta/archivo.py` | Descripcion del cambio |

---

### PASO 1: [Nombre del paso]

**Archivo:** `ruta/archivo.py` — funcion/bloque (lineas XX-YY)

**1.1** Cambio especifico 1

**1.2** Cambio especifico 2

```python
# Codigo exacto a insertar/reemplazar
```

**COMMIT:** `"Etiqueta: Descripcion del cambio"`

**VERIFICAR:** `pytest` / visual / etc.

---

### PASO 2: ...

(Repetir estructura por cada paso logico, 1 commit por paso)

---

### VALIDACION FINAL

```
☐ pytest pasa (XX tests)
☐ Check especifico 1
☐ Check especifico 2
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `docs/TASK_TEMPLATE.md` (si se modifica el formato)
- `.opencode/plans/TAREAS_INDEX.md` (agregar entrada de la tarea ejecutada)

### ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-NNN.md`.
El ID secuencial se asigna al crear el plan (ver ultimo ID en TAREAS_INDEX.md).
NO se elimina al ejecutar. Sirve como registro historico.

### ENTREGABLES

- Lista de archivos modificados
- `pytest` pasando
- Verificacion funcional completa
- Plan archivado en `.opencode/plans/TAREA-NNN.md`

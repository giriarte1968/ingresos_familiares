# TAREA: TAREA-114 — Fix flex_dormitorios=None al guardar valuación manual — Riesgo BAJO

### CONTEXTO

Al guardar una valuación manual, el código persiste `flex_dormitorios` en `_ultima_valuacion` usando la key `flex_dormitorios_{nombre}`, que **nunca es seteada** en session state. Esto siempre guarda `None`, causando que en el próximo re-entry (ej: Editar → Cancelar) Flex se desactive automáticamente, el motor pase a filtro estricto de dormitorios, encuentre < 3 comparables, y el usuario vea 0 comparables.

**Diagnóstico en logs:**
```
[DEBUG-MANUAL-SAVE] Francia 250b: flex_dormitorios=None preservados en UV
```
La key correcta para leer es `flex_active_{nombre}` (widget del checkbox).

### REGLA DE ORO

- `pytest` pasa después de cada paso
- El valor del motor NO cambia (solo preserva mejor el estado de Flex)
- El fix es puramente en la persistencia de UV, no en lógica de valuación

### ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_detail_sections.py` | Línea 1538: cambiar key `flex_dormitorios_{nombre}` por `flex_active_{nombre}` |

---

### PASO 1: Corregir lectura de flex_dormitorios en guardado manual

**Archivo:** `valu_detail_sections.py` — línea 1538

**1.1** Cambiar:
```python
uv['flex_dormitorios'] = st.session_state.get(f'flex_dormitorios_{nombre}', None)
```
Por:
```python
flex_active = st.session_state.get(f'flex_active_{nombre}', False)
uv['flex_dormitorios'] = [1, 2, 3, 4, 5] if flex_active else None
```

**VERIFICAR:** `pytest` + validar que Francia 250b preserve Flex tras guardar manual.

---

### VALIDACION FINAL

```
☐ pytest pasa (63+ tests)
☐ Francia 250b: guardar manual → Editar → Cancelar → Flex sigue activo
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md` (no requiere entrada, es parte de TAREA-104)
- `.opencode/plans/TAREAS_INDEX.md` (agregar entrada)

### ARCHIVO DE PLAN

`plan file`: `.opencode/plans/TAREA-114.md`

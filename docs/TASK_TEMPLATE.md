# Formato TAREA — Template para cambios estructurados

Cada cambio significativo debe documentarse en este formato antes de implementar.
El template se guarda como plan temporal (`.opencode/plans/tarea_nombre.md`) y se elimina al ejecutar.

---

## TAREA: [Nombre corto] — Riesgo [BAJO/MEDIO/ALTO]

### CONTEXTO

Problema actual que motiva el cambio, con referencias a código y comportamiento observado.

### REGLA DE ORO

- Condiciones que NO deben violarse bajo ningun concepto
- `pytest` pasa despues de cada paso
- Los valores del motor NO cambian (si aplica)
- etc.

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

### ENTREGABLES

- Lista de archivos modificados
- `pytest` pasando
- Verificacion funcional completa

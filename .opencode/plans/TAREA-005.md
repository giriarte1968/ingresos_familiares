# TAREA: TAREA-005 — Eliminar pantallazo numérico con st.status() — Riesgo BAJO

### CONTEXTO

Cuando el usuario abre el detalle de una propiedad, `mostrar_detalle_valu()` envía las secciones al frontend secuencialmente (header → rango → métricas → razonamiento → mapa + comparables → catastro → street view → historial). Cada `st.*` aparece en orden durante ~2.8s, produciendo un "pantallazo numérico" donde números grandes como "USD $120,000" aparecen antes que el mapa, catastro y demás contenido visual.

### REGLA DE ORO

- No cambiar lógica de valuación ni resultados
- `st.status` con `expanded=False` oculta todo hasta `expanded=True`
- El botón "← Volver al Portafolio" debe funcionar igual
- Los profile_blocks y StepLedgers deben preservarse

### ALCANCE

| Archivo | Cambio |
|---|---|
| `valu.py` | Reemplazar spinner + volver + mostrar_detalle_valu con un wrapper `st.status()` que oculta todo hasta que el render completo termina |

---

### PASO 1: Reemplazar bloque spinner+volver+detalle con st.status()

**Archivo:** `valu.py` — `mostrar_dashboard()` (líneas 324-348)

**1.1** Reemplazar el bloque `with st.spinner(...)` y las líneas posteriores con `with st.status(..., expanded=False)` que engloba todo: valuación, botón volver y `mostrar_detalle_valu()`.

**1.2** Al final, hacer `status.update(label="✔ Detalle listo", state="complete", expanded=True)`.

```python
            with st.status(f"Preparando detalle de {p_obj['nombre']}...", expanded=False) as _status:
                with profile_block("detalle_spinner_valuar", p_obj):
                    _sl = StepLedger("detalle_spinner_valuar_ledger", p_obj.get('nombre'))
                    _sl.mark("before_valuar")
                    resultado = valuar_con_cache(p_obj, forzar_recalculo=forzar, consultar_infomapa=False)
                    _sl.mark("after_valuar_con_cache")

                with profile_block("detalle_volver_btn", None):
                    if st.button("← Volver al Portafolio"):
                        st.session_state.prop_sel = None
                        st.rerun()

                with profile_block("mostrar_detalle_valu_total", p_obj):
                    mostrar_detalle_valu(p_obj, resultado, actualizar_propiedad)

                _sl.mark("after_render")
                _sl.close()
                _status.update(label="✔ Detalle listo", state="complete", expanded=True)
```

**COMMIT:** `"fix: Eliminar pantallazo numérico con st.status() para render atómico del detalle"`

**VERIFICAR:** Arrancar app con `streamlit run valu.py`, abrir detalle de una propiedad, confirmar que todo aparece de una vez sin parpadeo secuencial.

---

### PASO 2: Validación automática

Ejecutar `python scripts/auto_validate.py` y corregir errores si los hay.

---

### VALIDACION FINAL

```
☐ auto_validate.py pasa
☐ tests/test_regression.py pasa
☐ Visual: detalle aparece completo sin pantallazo numérico
☐ Botón "← Volver al Portafolio" funciona
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md` (agregar entrada TAREA-005)

### ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-005.md`.

### ENTREGABLES

- `valu.py` modificado
- `pytest` pasando
- Verificación visual: detalle sin pantallazo numérico
- Plan archivado en `.opencode/plans/TAREA-005.md`

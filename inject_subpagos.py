"""
Inject renderizar_tabla_egresos into app.py and update mostrar_egresos to use it.
This script modifies app.py in-place.
"""
import re

NEW_FUNC = '''
def renderizar_tabla_egresos(egresos_lista, datos, mes_seleccionado, is_preview=False):
    """Tabla de egresos unificada con flujo de subpagos integrado"""
    # Inicializar session state necesario
    if 'subpagos_por_egreso' not in st.session_state:
        st.session_state.subpagos_por_egreso = {}

    # Encabezados
    h1, h2, h3, h4, h5, h6, h7 = st.columns([1, 1.5, 2.5, 3, 1.5, 1.5, 1.2])
    h1.caption("Comp.")
    h2.caption("Fecha")
    h3.caption("ID")
    h4.caption("Descripcion / Comercio")
    h5.caption("Tipo")
    h6.caption("Monto")
    h7.caption("Categoria")
    st.divider()

    i = 0
    while i < len(egresos_lista):
        egreso = egresos_lista[i]
        i += 1

        if "u_id" not in egreso:
            eg_u_id = generar_id()
            egreso["u_id"] = eg_u_id
            if not is_preview:
                guardar_datos(datos)
        else:
            eg_u_id = egreso["u_id"]

        # Key unico para widgets Streamlit
        egreso_ui_key = re.sub(r"[^a-zA-Z0-9]", "_", eg_u_id)
        if is_preview:
            egreso_ui_key = f"pre_{egreso_ui_key}_{i}"

        es_subpago = "parent_id" in egreso
        esta_dividido = egreso.get("status") == "split"

        if es_subpago:
            prefix = "   -> "
        elif esta_dividido:
            prefix = "[Dividido] "
        else:
            prefix = ""

        sub_pagos_estado = st.session_state.subpagos_por_egreso.get(eg_u_id, [])
        has_subpagos = bool(egreso.get("sub_pagos")) or bool(sub_pagos_estado)

        col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1.5, 2.5, 3, 1.5, 1.5, 1.2])
        with col1:
            st.checkbox("V", value=has_subpagos, disabled=True, key=f"chk_{egreso_ui_key}")
        with col2:
            st.caption(str(egreso.get("fecha", "-"))[:10])
        with col3:
            st.caption(f"{eg_u_id[:8]}...")
        with col4:
            gasto_txt = egreso.get("gasto", "-")
            if esta_dividido:
                st.markdown(f"~~{prefix}{gasto_txt}~~")
            else:
                st.text(f"{prefix}{gasto_txt}")
        with col5:
            tipo = egreso.get("tipo", "Comercio")
            color = "blue" if tipo == "Comercio" else "green"
            st.markdown(f":{color}[{tipo}]")
        with col6:
            monto_val = egreso.get("monto", 0)
            if esta_dividido:
                st.markdown(f"~~${monto_val:,.0f}~~")
            else:
                st.markdown(f"**${monto_val:,.0f}**")
        with col7:
            st.caption(egreso.get("categoria", "-"))

        # Panel de desglose: todo dentro del mismo expander (sin flags externos)
        if not esta_dividido and not es_subpago:
            if sub_pagos_estado:
                expand_label = f"Ver/Confirmar {len(sub_pagos_estado)} sub-pagos detectados"
            else:
                expand_label = "+ Desglosar este pago (subir ticket)"

            with st.expander(expand_label, expanded=bool(sub_pagos_estado)):
                sub_pagos_actuales = st.session_state.subpagos_por_egreso.get(eg_u_id, [])

                if not sub_pagos_actuales:
                    # Etapa 1: subir y procesar
                    st.info("Subi el ticket fisico (Santa Fe Servicios) y presiona 'Extraer Sub-pagos'.")
                    uploaded = st.file_uploader(
                        "Ticket / Comprobante",
                        type=["jpg", "jpeg", "png", "pdf"],
                        key=f"upl_{egreso_ui_key}"
                    )
                    if uploaded:
                        if uploaded.type.startswith("image"):
                            st.image(uploaded, width=280)
                        else:
                            st.write(f"Archivo: {uploaded.name}")
                        if st.button("Extraer Sub-pagos con OCR", key=f"ocr_{egreso_ui_key}", type="primary"):
                            with st.spinner("Procesando con OCR..."):
                                try:
                                    reader = get_ocr_reader()
                                    result, texto_raw = extraer_subpagos_desde_comprobante(reader, uploaded)
                                    if result:
                                        st.session_state.subpagos_por_egreso[eg_u_id] = result
                                        if not is_preview:
                                            egreso["sub_pagos"] = result
                                            guardar_datos(datos)
                                        st.success(f"{len(result)} sub-pagos detectados.")
                                        st.rerun()
                                    else:
                                        st.error("No se detectaron sub-pagos. Revisa el texto extraido.")
                                        with st.expander("Texto OCR extraido"):
                                            st.text(texto_raw or "(vacio)")
                                except Exception as e:
                                    st.error(f"Error OCR: {e}")
                else:
                    # Etapa 2: revisar y confirmar
                    st.write(f"**{len(sub_pagos_actuales)} sub-pagos. Edita si es necesario antes de confirmar:**")
                    total_sp = 0
                    for si, sp in enumerate(sub_pagos_actuales):
                        sp_key = f"{egreso_ui_key}_sp{si}"
                        ca, cb = st.columns([3, 1])
                        with ca:
                            sp["descripcion"] = st.text_input(
                                "Descripcion", sp.get("descripcion", ""),
                                key=f"desc_{sp_key}", label_visibility="collapsed"
                            )
                        with cb:
                            sp["monto"] = st.number_input(
                                "Monto", value=float(sp.get("monto", 0)),
                                min_value=0.0, key=f"monto_{sp_key}", label_visibility="collapsed"
                            )
                        total_sp += sp.get("monto", 0)

                    st.divider()
                    diferencia = egreso.get("monto", 0) - total_sp
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.metric("Total desglosado", f"${total_sp:,.0f}",
                                  delta=f"Dif: ${diferencia:,.0f}", delta_color="off")
                    with c2:
                        if st.button("Reiniciar", key=f"reset_{egreso_ui_key}"):
                            del st.session_state.subpagos_por_egreso[eg_u_id]
                            st.rerun()

                    label_btn = "Confirmar Division" if not is_preview else "Confirmar (Preview)"
                    if st.button(label_btn, key=f"confirm_{egreso_ui_key}", type="primary", use_container_width=True):
                        egreso["status"] = "split"
                        egreso["monto_original_antes_de_split"] = egreso.get("monto", 0)
                        egreso["monto"] = 0

                        nuevos = []
                        for sp in sub_pagos_actuales:
                            desc = sp.get("descripcion", "").strip()
                            monto = sp.get("monto", 0)
                            if desc and monto > 0:
                                cat, subcat, _, tipo = categorizar_gasto(desc, datos)
                                nuevos.append({
                                    "u_id": generar_id(),
                                    "parent_id": eg_u_id,
                                    "fecha": egreso.get("fecha", ""),
                                    "gasto": desc,
                                    "monto": monto,
                                    "moneda": egreso.get("moneda", "ARS"),
                                    "fuente": "Santa Fe Servicios",
                                    "tipo": tipo,
                                    "categoria": cat,
                                    "subcategoria": subcat
                                })

                        egresos_lista.extend(nuevos)
                        if not is_preview:
                            guardar_datos(datos)
                        if eg_u_id in st.session_state.subpagos_por_egreso:
                            del st.session_state.subpagos_por_egreso[eg_u_id]
                        st.success(f"Division confirmada: {len(nuevos)} registros creados.")
                        st.rerun()

'''

# --- Snippet for preview table render in mostrar_egresos ---
PREVIEW_CALL = """
                        # Asignar u_id temporales para uso en preview
                        for g in gastos:
                            if "u_id" not in g:
                                g["u_id"] = generar_id() + "_pre"

                        # Tabla interactiva unificada (preview)
                        renderizar_tabla_egresos(gastos, datos, mes_seleccionado, is_preview=True)
"""

# --- Snippet for the permanent egresos section ---
PERMANENT_TABLE = """
    if egresos:
        total = sum(e.get("monto", 0) for e in egresos)
        st.metric("Total Egresos del Mes", f"${total:,.2f} ARS")

        df_temp = __import__("pandas").DataFrame(egresos)
        if "categoria" in df_temp.columns and not df_temp.empty:
            st.subheader("Por Categoria")
            por_cat = df_temp.groupby("categoria")["monto"].sum()
            st.bar_chart(por_cat)

        renderizar_tabla_egresos(egresos, datos, mes_seleccionado, is_preview=False)
    else:
        st.info("No hay egresos cargados para este mes")
"""

with open("app.py", encoding="utf-8", errors="replace") as f:
    content = f.read()

# 1. Inject renderizar_tabla_egresos before mostrar_egresos
INSERT_BEFORE = "def mostrar_egresos():"
if INSERT_BEFORE not in content:
    print("ERROR: 'def mostrar_egresos():' not found")
else:
    content = content.replace(INSERT_BEFORE, NEW_FUNC + "\n" + INSERT_BEFORE, 1)
    print("OK: renderizar_tabla_egresos injected")

    # 2. Find the dataframe preview block and replace with renderizar call
    # Pattern: the block that builds df_preview and shows st.dataframe
    old_preview = """                        df_preview = pd.DataFrame(gastos)[['fecha', 'gasto', 'monto', 'categoria', 'subcategoria']]
                        df_preview = df_preview.rename(columns={'gasto': 'GASTO'})
                        st.dataframe(df_preview)"""
    
    if old_preview in content:
        content = content.replace(old_preview, PREVIEW_CALL, 1)
        print("OK: preview dataframe replaced with renderizar call")
    else:
        # Try to find Se detectaron gastos block
        idx = content.find('st.success(f"Se detectaron {len(gastos)} gastos")')
        if idx > 0:
            # Find the dataframe call after it
            chunk = content[idx:idx+500]
            print("Preview area snippet:")
            print(repr(chunk))
        else:
            print("WARNING: preview block not found - skipping preview replacement")

    # 3. Find the permanent egresos table and replace with renderizar call
    # Look for the permanent table section
    perm_marker_start = "    if egresos:\n        df = pd.DataFrame(egresos)"
    perm_marker_end_candidates = [
        "    else:\n        st.info(\"No hay egresos cargados para este mes\")",
        "    else:\n        st.info('No hay egresos cargados para este mes')",
    ]
    
    found_perm = False
    for end_marker in perm_marker_end_candidates:
        if perm_marker_start in content and end_marker in content:
            start_pos = content.find(perm_marker_start)
            end_pos = content.find(end_marker, start_pos) + len(end_marker)
            old_block = content[start_pos:end_pos]
            content = content[:start_pos] + PERMANENT_TABLE + content[end_pos:]
            print(f"OK: permanent table replaced ({len(old_block)} chars)")
            found_perm = True
            break
    
    if not found_perm:
        print("WARNING: permanent table block not found - will need manual check")

    with open("app.py", "w", encoding="utf-8", errors="replace") as f:
        f.write(content)
    print(f"OK: app.py written, {len(content)} chars total")

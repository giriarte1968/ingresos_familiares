"""Script para reemplazar la funcion renderizar_tabla_egresos en app.py"""

NEW_FUNC = '''def renderizar_tabla_egresos(egresos_lista, datos, mes_seleccionado, is_preview=False):
    """Funcion unificada para renderizar la tabla de egresos con soporte para subpagos"""
    h1, h2, h3, h4, h5, h6, h7 = st.columns([1, 1.2, 1.5, 3, 1.2, 1.5, 1])
    h1.caption("Comp.")
    h2.caption("Fecha")
    h3.caption("ID")
    h4.caption("Descripcion / Comercio")
    h5.caption("Tipo")
    h6.caption("Monto")
    h7.caption("Categoria")
    st.divider()

    for idx, egreso in enumerate(egresos_lista):
        if "u_id" not in egreso:
            eg_u_id = generar_id()
            egreso["u_id"] = eg_u_id
            if not is_preview:
                guardar_datos(datos)
        else:
            eg_u_id = egreso["u_id"]

        egreso_ui_key = eg_u_id.replace(".", "_").replace("-", "_")
        if is_preview:
            egreso_ui_key = f"pre_{egreso_ui_key}_{idx}"

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

        col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1.2, 1.5, 3, 1.2, 1.5, 1])

        with col1:
            st.checkbox("V", value=has_subpagos, disabled=True, key=f"chk_{egreso_ui_key}")
        with col2:
            st.caption(egreso.get("fecha", "-")[:10])
        with col3:
            st.caption(f"{eg_u_id[:6]}...")
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

        # Panel de desglose: todo en el mismo expander, sin flags externos
        if not esta_dividido and not es_subpago:
            if sub_pagos_estado:
                expand_label = f"Ver/Confirmar {len(sub_pagos_estado)} sub-pagos detectados"
            else:
                expand_label = "+ Desglosar este pago (subir ticket)"

            with st.expander(expand_label, expanded=bool(sub_pagos_estado)):

                sub_pagos_actuales = st.session_state.subpagos_por_egreso.get(eg_u_id, [])

                if not sub_pagos_actuales:
                    st.info("Subi el ticket fisico (Santa Fe Servicios) y presiona el boton para extraer los conceptos.")
                    uploaded = st.file_uploader(
                        "Ticket de Santa Fe Servicios",
                        type=["jpg", "jpeg", "png", "pdf"],
                        key=f"upl_{egreso_ui_key}"
                    )
                    if uploaded:
                        if uploaded.type.startswith("image"):
                            st.image(uploaded, width=300)
                        else:
                            st.write(f"Archivo: {uploaded.name}")
                        if st.button("Extraer Sub-pagos con OCR", key=f"ocr_{egreso_ui_key}", type="primary"):
                            with st.spinner("Procesando con OCR... puede tardar unos segundos"):
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
                                    st.error(f"Error: {e}")
                else:
                    st.write(f"**{len(sub_pagos_actuales)} sub-pagos encontrados. Edita si es necesario:**")
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
                                min_value=0.0,
                                key=f"monto_{sp_key}", label_visibility="collapsed"
                            )
                        total_sp += sp.get("monto", 0)

                    st.divider()
                    diferencia = egreso.get("monto", 0) - total_sp
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        st.metric("Total desglosado", f"${total_sp:,.0f}", delta=f"Dif: ${diferencia:,.0f}", delta_color="off")
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

with open('app.py', encoding='utf-8', errors='replace') as f:
    content = f.read()

start_marker = 'def renderizar_tabla_egresos('
end_marker = '\ndef mostrar_egresos()'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"ERROR: markers not found. start={start_idx}, end={end_idx}")
else:
    new_content = content[:start_idx] + NEW_FUNC + '\n' + content[end_idx+1:]
    with open('app.py', 'w', encoding='utf-8', errors='replace') as f:
        f.write(new_content)
    print(f"OK: replaced {end_idx - start_idx} chars with {len(NEW_FUNC)} chars")
    print(f"New total: {len(new_content)} chars")

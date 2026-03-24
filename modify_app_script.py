"""
Script para modificar app.py: separar subpagos
"""
import re

with open("app.py", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# 1. Nueva version simplificada de renderizar_tabla_egresos
NUEVA_RENDERIZAR = '''
def renderizar_tabla_egresos(egresos_lista, datos, mes_seleccionado, is_preview=False):
    """Tabla de egresos unificada, solo visualización (subpagos se gestionan aparte)"""
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
            if not is_preview: guardar_datos(datos)
        else:
            eg_u_id = egreso["u_id"]

        egreso_ui_key = re.sub(r"[^a-zA-Z0-9]", "_", eg_u_id)
        if is_preview: egreso_ui_key = f"pre_{egreso_ui_key}_{i}"

        es_subpago = "parent_id" in egreso
        esta_dividido = egreso.get("status") == "split"

        prefix = "   -> " if es_subpago else ("[Dividido] " if esta_dividido else "")
        has_subpagos = bool(egreso.get("sub_pagos"))

        col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1.5, 2.5, 3, 1.5, 1.5, 1.2])
        with col1: st.checkbox("V", value=has_subpagos, disabled=True, key=f"chk_{egreso_ui_key}")
        with col2: st.caption(str(egreso.get("fecha", "-"))[:10])
        with col3: st.caption(f"{eg_u_id[:8]}...")
        with col4:
            gasto_txt = egreso.get("gasto", "-")
            if esta_dividido: st.markdown(f"~~{prefix}{gasto_txt}~~")
            else: st.text(f"{prefix}{gasto_txt}")
        with col5:
            tipo = egreso.get("tipo", "Comercio")
            color = "blue" if tipo == "Comercio" else "green"
            st.markdown(f":{color}[{tipo}]")
        with col6:
            monto_val = egreso.get("monto", 0)
            if esta_dividido: st.markdown(f"~~${monto_val:,.0f}~~")
            else: st.markdown(f"**${monto_val:,.0f}**")
        with col7: st.caption(egreso.get("categoria", "-"))
'''

# 2. Nueva sección de subpagos para inyectar al final de la visualización de egresos guardados
# Look for:       renderizar_tabla_egresos(egresos, datos, mes_seleccionado, is_preview=False)
NUEVA_SECCION_SUBPAGOS = '''        renderizar_tabla_egresos(egresos, datos, mes_seleccionado, is_preview=False)

        # ---------------------------------------------------------------------
        # SECCION: PROCESAR SUB-PAGOS (Ticket Físico)
        # ---------------------------------------------------------------------
        st.write("---")
        st.subheader("📑 Desglosar Pago Guardado (Ej: Ticket Santa Fe Servicios)")
        
        # Filtrar pagos que pueden dividirse (no son subpagos ni están divididos aún, y monto > 0)
        pagos_divisibles = [
            e for e in egresos 
            if "parent_id" not in e and e.get("status") != "split" and e.get("monto", 0) > 0
        ]
        
        if not pagos_divisibles:
            st.info("No hay pagos guardados disponibles para desglosar.")
        else:
            opciones_pagos = {
                e["u_id"]: f"{e.get('fecha', '')[:10]} | {e.get('gasto', '-')} | ${e.get('monto', 0):,.2f}"
                for e in pagos_divisibles
            }
            
            pago_seleccionado_id = st.selectbox(
                "Selecciona el pago que querés dividir:",
                options=list(opciones_pagos.keys()),
                format_func=lambda x: opciones_pagos[x]
            )
            
            pago_original = next(e for e in egresos if e["u_id"] == pago_seleccionado_id)
            
            col_upl, col_proc = st.columns([1, 1])
            with col_upl:
                ticket_file = st.file_uploader(
                    "Subir foto o PDF del ticket detallado",
                    type=["jpg", "jpeg", "png", "pdf"],
                    key="upl_subpago_seccion"
                )
                
            with col_proc:
                st.write("")
                st.write("")
                if ticket_file:
                    st.success(f"Archivo cargado: {ticket_file.name}")
                    if st.button("🔍 Extraer Sub-pagos con OCR", type="primary", use_container_width=True):
                        with st.spinner("Procesando ticket..."):
                            reader = get_ocr_reader()
                            import copy, io
                            # Leer bytes directo para no perderlos en reruns
                            bytes_file = ticket_file.read()
                            f_obj = io.BytesIO(bytes_file)
                            f_obj.name = ticket_file.name
                            res_sp, raw_txt = extraer_subpagos_desde_comprobante(reader, f_obj)
                            
                            if res_sp:
                                # Guardar temporalmente en un dict distinto para no chocar
                                st.session_state["subpagos_tmp"] = res_sp
                                st.session_state["sp_target_id"] = pago_seleccionado_id
                                st.rerun()
                            else:
                                st.error("No se encontraron sub-pagos.")
                                with st.expander("Ver texto OCR bruto"):
                                    st.text(raw_txt)

            # Si ya se hizo OCR y hay resultados temporales para mostrar
            if "subpagos_tmp" in st.session_state and st.session_state.get("sp_target_id") == pago_seleccionado_id:
                sub_pagos_actuales = st.session_state["subpagos_tmp"]
                st.write(f"### ✏️ Revisar y Confirmar ({len(sub_pagos_actuales)} ítems encontrados)")
                
                total_sp = 0
                for si, sp in enumerate(sub_pagos_actuales):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        sp["descripcion"] = st.text_input("Desc", sp.get("descripcion", ""), key=f"tmp_desc_{si}", label_visibility="collapsed")
                    with c2:
                        sp["monto"] = st.number_input("Monto", value=float(sp.get("monto", 0)), min_value=0.0, key=f"tmp_monto_{si}", label_visibility="collapsed")
                    total_sp += sp.get("monto", 0)
                
                st.divider()
                dif = pago_original.get("monto", 0) - total_sp
                
                col_met, col_btn1, col_btn2 = st.columns([2, 1, 1.5])
                with col_met:
                    st.metric("Total detallado", f"${total_sp:,.0f}", delta=f"Diferencia: ${dif:,.0f}", delta_color="off")
                
                with col_btn1:
                    st.write("")
                    if st.button("Descartar", use_container_width=True):
                        del st.session_state["subpagos_tmp"]
                        del st.session_state["sp_target_id"]
                        st.rerun()
                        
                with col_btn2:
                    st.write("")
                    if st.button("✅ Confirmar División", type="primary", use_container_width=True):
                        # Mutar el original
                        pago_original["status"] = "split"
                        pago_original["monto_original_antes_de_split"] = pago_original.get("monto", 0)
                        pago_original["monto"] = 0
                        pago_original["sub_pagos"] = copy.deepcopy(sub_pagos_actuales)
                        
                        # Crear los hijos directamente en 'egresos' (pasa por referencia, así que muta 'datos')
                        nuevos_hijos = []
                        for sp_hijo in sub_pagos_actuales:
                            desc = sp_hijo.get("descripcion", "").strip()
                            m = sp_hijo.get("monto", 0)
                            if desc and m > 0:
                                cat, subcat, _, tipo = categorizar_gasto(desc, datos)
                                nuevos_hijos.append({
                                    "u_id": generar_id(),
                                    "parent_id": pago_original["u_id"],
                                    "fecha": pago_original.get("fecha", ""),
                                    "gasto": desc,
                                    "monto": m,
                                    "moneda": pago_original.get("moneda", "ARS"),
                                    "fuente": "Santa Fe Servicios",
                                    "tipo": tipo,
                                    "categoria": cat,
                                    "subcategoria": subcat
                                })
                        
                        egresos.extend(nuevos_hijos)
                        guardar_datos(datos)
                        
                        # Limpiar estado
                        del st.session_state["subpagos_tmp"]
                        del st.session_state["sp_target_id"]
                        
                        st.success(f"¡Atómico! El pago fue desglosado en {len(nuevos_hijos)} conceptos.")
                        import time
                        time.sleep(1.5)
                        st.rerun()
'''

import re

# Sustituir la función renderizar_tabla_egresos 
# Buscamos de "def renderizar_tabla_egresos" hasta "def mostrar_egresos"
content_new = re.sub(
    r'(def renderizar_tabla_egresos\(.*?\):.*?)(?=\ndef mostrar_egresos\(\):)', 
    NUEVA_RENDERIZAR + '\n', 
    content, 
    flags=re.DOTALL
)

# Ahora inyectar la sección de abajo
content_new = content_new.replace(
    'renderizar_tabla_egresos(egresos, datos, mes_seleccionado, is_preview=False)', 
    NUEVA_SECCION_SUBPAGOS
)

with open("app.py", "w", encoding="utf-8", errors="replace") as f:
    f.write(content_new)

print("Script ejecutado: app.py actualizado.")

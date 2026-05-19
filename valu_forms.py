"""Formulario de propiedades para Valu — Diseño con tarjetas estilo Zillow."""
import streamlit as st
import uuid
from datetime import datetime


def _titulo_seccion(titulo, icono, color):
    """Muestra el título de la sección con estilo."""
    st.markdown(f"""
    <div style="color:{color};font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">
        {icono} {titulo}
    </div>
    """, unsafe_allow_html=True)


def ui_formulario_propiedad(prop_inicial=None, key_suffix="", show_geocode=True):
    """Función unificada para el formulario de propiedades v10.0 con diseño de tarjetas."""
    if prop_inicial is None:
        prop_inicial = {}
    
    from datetime import datetime
    ANIO_ACTUAL = datetime.now().year

    errores = []
    
    lat_key = f"lat_{key_suffix}"
    lon_key = f"lon_{key_suffix}"
    
    # === SECCIÓN 1: UBICACIÓN ===
    with st.container(border=True):
        _titulo_seccion("Ubicación", "📍", "#006AFF")
        
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre *", value=prop_inicial.get('nombre', ''), key=f"nombre_{key_suffix}")
            if not nombre or not nombre.strip():
                errores.append("El nombre es obligatorio")
            
            zonas = ["Centro", "Macrocentro", "Barrio Inglés", "Pichincha", "Abasto", "Martin", "Facultades", "Puerto Norte", "Barrio Tigre", "Rosario Norte", "Alvear", "San Martín", "General Paz", "Echesortu", "Fisherton", "Ruta 9", "Sur", "Norte", "Oeste", "Sexta Pellegrini", "República de la Sexta", "Otro"]
            zona = st.selectbox("Zona / Barrio *", zonas, index=zonas.index(prop_inicial.get('zona', 'Otro')) if prop_inicial.get('zona') in zonas else len(zonas)-1, key=f"zona_{key_suffix}")
            
            direccion = st.text_input("Dirección *", value=prop_inicial.get('direccion', ''), key=f"direccion_{key_suffix}")
            if not direccion or not direccion.strip():
                errores.append("La dirección es obligatoria")
        with col2:
            # Auto-geocodificar si la dirección cambió
            if show_geocode:
                addr = direccion.strip()
                if len(addr) >= 3:
                    last_key = f"_last_geo_{key_suffix}"
                    if st.session_state.get(last_key) != addr:
                        try:
                            from parsers.geocoder import geocoding_manager
                            geo = geocoding_manager(addr)
                            if geo and geo.get('lat'):
                                st.session_state[lat_key] = geo['lat']
                                st.session_state[lon_key] = geo['lon']
                                st.session_state[last_key] = addr
                        except Exception:
                            pass
            # Inicializar session_state si no existe (evita warning de value duplicado)
            if lat_key not in st.session_state:
                st.session_state[lat_key] = prop_inicial.get('lat', -32.9445)
            if lon_key not in st.session_state:
                st.session_state[lon_key] = prop_inicial.get('lon', -60.6319)
            lat_input = st.number_input("Latitud *", format="%.7f", key=lat_key)
            lon_input = st.number_input("Longitud *", format="%.7f", key=lon_key)
            if show_geocode:
                if st.button("📍 Geocodificar dirección", width='stretch',
                             disabled=not direccion.strip(), key=f"geobtn_{key_suffix}"):
                    from parsers.geocoder import geocoding_manager
                    with st.spinner("Buscando coordenadas..."):
                        geo = geocoding_manager(direccion)
                    if geo and geo.get('lat'):
                        st.session_state[lat_key] = geo['lat']
                        st.session_state[lon_key] = geo['lon']
                        st.success(f"Coordenadas: {geo['lat']:.7f}, {geo['lon']:.7f}")
                        st.rerun()
                    else:
                        st.error("No se encontró la dirección en OpenStreetMap")
            
            ub_tipos = ["calle", "avenida", "esquina", "pasaje"]
            ubicacion_tipo = st.selectbox("Tipo de Ubicación", ub_tipos, index=ub_tipos.index(prop_inicial.get('ubicacion_tipo', 'calle')) if prop_inicial.get('ubicacion_tipo') in ub_tipos else 0, key=f"ubica_tipo_{key_suffix}")
    
    # === SECCIÓN 2: EDIFICACIÓN ===
    with st.container(border=True):
        _titulo_seccion("Edificación", "🏢", "#7C3AED")
        
        col1, col2 = st.columns(2)
        with col1:
            tipos = ["departamento", "casa", "local", "oficina", "terreno"]
            tipo = st.selectbox("Tipo *", tipos, index=tipos.index(prop_inicial.get('tipo_inmueble', 'departamento')) if prop_inicial.get('tipo_inmueble') in tipos else 0, key=f"tipo_{key_suffix}")
            
            anio_const = st.number_input("Año construcción *", min_value=1900, max_value=ANIO_ACTUAL, value=int(prop_inicial.get('anio_construccion', 2000) or 2000), key=f"anio_const_{key_suffix}")
            if not anio_const or anio_const < 1900:
                errores.append("El año de construcción es obligatorio")
            
            import json, os
            try:
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "constructoras_rosario.json"), "r", encoding="utf-8") as f:
                    constr_data = json.load(f)
                    lista_c = []
                    for tier in constr_data.values():
                        lista_c.extend(tier.get("nombres", []))
                    lista_c = sorted(list(set(lista_c))) + ["Otra"]
            except:
                lista_c = ["Otra"]
            constructora_sel = st.selectbox("Constructora", lista_c, index=lista_c.index(prop_inicial.get('constructora', '')) if prop_inicial.get('constructora') in lista_c else lista_c.index("Otra"), key=f"const_sel_{key_suffix}")
            constructora = constructora_sel
            if constructora_sel == "Otra":
                constructora = st.text_input("Especificar Constructora", value=prop_inicial.get('constructora', ''), key=f"const_text_{key_suffix}")
        with col2:
            piso = st.number_input("Piso *", min_value=0, max_value=50, value=int(prop_inicial.get('piso', 0) or 0), key=f"piso_{key_suffix}")
            total_pisos = st.number_input("Total pisos edificio *", min_value=1, max_value=60, value=int(prop_inicial.get('total_pisos', 1) or 1), key=f"total_p_{key_suffix}")
            
            vistas = ["interna", "pulmon", "frente", "despejada", "rio"]
            vista = st.selectbox("Vista", vistas, index=vistas.index(prop_inicial.get('vista', 'frente')) if prop_inicial.get('vista') in vistas else 2, key=f"vista_{key_suffix}")
            
            gas_opts = ["si", "no", "en_proceso"]
            gas_ok = st.selectbox("Gas", gas_opts, index=gas_opts.index(prop_inicial.get('gas_ok', 'si')) if prop_inicial.get('gas_ok') in gas_opts else 0, key=f"gas_{key_suffix}")
    
    # === SECCIÓN 3: SUPERFICIES ===
    with st.container(border=True):
        _titulo_seccion("Superficies", "📐", "#0D9488")
        
        cs1, cs2, cs3, cs4 = st.columns(4)
        with cs1:
            m2_cubiertos = st.number_input("m² cubiertos *", min_value=0.0, value=float(prop_inicial.get('m2_cubiertos', 0.0)), step=0.5, key=f"m2_cub_{key_suffix}")
            if not m2_cubiertos or m2_cubiertos <= 0:
                errores.append("Los m² cubiertos son obligatorios")
        with cs2:
            m2_semi = st.number_input("m² semicub.", min_value=0.0, value=float(prop_inicial.get('m2_semicubiertos', 0.0)), key=f"m2_semi_{key_suffix}")
        with cs3:
            m2_dp = st.number_input("m² desc. propios", min_value=0.0, value=float(prop_inicial.get('m2_descubiertos_propios', 0.0)), key=f"m2_dp_{key_suffix}")
        with cs4:
            m2_dce = st.number_input("m² desc. común", min_value=0.0, value=float(prop_inicial.get('m2_descubiertos_comun_exclusivo', 0.0)), key=f"m2_dce_{key_suffix}")
        
        cs5, cs6 = st.columns(2)
        with cs5:
            orients = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"]
            orientacion = st.selectbox("Orientación", orients, index=orients.index(prop_inicial.get('orientacion', 'este')) if prop_inicial.get('orientacion') in orients else 2, key=f"orient_{key_suffix}")
        with cs6:
            vents = ["cruzada", "simple"]
            ventilacion = st.selectbox("Ventilación", vents, index=vents.index(prop_inicial.get('ventilacion', 'simple')) if prop_inicial.get('ventilacion') in vents else 1, key=f"vent_{key_suffix}")
    
    # === SECCIÓN 4: ESTADO Y CALIDAD ===
    with st.container(border=True):
        _titulo_seccion("Estado y Calidad", "🛠️", "#F59E0B")
        
        col1, col2 = st.columns(2)
        with col1:
            estados = ["a estrenar", "excelente", "muy bueno", "bueno", "regular", "a refaccionar"]
            estado_detalle = st.selectbox("Estado *", estados, index=estados.index(prop_inicial.get('estado_detalle', 'bueno')) if prop_inicial.get('estado_detalle') in estados else 3, key=f"estado_{key_suffix}")
            
            tiene_reciclado = st.checkbox("Reciclada", value=prop_inicial.get('reciclado', False), key=f"reciclado_{key_suffix}")
            reciclado_tipo, anio_reciclado = "ninguno", None
            if tiene_reciclado:
                reciclado_tipo = st.radio("Tipo reciclado", ["parcial", "total"], index=["parcial", "total"].index(prop_inicial.get('reciclado_tipo', 'parcial')) if prop_inicial.get('reciclado_tipo') in ["parcial", "total"] else 0, key=f"reciclado_tipo_{key_suffix}", horizontal=True)
                anio_reciclado = st.number_input("Año reciclado", min_value=2000, max_value=ANIO_ACTUAL, value=int(prop_inicial.get('anio_reciclado', 2020) or 2020), key=f"anio_reciclado_{key_suffix}")
            
            calidades = ["premium", "media", "economica"]
            calidad_edificio = st.selectbox("Calidad", calidades, index=calidades.index(prop_inicial.get('calidad_edificio', 'media')) if prop_inicial.get('calidad_edificio') in calidades else 1, key=f"calidad_{key_suffix}")
        with col2:
            suelos = ["madera_noble", "porcelanato", "ceramico", "estandar"]
            terminaciones_suelo = st.selectbox("Suelo", suelos, index=suelos.index(prop_inicial.get('terminaciones_suelo', 'estandar')) if prop_inicial.get('terminaciones_suelo') in suelos else 3, key=f"suelo_{key_suffix}")
            
            carps = ["piso_techo", "dvh", "estandar"]
            carpinteria = st.selectbox("Carpintería", carps, index=carps.index(prop_inicial.get('carpinteria', 'estandar')) if prop_inicial.get('carpinteria') in carps else 2, key=f"carp_{key_suffix}")
            
            cochera = st.checkbox("Cochera", value=prop_inicial.get('cochera', False), key=f"cochera_{key_suffix}")
    
    # === SECCIÓN 5: FUNCIONALIDAD ===
    with st.container(border=True):
        _titulo_seccion("Funcionalidad", "🧩", "#EC4899")
        
        col1, col2 = st.columns(2)
        with col1:
            dormitorios = st.number_input("Dormitorios *", min_value=0, max_value=10, value=int(prop_inicial.get('dormitorios', 0) or 0), key=f"dorm_{key_suffix}")
            if dormitorios is None or dormitorios < 0:
                errores.append("Los dormitorios son obligatorios")
            
            baños = st.number_input("Baños", min_value=0, max_value=10, value=int(prop_inicial.get('baños', 0) or 0), key=f"baños_{key_suffix}")
            toilet = st.checkbox("Toilette", value=prop_inicial.get('toilet', False), key=f"toilet_{key_suffix}")
            baño_servicio = st.checkbox("Baño de servicio", value=prop_inicial.get('baño_servicio', False), key=f"baño_serv_{key_suffix}")
            
            doble_ingreso = st.checkbox("Doble Ingreso", value=prop_inicial.get('doble_ingreso', False), key=f"doble_{key_suffix}")
            lavadero = st.checkbox("Lavadero Independiente", value=prop_inicial.get('lavadero_independiente', False), key=f"lavadero_{key_suffix}")
            layout_flexible = st.checkbox("Layout flexible", value=prop_inicial.get('layout_flexible', False), key=f"layout_{key_suffix}")
            placares = st.checkbox("Placares completos", value=prop_inicial.get('placares_completos', False), key=f"placares_{key_suffix}")
            despensa = st.checkbox("Despensa", value=prop_inicial.get('despensa', False), key=f"despensa_{key_suffix}")
            ascensores = st.number_input("Ascensores", min_value=1, max_value=4, value=int(prop_inicial.get('ascensores_edificio', 2) or 2), key=f"ascensores_{key_suffix}")
            
            amenities_opts = ["caldera_central", "radiadores", "seguridad_24hs", "seguridad_tag", "seguridad_camaras", "seguridad_totem", "aberturas_premium", "pileta", "sum", "gym"]
            detalles_default = [v for v in prop_inicial.get('detalles_categoria', []) if v in amenities_opts]
            detalles_cat = st.multiselect("Amenities", amenities_opts, default=detalles_default, key=f"detalles_{key_suffix}")
            
            vent_bano_opts = ["natural", "forzada", "sin_ventana"]
            ventilacion_bano = st.selectbox("Ventilación baño", vent_bano_opts, index=vent_bano_opts.index(prop_inicial.get('ventilacion_bano', 'natural')) if prop_inicial.get('ventilacion_bano') in vent_bano_opts else 0, key=f"vent_bano_{key_suffix}")
        with col2:
            descripcion_libre = st.text_area("Descripción libre", value=prop_inicial.get('descripcion_libre', ''), key=f"desc_{key_suffix}", height=200)
    
    # === SECCIÓN 6: DATOS FINANCIEROS ===
    with st.container(border=True):
        _titulo_seccion("Datos Financieros", "💰", "#16A34A")
        
        col1, col2 = st.columns(2)
        with col1:
            valor_compra_usd = st.number_input("Valor compra (USD)", min_value=0.0, step=1000.0, value=float(prop_inicial.get('valor_compra_usd', 0.0)), key=f"v_compra_{key_suffix}")
            fecha_compra = st.date_input("Fecha compra", value=datetime.strptime(prop_inicial.get('fecha_compra', '2020-01-01'), '%Y-%m-%d') if prop_inicial.get('fecha_compra') else datetime(2020, 1, 1), key=f"f_compra_{key_suffix}")
        with col2:
            expensas_ars = st.number_input("Expensas (ARS)", min_value=0, value=int(prop_inicial.get('expensas_ars', 0)), step=1000, key=f"exp_{key_suffix}")
            fecha_publicacion = st.date_input("Fecha de publicación", value=datetime.strptime(prop_inicial.get('fecha_publicacion', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d') if prop_inicial.get('fecha_publicacion') else datetime.now(), key=f"f_pub_{key_suffix}")
    
    # === PROCESAR DATOS ===
    seg = 'ninguna'
    if 'seguridad_24hs' in detalles_cat: seg = '24hs'
    elif 'seguridad_tag' in detalles_cat: seg = 'tag'
    elif 'seguridad_camaras' in detalles_cat: seg = 'camaras'
    
    data = {
        'nombre': nombre, 'tipo_inmueble': tipo, 'zona': zona, 'direccion': direccion,
        'lat': lat_input, 'lon': lon_input, 'ubicacion_tipo': ubicacion_tipo,
        'm2_cubiertos': m2_cubiertos, 'dormitorios': dormitorios, 'baños': baños,
        'toilet': toilet, 'baño_servicio': baño_servicio, 'anio_construccion': anio_const,
        'constructora': constructora, 'piso': piso, 'total_pisos': total_pisos,
        'vista': vista, 'gas_ok': gas_ok, 'm2_semicubiertos': m2_semi,
        'm2_descubiertos_propios': m2_dp, 'm2_descubiertos_comun_exclusivo': m2_dce,
        'balcon': False, 'tipo_balcon': 'ninguno', 'orientacion': orientacion,
        'ventilacion': ventilacion, 'estado_detalle': estado_detalle,
        'calidad_edificio': calidad_edificio, 'seguridad': seg,
        'terminaciones_suelo': terminaciones_suelo, 'carpinteria': carpinteria,
        'cochera': cochera, 'doble_ingreso': doble_ingreso,
        'lavadero_independiente': lavadero, 'reciclado': tiene_reciclado,
        'reciclado_tipo': reciclado_tipo, 'anio_reciclado': anio_reciclado,
        'ventilacion_bano': ventilacion_bano, 'layout_flexible': layout_flexible,
        'placares_completos': placares, 'despensa': despensa,
        'ascensores_edificio': ascensores, 'detalles_categoria': detalles_cat,
        'descripcion_libre': descripcion_libre, 'valor_compra_usd': valor_compra_usd,
        'fecha_compra': fecha_compra.strftime('%Y-%m-%d'),
        'fecha_publicacion': fecha_publicacion.strftime('%Y-%m-%d'),
        'expensas_ars': expensas_ars,
        'id': prop_inicial.get('id', f"prop_{uuid.uuid4().hex[:8]}")
    }
    
    # Validar campos obligatorios
    if errores:
        for err in errores:
            st.error(err)
        st.stop()
    
    return data
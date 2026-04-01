import streamlit as st
import pandas as pd


def _obtener_datos():
    if 'datos' in st.session_state and isinstance(st.session_state.datos, dict):
        meses = st.session_state.datos.get('meses', {})
        total = sum(
            len(m.get('egresos', [])) + len(m.get('ingresos_bancarios', []))
            for m in meses.values()
        )
        if total > 0:
            return st.session_state.datos

    try:
        import os, json
        ruta = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'datos.json'
        )
        if os.path.exists(ruta):
            with open(ruta, 'r', encoding='utf-8') as f:
                datos_disco = json.load(f)
                st.session_state.datos = datos_disco
                return datos_disco
    except Exception as e:
        st.error(f"Error leyendo datos: {e}")

    return {'meses': {}, 'activos': []}


def _obtener_meses_ordenados(datos):
    meses = list(datos.get('meses', {}).keys())
    meses = [m for m in meses if isinstance(m, str) and len(m) >= 7]
    return sorted(meses, reverse=True)


def _colectar_egresos(datos, periodo):
    meses_data = datos.get('meses', {})
    registros = []

    if periodo == "Todos los periodos":
        for mes, mes_data in meses_data.items():
            for e in mes_data.get('egresos', []):
                row = dict(e)
                row['periodo'] = mes
                registros.append(row)
    else:
        for e in meses_data.get(periodo, {}).get('egresos', []):
            row = dict(e)
            row['periodo'] = periodo
            registros.append(row)

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)
    for col in ['fecha', 'gasto', 'monto', 'moneda', 'fuente',
                'categoria', 'subcategoria', 'owner', 'medio_pago', 'u_id', 'periodo']:
        if col not in df.columns:
            df[col] = ''

    df['monto'] = pd.to_numeric(df['monto'], errors='coerce').fillna(0.0)
    df['medio_owner'] = df['medio_pago'].astype(str) + ' - ' + df['owner'].astype(str)
    return df


def _colectar_ingresos(datos, periodo):
    meses_data = datos.get('meses', {})
    registros = []

    if periodo == "Todos los periodos":
        for mes, mes_data in meses_data.items():
            for i in mes_data.get('ingresos_bancarios', []):
                row = dict(i)
                row['periodo'] = mes
                row['tipo_ingreso'] = 'bancario'
                registros.append(row)

            gan_fondos = mes_data.get('ganancia_fondos', 0)
            if gan_fondos and gan_fondos > 0:
                registros.append({
                    'periodo': mes,
                    'fecha': f"{mes}-28",
                    'descripcion': 'Ganancia Fondos Mutuos',
                    'monto': gan_fondos,
                    'banco': 'fondos_mutuos',
                    'categoria': 'inversion',
                    'owner': 'Gustavo',
                    'tipo_ingreso': 'fondos_mutuos'
                })

            plusv_prop = mes_data.get('plusvalia_propiedades', 0)
            if plusv_prop and plusv_prop > 0:
                registros.append({
                    'periodo': mes,
                    'fecha': f"{mes}-28",
                    'descripcion': 'Plusvalia Propiedades',
                    'monto': plusv_prop,
                    'banco': 'propiedades',
                    'categoria': 'inversion',
                    'owner': 'Gustavo',
                    'tipo_ingreso': 'plusvalia_propiedades'
                })

            plusv_adrs = mes_data.get('plusvalia_adrs', 0)
            if plusv_adrs and plusv_adrs > 0:
                registros.append({
                    'periodo': mes,
                    'fecha': f"{mes}-28",
                    'descripcion': 'Plusvalia ADRs',
                    'monto': plusv_adrs,
                    'banco': 'adrs',
                    'categoria': 'inversion',
                    'owner': 'Gustavo',
                    'tipo_ingreso': 'plusvalia_adrs'
                })

            for aj in mes_data.get('ajustes', []):
                monto_aj = aj.get('monto', 0)
                if monto_aj > 0:
                    registros.append({
                        'periodo': mes,
                        'fecha': aj.get('fecha', f"{mes}-15"),
                        'descripcion': aj.get('descripcion', 'Ajuste'),
                        'monto': monto_aj,
                        'banco': 'ajuste',
                        'categoria': aj.get('tipo', 'ajuste'),
                        'owner': '',
                        'tipo_ingreso': 'ajuste'
                    })
    else:
        mes_data = meses_data.get(periodo, {})

        for i in mes_data.get('ingresos_bancarios', []):
            row = dict(i)
            row['periodo'] = periodo
            row['tipo_ingreso'] = 'bancario'
            registros.append(row)

        gan_fondos = mes_data.get('ganancia_fondos', 0)
        if gan_fondos and gan_fondos > 0:
            registros.append({
                'periodo': periodo,
                'fecha': f"{periodo}-28",
                'descripcion': 'Ganancia Fondos Mutuos',
                'monto': gan_fondos,
                'banco': 'fondos_mutuos',
                'categoria': 'inversion',
                'owner': 'Gustavo',
                'tipo_ingreso': 'fondos_mutuos'
            })

        plusv_prop = mes_data.get('plusvalia_propiedades', 0)
        if plusv_prop and plusv_prop > 0:
            registros.append({
                'periodo': periodo,
                'fecha': f"{periodo}-28",
                'descripcion': 'Plusvalia Propiedades',
                'monto': plusv_prop,
                'banco': 'propiedades',
                'categoria': 'inversion',
                'owner': 'Gustavo',
                'tipo_ingreso': 'plusvalia_propiedades'
            })

        plusv_adrs = mes_data.get('plusvalia_adrs', 0)
        if plusv_adrs and plusv_adrs > 0:
            registros.append({
                'periodo': periodo,
                'fecha': f"{periodo}-28",
                'descripcion': 'Plusvalia ADRs',
                'monto': plusv_adrs,
                'banco': 'adrs',
                'categoria': 'inversion',
                'owner': 'Gustavo',
                'tipo_ingreso': 'plusvalia_adrs'
            })

        for aj in mes_data.get('ajustes', []):
            monto_aj = aj.get('monto', 0)
            if monto_aj > 0:
                registros.append({
                    'periodo': periodo,
                    'fecha': aj.get('fecha', f"{periodo}-15"),
                    'descripcion': aj.get('descripcion', 'Ajuste'),
                    'monto': monto_aj,
                    'banco': 'ajuste',
                    'categoria': aj.get('tipo', 'ajuste'),
                    'owner': '',
                    'tipo_ingreso': 'ajuste'
                })

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)
    for col in ['fecha', 'descripcion', 'monto', 'banco', 'categoria', 'owner', 'periodo', 'tipo_ingreso']:
        if col not in df.columns:
            df[col] = ''

    df['monto'] = pd.to_numeric(df['monto'], errors='coerce').fillna(0.0)
    return df


def _convertir_ingreso_clp_a_ars(ingreso, periodo_mes):
    """Convierte un ingreso CLP a ARS usando la tasa de la FECHA del ingreso"""
    monto = ingreso.get('monto', 0)

    if ingreso.get('monto_original_clp') and ingreso.get('banco') == 'santander_chile':
        clp = ingreso['monto_original_clp']
        fecha_ingreso = ingreso.get('fecha', periodo_mes)

        try:
            from app import obtener_precios_historicos
            usd_clp, usdt_ars = obtener_precios_historicos(fecha_ingreso)
        except:
            usd_clp = 925
            usdt_ars = 1465

        if not usd_clp:
            usd_clp = 925
        if not usdt_ars:
            try:
                from app import obtener_usdt_ars_binance
                usdt_ars = obtener_usdt_ars_binance() or 1465
            except:
                usdt_ars = 1465

        monto_ars = (clp / usd_clp) * usdt_ars
        return monto_ars

    return monto


def mostrar_reportes(mes_preseleccionado=None):
    st.header("Reportes")

    datos = _obtener_datos()
    meses = _obtener_meses_ordenados(datos)

    if not meses:
        st.info("No hay periodos cargados")
        return

    total_egresos = sum(len(datos.get('meses', {}).get(m, {}).get('egresos', [])) for m in meses)
    total_ingresos = sum(len(datos.get('meses', {}).get(m, {}).get('ingresos_bancarios', [])) for m in meses)
    st.caption(f"{len(meses)} periodos | {total_ingresos} ingresos bancarios | {total_egresos} egresos")

    opciones_periodo = ["Todos los periodos"] + meses
    if mes_preseleccionado in meses:
        default_index = opciones_periodo.index(mes_preseleccionado)
    else:
        default_index = 0

    periodo = st.selectbox(
        "Seleccionar periodo",
        opciones_periodo,
        index=default_index,
        key="reporte_periodo_selector"
    )

    tab_ingresos, tab_egresos, tab_balance = st.tabs([
        "Ingresos",
        "Egresos",
        "Balance"
    ])

    with tab_ingresos:
        df_ing = _colectar_ingresos(datos, periodo)

        if df_ing.empty:
            st.warning(f"No hay ingresos para {periodo}")
        else:
            # Convertir CLP a ARS usando tasa de fecha del ingreso
            df_ing['monto_convertido'] = df_ing.apply(
                lambda row: _convertir_ingreso_clp_a_ars(row, periodo), axis=1
            )

            total = df_ing['monto_convertido'].sum()
            cantidad = len(df_ing)

            bancarios = df_ing[df_ing['tipo_ingreso'] == 'bancario']['monto_convertido'].sum()
            fondos = df_ing[df_ing['tipo_ingreso'] == 'fondos_mutuos']['monto_convertido'].sum()
            plusv_prop = df_ing[df_ing['tipo_ingreso'] == 'plusvalia_propiedades']['monto_convertido'].sum()
            plusv_adrs = df_ing[df_ing['tipo_ingreso'] == 'plusvalia_adrs']['monto_convertido'].sum()
            ajustes_pos = df_ing[df_ing['tipo_ingreso'] == 'ajuste']['monto_convertido'].sum()

            st.subheader("Resumen de Ingresos")
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Ingresos", f"${total:,.0f}")
            m2.metric("Cantidad Movimientos", f"{cantidad}")
            m3.metric("Promedio", f"${total/cantidad:,.0f}" if cantidad > 0 else "$0")

            st.subheader("Desglose por Tipo")
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Bancarios", f"${bancarios:,.0f}")
            c2.metric("Fondos Mutuos", f"${fondos:,.0f}")
            c3.metric("Plusv. Propiedades", f"${plusv_prop:,.0f}")
            c4.metric("Plusv. ADRs", f"${plusv_adrs:,.0f}")
            c5.metric("Ajustes (+)", f"${ajustes_pos:,.0f}")

            st.subheader("Filtros")
            fc1, fc2 = st.columns(2)

            with fc1:
                tipos_ingreso = ["Todos"] + sorted([
                    str(x) for x in df_ing['tipo_ingreso'].dropna().unique() if str(x).strip()
                ])
                filtro_tipo = st.selectbox("Tipo ingreso", tipos_ingreso, key="rep_ing_tipo")

            with fc2:
                bancos = ["Todos"] + sorted([
                    str(x) for x in df_ing['banco'].dropna().unique() if str(x).strip()
                ])
                filtro_banco = st.selectbox("Fuente/Banco", bancos, key="rep_ing_banco")

            df_ing_f = df_ing.copy()
            if filtro_tipo != "Todos":
                df_ing_f = df_ing_f[df_ing_f['tipo_ingreso'] == filtro_tipo]
            if filtro_banco != "Todos":
                df_ing_f = df_ing_f[df_ing_f['banco'] == filtro_banco]

            if df_ing_f.empty:
                st.info("No hay datos con los filtros seleccionados")
            else:
                st.subheader("Distribucion")
                g1, g2 = st.columns(2)
                with g1:
                    st.caption("Por tipo de ingreso")
                    serie_tipo = df_ing_f.groupby('tipo_ingreso', dropna=False)['monto_convertido'].sum().sort_values(ascending=False)
                    st.bar_chart(serie_tipo)

                with g2:
                    st.caption("Por categoria")
                    serie_cat = df_ing_f.groupby('categoria', dropna=False)['monto_convertido'].sum().sort_values(ascending=False)
                    st.bar_chart(serie_cat)

                st.subheader("Rankings")
                rk1, rk2 = st.columns(2)

                with rk1:
                    st.caption("Por descripcion")
                    ing_desc = (
                        df_ing_f.groupby('descripcion', dropna=False)['monto_convertido']
                        .agg(['sum', 'count'])
                        .sort_values('sum', ascending=False)
                        .rename(columns={'sum': 'Total', 'count': 'Cant'})
                    )
                    st.dataframe(ing_desc, use_container_width=True)

                with rk2:
                    st.caption("Por banco/fuente")
                    ing_banco = (
                        df_ing_f.groupby('banco', dropna=False)['monto_convertido']
                        .agg(['sum', 'count'])
                        .sort_values('sum', ascending=False)
                        .rename(columns={'sum': 'Total', 'count': 'Cant'})
                    )
                    st.dataframe(ing_banco, use_container_width=True)

                st.subheader("Detalle de Ingresos")
                df_ing_f['monto_mostrar'] = df_ing_f.apply(
                    lambda r: f"${r['monto_convertido']:,.0f} (original: ${r['monto']:,.0f})" 
                    if r.get('monto_original_clp') and r.get('banco') == 'santander_chile' 
                    else f"${r['monto']:,.0f}", axis=1
                )
                cols_det = ['periodo', 'fecha', 'descripcion', 'monto_mostrar', 'monto_convertido', 'banco',
                            'categoria', 'owner', 'tipo_ingreso', 'monto_original_clp']
                cols_disp = [c for c in cols_det if c in df_ing_f.columns]
                st.dataframe(df_ing_f[cols_disp], use_container_width=True, hide_index=True)

                csv_ing = df_ing_f[['periodo', 'fecha', 'descripcion', 'monto_convertido', 'banco',
                            'categoria', 'owner', 'tipo_ingreso', 'monto_original_clp']].to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Descargar CSV Ingresos",
                    data=csv_ing,
                    file_name=f"ingresos_{periodo.replace(' ', '_')}.csv",
                    mime="text/csv"
                )

    with tab_egresos:
        df_eg = _colectar_egresos(datos, periodo)

        if df_eg.empty:
            st.warning(f"No hay egresos para {periodo}")
        else:
            total = df_eg['monto'].sum()
            cantidad = len(df_eg)
            promedio = df_eg['monto'].mean() if cantidad > 0 else 0
            maximo = df_eg['monto'].max() if cantidad > 0 else 0

            st.subheader("Resumen de Egresos")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Egresos", f"${total:,.2f}")
            m2.metric("Cantidad", f"{cantidad}")
            m3.metric("Ticket Promedio", f"${promedio:,.2f}")
            m4.metric("Gasto Maximo", f"${maximo:,.2f}")

            st.subheader("Filtros")
            c1, c2, c3 = st.columns(3)

            with c1:
                owners = ["Todos"] + sorted([str(x) for x in df_eg['owner'].dropna().unique() if str(x).strip()])
                filtro_owner = st.selectbox("Owner", owners, index=0, key="rep_owner")
            with c2:
                medios = ["Todos"] + sorted([str(x) for x in df_eg['medio_pago'].dropna().unique() if str(x).strip()])
                filtro_medio = st.selectbox("Medio de pago", medios, index=0, key="rep_medio")
            with c3:
                cats = ["Todos"] + sorted([str(x) for x in df_eg['categoria'].dropna().unique() if str(x).strip()])
                filtro_cat = st.selectbox("Categoria", cats, index=0, key="rep_cat")

            df_f = df_eg.copy()
            if filtro_owner != "Todos":
                df_f = df_f[df_f['owner'] == filtro_owner]
            if filtro_medio != "Todos":
                df_f = df_f[df_f['medio_pago'] == filtro_medio]
            if filtro_cat != "Todos":
                df_f = df_f[df_f['categoria'] == filtro_cat]

            if df_f.empty:
                st.info("No hay datos con los filtros seleccionados")
            else:
                st.subheader("Por Fuente")
                if 'fuente' in df_f.columns:
                    serie_fuente = df_f.groupby('fuente', dropna=False)['monto'].agg(['sum', 'count'])
                    serie_fuente.columns = ['Total', 'Cantidad']
                    st.dataframe(serie_fuente.sort_values('Total', ascending=False), use_container_width=True)

                st.subheader("Distribuciones")
                g1, g2 = st.columns(2)
                with g1:
                    st.caption("Por categoria")
                    serie_cat = df_f.groupby('categoria', dropna=False)['monto'].sum().sort_values(ascending=False)
                    st.bar_chart(serie_cat)
                with g2:
                    st.caption("Por medio-owner")
                    serie_medio = df_f.groupby('medio_owner', dropna=False)['monto'].sum().sort_values(ascending=False)
                    st.bar_chart(serie_medio)

                st.subheader("Tablas Dinamicas")
                st.caption("Gasto vs Medio-Owner")
                pivot_gasto = pd.pivot_table(df_f, values='monto', index='gasto', columns='medio_owner', aggfunc='sum', fill_value=0)
                st.dataframe(pivot_gasto, use_container_width=True)

                st.caption("Categoria vs Medio-Owner")
                pivot_cat = pd.pivot_table(df_f, values='monto', index='categoria', columns='medio_owner', aggfunc='sum', fill_value=0)
                st.dataframe(pivot_cat, use_container_width=True)

                st.subheader("Rankings")
                r1, r2, r3 = st.columns(3)
                with r1:
                    st.caption("Por gasto")
                    gasto_s = df_f.groupby(['gasto', 'fecha', 'monto'], dropna=False).size().reset_index(name='Cant')
                    gasto_s = gasto_s.rename(columns={'gasto': 'Gasto', 'fecha': 'Fecha', 'monto': 'Total'})
                    st.dataframe(gasto_s.sort_values('Total', ascending=False), use_container_width=True, hide_index=True)
                with r2:
                    st.caption("Por categoria")
                    cat_s = df_f.groupby('categoria', dropna=False)['monto'].agg(['sum', 'count']).sort_values('sum', ascending=False)
                    cat_s.columns = ['Total', 'Cant']
                    st.dataframe(cat_s, use_container_width=True)
                with r3:
                    st.caption("Por medio-owner")
                    med_s = df_f.groupby('medio_owner', dropna=False)['monto'].agg(['sum', 'count']).sort_values('sum', ascending=False)
                    med_s.columns = ['Total', 'Cant']
                    st.dataframe(med_s, use_container_width=True)

                st.subheader("Detalle")
                cols_det = ['periodo', 'fecha', 'gasto', 'monto', 'categoria', 'subcategoria', 'owner', 'medio_pago', 'fuente']
                cols_disp = [c for c in cols_det if c in df_f.columns]
                st.dataframe(df_f[cols_disp], use_container_width=True, hide_index=True)

                csv_eg = df_f[cols_disp].to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Descargar CSV Egresos",
                    data=csv_eg,
                    file_name=f"egresos_{periodo.replace(' ', '_')}.csv",
                    mime="text/csv"
                )

    with tab_balance:
        df_ing = _colectar_ingresos(datos, periodo)
        df_eg = _colectar_egresos(datos, periodo)

        # Convertir CLP a ARS en ingresos
        if not df_ing.empty:
            df_ing['monto_convertido'] = df_ing.apply(
                lambda row: _convertir_ingreso_clp_a_ars(row, periodo), axis=1
            )
        else:
            df_ing['monto_convertido'] = []

        total_ingresos = df_ing['monto_convertido'].sum() if not df_ing.empty else 0
        total_egresos = df_eg['monto'].sum() if not df_eg.empty else 0
        balance = total_ingresos - total_egresos

        st.subheader(f"Balance - {periodo}")

        b1, b2, b3 = st.columns(3)
        b1.metric("Total Ingresos", f"${total_ingresos:,.0f}")
        b2.metric("Total Egresos", f"${total_egresos:,.0f}")
        b3.metric(
            "Balance",
            f"${balance:,.0f}",
            delta=f"${balance:,.0f}",
            delta_color="normal"
        )

        if periodo == "Todos los periodos" and meses:
            st.subheader("Balance por Periodo")

            balance_data = []
            for m in sorted(datos.get('meses', {}).keys()):
                mes_data = datos['meses'][m]

                # Convertir ingresos a ARS usando tasa de fecha
                ing_bancarios_ars = 0
                for i in mes_data.get('ingresos_bancarios', []):
                    ing = dict(i)
                    ing['periodo'] = m
                    ing_bancarios_ars += _convertir_ingreso_clp_a_ars(ing, m)

                gan_fondos = mes_data.get('ganancia_fondos', 0) or 0
                plusv_prop = mes_data.get('plusvalia_propiedades', 0) or 0
                plusv_adrs = mes_data.get('plusvalia_adrs', 0) or 0
                ajustes_pos = sum(a.get('monto', 0) for a in mes_data.get('ajustes', []) if a.get('monto', 0) > 0)
                total_ing_mes = ing_bancarios_ars + gan_fondos + plusv_prop + plusv_adrs + ajustes_pos

                total_eg_mes = sum(e.get('monto', 0) for e in mes_data.get('egresos', []))
                balance_mes = total_ing_mes - total_eg_mes

                balance_data.append({
                    'Periodo': m,
                    'Ingresos': total_ing_mes,
                    'Egresos': total_eg_mes,
                    'Balance': balance_mes
                })

            if balance_data:
                df_balance = pd.DataFrame(balance_data)
                st.dataframe(df_balance, use_container_width=True, hide_index=True)

                st.caption("Balance mensual")
                chart_data = df_balance.set_index('Periodo')[['Ingresos', 'Egresos']]
                st.bar_chart(chart_data)

        if not df_ing.empty and not df_eg.empty:
            st.subheader("Composicion")

            comp1, comp2 = st.columns(2)

            with comp1:
                st.caption("Ingresos por tipo")
                if 'tipo_ingreso' in df_ing.columns and 'monto_convertido' in df_ing.columns:
                    comp_ing = df_ing.groupby('tipo_ingreso', dropna=False)['monto_convertido'].sum().sort_values(ascending=False)
                    st.bar_chart(comp_ing)

            with comp2:
                st.caption("Egresos por categoria")
                if 'categoria' in df_eg.columns:
                    comp_eg = df_eg.groupby('categoria', dropna=False)['monto'].sum().sort_values(ascending=False)
                    st.bar_chart(comp_eg)

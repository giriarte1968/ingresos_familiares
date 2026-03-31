import os
import json
import pandas as pd
import streamlit as st

DATOS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "datos.json"
)


def cargar_datos():
    """Usa la misma fuente que egresos: session_state primero, disco fallback"""
    if 'datos' in st.session_state and isinstance(st.session_state.datos, dict):
        # Verificar que tiene contenido
        meses = st.session_state.datos.get('meses', {})
        total = sum(len(m.get('egresos', [])) for m in meses.values())
        if total > 0:
            return st.session_state.datos

    # Fallback: disco
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

    return {'meses': {}}


def _obtener_meses_ordenados(datos):
    meses = list(datos.get("meses", {}).keys())
    meses = [m for m in meses if isinstance(m, str) and len(m) >= 7]
    return sorted(meses, reverse=True)


def _colectar_egresos(datos, periodo):
    """
    Retorna DataFrame de egresos:
    - periodo = "Todos los periodos" => concatena todo
    - periodo = "YYYY-MM" => solo ese mes
    """
    meses_data = datos.get("meses", {})

    registros = []
    if periodo == "Todos los periodos":
        for mes, mes_data in meses_data.items():
            for e in mes_data.get("egresos", []):
                row = dict(e)
                row["periodo"] = mes
                registros.append(row)
    else:
        for e in meses_data.get(periodo, {}).get("egresos", []):
            row = dict(e)
            row["periodo"] = periodo
            registros.append(row)

    if not registros:
        return pd.DataFrame()

    df = pd.DataFrame(registros)

    # Normalizar columnas esperadas
    for col in [
        "fecha", "gasto", "monto", "moneda", "fuente",
        "categoria", "subcategoria", "owner", "medio_pago", "u_id", "periodo"
    ]:
        if col not in df.columns:
            df[col] = ""

    # Monto numérico seguro
    df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0.0)
    df["medio_owner"] = df["medio_pago"].astype(str) + " - " + df["owner"].astype(str)

    return df


def mostrar_reportes(mes_preseleccionado=None):
    st.header("Reportes")

    datos = cargar_datos()
    meses = _obtener_meses_ordenados(datos)

    if not meses:
        st.info("No hay períodos cargados en datos.json")
        return

    # Selector de periodo siempre visible
    opciones_periodo = ["Todos los periodos"] + meses

    if mes_preseleccionado in meses:
        default_index = opciones_periodo.index(mes_preseleccionado)
    else:
        default_index = 0  # "Todos los periodos"

    periodo = st.selectbox(
        "Seleccionar período",
        opciones_periodo,
        index=default_index,
        key="reporte_periodo_selector"
    )

    df = _colectar_egresos(datos, periodo)

    if df.empty:
        st.warning(f"No hay egresos para el período seleccionado: {periodo}")
        return

    # Filtros
    st.subheader("Filtros")

    c1, c2, c3 = st.columns(3)

    with c1:
        owners = ["Todos"] + sorted([str(x) for x in df["owner"].dropna().unique() if str(x).strip()])
        filtro_owner = st.selectbox("Owner", owners, index=0, key="rep_owner")

    with c2:
        medios = ["Todos"] + sorted([str(x) for x in df["medio_pago"].dropna().unique() if str(x).strip()])
        filtro_medio = st.selectbox("Medio de pago", medios, index=0, key="rep_medio")

    with c3:
        cats = ["Todos"] + sorted([str(x) for x in df["categoria"].dropna().unique() if str(x).strip()])
        filtro_cat = st.selectbox("Categoría", cats, index=0, key="rep_cat")

    df_filtrado = df.copy()

    if filtro_owner != "Todos":
        df_filtrado = df_filtrado[df_filtrado["owner"] == filtro_owner]

    if filtro_medio != "Todos":
        df_filtrado = df_filtrado[df_filtrado["medio_pago"] == filtro_medio]

    if filtro_cat != "Todos":
        df_filtrado = df_filtrado[df_filtrado["categoria"] == filtro_cat]

    if df_filtrado.empty:
        st.info("No hay datos con los filtros seleccionados.")
        return

    # Métricas
    st.subheader("Resumen")
    total = df_filtrado["monto"].sum()
    cantidad = len(df_filtrado)
    promedio = df_filtrado["monto"].mean() if cantidad > 0 else 0
    maximo = df_filtrado["monto"].max() if cantidad > 0 else 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Egresos", f"${total:,.2f}")
    m2.metric("Cantidad Movimientos", f"{cantidad}")
    m3.metric("Ticket Promedio", f"${promedio:,.2f}")
    m4.metric("Gasto Máximo", f"${maximo:,.2f}")

    # Gráficos simples
    st.subheader("Distribuciones")

    g1, g2 = st.columns(2)

    with g1:
        st.caption("Total por categoría")
        serie_cat = df_filtrado.groupby("categoria", dropna=False)["monto"].sum().sort_values(ascending=False)
        st.bar_chart(serie_cat)

    with g2:
        st.caption("Total por medio de pago + owner")
        serie_medio_owner = df_filtrado.groupby("medio_owner", dropna=False)["monto"].sum().sort_values(ascending=False)
        st.bar_chart(serie_medio_owner)

    # Pivots
    st.subheader("Tablas Dinámicas")

    st.caption("Gasto vs Medio de Pago + Owner")
    pivot_gasto = pd.pivot_table(
        df_filtrado,
        values="monto",
        index="gasto",
        columns="medio_owner",
        aggfunc="sum",
        fill_value=0
    )
    st.dataframe(pivot_gasto, use_container_width=True)

    st.caption("Categoría vs Medio de Pago + Owner")
    pivot_cat = pd.pivot_table(
        df_filtrado,
        values="monto",
        index="categoria",
        columns="medio_owner",
        aggfunc="sum",
        fill_value=0
    )
    st.dataframe(pivot_cat, use_container_width=True)

    # Rankings
    st.subheader("Rankings")
    r1, r2, r3 = st.columns(3)

    with r1:
        st.caption("Por gasto + fecha")
        gasto_summary = (
            df_filtrado.groupby(['gasto', 'fecha'], dropna=False)['monto']
            .agg(['sum', 'count'])
            .sort_values('sum', ascending=False)
            .rename(columns={'sum': 'Total', 'count': 'Cantidad'})
        )
        st.dataframe(gasto_summary, use_container_width=True)

    with r2:
        st.caption("Por categoría")
        cat_summary = (
            df_filtrado.groupby("categoria", dropna=False)["monto"]
            .agg(["sum", "count"])
            .sort_values("sum", ascending=False)
            .rename(columns={"sum": "Total", "count": "Cantidad"})
        )
        st.dataframe(cat_summary, use_container_width=True)

    with r3:
        st.caption("Por medio-owner")
        medio_summary = (
            df_filtrado.groupby("medio_owner", dropna=False)["monto"]
            .agg(["sum", "count"])
            .sort_values("sum", ascending=False)
            .rename(columns={"sum": "Total", "count": "Cantidad"})
        )
        st.dataframe(medio_summary, use_container_width=True)

    # Detalle + export
    st.subheader("Detalle")
    cols_detalle = [
        "periodo", "fecha", "gasto", "monto", "categoria",
        "subcategoria", "owner", "medio_pago", "fuente", "u_id"
    ]
    st.dataframe(df_filtrado[cols_detalle], use_container_width=True)

    csv_bytes = df_filtrado[cols_detalle].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Descargar CSV (reporte filtrado)",
        data=csv_bytes,
        file_name=f"reporte_egresos_{periodo.replace(' ', '_')}.csv",
        mime="text/csv"
    )
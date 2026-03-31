import streamlit as st
import pandas as pd
import json
import os

DATOS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'datos.json')

def cargar_datos():
    try:
        if os.path.exists(DATOS_FILE):
            with open(DATOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error cargando datos: {e}")
    return {'meses': {}}

def mostrar_reportes(mes):
    st.header(f"Reportes - {mes}")
    
    datos = cargar_datos()
    mes_data = datos.get('meses', {}).get(mes, {})
    egresos = mes_data.get('egresos', [])
    
    if not egresos:
        st.info("No hay egresos registrados para este mes")
        return
    
    df = pd.DataFrame(egresos)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Egresos", f"${df['monto'].sum():,.0f}")
    with col2:
        st.metric("Cantidad", len(df))
    
    df['medio_owner'] = df['medio_pago'].astype(str) + ' - ' + df['owner'].astype(str)
    
    st.subheader("Gasto vs Medio de Pago + Owner")
    pivot = pd.pivot_table(
        df,
        values='monto',
        index='gasto',
        columns='medio_owner',
        aggfunc='sum',
        fill_value=0
    )
    st.dataframe(pivot.style.format("${:,.0f}"))
    
    st.subheader("Categoría vs Medio de Pago + Owner")
    pivot_cat = pd.pivot_table(
        df,
        values='monto',
        index='categoria',
        columns='medio_owner',
        aggfunc='sum',
        fill_value=0
    )
    st.dataframe(pivot_cat.style.format("${:,.0f}"))
    
    st.subheader("Detalle por Gasto")
    gasto_summary = df.groupby('gasto')['monto'].agg(['sum', 'count']).sort_values('sum', ascending=False)
    gasto_summary.columns = ['Total', 'Cantidad']
    st.dataframe(gasto_summary.style.format("${:,.0f}"))
    
    st.subheader("Detalle por Categoría")
    cat_summary = df.groupby('categoria')['monto'].agg(['sum', 'count']).sort_values('sum', ascending=False)
    cat_summary.columns = ['Total', 'Cantidad']
    st.dataframe(cat_summary.style.format("${:,.0f}"))
    
    st.subheader("Detalle por Medio de Pago + Owner")
    medio_summary = df.groupby('medio_owner')['monto'].agg(['sum', 'count']).sort_values('sum', ascending=False)
    medio_summary.columns = ['Total', 'Cantidad']
    st.dataframe(medio_summary.style.format("${:,.0f}"))
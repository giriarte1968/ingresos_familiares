"""
Aplicación Streamlit - Sistema de Scraping Inmobiliario Rosario
================================================================
Interfaz gráfica para ejecutar y visualizar el scraping de inmobiliarias.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path
import json
import time
import sys

# Agregar el directorio actual al path para imports
sys.path.insert(0, str(Path(__file__).parent))

from config import INMOBILIARIAS, CARACTERISTICAS, SCRAPING_CONFIG
from scraper import InmobiliariaScraper
from main import ScrapingOrchestrator, get_available_inmobiliarias, load_latest_results
from utils import stats, save_json, generate_filename, ensure_dir


# =============================================================================
# CONFIGURACIÓN DE LA PÁGINA
# =============================================================================

st.set_page_config(
    page_title="Scraping Inmobiliario Rosario",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    .stProgress > div > div > div {
        background-color: #1f77b4;
    }
    .property-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

@st.cache_data(ttl=300)
def load_saved_results():
    """Carga resultados guardados en caché."""
    return load_latest_results()


def get_inmobiliarias_df():
    """Retorna DataFrame de inmobiliarias disponibles."""
    return pd.DataFrame([
        {"Nombre": i["nombre"], "URL": i["url"], "Activo": i.get("activo", True)}
        for i in INMOBILIARIAS
    ])


def properties_to_df(properties):
    """Convierte lista de propiedades a DataFrame."""
    if not properties:
        return pd.DataFrame()
    
    df = pd.DataFrame(properties)
    
    # Columnas principales a mostrar
    main_cols = [
        "titulo", "precio", "moneda", "tipo_propiedad", "ubicacion", "barrio",
        "superficie_total", "superficie_cubierta", "ambientes", "dormitorios",
        "banos", "antiguedad", "amenities", "fuente", "url_propiedad"
    ]
    
    # Filtrar solo columnas que existen
    cols_to_show = [c for c in main_cols if c in df.columns]
    
    return df[cols_to_show] if cols_to_show else df


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar():
    """Renderiza la barra lateral."""
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Bandera_de_Rosario.svg/1200px-Bandera_de_Rosario.svg.png", 
                 width=200)
        
        st.markdown("### 🏠 Configuración")
        
        # Seleccionar modo
        modo = st.radio(
            "Modo de operación:",
            ["📊 Ver Resultados", "🚀 Ejecutar Scraping", "⚙️ Configuración"],
            index=0
        )
        
        return modo


# =============================================================================
# PÁGINA: VER RESULTADOS
# =============================================================================

def render_results_page():
    """Renderiza la página de resultados."""
    st.markdown('<h1 class="main-header">📊 Resultados del Scraping</h1>', 
                unsafe_allow_html=True)
    
    # Cargar resultados
    results = load_saved_results()
    
    if not results:
        st.info("📭 No hay resultados guardados. Ejecuta el scraping primero.")
        return
    
    # Mostrar métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Propiedades",
            value=results.get("total_propiedades", 0)
        )
    
    with col2:
        st.metric(
            label="Inmobiliarias",
            value=len(results.get("inmobiliarias_incluidas", []))
        )
    
    with col3:
        fecha = results.get("fecha_extraccion", "N/A")
        if fecha != "N/A":
            fecha = datetime.fromisoformat(fecha).strftime("%d/%m/%Y %H:%M")
        st.metric(label="Última Actualización", value=fecha)
    
    with col4:
        props_por_inmo = results.get("propiedades_por_inmobiliaria", {})
        if props_por_inmo:
            max_inmo = max(props_por_inmo.items(), key=lambda x: x[1])
            st.metric(label="Top Inmobiliaria", value=max_inmo[0][:15] + "...")
    
    st.markdown("---")
    
    # Convertir a DataFrame
    properties = results.get("propiedades", [])
    df = properties_to_df(properties)
    
    if df.empty:
        st.warning("No hay propiedades para mostrar")
        return
    
    # Tabs para diferentes vistas
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Listado", "📈 Estadísticas", "🗺️ Por Ubicación", "🏢 Por Inmobiliaria"
    ])
    
    # Tab 1: Listado de propiedades
    with tab1:
        st.markdown("### 📋 Listado de Propiedades")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tipos = df["tipo_propiedad"].dropna().unique().tolist() if "tipo_propiedad" in df else []
            tipo_filtro = st.multiselect("Tipo de propiedad", tipos, default=tipos)
        
        with col2:
            fuentes = df["fuente"].dropna().unique().tolist() if "fuente" in df else []
            fuente_filtro = st.multiselect("Inmobiliaria", fuentes, default=fuentes)
        
        with col3:
            if "precio" in df.columns and not df["precio"].isna().all():
                precio_min = float(df["precio"].min())
                precio_max = float(df["precio"].max())
                precio_rango = st.slider(
                    "Rango de precio (USD)", 
                    precio_min, precio_max, 
                    (precio_min, precio_max)
                )
            else:
                precio_rango = None
        
        # Aplicar filtros
        df_filtrado = df.copy()
        
        if tipo_filtro and "tipo_propiedad" in df:
            df_filtrado = df_filtrado[df_filtrado["tipo_propiedad"].isin(tipo_filtro)]
        
        if fuente_filtro and "fuente" in df:
            df_filtrado = df_filtrado[df_filtrado["fuente"].isin(fuente_filtro)]
        
        if precio_rango and "precio" in df:
            df_filtrado = df_filtrado[
                (df_filtrado["precio"] >= precio_rango[0]) & 
                (df_filtrado["precio"] <= precio_rango[1])
            ]
        
        # Mostrar tabla
        st.dataframe(
            df_filtrado,
            use_container_width=True,
            hide_index=True,
            column_config={
                "url_propiedad": st.column_config.LinkColumn("Link"),
                "imagen_principal": st.column_config.ImageColumn("Imagen"),
                "precio": st.column_config.NumberColumn("Precio", format="%.0f"),
                "superficie_total": st.column_config.NumberColumn("m² Total"),
                "amenities": st.column_config.ListColumn("Amenities")
            }
        )
        
        # Descargar como CSV
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"propiedades_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # Tab 2: Estadísticas
    with tab2:
        st.markdown("### 📈 Estadísticas Generales")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribución por tipo de propiedad
            if "tipo_propiedad" in df:
                fig_tipo = px.pie(
                    df, 
                    names="tipo_propiedad", 
                    title="Distribución por Tipo de Propiedad"
                )
                st.plotly_chart(fig_tipo, use_container_width=True)
        
        with col2:
            # Distribución de precios
            if "precio" in df and not df["precio"].isna().all():
                fig_precio = px.histogram(
                    df[df["precio"].notna()], 
                    x="precio",
                    nbins=30,
                    title="Distribución de Precios"
                )
                st.plotly_chart(fig_precio, use_container_width=True)
        
        # Estadísticas adicionales
        col3, col4 = st.columns(2)
        
        with col3:
            # Distribución por ambientes
            if "ambientes" in df:
                df_amb = df["ambientes"].dropna().astype(int)
                if not df_amb.empty:
                    fig_amb = px.bar(
                        df_amb.value_counts().sort_index(),
                        title="Distribución por Ambientes"
                    )
                    st.plotly_chart(fig_amb, use_container_width=True)
        
        with col4:
            # Distribución por barrio
            if "barrio" in df:
                barrios = df["barrio"].dropna().value_counts().head(15)
                if not barrios.empty:
                    fig_barrio = px.bar(
                        barrios,
                        title="Top 15 Barrios"
                    )
                    st.plotly_chart(fig_barrio, use_container_width=True)
        
        # Métricas agregadas
        st.markdown("#### 📊 Métricas Agregadas")
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        
        with col_m1:
            if "precio" in df and not df["precio"].isna().all():
                st.metric("Precio Promedio (USD)", f"${df['precio'].mean():,.0f}")
        
        with col_m2:
            if "superficie_total" in df and not df["superficie_total"].isna().all():
                st.metric("m² Promedio", f"{df['superficie_total'].mean():.0f}")
        
        with col_m3:
            if "ambientes" in df and not df["ambientes"].isna().all():
                st.metric("Ambientes Promedio", f"{df['ambientes'].mean():.1f}")
        
        with col_m4:
            if "antiguedad" in df and not df["antiguedad"].isna().all():
                st.metric("Antigüedad Promedio (años)", f"{df['antiguedad'].mean():.0f}")
    
    # Tab 3: Por ubicación
    with tab3:
        st.markdown("### 🗺️ Análisis por Ubicación")
        
        if "barrio" in df:
            # Heatmap de precios por barrio
            precio_por_barrio = df.groupby("barrio").agg({
                "precio": ["mean", "min", "max", "count"]
            }).round(0)
            
            precio_por_barrio.columns = ["Precio Promedio", "Precio Mín", "Precio Máx", "Cantidad"]
            precio_por_barrio = precio_por_barrio.sort_values("Cantidad", ascending=False)
            
            st.dataframe(precio_por_barrio.head(20), use_container_width=True)
            
            # Gráfico de dispersión precio vs superficie
            if "superficie_total" in df and "precio" in df:
                df_scatter = df.dropna(subset=["superficie_total", "precio"])
                if not df_scatter.empty:
                    fig_scatter = px.scatter(
                        df_scatter,
                        x="superficie_total",
                        y="precio",
                        color="barrio",
                        hover_data=["titulo"],
                        title="Precio vs Superficie por Barrio"
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("No hay datos de ubicación disponibles")
    
    # Tab 4: Por inmobiliaria
    with tab4:
        st.markdown("### 🏢 Análisis por Inmobiliaria")
        
        # Propiedades por inmobiliaria
        props_por_inmo = results.get("propiedades_por_inmobiliaria", {})
        
        if props_por_inmo:
            fig_inmo = px.bar(
                x=list(props_por_inmo.keys()),
                y=list(props_por_inmo.values()),
                title="Propiedades por Inmobiliaria",
                labels={"x": "Inmobiliaria", "y": "Cantidad"}
            )
            fig_inmo.update_xaxes(tickangle=45)
            st.plotly_chart(fig_inmo, use_container_width=True)
        
        # Tabla detallada por inmobiliaria
        if "fuente" in df:
            analisis_inmo = df.groupby("fuente").agg({
                "precio": ["mean", "min", "max"],
                "superficie_total": "mean"
            }).round(0)
            
            analisis_inmo.columns = ["Precio Prom", "Precio Min", "Precio Max", "m² Prom"]
            st.dataframe(analisis_inmo, use_container_width=True)


# =============================================================================
# PÁGINA: EJECUTAR SCRAPING
# =============================================================================

def render_scraping_page():
    """Renderiza la página para ejecutar scraping."""
    st.markdown('<h1 class="main-header">🚀 Ejecutar Scraping</h1>', 
                unsafe_allow_html=True)
    
    # Configuración del scraping
    st.markdown("### ⚙️ Configuración")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Selección de inmobiliarias
        st.markdown("#### Inmobiliarias a procesar")
        
        seleccion = st.radio(
            "Modo de selección:",
            ["Todas las activas", "Selección manual", "Top N"]
        )
        
        inmobiliarias_seleccionadas = []
        
        if seleccion == "Todas las activas":
            inmobiliarias_seleccionadas = [i for i in INMOBILIARIAS if i.get("activo", True)]
        
        elif seleccion == "Selección manual":
            opciones = {i["nombre"]: i for i in INMOBILIARIAS if i.get("activo", True)}
            seleccionadas = st.multiselect(
                "Selecciona inmobiliarias:",
                list(opciones.keys()),
                default=list(opciones.keys())[:5]
            )
            inmobiliarias_seleccionadas = [opciones[s] for s in seleccionadas]
        
        else:  # Top N
            n = st.slider("Número de inmobiliarias:", 1, 50, 10)
            inmobiliarias_seleccionadas = [
                i for i in INMOBILIARIAS if i.get("activo", True)
            ][:n]
        
        st.info(f"📊 {len(inmobiliarias_seleccionadas)} inmobiliarias seleccionadas")
    
    with col2:
        # Parámetros de scraping
        st.markdown("#### Parámetros de Scraping")
        
        max_pages = st.slider(
            "Máximo de páginas por inmobiliaria:",
            1, 20, 5
        )
        
        use_selenium = st.checkbox(
            "Usar Selenium (para sitios con JavaScript)",
            value=False
        )
        
        concurrent = st.checkbox(
            "Ejecutar en paralelo",
            value=True
        )
        
        max_workers = st.slider(
            "Workers concurrentes:",
            1, 10, 3
        ) if concurrent else 1
    
    # Mostrar lista de inmobiliarias
    with st.expander("📋 Ver inmobiliarias seleccionadas"):
        df_inmo = pd.DataFrame([
            {"Nombre": i["nombre"], "URL": i["url"]}
            for i in inmobiliarias_seleccionadas
        ])
        st.dataframe(df_inmo, use_container_width=True, hide_index=True)
    
    # Botón para ejecutar
    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    
    with col_btn2:
        ejecutar = st.button(
            "🚀 INICIAR SCRAPING",
            type="primary",
            use_container_width=True
        )
    
    if ejecutar:
        if not inmobiliarias_seleccionadas:
            st.error("❌ Debes seleccionar al menos una inmobiliaria")
            return
        
        # Crear placeholders para progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        metrics_placeholder = st.empty()
        
        # Ejecutar scraping
        try:
            orchestrator = ScrapingOrchestrator()
            
            total = len(inmobiliarias_seleccionadas)
            
            # Callback para actualizar progreso
            def update_progress(current, total, nombre):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"Procesando: {nombre} ({current}/{total})")
                
                # Actualizar métricas
                with metrics_placeholder.container():
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Procesadas", current)
                    col2.metric("Propiedades", len(orchestrator.all_properties))
                    col3.metric("Errores", len(orchestrator.errors))
            
            # Ejecutar
            status_text.text("Iniciando scraping...")
            
            summary = orchestrator.run(
                inmobiliarias=inmobiliarias_seleccionadas,
                max_pages_per_site=max_pages,
                use_selenium=use_selenium,
                concurrent=concurrent,
                max_workers=max_workers
            )
            
            progress_bar.progress(1.0)
            
            # Mostrar resultados
            st.success("✅ Scraping completado exitosamente!")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Propiedades", summary["total_properties"])
            col2.metric("Tiempo (seg)", summary["elapsed_seconds"])
            col3.metric("Errores", summary["errors_count"])
            col4.metric("Inmobiliarias", summary["inmobiliarias_processed"])
            
            # Mostrar errores si hay
            if summary["errors"]:
                with st.expander("⚠️ Ver errores"):
                    for error in summary["errors"]:
                        st.error(f"**{error['inmobiliaria']}**: {error['error']}")
            
            # Botón para ver resultados
            if st.button("📊 Ver Resultados"):
                st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error durante el scraping: {str(e)}")
            st.exception(e)


# =============================================================================
# PÁGINA: CONFIGURACIÓN
# =============================================================================

def render_config_page():
    """Renderiza la página de configuración."""
    st.markdown('<h1 class="main-header">⚙️ Configuración</h1>', 
                unsafe_allow_html=True)
    
    # Lista de inmobiliarias
    st.markdown("### 🏢 Inmobiliarias Disponibles")
    
    df = get_inmobiliarias_df()
    
    # Filtro
    search = st.text_input("🔍 Buscar inmobiliaria:")
    if search:
        df = df[df["Nombre"].str.contains(search, case=False)]
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "URL": st.column_config.LinkColumn("URL"),
            "Activo": st.column_config.CheckboxColumn("Activo")
        }
    )
    
    # Características extraídas
    st.markdown("### 📝 Características Extraídas")
    
    cols = st.columns(5)
    for i, carac in enumerate(CARACTERISTICAS):
        cols[i % 5].markdown(f"- {carac}")
    
    # Configuración de scraping
    st.markdown("### 🔧 Configuración de Scraping")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.json({
            "timeout": SCRAPING_CONFIG["timeout"],
            "min_delay": SCRAPING_CONFIG["min_delay"],
            "max_delay": SCRAPING_CONFIG["max_delay"],
            "max_retries": SCRAPING_CONFIG["max_retries"]
        })
    
    with col2:
        st.json({
            "max_concurrent": SCRAPING_CONFIG["max_concurrent"],
            "output_dir": SCRAPING_CONFIG["output_dir"]
        })
    
    # Información del sistema
    st.markdown("### ℹ️ Información del Sistema")
    
    try:
        from scraper import HAS_SELENIUM, HAS_UNDETECTED, HAS_LXML
        
        st.markdown(f"""
        - **Selenium disponible:** {'✅' if HAS_SELENIUM else '❌'}
        - **Undetected ChromeDriver:** {'✅' if HAS_UNDETECTED else '❌'}
        - **LXML Parser:** {'✅' if HAS_LXML else '❌'}
        """)
    except:
        st.warning("No se pudo verificar el estado de las dependencias")


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Función principal de la aplicación."""
    
    # Renderizar sidebar y obtener modo
    modo = render_sidebar()
    
    # Renderizar página según selección
    if modo == "📊 Ver Resultados":
        render_results_page()
    elif modo == "🚀 Ejecutar Scraping":
        render_scraping_page()
    else:
        render_config_page()


if __name__ == "__main__":
    main()

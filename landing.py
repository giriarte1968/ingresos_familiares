# landing.py
import streamlit as st
from landing_content import (
    get_landing_stats, get_hero_html, get_problem_html, get_how_html,
    get_features_html, get_example_html, get_target_html,
    get_trust_html, get_cta_html, get_footer_html, get_divider_edificios_html
)
from valu_design import LANDING_CSS

def mostrar_landing():
    # Ocultar sidebar de Streamlit y headers en la landing
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    .stApp > header { display: none; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding: 0 !important; max-width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

    # Inyectar CSS + tipografía
    st.markdown(LANDING_CSS, unsafe_allow_html=True)

    # Obtener stats dinámicos
    stats = get_landing_stats()

    # Renderizar secciones en orden usando funciones
    st.markdown(get_hero_html(stats), unsafe_allow_html=True)
    st.markdown(get_problem_html(), unsafe_allow_html=True)
    st.markdown(get_how_html(), unsafe_allow_html=True)
    st.markdown(get_features_html(), unsafe_allow_html=True)
    st.markdown(get_divider_edificios_html(), unsafe_allow_html=True)
    
    # Ejemplo real
    st.markdown(get_example_html(stats.get('ejemplo_propiedad', 'Mabel'), stats), unsafe_allow_html=True)
    
    st.markdown(get_target_html(), unsafe_allow_html=True)
    st.markdown(get_trust_html(), unsafe_allow_html=True)
    st.markdown(get_cta_html(), unsafe_allow_html=True)
    
    # Callback para el botón
    def ir_al_dashboard():
        st.session_state.vista_actual = 'dashboard'
        st.session_state.page = "Portfolio"
        
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='margin-top: -30px; margin-bottom: 40px;'></div>", unsafe_allow_html=True)
        st.button("🚀 Comenzar a Valuar Ahora", 
                  use_container_width=True, 
                  type="primary", 
                  key="main_cta",
                  on_click=ir_al_dashboard)

    st.markdown(get_footer_html(), unsafe_allow_html=True)


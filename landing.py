# landing.py
import streamlit as st
from landing_content import (
    get_landing_stats, get_hero_html, get_problem_html, get_how_html,
    get_features_html, get_target_html,
    get_trust_html, get_cta_html, get_footer_html, get_divider_edificios_html
)
from valu_design import LANDING_CSS

def mostrar_landing():
    # Transición: si venimos de un clic en CTA, mostrar spinner y redirigir
    if st.session_state.pop('_transition_clear', False):
        st.markdown("<div style='text-align:center;padding:80px 20px;color:#9CA3AF;font-family:Inter;font-size:18px;'>🔄 Cargando...</div>", unsafe_allow_html=True)
        st.session_state.vista_actual = 'dashboard'
        st.session_state.page = "Portfolio"
        st.rerun()
    
    # Ocultar sidebar de Streamlit y headers en la landing
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    .stApp > header { display: none; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding: 0 !important; max-width: 100% !important; }
    
    /* CTA button transparent with rounded border */
    div[data-testid="baseButton-primary"] {
        background: transparent !important;
        border: 2px solid white !important;
        border-radius: 50px !important;
        padding: 12px 32px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 17px !important;
        transition: all 0.3s ease !important;
        height: auto !important;
        color: white !important;
    }
    div[data-testid="baseButton-primary"]:hover {
        background: rgba(255,255,255,0.15) !important;
        transform: scale(1.03) !important;
    }
    div[data-testid="baseButton-primary"] p {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 17px !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Inyectar CSS + tipografía
    st.markdown(LANDING_CSS, unsafe_allow_html=True)

    # Obtener stats dinámicos
    stats = get_landing_stats()

    # Renderizar secciones en orden usando funciones
    st.markdown(get_hero_html(stats), unsafe_allow_html=True)
    
    # Callback para el botón
    def ir_al_dashboard():
        st.session_state._transition_clear = True
    
    # BOTÓN CTA — ARRIBA, visible sin scroll
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        st.button("🚀 Comenzar a Valuar Ahora", 
                  use_container_width=True, 
                  type="primary", 
                  key="main_cta",
                  on_click=ir_al_dashboard)
    
    st.markdown(get_problem_html(), unsafe_allow_html=True)
    st.markdown(get_how_html(), unsafe_allow_html=True)
    st.markdown(get_features_html(), unsafe_allow_html=True)
    st.markdown(get_divider_edificios_html(), unsafe_allow_html=True)
    
    st.markdown(get_target_html(), unsafe_allow_html=True)
    st.markdown(get_trust_html(), unsafe_allow_html=True)
    st.markdown(get_cta_html(), unsafe_allow_html=True)
    
    st.markdown(get_footer_html(), unsafe_allow_html=True)


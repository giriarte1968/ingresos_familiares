# landing.py
import streamlit as st
from landing_content import (
    get_landing_stats, get_hero_html, get_problem_html, get_how_html,
    get_deliverables_html, get_faq_html, get_features_html, get_target_html,
    get_trust_html, get_cta_html, get_footer_html, get_divider_edificios_html
)
from valu_design import LANDING_CSS

def mostrar_landing():
    # Transición: si venimos de un clic en CTA, mostrar overlay y redirigir
    if st.session_state.pop('_transition_clear', False):
        st.session_state._loading_overlay = True
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
    
    /* CTA button matching landing page look and feel (Emerald Green) */
    .stButton > button[kind="primary"] {
        background: #10b981 !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 16px 32px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 18px !important;
        transition: all 0.3s ease !important;
        height: auto !important;
        color: white !important;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #059669 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4) !important;
    }
    .stButton > button[kind="primary"] p {
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 18px !important;
        color: white !important;
    }

    [data-section] { scroll-margin-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

    # Inyectar CSS + tipografía
    st.markdown(LANDING_CSS, unsafe_allow_html=True)

    # Obtener stats dinámicos
    stats = get_landing_stats()

    # Renderizar secciones en orden usando funciones
    try:
        st.markdown(get_hero_html(stats), unsafe_allow_html=True)
    except Exception:
        st.markdown(f"""
        <div style="text-align:center;padding:80px 20px;color:white;background:#0f162a;font-family:Inter;">
            <h1 style="font-size:2.5rem;margin-bottom:16px;">Valu</h1>
            <p style="font-size:1.1rem;opacity:0.9;">Valuador Automático de Propiedades · Rosario</p>
        </div>
        """, unsafe_allow_html=True)
    
    # BOTÓN CTA — ARRIBA, visible sin scroll
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 Comenzar a Valuar Ahora", width='stretch', type="primary", key="main_cta"):
            st.session_state._transition_clear = True
            st.rerun()
    
    st.markdown(get_problem_html(), unsafe_allow_html=True)
    st.markdown(get_how_html(), unsafe_allow_html=True)
    st.markdown(get_deliverables_html(), unsafe_allow_html=True)
    st.markdown(get_features_html(), unsafe_allow_html=True)
    st.markdown(get_divider_edificios_html(), unsafe_allow_html=True)
    
    st.markdown(get_target_html(), unsafe_allow_html=True)
    st.markdown(get_faq_html(), unsafe_allow_html=True)
    st.markdown(get_trust_html(), unsafe_allow_html=True)
    st.markdown(get_cta_html(), unsafe_allow_html=True)
    
    st.markdown(get_footer_html(), unsafe_allow_html=True)

    st.markdown("""
<script>
(function() {
  if (window.__keyNavInit) return;
  window.__keyNavInit = true;

  function getTopSection(sections) {
    var best = 0, bestDist = Infinity;
    for (var i = 0; i < sections.length; i++) {
      var r = sections[i].getBoundingClientRect();
      var dist = Math.abs(r.top);
      if (dist < bestDist) { bestDist = dist; best = i; }
    }
    return best;
  }

  var handler = function(e) {
    var key = e.key;
    if (key !== 'PageDown' && key !== 'PageUp' && key !== 'Home' && key !== 'End') return;
    var t = (e.target || e.srcElement).tagName;
    if (t === 'INPUT' || t === 'TEXTAREA' || t === 'SELECT') return;
    var sections = Array.from(document.querySelectorAll('[data-section]'));
    if (!sections.length) return;
    e.preventDefault();
    if (key === 'Home') { sections[0].scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
    if (key === 'End') { sections[sections.length - 1].scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
    var cur = getTopSection(sections);
    var tgt = (key === 'PageDown') ? Math.min(cur + 1, sections.length - 1) : Math.max(cur - 1, 0);
    if (tgt !== cur) sections[tgt].scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { window.addEventListener('keydown', handler); });
  } else {
    window.addEventListener('keydown', handler);
  }
})();
</script>
""", unsafe_allow_html=True)


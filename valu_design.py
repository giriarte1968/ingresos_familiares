"""Valu Design System — CSS y componentes HTML premium estilo Zillow."""

VALU_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

/* Sidebar dark navy */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0F1629 0%, #1A2340 100%) !important; }
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label { color: rgba(255,255,255,0.50) !important; font-size: 10px !important; text-transform: uppercase !important; letter-spacing: 1.2px !important; }
[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
[data-testid="stSidebar"] .stRadio > div > label { background: transparent !important; border-radius: 8px !important; padding: 8px 12px !important; transition: all 0.2s ease !important; border-left: 3px solid transparent !important; }
[data-testid="stSidebar"] .stRadio > div > label:hover { background: rgba(255,255,255,0.06) !important; border-left-color: rgba(0,106,255,0.4) !important; }
[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
[data-testid="stSidebar"] .stRadio > div > label[aria-checked="true"] { background: rgba(0,106,255,0.15) !important; border-left-color: #006AFF !important; }
[data-testid="stSidebar"] .stSelectbox > div > div { background: rgba(255,255,255,0.07) !important; border: 1px solid rgba(255,255,255,0.12) !important; border-radius: 8px !important; }

/* Fondo de pagina */
.main .block-container { background-color: #F4F6FB; padding-top: 1.5rem; }

/* Ocultar header y footer default */
header[data-testid="stHeader"] { background: #0F1629 !important; }
.stDeployButton { display: none; }

/* Botones premium */
.stButton > button, .stLinkButton > a { border-radius: 12px !important; font-weight: 600 !important; transition: all 0.2s ease !important; }
.stButton > button:hover, .stLinkButton > a:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(16, 185, 129, 0.25) !important; }
.stButton > button[kind="primary"], .stLinkButton > a[kind="primary"] { background: #10b981 !important; border: none !important; color: white !important; }

/* Boton oscuro generico para detalle (reutilizable con clase) */
.detail-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 100%; padding: 0.55rem 1rem; border-radius: 12px;
    font-weight: 600; font-size: 0.9rem; text-decoration: none;
    background: #064e3b; color: white !important;
    border: 1px solid #065f46; box-sizing: border-box;
    transition: all 0.25s ease; cursor: pointer;
    line-height: 1.4; font-family: inherit;
    min-height: 2.6rem;
}
.detail-btn:hover {
    background: #059669; color: white !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(5, 150, 105, 0.35);
    text-decoration: none;
}

/* Botones primary de Streamlit (Volver, Editar, Revaluar) - mismas dimensiones que detail-btn */
.stButton > button[kind="primary"] {
    background: #064e3b !important; color: white !important;
    border: 1px solid #065f46 !important;
    padding: 0.55rem 1rem !important;
    font-size: 0.9rem !important;
    line-height: 1.4 !important;
    min-height: 2.6rem !important;
    height: auto !important;
}
.stButton > button[kind="primary"]:hover {
    background: #059669 !important; color: white !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(5, 150, 105, 0.35) !important;
}
.stButton > button[kind="primary"]:hover, .stLinkButton > a[kind="primary"]:hover { background: #34d399 !important; box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4) !important; }

/* Form submit buttons (Guardar Cambios, Cancelar) - mismo estilo dark green */
.stFormSubmitButton > button {
    background: #064e3b !important; color: white !important;
    border: 1px solid #065f46 !important;
    padding: 0.55rem 1rem !important;
    font-size: 0.9rem !important;
    line-height: 1.4 !important;
    min-height: 2.6rem !important;
    height: auto !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}
.stFormSubmitButton > button:hover {
    background: #059669 !important;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(5, 150, 105, 0.35) !important;
}

/* Expanders */
.streamlit-expanderHeader { font-weight: 600 !important; color: #1A2B5C !important; }

/* Steps v2 — rediseño centrado */
.steps-grid { position: relative; }
.step-card-v2 { text-align: center; padding: 32px 20px; position: relative; background: white; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.04); transition: box-shadow 0.3s ease; }
.step-card-v2:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.step-icon-circle { width: 72px; height: 72px; border-radius: 50%; background: #ecfdf5; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; }
.step-number-small { font-size: 14px; font-weight: 800; color: #10b981; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px; }
.step-number-small::before { content: 'PASO '; }
.step-title-v2 { font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 12px; }
.card-text { font-size: 0.85rem; color: #64748b; line-height: 1.5; }

@media (min-width: 769px) {
    .step-connector-wrapper { position: relative; }
    .step-connector-wrapper::before { content: ''; position: absolute; top: 68px; left: 20%; width: 60%; height: 2px; background: linear-gradient(to right, #10b981, #e2e8f0, #10b981); z-index: 0; }
    .step-card-v2 { position: relative; z-index: 1; }
}

/* Hero SVG illustration */
.hero-illustration { max-width: 800px; margin: 0 auto 24px; opacity: 0.6; }
.city-svg { width: 100%; height: auto; }

/* Example mini-map */
.example-map-mini { text-align: center; margin-bottom: 24px; }
.example-map-mini svg { max-width: 280px; width: 100%; }

/* Feature cards v2 */
.feature-card-v2 {
    padding: 22px 20px;
    position: relative;
    overflow: hidden;
}
.feature-card-v2::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 3px;
    background: linear-gradient(90deg, #006AFF, #10b981);
    opacity: 0.7;
}
.feature-icon-wrapper { width: 52px; height: 52px; border-radius: 14px; background: #ecfdf5; display: flex; align-items: center; justify-content: center; margin-bottom: 14px; }
.feature-icon-wrapper svg { width: 28px; height: 28px; }
.feature-title { color: #0f172a; font-weight: 800; margin-bottom: 6px; font-size: 1.02rem; letter-spacing: -0.01em; }

/* Hero with image background */
.hero-with-image {
    position: relative;
    background-image: url('https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=70&fm=webp');
    background-size: cover;
    background-position: center 40%;
    min-height: 600px;
}
.hero-overlay {
    background: linear-gradient(180deg, rgba(15, 22, 42, 0.70) 0%, rgba(15, 22, 42, 0.60) 50%, rgba(15, 22, 42, 0.80) 100%);
    padding: 80px 20px;
    min-height: 600px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.hero-content { text-align: center; max-width: 900px; margin: 0 auto; color: white; }
.hero-title { font-size: 2.5rem; font-weight: 800; margin-bottom: 20px; line-height: 1.2; }
.hero-sub { font-size: 1.1rem; opacity: 0.9; max-width: 700px; margin: 0 auto; }

/* Divider with image */
.landing-divider-image {
    background-image: url('https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=1200&q=70&fm=webp');
    background-size: cover;
    background-position: center;
    height: 250px;
}
.divider-overlay {
    background: rgba(15, 22, 42, 0.80);
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
}
.divider-stats { display: flex; gap: 80px; color: white; text-align: center; }
.divider-stat-number { font-size: 2.5rem; font-weight: 800; color: #10b981; }
.divider-stat-label { font-size: 0.9rem; opacity: 0.8; margin-top: 4px; }

/* Target cards with images */
.target-card-v2 { border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.04); transition: transform 0.3s ease, box-shadow 0.3s ease; }
.target-card-v2:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }
.target-image { height: 160px; background-size: cover; background-position: center; }
.target-card-content { padding: 24px; text-align: center; }

@media (max-width: 768px) {
    .hero-title { font-size: 1.8rem; }
    .divider-stats { flex-direction: column; gap: 24px; }
    .landing-divider-image { height: auto; padding: 40px 0; }
}
</style>
"""

def kpi_card(icon, title, value, subtitle, border_color="#006AFF"):
    return f"""
    <div style="background:white;border-radius:16px;padding:24px;box-shadow:0 4px 12px rgba(0,0,0,0.08);border-top:4px solid {border_color};font-family:'Inter',sans-serif;">
        <div style="font-size:28px;margin-bottom:8px;">{icon}</div>
        <div style="color:#6B7280;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.8px;">{title}</div>
        <div style="color:#1A2B5C;font-size:28px;font-weight:800;margin:8px 0 4px 0;line-height:1.1;">{value}</div>
        <div style="color:#9CA3AF;font-size:13px;">{subtitle}</div>
    </div>
    """

def property_card(nombre, zona, m2, dorms, tipo, valor_usd, cap_rate, alq_ars, n_comps, alq_min=0, alq_max=0, cache_info=''):
    tipo_color = "#006AFF" if "depart" in tipo.lower() else "#0D9488" if "casa" in tipo.lower() else "#7C3AED"
    dot_color = "#16A34A" if n_comps >= 15 else "#F59E0B" if n_comps >= 8 else "#DC2626"
    cache_line = f'<div style="color:#006AFF;font-size:11px;margin-bottom:8px;">{cache_info}</div>' if cache_info else ''
    
    if alq_min > 0 and alq_max > 0:
        alq_text = f"${alq_min:,.0f} - ${alq_max:,.0f}"
    else:
        alq_text = f"${alq_ars:,.0f}"

    return ('<div style="background:white;border-radius:16px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.07);border:1px solid #F0F0F5;font-family:\'Inter\',sans-serif;min-height:180px;box-sizing:border-box;width:100%;">'
            + (cache_line or '')
            + '<div style="margin-bottom:10px;">'
            + f'<span style="background:{tipo_color}15;color:{tipo_color};font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;text-transform:uppercase;letter-spacing:0.5px;">{tipo.upper()}</span>'
            + f'<span style="background:#0D948815;color:#0D9488;font-size:10px;font-weight:700;padding:3px 8px;border-radius:20px;text-transform:uppercase;letter-spacing:0.5px;margin-left:4px;">{zona.upper()}</span>'
            + '</div>'
            + '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">'
            + f'<strong style="color:#1A2B5C;font-size:16px;font-weight:700;word-wrap:break-word;">{nombre}</strong>'
            + f'<span style="width:10px;height:10px;border-radius:50%;background:{dot_color};display:inline-block;margin-top:4px;flex-shrink:0;"></span>'
            + '</div>'
            + f'<div style="color:#9CA3AF;font-size:12px;margin-bottom:12px;">{zona} · {m2:.0f}m² · {dorms}D</div>'
            + f'<div style="color:#1A2B5C;font-size:22px;font-weight:700;margin-bottom:4px;">${valor_usd:,.0f} <span style="font-size:13px;font-weight:500;">USD</span></div>'
            + f'<div style="color:#9CA3AF;font-size:12px;">Cap Rate: {cap_rate*100:.1f}% · Alq: {alq_text} ARS</div>'
            + '</div>')

def hero_price(valor_usd, valor_ars, dolar, m2_base, n_comps, zona):
    return f"""
    <div style="background:linear-gradient(135deg,#006AFF 0%,#004FC4 100%);border-radius:16px;padding:28px;color:white;font-family:'Inter',sans-serif;">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;opacity:0.8;margin-bottom:8px;">VALUACIÓN VPP</div>
        <div style="font-size:38px;font-weight:800;line-height:1.1;">$ {valor_usd:,.0f} <span style="font-size:18px;font-weight:500;">USD</span></div>
        <div style="font-size:16px;opacity:0.85;margin-top:4px;">${valor_ars:,.0f} ARS</div>
        <div style="font-size:12px;opacity:0.6;margin-top:12px;">Dólar ${dolar:,.0f} · m²/USD en {zona}: ${m2_base:,.0f} ({n_comps} comp.)</div>
    </div>
    """

def metric_card(icon, title, value, subtitle, border_color="#006AFF"):
    return f"""
    <div style="background:white;border-radius:12px;padding:20px;border-left:4px solid {border_color};box-shadow:0 2px 8px rgba(0,0,0,0.06);font-family:'Inter',sans-serif;">
        <div style="color:#6B7280;font-size:12px;font-weight:600;margin-bottom:8px;">{icon} {title}</div>
        <div style="color:#1A2B5C;font-size:22px;font-weight:700;margin-bottom:4px;">{value}</div>
        <div style="color:#9CA3AF;font-size:12px;">{subtitle}</div>
    </div>
    """

def insights_card(title, arguments):
    items_html = "".join([f'<li style="margin-bottom:8px;color:#4B5563;">• {arg}</li>' for arg in arguments])
    return f"""
    <div style="background:white;border-radius:16px;padding:24px;box-shadow:0 4px 12px rgba(0,0,0,0.08);border-left:4px solid #7C3AED;font-family:'Inter',sans-serif;">
        <div style="color:#7C3AED;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">🔍 Razonamiento de Valuación</div>
        <h3 style="color:#1A2B5C;margin:0 0 16px 0;font-size:18px;">{title}</h3>
        <ul style="list-style:none;padding:0;margin:0;font-size:14px;">
            {items_html}
        </ul>
        <div style="margin-top:16px;padding-top:12px;border-top:1px solid #F3F4F6;color:#9CA3AF;font-size:11px;">
            Este análisis se basa en el motor AVM v7 comparando atributos estructurales y geolocalización.
        </div>
    </div>
    """

def range_bar(v_cons, v_opt, spread):
    return f"""
    <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.06);font-family:'Inter',sans-serif;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <div><div style="color:#006AFF;font-size:18px;font-weight:700;">${v_cons:,.0f}</div><div style="color:#9CA3AF;font-size:11px;">Conservador</div></div>
            <div style="text-align:center;flex:1;margin:0 20px;">
                <div style="height:10px;border-radius:5px;background:linear-gradient(to right,#006AFF,#16A34A,#F59E0B);margin-bottom:6px;"></div>
                <span style="color:#9CA3AF;font-size:11px;">Spread {spread:.1f}%</span>
            </div>
            <div style="text-align:right;"><div style="color:#16A34A;font-size:18px;font-weight:700;">${v_opt:,.0f}</div><div style="color:#9CA3AF;font-size:11px;">Optimista</div></div>
        </div>
    </div>
    """

def form_section(title, color="#006AFF", icon="📍"):
    """Genera el HTML de apertura para una sección de formulario con estilo tarjeta."""
    return f"""
    <div style="background:white;border-radius:16px;padding:20px;margin:12px 0;border-left:4px solid {color};box-shadow:0 4px 12px rgba(0,0,0,0.08);font-family:'Inter',sans-serif;">
        <div style="color:{color};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:16px;">{icon} {title}</div>
    """


LANDING_HTML = """
<div style="text-align:center;padding:60px 20px;font-family:'Inter',sans-serif;">
    <div style="font-size:64px;margin-bottom:16px;">🏠</div>
    <h1 style="color:#1A2B5C;font-size:42px;font-weight:800;margin-bottom:8px;">Valu</h1>
    <p style="color:#6B7280;font-size:18px;margin-bottom:32px;">Valuador Automático de Propiedades · Rosario, Argentina</p>
    <div style="display:flex;justify-content:center;gap:32px;margin-bottom:48px;">
        <div style="text-align:center;">
            <div style="font-size:32px;">📊</div>
            <div style="color:#1A2B5C;font-weight:600;margin-top:8px;">Valuación AVM</div>
            <div style="color:#9CA3AF;font-size:13px;">Motor v7 con comparables</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:32px;">🗺️</div>
            <div style="color:#1A2B5C;font-weight:600;margin-top:8px;">Mapas Interactivos</div>
            <div style="color:#9CA3AF;font-size:13px;">Geolocalización precisa</div>
        </div>
        <div style="text-align:center;">
            <div style="font-size:32px;">💰</div>
            <div style="color:#1A2B5C;font-weight:600;margin-top:8px;">ROI & Cap Rate</div>
            <div style="color:#9CA3AF;font-size:13px;">Métricas de inversión</div>
        </div>
    </div>
    <p style="color:#9CA3AF;font-size:13px;">Seleccioná una opción del menú lateral para comenzar →</p>
</div>
"""

LANDING_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
    :root {
        --primary: #0f162a;
        --primary-light: #1a2332;
        --accent: #10b981;
        --accent-hover: #059669;
        --light-bg: #f8fafc;
        --text: #334155;
        --text-light: #64748b;
        --border: #e2e8f0;
        --warning-bg: #fffbeb;
        --warning-border: #f59e0b;
    }

    /* Landing Components */
    .landing-hero { 
        padding: 100px 20px; 
        background: var(--primary); 
        text-align: center; 
        color: white;
        font-family: 'Inter', sans-serif;
    }
    .landing-hero h1 { 
        font-size: 3.5rem; 
        font-weight: 800; 
        margin-bottom: 24px;
        line-height: 1.1;
    }
    
    .landing-section { 
        padding: 80px 20px; 
        max-width: 1100px; 
        margin: 0 auto;
        font-family: 'Inter', sans-serif;
    }
    .landing-section-alt { 
        background: var(--light-bg); 
    }
    
    .landing-card { 
        background: white; 
        border-radius: 16px; 
        padding: 24px 22px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.04);
        border: 1px solid var(--border);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .landing-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.10);
    }
    
    .landing-badge { 
        display: inline-block; 
        border: 1px solid var(--accent);
        border-radius: 20px; 
        padding: 6px 16px; 
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--accent); 
        margin-bottom: 24px; 
    }
    
    .landing-grid-3 { 
        display: grid; 
        grid-template-columns: repeat(3, 1fr); 
        gap: 32px; 
    }
    .landing-grid-2 { 
        display: grid; 
        grid-template-columns: repeat(2, 1fr); 
        gap: 32px; 
    }
    
    .landing-step-number { 
        font-size: 64px; 
        color: var(--accent); 
        font-weight: 800;
        opacity: 0.3;
        line-height: 1;
    }
    
    .landing-disclaimer { 
        border-left: 6px solid var(--warning-border);
        background: var(--warning-bg); 
        padding: 40px;
        border-radius: 0 16px 16px 0; 
    }
    
    .hero-with-image {
        position: relative;
        background-image: url('https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1200&q=70&fm=webp');
        background-size: cover;
        background-position: center 40%;
        min-height: 600px;
    }
    .hero-overlay {
        background: linear-gradient(180deg, rgba(15, 22, 42, 0.70) 0%, rgba(15, 22, 42, 0.60) 50%, rgba(15, 22, 42, 0.80) 100%);
        padding: 80px 20px;
        min-height: 600px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .hero-content { text-align: center; max-width: 900px; margin: 0 auto; color: white; }
    .hero-title { font-size: 2.5rem; font-weight: 800; margin-bottom: 20px; line-height: 1.2; }
    .hero-sub { font-size: 1.25rem; opacity: 0.9; max-width: 800px; margin: 0 auto 32px; }
    .landing-mockup { max-width: 500px; margin: 0 auto; }
    .mockup-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 24px; text-align: left; }
    .mockup-header { color: var(--accent); font-weight: 700; margin-bottom: 8px; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; }
    .mockup-price { font-size: 32px; font-weight: 800; margin-bottom: 4px; }
    .mockup-range { font-size: 14px; opacity: 0.7; }
    .mockup-bar { margin-top: 16px; height: 4px; background: #334155; border-radius: 2px; }
    .mockup-progress { width: 60%; height: 100%; background: var(--accent); border-radius: 2px; }
    .mockup-labels { display: flex; justify-content: space-between; font-size: 12px; margin-top: 8px; opacity: 0.6; }

    /* FAQ section */
    .faq-section { max-width: 800px; }
    .faq-grid { display: flex; flex-direction: column; gap: 24px; }
    .faq-item { background: white; border-radius: 16px; padding: 28px; border: 1px solid var(--border); text-align: left; }
    .faq-item h3 { font-size: 1.05rem; font-weight: 700; color: var(--primary); margin: 0 0 8px; }
    .faq-item p { font-size: 0.9rem; color: var(--text-light); margin: 0; line-height: 1.6; }

    /* Section shared styles */
    .section-kicker { color: var(--accent); font-weight: 700; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; text-align: center; }
    .section-title { font-size: 2rem; font-weight: 800; color: var(--primary); margin-bottom: 12px; text-align: center; }
    .section-subtitle { color: var(--text-light); font-size: 1.05rem; max-width: 600px; margin: 0 auto 40px; text-align: center; }

    /* Deliverables section */
    .deliverables-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
    .deliverable-card { background: white; border-radius: 16px; padding: 28px; border: 1px solid var(--border); text-align: center; transition: transform 0.2s ease, box-shadow 0.2s ease; }
    .deliverable-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
    .deliverable-icon { width: 48px; height: 48px; border-radius: 50%; background: #ecfdf5; color: var(--accent); font-size: 1.2rem; font-weight: 800; display: flex; align-items: center; justify-content: center; margin: 0 auto 16px; }
    .deliverable-card h3 { font-size: 1.1rem; font-weight: 700; color: var(--primary); margin: 0 0 8px; }
    .deliverable-card p { font-size: 0.9rem; color: var(--text-light); margin: 0; line-height: 1.5; }

    .landing-example { 
        background: white; 
        border: 2px solid var(--border);
        border-radius: 24px; 
        padding: 40px; 
        max-width: 700px; 
        margin: 0 auto;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }
    
    .landing-footer { 
        background: #0a0f1e; 
        color: white; 
        padding: 60px 20px;
        text-align: center;
        font-family: 'Inter', sans-serif;
    }

    /* Final CTA */
    .final-cta { background: var(--primary); padding: 80px 20px; text-align: center; color: white; font-family: 'Inter', sans-serif; }
    .final-cta-inner { max-width: 640px; margin: 0 auto; }
    .final-cta h2 { font-size: 2.2rem; font-weight: 800; margin-bottom: 16px; line-height: 1.2; }
    .final-cta p { font-size: 1.1rem; opacity: 0.85; margin-bottom: 20px; }
    .section-kicker-dark { color: var(--accent) !important; }
    .final-cta-note { font-size: 0.85rem; opacity: 0.5; letter-spacing: 0.5px; }

    @media (max-width: 768px) {
        .landing-grid-3, .landing-grid-2 { grid-template-columns: 1fr; }
        .landing-hero h1 { font-size: 2.2rem; }
        .landing-hero { padding: 60px 20px; }
        .landing-section { padding: 60px 20px; }
    }

    /* Landing premium refresh */
    .hero-premium {
        min-height: 660px;
    }

    .hero-overlay-premium {
        background:
            radial-gradient(circle at 80% 20%, rgba(16, 185, 129, 0.22), transparent 28%),
            linear-gradient(135deg, rgba(15, 22, 42, 0.88) 0%, rgba(15, 22, 42, 0.70) 48%, rgba(15, 22, 42, 0.88) 100%);
    }

    .hero-premium-grid {
        max-width: 1180px;
        width: 100%;
        display: grid;
        grid-template-columns: 1.15fr 0.85fr;
        gap: 48px;
        align-items: center;
    }

    .hero-copy {
        text-align: left;
    }

    .hero-title-premium {
        font-size: clamp(2.6rem, 5vw, 5rem);
        line-height: 0.98;
        letter-spacing: -0.055em;
        margin-bottom: 24px;
    }

    .hero-sub-premium {
        font-size: 1.18rem;
        line-height: 1.6;
        margin: 0 0 24px 0;
        max-width: 680px;
    }

    .hero-proof-row {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 24px;
    }

    .hero-proof-row span {
        background: rgba(255,255,255,0.10);
        border: 1px solid rgba(255,255,255,0.16);
        color: rgba(255,255,255,0.88);
        padding: 8px 12px;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
    }

    .hero-microcopy {
        margin-top: 18px;
        color: rgba(255,255,255,0.65);
        font-size: 0.9rem;
    }

    .hero-result-card {
        background: rgba(255,255,255,0.96);
        color: #0f172a;
        border-radius: 26px;
        padding: 28px;
        box-shadow: 0 28px 80px rgba(0,0,0,0.30);
        border: 1px solid rgba(255,255,255,0.40);
    }

    .result-card-top {
        display: flex;
        justify-content: space-between;
        gap: 18px;
        align-items: flex-start;
    }

    .result-eyebrow {
        color: #10b981;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-weight: 900;
    }

    .result-title {
        font-size: 1.45rem;
        font-weight: 900;
        margin-top: 4px;
    }

    .result-subtitle {
        color: #64748b;
        font-size: 0.9rem;
    }

    .result-badge {
        background: #dcfce7;
        color: #166534;
        border-radius: 999px;
        padding: 6px 10px;
        font-size: 0.78rem;
        font-weight: 900;
    }

    .result-main-price {
        font-size: 3rem;
        font-weight: 950;
        letter-spacing: -0.055em;
        color: #006AFF;
        margin-top: 30px;
    }

    .result-range {
        color: #64748b;
        font-size: 0.92rem;
    }

    .result-bar {
        height: 10px;
        background: #e2e8f0;
        border-radius: 999px;
        margin: 18px 0;
        overflow: hidden;
    }

    .result-bar-fill {
        width: 66%;
        height: 100%;
        background: linear-gradient(90deg, #006AFF, #10b981, #f59e0b);
        border-radius: 999px;
    }

    .result-metrics {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
    }

    .result-metrics div {
        background: #f8fafc;
        border-radius: 14px;
        padding: 12px;
    }

    .result-metrics span {
        display: block;
        color: #64748b;
        font-size: 0.75rem;
        margin-bottom: 5px;
    }

    .result-metrics strong {
        font-size: 0.95rem;
    }

    .trust-bar {
        background: white;
        border-bottom: 1px solid #e2e8f0;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
    }

    .trust-bar-inner {
        max-width: 1100px;
        margin: 0 auto;
        padding: 26px 20px;
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 18px;
        font-family: 'Inter', sans-serif;
    }

    .trust-item strong {
        display: block;
        color: #0f172a;
        font-size: 1.25rem;
        font-weight: 900;
    }

    .trust-item span {
        display: block;
        color: #64748b;
        font-size: 0.88rem;
        margin-top: 3px;
    }

    .section-kicker {
        text-align: center;
        color: #10b981;
        font-size: 0.78rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        margin-bottom: 10px;
    }

    .section-kicker-dark {
        color: #93f5c8;
    }

    .section-title {
        text-align: center;
        margin-bottom: 14px;
    }

    .section-subtitle {
        max-width: 720px;
        margin: 0 auto 38px auto;
        text-align: center;
        color: #64748b;
        line-height: 1.6;
    }

    .example-case-card {
        display: grid;
        grid-template-columns: 0.85fr 1.15fr;
        gap: 20px;
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 26px;
        padding: 20px;
        box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08);
    }

    .example-property-panel,
    .example-result-panel {
        border-radius: 20px;
        padding: 28px;
    }

    .example-property-panel {
        background: #0f172a;
        color: white;
    }

    .example-result-panel {
        background: #f8fafc;
    }

    .example-label {
        color: #10b981;
        font-size: 0.76rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 10px;
    }

    .example-property-panel h3 {
        font-size: 2rem;
        margin: 0 0 8px 0;
    }

    .example-property-panel p {
        color: rgba(255,255,255,0.72);
    }

    .example-attrs {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        margin-top: 32px;
    }

    .example-attrs div {
        background: rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 14px;
    }

    .example-attrs strong {
        display: block;
        font-size: 1.35rem;
    }

    .example-attrs span {
        color: rgba(255,255,255,0.68);
        font-size: 0.78rem;
    }

    .example-price {
        color: #006AFF;
        font-size: 3rem;
        font-weight: 950;
        letter-spacing: -0.055em;
    }

    .example-range {
        color: #64748b;
        margin-bottom: 22px;
    }

    .example-result-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
    }

    .example-result-grid div {
        background: white;
        border-radius: 16px;
        padding: 16px;
    }

    .example-result-grid span {
        color: #64748b;
        display: block;
        font-size: 0.82rem;
        margin-bottom: 6px;
    }

    .example-result-grid strong {
        color: #0f172a;
        font-size: 1.1rem;
    }

    .deliverables-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 18px;
    }

    .deliverable-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 26px;
        box-shadow: 0 10px 28px rgba(15,23,42,0.06);
    }

    .deliverable-icon {
        width: 38px;
        height: 38px;
        background: #dcfce7;
        color: #166534;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        margin-bottom: 18px;
    }

    .deliverable-card h3 {
        color: #0f172a;
        margin-bottom: 8px;
    }

    .deliverable-card p {
        color: #64748b;
        font-size: 0.94rem;
        line-height: 1.55;
    }

    .faq-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 18px;
    }

    .faq-item {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 8px 20px rgba(15,23,42,0.04);
    }

    .faq-item h3 {
        color: #0f172a;
        margin-bottom: 8px;
        font-size: 1.05rem;
    }

    .faq-item p {
        color: #64748b;
        line-height: 1.55;
        font-size: 0.94rem;
    }

    .final-cta {
        background:
            radial-gradient(circle at 20% 20%, rgba(16,185,129,0.22), transparent 30%),
            linear-gradient(135deg, #0f172a, #111827);
        color: white;
        padding: 90px 20px;
        text-align: center;
        font-family: 'Inter', sans-serif;
    }

    .final-cta-inner {
        max-width: 780px;
        margin: 0 auto;
    }

    .final-cta h2 {
        font-size: clamp(2rem, 4vw, 3.4rem);
        line-height: 1.05;
        letter-spacing: -0.045em;
        margin: 0 0 18px 0;
    }

    .final-cta p {
        color: rgba(255,255,255,0.76);
        font-size: 1.08rem;
        line-height: 1.6;
    }

    .final-cta-note {
        margin-top: 20px;
        color: rgba(255,255,255,0.58);
        font-size: 0.92rem;
    }

    @media (max-width: 900px) {
        .hero-premium-grid,
        .example-case-card {
            grid-template-columns: 1fr;
        }

        .hero-copy {
            text-align: center;
        }

        .hero-proof-row {
            justify-content: center;
        }

        .trust-bar-inner,
        .deliverables-grid {
            grid-template-columns: repeat(2, 1fr);
        }

        .result-metrics,
        .example-attrs {
            grid-template-columns: 1fr;
        }
    }

    @media (max-width: 640px) {
        .trust-bar-inner,
        .deliverables-grid,
        .faq-grid,
        .example-result-grid {
            grid-template-columns: 1fr;
        }

        .hero-result-card {
            padding: 20px;
        }

        .result-main-price,
        .example-price {
            font-size: 2.25rem;
        }
    }
</style>
"""

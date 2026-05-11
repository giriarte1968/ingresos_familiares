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
.stButton > button { border-radius: 10px !important; font-weight: 600 !important; transition: all 0.2s ease !important; }
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,106,255,0.25) !important; }
.stButton > button[kind="primary"] { background: linear-gradient(135deg, #006AFF, #004FC4) !important; border: none !important; }

/* Expanders */
.streamlit-expanderHeader { font-weight: 600 !important; color: #1A2B5C !important; }
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

    return f"""
    <div style="background:white;border-radius:16px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.07);border:1px solid #F0F0F5;font-family:'Inter',sans-serif;height:100%;transition:all 0.2s ease;">
        {cache_line}
        <div style="margin-bottom:12px;">
            <span style="background:{tipo_color}15;color:{tipo_color};font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;text-transform:uppercase;letter-spacing:0.5px;">{tipo.upper()}</span>
            <span style="background:#0D948815;color:#0D9488;font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px;text-transform:uppercase;letter-spacing:0.5px;margin-left:4px;">{zona.upper()}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:4px;">
            <strong style="color:#1A2B5C;font-size:17px;font-weight:700;">{nombre}</strong>
            <span style="width:10px;height:10px;border-radius:50%;background:{dot_color};display:inline-block;margin-top:4px;flex-shrink:0;"></span>
        </div>
        <div style="color:#9CA3AF;font-size:12px;margin-bottom:16px;">{zona} · {m2:.0f}m² · {dorms}D</div>
        <div style="color:#1A2B5C;font-size:24px;font-weight:700;margin-bottom:4px;">${valor_usd:,.0f} <span style="font-size:14px;font-weight:500;">USD</span></div>
        <div style="color:#9CA3AF;font-size:12px;margin-bottom:16px;">Cap Rate: {cap_rate*100:.1f}% · Alq: {alq_text} ARS</div>
        <div style="height:1px;background:#F0F0F5;"></div>
    </div>
    """

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

def form_section_close():
    """Cierra la sección del formulario."""
    return "</div>"


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

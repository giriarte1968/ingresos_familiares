import json
import os
from datetime import datetime

# ==========================================
# ESTADÍSTICAS DINÁMICAS
# ==========================================

def get_landing_stats() -> dict:
    """Obtiene estadísticas reales del sistema para el landing."""
    stats = {
        'fecha_ultimo_scraping': datetime.now().strftime('%Y-%m-%d'),
        'total_propiedades_scraping': 9766,
        'total_registros_catastro': 21130,
        'ejemplo_propiedad': 'Mabel',
        'dolar_actual': 1480.00,
        'ejemplo_valor_usd': 77139,
        'ejemplo_rango_min': 72000,
        'ejemplo_rango_max': 82000,
        'ejemplo_alquiler': 516000,
        'ejemplo_cap_rate': 5.4,
    }
    
    # Intentar cargar desde cache_scraping si existe
    try:
        cache_path = os.path.join(os.path.dirname(__file__), "cache_scraping.json")
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
                propiedades = cache.get('propiedades', [])
                if propiedades:
                    stats['total_propiedades_scraping'] = len(propiedades)
            
            # Fecha del archivo cache
            mtime = os.path.getmtime(cache_path)
            stats['fecha_ultimo_scraping'] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    except Exception:
        pass  # Usar defaults
        
    return stats


# ==========================================
# PLANTILLAS HTML
# ==========================================

def get_hero_html(stats: dict) -> str:
    return f"""
    <div class="hero-with-image">
        <div class="hero-overlay">
            <div class="hero-content">
                <div class="landing-badge">Datos de mercado actualizados · Rosario</div>
                <h1 class="hero-title">Sabé cuánto vale tu propiedad<br>en Rosario</h1>
                <p class="hero-sub">Valuación automática basada en más de <b>{stats['total_propiedades_scraping']:,}</b> propiedades reales del mercado. El estándar de datos para el mercado inmobiliario local.</p>
                <div class="landing-mockup">
                    <div class="mockup-card">
                        <div class="mockup-header">EJEMPLO DE RESULTADO</div>
                        <div class="mockup-price">USD {stats['ejemplo_valor_usd']:,}</div>
                        <div class="mockup-range">Rango: USD {stats['ejemplo_rango_min']:,} — {stats['ejemplo_rango_max']:,}</div>
                        <div class="mockup-bar">
                            <div class="mockup-progress"></div>
                        </div>
                        <div class="mockup-labels">
                            <span>Conservador</span>
                            <span>Optimista</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

def get_problem_html() -> str:
    return """
    <div class="landing-section">
        <h2 style="text-align: center; margin-bottom: 48px;">¿Cuánto vale realmente tu departamento?</h2>
        <div class="landing-grid-3">
            <div class="landing-card">
                <h3 style="font-size: 1.2rem; margin-bottom: 12px; color: #0f162a;">Las tasaciones tardan días</h3>
                <p style="color: #64748b; font-size: 0.95rem;">Pedir una tasación profesional lleva tiempo y muchas veces tiene un costo elevado antes de empezar a vender.</p>
            </div>
            <div class="landing-card">
                <h3 style="font-size: 1.2rem; margin-bottom: 12px; color: #0f162a;">Precios de lista inflados</h3>
                <p style="color: #64748b; font-size: 0.95rem;">Los portales muestran lo que los dueños piden, no lo que se vende. Esa brecha te hace perder meses sin consultas.</p>
            </div>
            <div class="landing-card">
                <h3 style="font-size: 1.2rem; margin-bottom: 12px; color: #0f162a;">Negociación a ciegas</h3>
                <p style="color: #64748b; font-size: 0.95rem;">Sin datos de comparables reales en tu misma zona, es imposible defender el valor de tu propiedad ante una oferta.</p>
            </div>
        </div>
        <div style="text-align: center; margin-top: 48px; font-weight: 600; color: #1e293b;">
            Valu analiza el mercado real y te da un rango de valor basado en propiedades similares en tu zona.
        </div>
    </div>
    """

def get_how_html() -> str:
    pasos = [
        {
            'numero': '1',
            'titulo': 'Cargá tu propiedad',
            'desc': 'Ingresá dirección, metros, dormitorios, año y estado. Cuantos más datos, más precisa la valuación.',
            'icon': '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="9" x2="15" y2="9"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="12" y2="17"/></svg>'
        },
        {
            'numero': '2',
            'titulo': 'Valu analiza el mercado',
            'desc': 'Nuestro motor busca comparables en un radio de 300m, ajusta por antigüedad y calidad, y calcula los escenarios.',
            'icon': '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/><line x1="11" y1="8" x2="11" y2="14"/></svg>'
        },
        {
            'numero': '3',
            'titulo': 'Recibí tu valuación',
            'desc': 'Obtené el valor de venta esperado, sugerencia de alquiler, Cap Rate y un informe narrativo detallado.',
            'icon': '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
        }
    ]
    cards = ''.join(
        '<div class="step-card-v2">'
        f'<div class="step-icon-circle">{p["icon"]}</div>'
        f'<div class="step-number-small">{p["numero"]}</div>'
        f'<h3 class="step-title-v2">{p["titulo"]}</h3>'
        f'<p class="card-text">{p["desc"]}</p>'
        '</div>'
        for p in pasos
    )
    return (
        '<div class="landing-section-alt">'
        '<div class="landing-section">'
        '<h2 class="section-title">Cómo funciona</h2>'
        '<div class="step-connector-wrapper">'
        f'<div class="landing-grid-3 steps-grid">{cards}</div>'
        '</div>'
        '</div>'
        '</div>'
    )

def get_features_html() -> str:
    features = [
        ("3 escenarios de precio",
         "No un número mágico, sino un rango: Conservador, Mercado y Optimista.",
         '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>'),
        ("Cap Rate del mercado",
         "Rendimiento anual neto calculado con datos de alquileres reales de la zona.",
         '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>'),
        ("Datos de Infomapa Rosario",
         "Conexión directa con la base de datos municipal: profesionales, planos oficiales y más.",
         '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>'),
        ("Planos de mensura oficiales",
         "Acceso con un click al PDF del plano de mensura original para verificar superficies.",
         '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>'),
        ("Transparencia total",
         "Ves exactamente cuántos comparables se usaron para llegar al precio final.",
         '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'),
        ("Informe profesional",
         "Texto narrativo que explica la valuación en lenguaje humano, listo para compartir.",
         '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>'),
        ("Historial de valores",
         "Seguimiento de cómo cambia el valor de tu propiedad mes a mes según el mercado.",
         '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'),
        ("USD y ARS siempre",
         "Conversión automática con dólar Binance actualizado para no perder referencia.",
         '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="1.5"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>'),
    ]
    cards = ''.join(
        f'<div class="landing-card feature-card-v2">'
        f'<div class="feature-icon-wrapper">{icon}</div>'
        f'<h4 class="feature-title">{titulo}</h4>'
        f'<p class="card-text">{desc}</p></div>'
        for titulo, desc, icon in features
    )
    return (
        '<div class="landing-section">'
        '<h2 style="text-align: center; margin-bottom: 48px;">Qué te da Valu</h2>'
        f'<div class="landing-grid-3">{cards}</div>'
        '</div>'
    )

def get_example_html(ejemplo_propiedad: str, stats: dict) -> str:
    # Tratar de valuar en tiempo real si existe la propiedad
    valor_usd = stats['ejemplo_valor_usd']
    min_usd = stats['ejemplo_rango_min']
    max_usd = stats['ejemplo_rango_max']
    alq = stats['ejemplo_alquiler']
    cap = stats['ejemplo_cap_rate']
    
    try:
        # Cargar propiedad
        props_path = os.path.join(os.path.dirname(__file__), "propiedades.json")
        if os.path.exists(props_path):
            with open(props_path, 'r', encoding='utf-8') as f:
                props = json.load(f)
            
            p_obj = next((p for p in props if p.get('nombre') == ejemplo_propiedad), None)
            if p_obj:
                from parsers.motor_vpp_core import valuar_con_cache
                res = valuar_con_cache(p_obj)
                
                if res and res.get('valor_propiedad_usd'):
                    valor_usd = int(res['valor_propiedad_usd'])
                    alq = int(res.get('alquiler_estimado_ars', alq))
                    cap = round(res.get('cap_rate', cap), 1)
                    rango_m = res.get('valor_rango', {})
                    if rango_m:
                        min_usd = int(rango_m.get('min', valor_usd*0.95))
                        max_usd = int(rango_m.get('max', valor_usd*1.05))
    except Exception:
        pass
        
    return f"""
    <div class="landing-section-alt">
        <div class="landing-section">
            <h2 style="text-align: center; margin-bottom: 48px;">Ejemplo real</h2>
            <div class="landing-example">
                <div class="example-map-mini">
                    <svg viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg">
                        <rect width="200" height="120" rx="8" fill="#f1f5f9"/>
                        <line x1="30" y1="0" x2="30" y2="120" stroke="#e2e8f0" stroke-width="0.5"/>
                        <line x1="80" y1="0" x2="80" y2="120" stroke="#e2e8f0" stroke-width="0.5"/>
                        <line x1="130" y1="0" x2="130" y2="120" stroke="#e2e8f0" stroke-width="0.5"/>
                        <line x1="180" y1="0" x2="180" y2="120" stroke="#e2e8f0" stroke-width="0.5"/>
                        <line x1="0" y1="30" x2="200" y2="30" stroke="#e2e8f0" stroke-width="0.5"/>
                        <line x1="0" y1="60" x2="200" y2="60" stroke="#e2e8f0" stroke-width="0.5"/>
                        <line x1="0" y1="90" x2="200" y2="90" stroke="#e2e8f0" stroke-width="0.5"/>
                        <circle cx="100" cy="60" r="40" fill="none" stroke="#10b981" stroke-width="1" stroke-dasharray="4 2" opacity="0.4"/>
                        <circle cx="85" cy="50" r="3" fill="#94a3b8"/>
                        <circle cx="110" cy="45" r="3" fill="#94a3b8"/>
                        <circle cx="120" cy="65" r="3" fill="#94a3b8"/>
                        <circle cx="90" cy="70" r="3" fill="#94a3b8"/>
                        <circle cx="75" cy="62" r="3" fill="#94a3b8"/>
                        <circle cx="105" cy="78" r="3" fill="#94a3b8"/>
                        <circle cx="115" cy="52" r="3" fill="#94a3b8"/>
                        <circle cx="100" cy="60" r="5" fill="#ef4444"/>
                        <text x="100" y="105" text-anchor="middle" font-size="8" fill="#94a3b8" font-family="Inter">Radio 300m · 81 comparables</text>
                    </svg>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                    <div>
                        <div style="font-weight: 800; font-size: 1.2rem;">Departamento en Barrio Martín</div>
                        <div style="color: #64748b; font-size: 0.9rem;">1 dormitorio · 43 m² · Año 1998</div>
                    </div>
                    <div style="background: #ecfdf5; color: #10b981; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700;">ALTA CONFIANZA</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 32px;">
                    <div>
                        <div style="font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">Valor estimado</div>
                        <div style="font-size: 2rem; font-weight: 800; color: #0f162a;">USD {valor_usd:,}</div>
                        <div style="font-size: 0.9rem; color: #64748b;">Rango: {min_usd//1000}k — {max_usd//1000}k</div>
                    </div>
                    <div>
                        <div style="font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px;">Renta & ROI</div>
                        <div style="font-size: 1.5rem; font-weight: 700; color: #0f162a;">${alq:,}<span style="font-size: 1rem; font-weight: 400;">/mes</span></div>
                        <div style="font-size: 0.9rem; color: #10b981; font-weight: 600;">Cap Rate: {cap}% anual</div>
                    </div>
                </div>
                <div style="background: #f8fafc; border-radius: 12px; padding: 20px; font-size: 0.9rem; border-left: 4px solid #10b981; color: #475569;">
                    "Se ubica en una zona con alta actividad inmobiliaria. Propiedades comparables en el área sustentan la valuación..."
                </div>
            </div>
        </div>
    </div>
    """

def get_divider_edificios_html() -> str:
    return """
    <div class="landing-divider-image">
        <div class="divider-overlay">
            <div class="divider-stats">
                <div class="divider-stat">
                    <div class="divider-stat-number">9,000+</div>
                    <div class="divider-stat-label">Propiedades analizadas</div>
                </div>
                <div class="divider-stat">
                    <div class="divider-stat-number">21,000+</div>
                    <div class="divider-stat-label">Registros catastrales</div>
                </div>
                <div class="divider-stat">
                    <div class="divider-stat-number">300m</div>
                    <div class="divider-stat-label">Radio de comparables</div>
                </div>
            </div>
        </div>
    </div>
    """

def get_target_html() -> str:
    targets = [
        ("Propietarios", "Sabé cuánto vale tu casa o departamento hoy mismo, sin compromisos ni esperas.", "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=400&q=70&fm=webp"),
        ("Inversores", "Compará rendimientos reales entre barrios usando el Cap Rate calculado con datos frescos.", "https://images.unsplash.com/photo-1554469384-e58fac16e23a?w=400&q=70&fm=webp"),
        ("Corredores", "Tasaciones rápidas para captación con un informe profesional que respalda tu opinión de valor.", "https://images.unsplash.com/photo-1560520653-9e0e4c89eb11?w=400&q=70&fm=webp"),
    ]
    cards = ''.join(
        f'<div class="target-card-v2">'
        f'<div class="target-image" style="background-image: url(\'{img}\');"></div>'
        '<div class="target-card-content">'
        f'<h3 style="margin-bottom: 12px; color: #0f162a;">{titulo}</h3>'
        f'<p style="color: #64748b; font-size: 0.95rem;">{desc}</p>'
        '</div>'
        '</div>'
        for titulo, desc, img in targets
    )
    return (
        '<div class="landing-section">'
        '<h2 style="text-align: center; margin-bottom: 48px;">¿Para quién es Valu?</h2>'
        f'<div class="landing-grid-3">{cards}</div>'
        '</div>'
    )

def get_trust_html() -> str:
    svg_check = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>'
    svg_x = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'
    
    return f"""
    <div class="landing-section">
        <div class="landing-disclaimer">
            <h3 style="margin-bottom: 24px; color: #92400e; font-size: 1.4rem;">Lo que Valu es y lo que no es</h3>
            <div class="landing-grid-2">
                <div>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        <li style="margin-bottom: 16px; display: flex; align-items: flex-start; gap: 12px;">
                            <div style="flex-shrink: 0; padding-top: 2px;">{svg_check}</div>
                            <span style="color: #475569;">Herramienta de estimación basada en datos reales del mercado.</span>
                        </li>
                        <li style="margin-bottom: 16px; display: flex; align-items: flex-start; gap: 12px;">
                            <div style="flex-shrink: 0; padding-top: 2px;">{svg_check}</div>
                            <span style="color: #475569;">Modelo estadístico calibrado específicamente para Rosario.</span>
                        </li>
                        <li style="margin-bottom: 16px; display: flex; align-items: flex-start; gap: 12px;">
                            <div style="flex-shrink: 0; padding-top: 2px;">{svg_check}</div>
                            <span style="color: #475569;">Transparente: muestra cuántos datos usa y de dónde vienen.</span>
                        </li>
                    </ul>
                </div>
                <div>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        <li style="margin-bottom: 16px; display: flex; align-items: flex-start; gap: 12px;">
                            <div style="flex-shrink: 0; padding-top: 2px;">{svg_x}</div>
                            <span style="color: #475569;">No reemplaza una tasación profesional de un tasador matriculado.</span>
                        </li>
                        <li style="margin-bottom: 16px; display: flex; align-items: flex-start; gap: 12px;">
                            <div style="flex-shrink: 0; padding-top: 2px;">{svg_x}</div>
                            <span style="color: #475569;">No garantiza el precio final de una operación de cierre.</span>
                        </li>
                        <li style="margin-bottom: 16px; display: flex; align-items: flex-start; gap: 12px;">
                            <div style="flex-shrink: 0; padding-top: 2px;">{svg_x}</div>
                            <span style="color: #475569;">Zonas con pocos datos tienen menor precisión estadística.</span>
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    """

def get_cta_html() -> str:
    return """
    <div style="background: #0f162a; padding: 80px 20px 40px 20px; text-align: center; color: white;">
        <div>
            <h2 style="font-size: 2.5rem; margin-bottom: 16px;">Empezá a valuar tus propiedades</h2>
            <p style="font-size: 1.1rem; opacity: 0.8; margin-bottom: 24px;">Sin registro. Sin costo. Con datos reales del mercado de Rosario.</p>
        </div>
    </div>
    """

def get_footer_html() -> str:
    return """
    <footer class="landing-footer">
        <div style="font-weight: 800; font-size: 1.5rem; margin-bottom: 8px;">Valu</div>
        <div style="opacity: 0.6; font-size: 0.9rem; margin-bottom: 24px;">Valuador Automático de Propiedades · Rosario, Argentina</div>
        <div style="display: flex; justify-content: center; gap: 32px; margin-bottom: 32px; font-size: 0.9rem;">
            <a href="#" style="color: white; opacity: 0.6; text-decoration: none;">Metodología</a>
            <a href="#" style="color: white; opacity: 0.6; text-decoration: none;">Datos</a>
            <a href="#" style="color: white; opacity: 0.6; text-decoration: none;">Contacto</a>
        </div>
        <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 24px; font-size: 0.8rem; opacity: 0.4;">
            Modelo hedónico híbrido calibrado · Datos: Portales inmobiliarios + Catastro oficial<br>
            © 2026 Valu. Uso informativo y estadístico exclusivamente.
        </div>
    </footer>
    """

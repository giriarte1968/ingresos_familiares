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
        'ejemplo_zona': 'Barrio Martin',
        'ejemplo_tipo': 'Departamento',
        'ejemplo_valor_usd': 72241,
        'ejemplo_rango_min': 68000,
        'ejemplo_rango_max': 76000,
        'ejemplo_alquiler': 516000,
        'ejemplo_cap_rate': 5.4,
        'ejemplo_comparables': 27,
        'ejemplo_confianza': 'Alta',
        'dolar_actual': 1480.00,
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
    """Hero principal con mockup enriquecido.

    Devuelve HTML compacto sin lineas indentadas para evitar que Markdown
    lo interprete como bloque de codigo.
    """
    ejemplo_propiedad = stats.get('ejemplo_propiedad', 'Mabel')
    ejemplo_zona = stats.get('ejemplo_zona', 'Barrio Martin')
    ejemplo_tipo = stats.get('ejemplo_tipo', 'Departamento')
    ejemplo_valor = stats.get('ejemplo_valor_usd', 72241)
    ejemplo_min = stats.get('ejemplo_rango_min', 68000)
    ejemplo_max = stats.get('ejemplo_rango_max', 76000)
    ejemplo_alquiler = stats.get('ejemplo_alquiler', 516000)
    ejemplo_cap = stats.get('ejemplo_cap_rate', 5.4)
    ejemplo_comps = stats.get('ejemplo_comparables', 27)
    ejemplo_confianza = str(stats.get('ejemplo_confianza', 'Alta')).lower()

    return (
        f'<div class="hero-with-image">'
        f'<div class="hero-overlay">'
        f'<div class="hero-content">'
        f'<div class="landing-badge">Datos de mercado actualizados · Rosario</div>'
        f'<h1 class="hero-title">Sabé cuánto vale tu propiedad<br>en Rosario</h1>'
        f'<p class="hero-sub">Valuación automática basada en más de <b>9,000</b> propiedades reales del mercado. El estándar de datos para el mercado inmobiliario local.</p>'
        f'<div class="landing-mockup" style="max-width:560px;margin:0 auto;">'
        f'<div class="mockup-card" style="background:rgba(255,255,255,0.96);color:#0f172a;border:1px solid rgba(255,255,255,0.35);border-radius:22px;padding:26px;box-shadow:0 22px 60px rgba(0,0,0,0.28);">'
        f'<div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:18px;">'
        f'<div>'
        f'<div class="mockup-header" style="color:#10b981;margin-bottom:6px;">EJEMPLO DE RESULTADO</div>'
        f'<div style="font-size:22px;font-weight:900;color:#0f172a;line-height:1.1;">{ejemplo_propiedad} · {ejemplo_zona}</div>'
        f'<div style="color:#64748b;font-size:13px;margin-top:4px;">{ejemplo_tipo}</div>'
        f'</div>'
        f'<div style="background:#dcfce7;color:#166534;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:900;white-space:nowrap;">Confianza {ejemplo_confianza}</div>'
        f'</div>'
        f'<div class="mockup-price" style="color:#006AFF;font-size:38px;letter-spacing:-0.04em;margin-bottom:4px;">USD {ejemplo_valor:,.0f}</div>'
        f'<div class="mockup-range" style="color:#64748b;font-size:14px;opacity:1;">Rango: USD {ejemplo_min:,.0f} — {ejemplo_max:,.0f}</div>'
        f'<div class="mockup-bar" style="margin-top:18px;height:9px;background:#e2e8f0;border-radius:999px;overflow:hidden;">'
        f'<div class="mockup-progress" style="width:64%;height:100%;background:linear-gradient(90deg,#006AFF,#10b981,#f59e0b);border-radius:999px;"></div>'
        f'</div>'
        f'<div class="mockup-labels" style="color:#64748b;opacity:1;font-size:12px;margin-top:8px;">'
        f'<span>Conservador</span><span>Optimista</span>'
        f'</div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:18px;">'
        f'<div style="background:#f8fafc;border-radius:14px;padding:12px;">'
        f'<div style="color:#64748b;font-size:11px;margin-bottom:4px;">Alquiler estimado</div>'
        f'<div style="color:#0f172a;font-weight:900;font-size:14px;">ARS {ejemplo_alquiler:,.0f}</div>'
        f'</div>'
        f'<div style="background:#f8fafc;border-radius:14px;padding:12px;">'
        f'<div style="color:#64748b;font-size:11px;margin-bottom:4px;">Cap Rate</div>'
        f'<div style="color:#0f172a;font-weight:900;font-size:14px;">{ejemplo_cap:.1f}%</div>'
        f'</div>'
        f'<div style="background:#f8fafc;border-radius:14px;padding:12px;">'
        f'<div style="color:#64748b;font-size:11px;margin-bottom:4px;">Comparables</div>'
        f'<div style="color:#0f172a;font-weight:900;font-size:14px;">{ejemplo_comps}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )

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
            'desc': 'Nuestro motor busca comparables en un radio cercano, ajusta por antigüedad y calidad, y calcula los escenarios.',
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

def get_deliverables_html() -> str:
    items = [
        ("Valor estimado", "Precio de referencia en USD y ARS para publicación y análisis."),
        ("Rango de venta", "Escenarios conservador, mercado y optimista para negociar mejor."),
        ("Alquiler y Cap Rate", "Estimación de renta mensual y rendimiento anual esperado."),
        ("Comparables reales", "Muestras de mercado cercanas usadas como respaldo del cálculo."),
    ]
    cards = ''.join(
        f'<div class="deliverable-card">'
        f'<div class="deliverable-icon">{i}</div>'
        f'<h3>{title}</h3>'
        f'<p>{desc}</p>'
        f'</div>'
        for i, (title, desc) in enumerate(items, 1)
    )
    return (
        '<div class="landing-section-alt">'
        '<div class="landing-section">'
        '<div class="section-kicker">Informe claro</div>'
        '<h2 class="section-title">Qué recibís con Valu</h2>'
        '<div style="text-align:center;max-width:720px;margin:0 auto 38px;color:#64748b;font-size:1.05rem;line-height:1.6;">No solo un número: una lectura completa del activo y su contexto de mercado.</div>'
        f'<div class="deliverables-grid">{cards}</div>'
        '</div>'
        '</div>'
    )

def get_faq_html() -> str:
    faqs = [
        (
            "¿Valu reemplaza una tasación profesional?",
            "No. Valu es una herramienta estadística de estimación. Sirve para orientar decisiones, pero no reemplaza una tasación profesional matriculada."
        ),
        (
            "¿De dónde salen los datos?",
            "Valu usa datos de mercado inmobiliario, comparables publicados, cache propio de scraping y fuentes catastrales disponibles."
        ),
        (
            "¿Funciona fuera de Rosario?",
            "Actualmente el modelo está calibrado para Rosario. Usarlo fuera de esa ciudad puede reducir la precisión."
        ),
        (
            "¿Qué pasa si hay pocos datos en mi zona?",
            "Valu lo refleja en la confianza y en el rango estimado. Menos comparables implica mayor incertidumbre."
        ),
    ]
    html = ''.join(
        '<div class="faq-item">'
        f'<h3>{q}</h3>'
        f'<p>{a}</p>'
        '</div>'
        for q, a in faqs
    )
    return (
        '<div class="landing-section faq-section">'
        '<div class="section-kicker">Preguntas frecuentes</div>'
        '<h2 class="section-title">Antes de empezar</h2>'
        f'<div class="faq-grid">{html}</div>'
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

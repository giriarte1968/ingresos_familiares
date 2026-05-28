from pathlib import Path
from datetime import datetime
import shutil

lc = Path("landing_content.py")
if not lc.exists():
    raise SystemExit("ERROR: no encuentro landing_content.py. Ejecuta este script desde la carpeta del proyecto.")

backup = Path(f"landing_content.py.backup_mockup_render_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(lc, backup)
print(f"Backup creado: {backup.name}")

s = lc.read_text(encoding="utf-8")

# Asegurar defaults necesarios del ejemplo, sin duplicar si ya existen.
if "'ejemplo_zona'" not in s:
    s = s.replace(
        "        'ejemplo_propiedad': 'Mabel',\n",
        "        'ejemplo_propiedad': 'Mabel',\n"
        "        'ejemplo_zona': 'Barrio Martin',\n"
        "        'ejemplo_tipo': 'Departamento',\n",
        1,
    )
if "'ejemplo_comparables'" not in s:
    s = s.replace(
        "        'ejemplo_cap_rate': 5.4,\n",
        "        'ejemplo_cap_rate': 5.4,\n"
        "        'ejemplo_comparables': 27,\n"
        "        'ejemplo_confianza': 'Alta',\n",
        1,
    )
# Ajustar valores del ejemplo si siguen con los anteriores.
s = s.replace("'ejemplo_valor_usd': 77139", "'ejemplo_valor_usd': 72241")
s = s.replace("'ejemplo_rango_min': 72000", "'ejemplo_rango_min': 68000")
s = s.replace("'ejemplo_rango_max': 82000", "'ejemplo_rango_max': 76000")

start_marker = "def get_hero_html(stats: dict) -> str:"
end_marker = "\ndef get_problem_html() -> str:"
start = s.find(start_marker)
if start == -1:
    raise SystemExit("ERROR: no encontre def get_hero_html(stats: dict)")
end = s.find(end_marker, start)
if end == -1:
    raise SystemExit("ERROR: no encontre def get_problem_html() despues del hero")

new_hero = r'''def get_hero_html(stats: dict) -> str:
    """Hero principal con mockup enriquecido del resultado de Valu.

    IMPORTANTE: esta función retorna HTML real con <div>, no entidades escapadas
    como &lt;div&gt;. `landing.py` debe renderizarla con unsafe_allow_html=True.
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
    ejemplo_confianza = stats.get('ejemplo_confianza', 'Alta')

    return f"""
    <div class="hero-with-image">
        <div class="hero-overlay">
            <div class="hero-content">
                <div class="landing-badge">Datos de mercado actualizados · Rosario</div>
                <h1 class="hero-title">Sabé cuánto vale tu propiedad<br>en Rosario</h1>
                <p class="hero-sub">Valuación automática basada en más de <b>{stats['total_propiedades_scraping']:,}</b> propiedades reales del mercado. El estándar de datos para el mercado inmobiliario local.</p>

                <div class="landing-mockup" style="max-width:560px;margin:0 auto;">
                    <div class="mockup-card" style="background:rgba(255,255,255,0.96);color:#0f172a;border:1px solid rgba(255,255,255,0.35);border-radius:22px;padding:26px;box-shadow:0 22px 60px rgba(0,0,0,0.28);">
                        <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:18px;">
                            <div>
                                <div class="mockup-header" style="color:#10b981;margin-bottom:6px;">EJEMPLO DE RESULTADO</div>
                                <div style="font-size:22px;font-weight:900;color:#0f172a;line-height:1.1;">{ejemplo_propiedad} · {ejemplo_zona}</div>
                                <div style="color:#64748b;font-size:13px;margin-top:4px;">{ejemplo_tipo}</div>
                            </div>
                            <div style="background:#dcfce7;color:#166534;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:900;white-space:nowrap;">
                                Confianza {str(ejemplo_confianza).lower()}
                            </div>
                        </div>

                        <div class="mockup-price" style="color:#006AFF;font-size:38px;letter-spacing:-0.04em;margin-bottom:4px;">
                            USD {ejemplo_valor:,.0f}
                        </div>
                        <div class="mockup-range" style="color:#64748b;font-size:14px;opacity:1;">
                            Rango: USD {ejemplo_min:,.0f} — {ejemplo_max:,.0f}
                        </div>

                        <div class="mockup-bar" style="margin-top:18px;height:9px;background:#e2e8f0;border-radius:999px;overflow:hidden;">
                            <div class="mockup-progress" style="width:64%;height:100%;background:linear-gradient(90deg,#006AFF,#10b981,#f59e0b);border-radius:999px;"></div>
                        </div>
                        <div class="mockup-labels" style="color:#64748b;opacity:1;font-size:12px;margin-top:8px;">
                            <span>Conservador</span>
                            <span>Optimista</span>
                        </div>

                        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:18px;">
                            <div style="background:#f8fafc;border-radius:14px;padding:12px;">
                                <div style="color:#64748b;font-size:11px;margin-bottom:4px;">Alquiler estimado</div>
                                <div style="color:#0f172a;font-weight:900;font-size:14px;">ARS {ejemplo_alquiler:,.0f}</div>
                            </div>
                            <div style="background:#f8fafc;border-radius:14px;padding:12px;">
                                <div style="color:#64748b;font-size:11px;margin-bottom:4px;">Cap Rate</div>
                                <div style="color:#0f172a;font-weight:900;font-size:14px;">{ejemplo_cap:.1f}%</div>
                            </div>
                            <div style="background:#f8fafc;border-radius:14px;padding:12px;">
                                <div style="color:#64748b;font-size:11px;margin-bottom:4px;">Comparables</div>
                                <div style="color:#0f172a;font-weight:900;font-size:14px;">{ejemplo_comps}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
'''

s = s[:start] + new_hero + s[end:]
lc.write_text(s, encoding="utf-8")
print("OK: landing_content.py actualizado con HTML real, no escapado.")

# Verificacion adicional: asegurar unsafe_allow_html=True en landing.py para el hero.
landing = Path("landing.py")
if landing.exists():
    ls = landing.read_text(encoding="utf-8")
    if "st.markdown(get_hero_html(stats))" in ls:
        lb = Path(f"landing.py.backup_mockup_render_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copy2(landing, lb)
        ls = ls.replace("st.markdown(get_hero_html(stats))", "st.markdown(get_hero_html(stats), unsafe_allow_html=True)")
        landing.write_text(ls, encoding="utf-8")
        print("OK: landing.py ajustado para usar unsafe_allow_html=True en el hero.")
    else:
        print("OK: landing.py ya parece renderizar el hero con HTML habilitado.")

print("Reinicia Streamlit: Ctrl+C y luego streamlit run valu.py")

from pathlib import Path
from datetime import datetime
import shutil
import sys

p = Path("landing_content.py")
if not p.exists():
    raise SystemExit("ERROR: no encuentro landing_content.py. Ejecuta este script desde la carpeta del proyecto.")

s = p.read_text(encoding="utf-8")
backup = Path(f"landing_content.py.backup_mockup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(p, backup)
print(f"Backup creado: {backup.name}")

# 1) Actualizar defaults del ejemplo para que el mockup muestre Mabel con datos completos.
old_stats = """        'ejemplo_propiedad': 'Mabel',
        'dolar_actual': 1480.00,
        'ejemplo_valor_usd': 77139,
        'ejemplo_rango_min': 72000,
        'ejemplo_rango_max': 82000,
        'ejemplo_alquiler': 516000,
        'ejemplo_cap_rate': 5.4,
"""
new_stats = """        'ejemplo_propiedad': 'Mabel',
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
"""

if old_stats in s:
    s = s.replace(old_stats, new_stats, 1)
    print("OK: defaults del ejemplo actualizados.")
else:
    # Si ya estaban agregados, no fallar.
    print("Aviso: no encontre el bloque exacto de stats; sigo con el reemplazo del hero.")

# 2) Reemplazar solo get_hero_html().
start_marker = "def get_hero_html(stats: dict) -> str:"
end_marker = "\ndef get_problem_html() -> str:"
start = s.find(start_marker)
if start == -1:
    raise SystemExit("ERROR: no encontre def get_hero_html(stats: dict) en landing_content.py")
end = s.find(end_marker, start)
if end == -1:
    raise SystemExit("ERROR: no encontre def get_problem_html() despues del hero")

new_hero = r'''def get_hero_html(stats: dict) -> str:
    """Hero principal con mockup enriquecido del resultado de Valu."""
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
p.write_text(s, encoding="utf-8")
print("OK: mockup del hero actualizado en landing_content.py")
print("Reinicia Streamlit: Ctrl+C y luego streamlit run valu.py")

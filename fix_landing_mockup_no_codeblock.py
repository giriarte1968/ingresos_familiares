from pathlib import Path
from datetime import datetime
import shutil

p = Path("landing_content.py")
if not p.exists():
    raise SystemExit("ERROR: no encuentro landing_content.py. Ejecuta este script desde la carpeta del proyecto.")

backup = Path(f"landing_content.py.backup_no_codeblock_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(p, backup)
print(f"Backup creado: {backup.name}")

s = p.read_text(encoding="utf-8")

# Defaults del ejemplo, sin duplicar.
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

# IMPORTANTE: retorna HTML en una sola cadena sin saltos indentados.
# Streamlit Markdown interpreta HTML indentado como bloque de codigo.
new_func = '''def get_hero_html(stats: dict) -> str:
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
        f'<p class="hero-sub">Valuación automática basada en más de <b>{stats["total_propiedades_scraping"]:,}</b> propiedades reales del mercado. El estándar de datos para el mercado inmobiliario local.</p>'
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
'''

s = s[:start] + new_func + s[end:]
p.write_text(s, encoding="utf-8")
print("OK: get_hero_html ahora devuelve HTML compacto sin indentacion de bloque de codigo.")
print("Reinicia Streamlit: Ctrl+C y luego streamlit run valu.py")

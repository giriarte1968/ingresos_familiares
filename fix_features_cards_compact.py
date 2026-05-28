from pathlib import Path
from datetime import datetime
import shutil

content = Path("landing_content.py")
design = Path("valu_design.py")
if not content.exists():
    raise SystemExit("ERROR: no encuentro landing_content.py. Ejecuta este script desde la carpeta del proyecto.")
if not design.exists():
    raise SystemExit("ERROR: no encuentro valu_design.py. Ejecuta este script desde la carpeta del proyecto.")

for p in (content, design):
    backup = Path(f"{p.name}.backup_features_compact_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(p, backup)
    print(f"Backup creado: {backup.name}")

s = content.read_text(encoding="utf-8")
start = s.find("def get_features_html() -> str:")
if start == -1:
    raise SystemExit("ERROR: no encontre def get_features_html() en landing_content.py")
end = s.find("\ndef get_divider_edificios_html() -> str:", start)
if end == -1:
    raise SystemExit("ERROR: no encontre def get_divider_edificios_html() despues de get_features_html")

new_func = r"""def get_features_html() -> str:
    """ + '"""' + r"""Sección compacta y liviana: tarjetas más chicas, iconos SVG más visibles.""" + '"""' + r"""
    features = [
        ("3 escenarios de precio", "Conservador, Mercado y Optimista para negociar con más contexto.", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 19V9"/><path d="M12 19V5"/><path d="M20 19v-7"/><path d="M3 19h18"/></svg>'),
        ("Cap Rate del mercado", "Rendimiento anual estimado con datos reales de alquileres cercanos.", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 17l6-6 4 4 6-8"/><path d="M15 7h5v5"/></svg>'),
        ("Datos de Infomapa", "Cruce con información municipal, catastro y registros oficiales.", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M4 10h16"/><path d="M10 20V10"/></svg>'),
        ("Planos oficiales", "Acceso rápido a documentación y planos cuando están disponibles.", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 3h7l4 4v14H7z"/><path d="M14 3v5h5"/><path d="M9 13h6"/><path d="M9 17h4"/></svg>'),
        ("Transparencia total", "Ves comparables, confianza y datos usados para sostener el valor.", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>'),
        ("Informe profesional", "Explicación clara, lista para compartir o defender una decisión.", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 3h9l3 3v15H6z"/><path d="M9 10h6"/><path d="M9 14h6"/><path d="M9 18h4"/></svg>'),
        ("Historial de valores", "Seguimiento de cambios de valor según mercado y recalculaciones.", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 19h16"/><path d="M6 16l4-4 3 3 5-7"/><circle cx="6" cy="16" r="1"/><circle cx="10" cy="12" r="1"/><circle cx="13" cy="15" r="1"/><circle cx="18" cy="8" r="1"/></svg>'),
        ("USD y ARS siempre", "Conversión automática para leer el valor en ambas monedas.", '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v18"/><path d="M17 7H9.5a3 3 0 0 0 0 6H14a3 3 0 0 1 0 6H7"/></svg>'),
    ]

    cards = ''.join(
        f'<div class="feature-card-v3">'
        f'<div class="feature-index-v3">{i:02d}</div>'
        f'<div class="feature-icon-v3">{icon}</div>'
        f'<h4>{title}</h4>'
        f'<p>{desc}</p>'
        f'</div>'
        for i, (title, desc, icon) in enumerate(features, 1)
    )

    return (
        '<div class="features-v3-band">'
        '<div class="features-v3-section">'
        '<div class="features-v3-kicker">Qué incluye</div>'
        '<h2>Qué te da Valu</h2>'
        '<p class="features-v3-subtitle">Una lectura clara del precio, la renta y la confianza estadística sin recargar la experiencia.</p>'
        f'<div class="features-v3-grid">{cards}</div>'
        '</div>'
        '</div>'
    )
"""

content.write_text(s[:start] + new_func + s[end:], encoding="utf-8")
print("OK: get_features_html reemplazado por versión compacta.")

css = r'''

/* Features compact v3 — liviano, sin JS ni imágenes */
.features-v3-band { background:#0b111c; padding:72px 20px; font-family:'Inter',sans-serif; }
.features-v3-section { max-width:1120px; margin:0 auto; }
.features-v3-kicker { text-align:center; color:#10b981; font-size:.78rem; font-weight:900; letter-spacing:.14em; text-transform:uppercase; margin-bottom:10px; }
.features-v3-section h2 { color:#fff; text-align:center; font-size:clamp(2rem,3vw,2.8rem); line-height:1.05; letter-spacing:-.045em; margin:0 0 12px 0; }
.features-v3-subtitle { color:rgba(226,232,240,.72); text-align:center; max-width:680px; margin:0 auto 34px auto; line-height:1.55; }
.features-v3-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; }
.feature-card-v3 { position:relative; min-height:178px; padding:22px; border-radius:20px; background:linear-gradient(180deg,#fff 0%,#f8fafc 100%); border:1px solid rgba(226,232,240,.95); box-shadow:0 12px 30px rgba(0,0,0,.16); overflow:hidden; transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
.feature-card-v3::after { content:""; position:absolute; inset:0 0 auto 0; height:3px; background:linear-gradient(90deg,#006AFF,#10b981); opacity:.85; }
.feature-card-v3:hover { transform:translateY(-3px); box-shadow:0 18px 38px rgba(0,0,0,.22); border-color:rgba(16,185,129,.35); }
.feature-icon-v3 { width:54px; height:54px; border-radius:16px; background:#ecfdf5; color:#10b981; display:flex; align-items:center; justify-content:center; margin-bottom:18px; }
.feature-icon-v3 svg { width:30px; height:30px; }
.feature-index-v3 { position:absolute; right:18px; top:18px; color:#e2e8f0; font-size:1.25rem; font-weight:900; letter-spacing:-.04em; }
.feature-card-v3 h4 { color:#0f172a !important; font-size:1.02rem; line-height:1.25; margin:0 0 8px 0; font-weight:900; letter-spacing:-.02em; }
.feature-card-v3 p { color:#64748b; font-size:.92rem; line-height:1.5; margin:0; }
@media (max-width:1050px) { .features-v3-grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:620px) { .features-v3-band { padding:54px 16px; } .features-v3-grid { grid-template-columns:1fr; } .feature-card-v3 { min-height:auto; } }
'''

d = design.read_text(encoding="utf-8")
if "Features compact v3" not in d:
    idx = d.rfind("</style>")
    if idx == -1:
        raise SystemExit("ERROR: no encontre </style> en valu_design.py")
    d = d[:idx] + css + "\n" + d[idx:]
    design.write_text(d, encoding="utf-8")
    print("OK: CSS compacto agregado a valu_design.py")
else:
    print("OK: CSS compacto ya existia en valu_design.py")

print("Reinicia Streamlit: Ctrl+C y luego streamlit run valu.py")

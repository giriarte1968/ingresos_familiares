from pathlib import Path
from datetime import datetime
import re
import shutil

p = Path("valu_design.py")
if not p.exists():
    raise SystemExit("ERROR: no encuentro valu_design.py. Ejecuta este script desde la carpeta del proyecto.")

backup = Path(f"valu_design.py.backup_css_visible_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(p, backup)
print(f"Backup creado: {backup.name}")

s = p.read_text(encoding="utf-8")
original = s

# 1) Remover bloque fallido si quedó visible como texto dentro del LANDING_CSS
#    Caso con comentario completo.
s = re.sub(
    r"\n?/\* FIX SEGURO[^*]*\*+(?:[^/*][^*]*\*+)*/\s*"
    r"\.feature-card-v2\s*\{[\s\S]*?\.feature-card-v2\s+\.card-text\s*,\s*\.feature-card-v2\s+p\s*\{[^}]*\}\s*",
    "\n",
    s,
    flags=re.MULTILINE,
)

# 2) Remover bloque minificado sin comentario, pero SOLO si contiene !important
#    para no borrar estilos originales.
s = re.sub(
    r"\.feature-card-v2\s*\{[^{}]*!important[^{}]*\}\s*"
    r"\.feature-card-v2:hover\s*\{[^{}]*!important[^{}]*\}\s*"
    r"\.feature-card-v2\s+\.feature-icon-wrapper\s*\{[^{}]*!important[^{}]*\}\s*"
    r"\.feature-card-v2\s+\.feature-icon-wrapper\s+svg\s*\{[^{}]*!important[^{}]*\}\s*"
    r"\.feature-card-v2\s+\.feature-title\s*\{[^{}]*!important[^{}]*\}\s*"
    r"\.feature-card-v2\s+\.card-text\s*,\s*\.feature-card-v2\s+p\s*\{[^{}]*!important[^{}]*\}\s*",
    "\n",
    s,
    flags=re.MULTILINE,
)

safe_css = r'''

/* SAFE CSS — Mejora liviana de "Qué te da Valu" (dentro de LANDING_CSS) */
.feature-card-v2 {
    padding: 22px 24px !important;
    border-radius: 18px !important;
    min-height: 210px !important;
    align-self: start !important;
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
    border: 1px solid rgba(226, 232, 240, 0.95) !important;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08) !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease !important;
}
.feature-card-v2:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 16px 34px rgba(15, 23, 42, 0.13) !important;
    border-color: rgba(16, 185, 129, 0.35) !important;
}
.feature-card-v2 .feature-icon-wrapper {
    width: 58px !important;
    height: 58px !important;
    border-radius: 16px !important;
    background: #ecfdf5 !important;
    color: #10b981 !important;
    margin-bottom: 18px !important;
}
.feature-card-v2 .feature-icon-wrapper svg {
    width: 32px !important;
    height: 32px !important;
    stroke-width: 1.8 !important;
}
.feature-card-v2 .feature-title {
    color: #0f172a !important;
    opacity: 1 !important;
    font-size: 1.08rem !important;
    line-height: 1.25 !important;
    font-weight: 900 !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 10px !important;
}
.feature-card-v2 .card-text,
.feature-card-v2 p {
    color: #475569 !important;
    opacity: 1 !important;
    font-size: 0.94rem !important;
    line-height: 1.55 !important;
}
'''

# 3) Insertar CSS seguro dentro del <style> de LANDING_CSS, no después.
if "SAFE CSS — Mejora liviana" not in s:
    landing_idx = s.find('LANDING_CSS = """')
    if landing_idx == -1:
        raise SystemExit("ERROR: no encuentro LANDING_CSS en valu_design.py")
    style_end = s.find("</style>", landing_idx)
    if style_end == -1:
        raise SystemExit("ERROR: no encuentro </style> dentro de LANDING_CSS")
    s = s[:style_end] + safe_css + "\n" + s[style_end:]
    print("OK: CSS seguro insertado dentro de LANDING_CSS.")
else:
    print("OK: CSS seguro ya estaba aplicado.")

p.write_text(s, encoding="utf-8")
print("OK: valu_design.py actualizado.")
print("Reinicia Streamlit: Ctrl+C y luego streamlit run valu.py")

from pathlib import Path
from datetime import datetime
import shutil

p = Path("landing.py")
if not p.exists():
    raise SystemExit("ERROR: no encuentro landing.py. Ejecuta este script desde la carpeta del proyecto.")

backup = Path(f"landing.py.backup_render_hero_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(p, backup)
print(f"Backup creado: {backup.name}")

s = p.read_text(encoding="utf-8")
lines = s.splitlines()
out = []
changed = False

for line in lines:
    stripped = line.strip()

    # Eliminar una importacion local anterior si ya estaba justo antes de la linea del hero
    # No molesta dejar imports duplicados, pero evitamos repetir en cada corrida.
    if stripped == "import html as _html":
        # La volveremos a insertar en el lugar correcto si detectamos el hero.
        continue

    # Reemplazar cualquier forma conocida de render del hero.
    if "get_hero_html(stats)" in stripped and (stripped.startswith("st.markdown(") or stripped.startswith("st.write(")):
        indent = line[:len(line) - len(line.lstrip())]
        out.append(indent + "import html as _html")
        out.append(indent + "st.markdown(_html.unescape(_html.unescape(get_hero_html(stats))), unsafe_allow_html=True)")
        changed = True
    else:
        out.append(line)

if not changed:
    print("AVISO: no encontre una linea st.markdown/st.write con get_hero_html(stats).")
    print("Copia aqui la salida de: findstr /n /c:\"get_hero_html(stats)\" landing.py")
else:
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("OK: landing.py ahora hace doble html.unescape y renderiza el hero con unsafe_allow_html=True.")

print("\nAhora ejecuta estas verificaciones:")
print('  findstr /n /c:"get_hero_html(stats)" landing.py')
print('  findstr /n /c:"&lt;div" landing_content.py')
print("\nLuego reinicia Streamlit: Ctrl+C y despues streamlit run valu.py")

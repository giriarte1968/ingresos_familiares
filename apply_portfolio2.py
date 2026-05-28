from pathlib import Path
from datetime import datetime
import shutil
import sys

root = Path.cwd()
valu = root / "valu.py"
p2 = root / "valu_portfolio2.py"

if not valu.exists():
    print("ERROR: no encuentro valu.py. Ejecuta este script desde la raiz del proyecto.")
    sys.exit(1)

if not p2.exists():
    print("ERROR: no encuentro valu_portfolio2.py.")
    print("Copia valu_portfolio2.py a la raiz del proyecto antes de ejecutar este script.")
    sys.exit(1)

backup = root / f"valu.py.backup_portfolio2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy2(valu, backup)
print(f"Backup creado: {backup.name}")

s = valu.read_text(encoding="utf-8")
changed = False

# 1) Insertar rama Portfolio2 antes de Inventario
if 'st.session_state.page == "Portfolio2"' not in s:
    marker = '    elif st.session_state.page == "Inventario":'
    idx = s.find(marker)

    if idx == -1:
        print("ERROR: no encontre el bloque de Inventario para insertar Portfolio2.")
        print("No se modifico valu.py.")
        sys.exit(2)

    insert = '''    elif st.session_state.page == "Portfolio2":
        from valu_portfolio2 import mostrar_portfolio2
        mostrar_portfolio2(
            cargar_propiedades_fn=cargar_propiedades,
            obtener_usdt_fn=obtener_usdt_ars_binance,
        )

'''

    s = s[:idx] + insert + s[idx:]
    changed = True
    print("OK: rama Portfolio2 insertada.")
else:
    print("OK: rama Portfolio2 ya existia.")

# 2) Reemplazar linea del menu de navegacion
if '"Portfolio2"' not in s:
    print("ERROR: Portfolio2 no quedo insertado correctamente.")
    sys.exit(3)

if 'nav_options = ["Portfolio", "Portfolio2", "Inventario", "Cargar Mercado", "Configuración"]' not in s:
    lines = s.splitlines()
    new_lines = []
    replaced = False

    for line in lines:
        stripped = line.strip()

        if (
            'st.session_state.page = st.radio(' in stripped
            and 'Portfolio' in stripped
            and 'Inventario' in stripped
            and 'Cargar Mercado' in stripped
        ):
            indent = line[:len(line) - len(line.lstrip())]

            new_lines.extend([
                indent + 'nav_options = ["Portfolio", "Portfolio2", "Inventario", "Cargar Mercado", "Configuración"]',
                indent + 'forced_nav = st.session_state.pop("_force_nav_page", None)',
                indent + 'if forced_nav in nav_options:',
                indent + '    st.session_state["nav_page_radio"] = forced_nav',
                indent + 'if "nav_page_radio" not in st.session_state:',
                indent + '    st.session_state["nav_page_radio"] = st.session_state.page if st.session_state.page in nav_options else "Portfolio"',
                indent + 'st.radio("NAVEGACIÓN", nav_options, key="nav_page_radio")',
                indent + 'st.session_state.page = st.session_state["nav_page_radio"]',
            ])

            replaced = True
            changed = True
            print("OK: menu de navegacion actualizado.")
        else:
            new_lines.append(line)

    if not replaced:
        print("ERROR: no encontre la linea st.radio de NAVEGACION.")
        print("No pude agregar Portfolio2 al menu.")
        sys.exit(4)

    s = "\n".join(new_lines) + "\n"
else:
    print("OK: menu de navegacion ya incluia Portfolio2.")

if changed:
    valu.write_text(s, encoding="utf-8")
    print("valu.py actualizado.")
else:
    print("No habia cambios pendientes en valu.py.")

print("")
print("Listo.")
print("Ahora ejecuta:")
print("  streamlit run valu.py")
print("")
print("Si streamlit no funciona directo, usa:")
print("  python -m streamlit run valu.py")
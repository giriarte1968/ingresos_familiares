"""Fix: agrega espaciado entre KPIs y mapa del portfolio."""
content = open('valu.py', encoding='utf-8').read()

old = "                # MAPA DE ACTIVOS\n                import folium\n                from streamlit.components.v1 import html"
new = "                # MAPA DE ACTIVOS\n                st.markdown('<div style=\"margin-top:18px;\"></div>', unsafe_allow_html=True)\n                import folium\n                from streamlit.components.v1 import html"

if old in content:
    content = content.replace(old, new, 1)
    print('Spacing patch OK')
else:
    print('NOT FOUND - searching...')
    idx = content.find('MAPA DE ACTIVOS')
    print(repr(content[idx:idx+200]))

open('valu.py', 'w', encoding='utf-8').write(content)

import ast
ast.parse(content)
print('Syntax OK')
assert 'pad_s = base * 0.9' in content
assert 'pad_n = base * 0.15' in content
print('All checks passed')

"""Fix TTLs in app.py — replaces hardcoded ttls with TTL_ENTORNO variables"""
import re, os
path = r"C:\Users\Gustavo\ingresos_familiares_st\app.zy"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
replacements = {
    "@st.cache_data(TTL=86400*7)  # Cache por 7 dias": "@st.cache_data(ttl=TTL_LARGO)",
    "@st.cache_data(TTL=86400*30)": "@st.cache_data(ttl=TTL_LARGO)",
    "@st.cache_data(TTL=36_000)": "@st.cache_data(ttl=TTL_CORTO)",
    "@st.cache_data(TTL=86_400)": "@st.cache_data(ttl=TTL_MEDIO)",
    "@st.cache_data(TTL=86400)": "@st.cache_data(ttl=TTL_MEDIO)",
}
count = 0
for old, new in replacements.items():
    n = content.count(old)
    content = content.replace(old, new)
    count += n
with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print(f"Replaced {count} occurrences")
remaining = re.findall(r"@st.cache_(?:data|resource)\(ttl=\d+\)", content)
if remaining:
    print(f"WARNING: {len(remaining)} hardcoded TTLs remain:")
    for r_ in remaining:
        print(f"  {r_}")
else:
    print("OK: No hardcoded TTLs remain")
"""Fix TTLs in app.py — replaces hardcoded ttls with TTL_ENTORNO variables"""
import re, os
path = r"C:\Users\Gustavo\ingresos_familiares_st\app.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
replacements = {
    r"@st.cache_data\(ttl=86400\*7\)": "@st.cache_data(ttl=TTL_ENTORNO['largo'])",
    r"@st.cache_data\(ttl=86400\*30\)": "@st.cache_data(ttl=TTL_ENTORNO['largo'])",
    r"@st.cache_data\(ttl=36_000\)": "@st.cache_data(ttl=TTL_ENTORNO['corto'])",
    r"@st.cache_data\(ttl=86_400\)": "@st.cache_data(ttl=TTL_ENTORNO['medio'])",
    r"@st.cache_data\(ttl=86400\)": "@st.cache_data(ttl=TTL_ENTORNO['medio'])",
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
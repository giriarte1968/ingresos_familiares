import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from gen_pdf_ttl import load_property, load_cache, build_context, render_html, html_to_pdf

nombre = "Entre Rios 1372"
prop = load_property(nombre)
assert prop is not None, "Propiedad no encontrada"

cache_data = load_cache(nombre)
print("Cache data loaded:", bool(cache_data))

ctx = build_context(prop, cache_data)
html = render_html(ctx)
print("HTML generated successfully, size:", len(html), "chars")

try:
    pdf_bytes = html_to_pdf(html)
    print("PDF generated successfully! Size:", len(pdf_bytes), "bytes")
except Exception as e:
    print("PDF generation error:", e)


import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
from parsers.deep_scraper import scrape_property_detail

cache_path = r'C:\Users\Gustavo\ingresos_familiares_st\cache_scraping.json'
with open(cache_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

props = data.get('propiedades', [])
# Get first 5 props that have a URL
urls = [p for p in props if p.get('url')][:5]

print(f"Testing extraction for {len(urls)} properties...")
for p in urls:
    res = scrape_property_detail(p)
    print(f"URL: {p.get('url')} -> Year: {res.get('anio_construccion')}")

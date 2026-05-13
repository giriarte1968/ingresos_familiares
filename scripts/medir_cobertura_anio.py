"""
Mide cobertura de enriquecimiento de año para propiedades ancla (Fase 1).
Ejecutar: python scripts/medir_cobertura_anio.py
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.mercado_inmobiliario import valuar_propiedad_v7

with open('propiedades.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
props = data.get('propiedades', [])

NOMBRES = ['Mabel', 'Ayacucho', 'Vera Mujica', 'P1200', 'Amenabar']

print(f"{'Propiedad':15} | {'Total':>6} | {'Con año':>8} | {'ALTA':>5} | {'MEDIA':>6} | {'%':>6}")
print("=" * 70)

for nombre in NOMBRES:
    match = [p for p in props if nombre.lower() in p.get('nombre', '').lower()]
    if not match:
        print(f"{nombre:15} | {'N/E':>6}")
        continue
    prop = match[0]
    result = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    meta = result.get('resolution_metadata', {})

    total = meta.get('n_comparables_total', 0)
    alta = meta.get('n_con_anio_alta', 0)
    media = meta.get('n_con_anio_media', 0)
    n_anio = alta + media
    pct = meta.get('pct_con_anio', 0)

    print(f"{nombre:15} | {total:>6} | {n_anio:>8} | {alta:>5} | {media:>6} | {pct:>5}%")

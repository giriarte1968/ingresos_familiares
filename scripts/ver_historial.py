"""
Herramienta CLI para consultar el historial de valuaciones.
Uso:
    python scripts/ver_historial.py                    # Todo el historial
    python scripts/ver_historial.py Mabel              # Solo Mabel
    python scripts/ver_historial.py Mabel --ultimas 5  # Últimas 5
    python scripts/ver_historial.py --scrapings        # Listar scrapings
"""
import argparse
import sys
import os
from datetime import datetime

# Añadir directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parsers.valuacion_historial import cargar_historial, listar_snapshots_scraping

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('propiedad', nargs='?', default=None)
    parser.add_argument('--ultimas', type=int, default=None)
    parser.add_argument('--scrapings', action='store_true')
    args = parser.parse_args()

    if args.scrapings:
        snaps = listar_snapshots_scraping()
        print(f"\n{'Archivo':50} | {'Fecha':10} | {'Hash':12} | {'Tamaño':8}")
        print("-" * 90)
        for s in snaps:
            print(f"{s['archivo']:50} | {s['fecha']:10} | {s['hash']:12} | {s['tamanio_kb']:>6} KB")
    else:
        historial = cargar_historial(propiedad=args.propiedad, limite=args.ultimas)
        print(f"\n{len(historial)} valuaciones encontradas")
        print(f"\n{'Fecha':17} | {'Propiedad':15} | {'Valor USD':>10} | {'m² base':>8} | {'Motivo':20}")
        print("-" * 90)
        for r in historial:
            try:
                ts = datetime.fromisoformat(r['timestamp']).strftime("%d/%m/%Y %H:%M")
            except:
                ts = r['timestamp'][:16]
            res = r.get('resultado', {})
            mkt = r.get('snapshot_mercado', {})
            print(f"{ts:17} | {r.get('propiedad','?'):15} | "
                  f"${res.get('valor_venta',0):>9,.0f} | "
                  f"${mkt.get('m2_base_venta',0):>7,.0f} | "
                  f"{r.get('razon_recalculo','?')[:20]:20}")

if __name__ == "__main__":
    main()

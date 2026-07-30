#!/usr/bin/env python3
"""
CT Alquiler: Análisis de tendencia temporal desde scraping propio.
Calcula el CT (corrección temporal) para alquileres comparando datos
de cache_scraping.json con fuentes oficiales (IPEC, ICL, CESO).
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
import math


def load_alquileres(cache_path):
    """Carga y filtra propiedades de alquiler del cache."""
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    props = data.get('propiedades', [])
    alquileres = []
    
    for p in props:
        if p.get('operacion') != 'alquiler':
            continue
        
        # Validaciones básicas
        precio = p.get('precio', 0) or 0
        m2 = p.get('m2_cubiertos', 0) or p.get('m2', 0) or 0
        date_created = p.get('date_created', '')
        moneda = (p.get('moneda', '') or '').upper()
        
        if precio < 5000 or m2 <= 0 or not date_created:
            continue
        
        # Filtro de calidad: excluir valores sospechosos
        if moneda == 'USD':
            valor_m2 = precio / m2 if m2 > 0 else 0
            if valor_m2 > 30:  # Precio de venta, no alquiler
                continue
        elif moneda == 'ARS':
            valor_m2 = precio / m2 if m2 > 0 else 0
            if valor_m2 < 500:  # Probablemente habitación o alquiler semanal
                continue
        
        # Parsear fecha
        try:
            if 'T' in date_created:
                fecha = datetime.fromisoformat(date_created.replace('Z', '+00:00'))
            else:
                fecha = datetime.strptime(date_created[:10], '%Y-%m-%d')
        except (ValueError, TypeError):
            continue
        
        # Normalizar a ARS/m²
        if moneda == 'USD':
            # Usar un tipo de cambio fijo razonable para el período
            # El Binance API puede no estar disponible offline
            dolar = 1480.0  # USD/ARS approx
            precio_ars = precio * dolar
        elif moneda == 'ARS':
            precio_ars = precio
        else:
            continue
        
        precio_m2_ars = precio_ars / m2
        
        dorms = p.get('dormitorios', 0) or 0
        
        alquileres.append({
            'fecha': fecha,
            'mes': fecha.strftime('%Y-%m'),
            'precio': precio,
            'precio_ars': precio_ars,
            'm2': m2,
            'precio_m2_ars': precio_m2_ars,
            'moneda': moneda,
            'dormitorios': dorms,
            'direccion': (p.get('direccion', '') or '')[:40],
        })
    
    return alquileres


def group_by_month(alquileres):
    """Agrupa alquileres por mes y calcula mediana."""
    by_month = defaultdict(list)
    for a in alquileres:
        by_month[a['mes']].append(a)
    
    result = {}
    for mes, entries in sorted(by_month.items()):
        if len(entries) < 5:
            continue  # Requisito mínimo: 5 observaciones por mes
        
        precios = sorted([e['precio_m2_ars'] for e in entries])
        n = len(precios)
        median = precios[n // 2] if n % 2 == 1 else (precios[n // 2 - 1] + precios[n // 2]) / 2
        
        result[mes] = {
            'median': median,
            'n': n,
            'min': precios[0],
            'max': precios[-1],
            'p25': precios[n // 4],
            'p75': precios[3 * n // 4],
        }
    
    return result


def group_by_dorms_and_month(alquileres):
    """Agrupa por dormitorios y mes."""
    by_dorms = defaultdict(list)
    for a in alquileres:
        d = a['dormitorios']
        if d in (1, 2, 3):
            by_dorms[d].append(a)
    
    result = {}
    for dorms, entries in by_dorms.items():
        result[dorms] = group_by_month(entries)
    
    return result


def calculate_cagr(first_median, last_median, months):
    """Calcula CAGR anual."""
    if first_median <= 0 or last_median <= 0 or months <= 0:
        return None
    return (last_median / first_median) ** (12 / months) - 1


def linear_regression(x_vals, y_vals):
    """Regresión lineal simple. Retorna (pendiente, r2)."""
    n = len(x_vals)
    if n < 2:
        return None, None
    
    sum_x = sum(x_vals)
    sum_y = sum(y_vals)
    sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
    sum_x2 = sum(x * x for x in x_vals)
    
    denom = n * sum_x2 - sum_x ** 2
    if denom == 0:
        return None, None
    
    pendiente = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - pendiente * sum_x) / n
    
    # R²
    y_mean = sum_y / n
    ss_res = sum((y - (pendiente * x + intercept)) ** 2 for x, y in zip(x_vals, y_vals))
    ss_tot = sum((y - y_mean) ** 2 for y in y_vals)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    return pendiente, r2


def print_report(monthly_data, by_dorms_data, total_count, usd_count, ars_count):
    """Imprime el reporte completo."""
    print("=" * 70)
    print("  CT ALQUILER: ANÁLISIS DE TENDENCIA TEMPORAL")
    print("=" * 70)
    print(f"\nDataset: {total_count:,} alquileres (USD: {usd_count:,}, ARS: {ars_count:,})")
    
    if not monthly_data:
        print("\n❌ No hay suficientes datos (meses con n≥5) para calcular CT.")
        return
    
    months_sorted = sorted(monthly_data.keys())
    first_month = months_sorted[0]
    last_month = months_sorted[-1]
    first_data = monthly_data[first_month]
    last_data = monthly_data[last_month]
    
    print(f"Periodo válido: {first_month} a {last_month}")
    print(f"Meses con n>=5: {len(monthly_data)}")
    
    # ── Mediana mensual ──
    print(f"\n{'─' * 70}")
    print("  MEDIANA MENSUAL ARS/m²")
    print(f"{'─' * 70}")
    print(f"{'Mes':<10} {'Mediana':>12} {'n':>5} {'P25':>12} {'P75':>12}")
    print(f"{'─' * 10} {'─' * 12} {'─' * 5} {'─' * 12} {'─' * 12}")
    
    for mes in months_sorted:
        d = monthly_data[mes]
        print(f"{mes:<10} {d['median']:>12,.0f} {d['n']:>5} {d['p25']:>12,.0f} {d['p75']:>12,.0f}")
    
    # ── Tendencia general ──
    n_months = len(months_sorted)
    cagr = calculate_cagr(first_data['median'], last_data['median'], n_months)
    
    # Regresión lineal
    x_vals = list(range(n_months))
    y_vals = [monthly_data[m]['median'] for m in months_sorted]
    pendiente, r2 = linear_regression(x_vals, y_vals)
    
    print(f"\n{'─' * 70}")
    print("  TENDENCIA GENERAL")
    print(f"{'─' * 70}")
    
    if cagr is not None:
        ct_anual = cagr
        ct_mensual = (1 + cagr) ** (1/12) - 1
        print(f"  Primera mediana ({first_month}):  ${first_data['median']:,.0f} ARS/m²")
        print(f"  Última mediana ({last_month}):    ${last_data['median']:,.0f} ARS/m²")
        print(f"  Variación total:                   {((last_data['median'] / first_data['median']) - 1) * 100:+.1f}%")
        print(f"  Período:                           {n_months} meses")
        print(f"\n  CAGR anual:                        {ct_anual * 100:+.1f}%")
        print(f"  CT mensual:                        {ct_mensual * 100:+.2f}%")
        print(f"  CT Rate anual:                     {ct_anual:+.4f}")
    
    if pendiente is not None:
        print(f"\n  Regresión lineal:")
        print(f"    Pendiente:    {pendiente:+,.0f} ARS/m²/mes")
        print(f"    R²:          {r2:.3f}")
    
    # ── Por dormitorios ──
    print(f"\n{'─' * 70}")
    print("  CT POR DORMITORIOS")
    print(f"{'─' * 70}")
    print(f"{'Dorm':>5} {'CAGR Anual':>12} {'CT Mensual':>12} {'Meses':>6} {'Primera':>12} {'Última':>12}")
    print(f"{'─' * 5} {'─' * 12} {'─' * 12} {'─' * 6} {'─' * 12} {'─' * 12}")
    
    for dorms in [1, 2, 3]:
        if dorms in by_dorms_data and by_dorms_data[dorms]:
            dm = by_dorms_data[dorms]
            dm_months = sorted(dm.keys())
            if len(dm_months) >= 2:
                first = dm[dm_months[0]]
                last = dm[dm_months[-1]]
                cagr_d = calculate_cagr(first['median'], last['median'], len(dm_months))
                ct_m = (1 + cagr_d) ** (1/12) - 1 if cagr_d else 0
                print(f"{dorms:>5}d {cagr_d * 100:>+11.1f}% {ct_m * 100:>+11.2f}% {len(dm_months):>6} ${first['median']:>11,.0f} ${last['median']:>11,.0f}")
            else:
                print(f"{dorms:>5}d {'N/A':>12} {'N/A':>12} {len(dm_months):>6} {'N/A':>12} {'N/A':>12}")
        else:
            print(f"{dorms:>5}d {'sin datos':>12} {'sin datos':>12} {'0':>6} {'N/A':>12} {'N/A':>12}")
    
    # ── Comparación con fuentes oficiales ──
    print(f"\n{'─' * 70}")
    print("  COMPARACIÓN CON FUENTES OFICIALES")
    print(f"{'─' * 70}")
    print(f"{'Fuente':<25} {'Tasa YoY':>12} {'vs Nuestro CT':>15}")
    print(f"{'─' * 25} {'─' * 12} {'─' * 15}")
    
    fuentes = [
        ("IPEC Alquiler Sta. Fe", 0.399, "Jun 2026"),
        ("ICL (BCRA)", 0.326, "May 2026"),
        ("CESO Rosario", 0.321, "May 2026"),
        ("COCIR/UNR ofertas", 0.667, "Mar 2025"),
    ]
    
    our_rate = cagr if cagr else 0
    
    for nombre, tasa, periodo in fuentes:
        diff = our_rate - tasa
        print(f"{nombre:<25} {tasa * 100:>+11.1f}% {diff * 100:>+14.1f}pp")
    
    # CT venta actual
    print(f"\n{'─' * 70}")
    print("  DIVERGENCIA ALQUILER vs VENTA")
    print(f"{'─' * 70}")
    print(f"  Nuestro CT alquiler:   {our_rate * 100:+.1f}% anual")
    print(f"  CT venta (resto):      -0.1% anual")
    print(f"  CT venta (centro):     +1.2% anual")
    print(f"  CT venta (PN):         +3.9% anual")
    print(f"\n  → Los mercados se mueven en DIRECCIONES OPUESTAS")
    print(f"  → El CT de venta NO es apropiado para alquileres")
    
    # ── Recomendación ──
    print(f"\n{'─' * 70}")
    print("  RECOMENDACIÓN")
    print(f"{'─' * 70}")
    
    if cagr is not None:
        # Promedio ponderado: 60% nuestros datos + 40% IPEC
        our_weight = 0.60
        ipec_weight = 0.40
        ct_sugerido = our_rate * our_weight + 0.399 * ipec_weight
        
        print(f"  CT alquiler sugerido:  {ct_sugerido * 100:+.1f}% anual")
        print(f"  (60% nuestros datos + 40% IPEC)")
        print(f"\n  Para zonas_depreciacion.json:")
        print(f'    "ct_alquiler_rate": {ct_sugerido:.4f}')
        
        # Por dormitorios si están disponibles
        print(f"\n  Por dormitorios (si hay datos suficientes):")
        for dorms in [1, 2, 3]:
            if dorms in by_dorms_data and by_dorms_data[dorms]:
                dm = by_dorms_data[dorms]
                dm_months = sorted(dm.keys())
                if len(dm_months) >= 2:
                    first = dm[dm_months[0]]
                    last = dm[dm_months[-1]]
                    cagr_d = calculate_cagr(first['median'], last['median'], len(dm_months))
                    if cagr_d:
                        ct_d = cagr_d * our_weight + 0.399 * ipec_weight
                        print(f"    {dorms}d: {ct_d * 100:+.1f}% anual (ct_rate={ct_d:.4f})")
    else:
        print("  No hay suficientes datos para recomendación.")
        print("  Usar IPEC como proxy: +39.9% anual (ct_rate=0.3990)")
    
    print(f"\n{'=' * 70}")


def main():
    # Encontrar cache_scraping.json
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_path = os.path.join(base_dir, 'cache_scraping.json')
    
    if not os.path.exists(cache_path):
        print(f"Error: No se encontró {cache_path}")
        sys.exit(1)
    
    print("Cargando alquileres desde cache_scraping.json...")
    alquileres = load_alquileres(cache_path)
    
    total = len(alquileres)
    usd_count = sum(1 for a in alquileres if a['moneda'] == 'USD')
    ars_count = sum(1 for a in alquileres if a['moneda'] == 'ARS')
    
    print(f"Alquileres válidos: {total:,} (USD: {usd_count:,}, ARS: {ars_count:,})")
    
    # Agrupar por mes
    monthly_data = group_by_month(alquileres)
    
    # Agrupar por dormitorios y mes
    by_dorms_data = group_by_dorms_and_month(alquileres)
    
    # Imprimir reporte
    print_report(monthly_data, by_dorms_data, total, usd_count, ars_count)


if __name__ == '__main__':
    main()

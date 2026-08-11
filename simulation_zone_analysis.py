#!/usr/bin/env python3
"""
Zone-by-Zone Alquiler Analysis
"""

import json
import numpy as np
from collections import defaultdict

MAD_THRESHOLD = 3.0
MODIFIED_Z_FACTOR = 0.6745
MAX_USD_M2 = 25
MIN_ARS_M2 = 1000
MAX_ARS_M2 = 20000

def load_data():
    with open('cache_scraping.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['propiedades']

def run_analysis():
    entries = load_data()
    alquiler = [e for e in entries if e.get('operacion', '').lower() == 'alquiler']
    
    # Group by zone
    zones = defaultdict(lambda: {'ARS': [], 'USD': []})
    for entry in alquiler:
        zone = entry.get('zona', 'Sin zona')
        moneda = entry.get('moneda', '').upper()
        zones[zone][moneda].append(entry)
    
    print("=" * 100)
    print("ZONE-BY-ZONE ALQUILER ANALYSIS")
    print("=" * 100)
    print()
    
    print(f"{'Zone':<20} {'ARS':>6} {'USD':>6} {'ARS Med':>10} {'USD Med':>10} {'ARS MAD':>10} {'USD MAD':>10}")
    print("-" * 100)
    
    for zone in sorted(zones.keys()):
        ars = [e['valor_m2'] for e in zones[zone]['ARS'] if e.get('valor_m2', 0) > 0]
        usd = [e['valor_m2'] for e in zones[zone]['USD'] if e.get('valor_m2', 0) > 0]
        
        ars_median = np.median(ars) if ars else 0
        usd_median = np.median(usd) if usd else 0
        
        ars_mad = np.median(np.abs(np.array(ars) - ars_median)) if len(ars) > 2 else 0
        usd_mad = np.median(np.abs(np.array(usd) - usd_median)) if len(usd) > 2 else 0
        
        print(f"{zone:<20} {len(ars):>6} {len(usd):>6} {ars_median:>10,.0f} {usd_median:>10.2f} {ars_mad:>10,.0f} {usd_mad:>10.2f}")
    
    print()
    
    # Show "Otro" zone in detail (most entries)
    print("=" * 100)
    print("DETAILED ANALYSIS - 'Otro' ZONE (contains most entries)")
    print("=" * 100)
    print()
    
    otro_ars = [e for e in zones['Otro']['ARS']]
    otro_usd = [e for e in zones['Otro']['USD']]
    
    ars_values = [e['valor_m2'] for e in otro_ars if e.get('valor_m2', 0) > 0]
    usd_values = [e['valor_m2'] for e in otro_usd if e.get('valor_m2', 0) > 0]
    
    print(f"ARS entries: {len(ars_values)}")
    print(f"USD entries: {len(usd_values)}")
    print()
    
    # Distribution
    print("ARS Distribution:")
    for low, high, label in [(0, 5000, '< 5k'), (5000, 10000, '5k-10k'), (10000, 15000, '10k-15k'), (15000, 20000, '15k-20k'), (20000, 100000, '> 20k')]:
        count = sum(1 for v in ars_values if low <= v < high)
        pct = count / len(ars_values) * 100 if ars_values else 0
        print(f"  {label}: {count} ({pct:.1f}%)")
    print()
    
    print("USD Distribution:")
    for low, high, label in [(0, 5, '< 5'), (5, 10, '5-10'), (10, 15, '10-15'), (15, 25, '15-25'), (25, 1000, '> 25')]:
        count = sum(1 for v in usd_values if low <= v < high)
        pct = count / len(usd_values) * 100 if usd_values else 0
        print(f"  {label}: {count} ({pct:.1f}%)")
    print()
    
    # Effect of exclusion
    print("Effect of Exclusion:")
    
    # ARS
    ars_clean = [v for v in ars_values if MIN_ARS_M2 <= v <= MAX_ARS_M2]
    if len(ars_clean) >= 3:
        arr = np.array(ars_clean)
        med = np.median(arr)
        mad = np.median(np.abs(arr - med))
        z = MODIFIED_Z_FACTOR * (arr - med) / mad if mad > 0 else np.zeros_like(arr)
        arr_final = arr[np.abs(z) <= MAD_THRESHOLD]
        final_median = np.median(arr_final)
    else:
        final_median = np.median(ars_clean) if ars_clean else 0
    
    original_median = np.median(ars_values) if ars_values else 0
    print(f"  ARS: {original_median:,.0f} -> {final_median:,.0f} ({((final_median/original_median - 1)*100) if original_median else 0:+.1f}%)")
    
    # USD
    usd_clean = [v for v in usd_values if v <= MAX_USD_M2]
    if len(usd_clean) >= 3:
        arr = np.array(usd_clean)
        med = np.median(arr)
        mad = np.median(np.abs(arr - med))
        z = MODIFIED_Z_FACTOR * (arr - med) / mad if mad > 0 else np.zeros_like(arr)
        arr_final = arr[np.abs(z) <= MAD_THRESHOLD]
        final_median = np.median(arr_final)
    else:
        final_median = np.median(usd_clean) if usd_clean else 0
    
    original_median = np.median(usd_values) if usd_values else 0
    print(f"  USD: {original_median:.2f} -> {final_median:.2f} ({((final_median/original_median - 1)*100) if original_median else 0:+.1f}%)")
    print()
    
    # Show the extreme outliers
    print("=" * 100)
    print("EXTREME OUTLIERS (should not exist in alquiler)")
    print("=" * 100)
    print()
    
    extreme_usd = [e for e in otro_usd if e.get('valor_m2', 0) > 25]
    print(f"USD entries with valor_m2 > 25: {len(extreme_usd)}")
    print("Sample (first 5):")
    for e in extreme_usd[:5]:
        print(f"  {e.get('valor_m2', 0):,.2f} USD/m2 - {e.get('direccion', 'N/A')[:50]}")
    print()
    
    extreme_ars = [e for e in otro_ars if e.get('valor_m2', 0) > 20000]
    print(f"ARS entries with valor_m2 > 20,000: {len(extreme_ars)}")
    print("Sample (first 5):")
    for e in extreme_ars[:5]:
        print(f"  {e.get('valor_m2', 0):,.0f} ARS/m2 - {e.get('direccion', 'N/A')[:50]}")

if __name__ == '__main__':
    run_analysis()

#!/usr/bin/env python3
"""
Detailed Analysis of Alquiler Data Distribution
"""

import json
import numpy as np
from collections import defaultdict

# Configuration
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
    
    ars = [e for e in alquiler if e.get('moneda', '').upper() == 'ARS']
    usd = [e for e in alquiler if e.get('moneda', '').upper() == 'USD']
    
    print("=" * 80)
    print("DISTRIBUTION ANALYSIS")
    print("=" * 80)
    print()
    
    # ARS Analysis
    print("ARS ENTRIES:")
    ars_values = [e['valor_m2'] for e in ars if e.get('valor_m2', 0) > 0]
    print(f"  Count: {len(ars_values)}")
    print(f"  Mean: {np.mean(ars_values):,.0f}")
    print(f"  Median: {np.median(ars_values):,.0f}")
    print(f"  Std: {np.std(ars_values):,.0f}")
    print(f"  Min: {min(ars_values):,.0f}")
    print(f"  Max: {max(ars_values):,.0f}")
    print()
    
    # Percentiles
    print("  Percentiles:")
    for p in [10, 25, 50, 75, 90, 95, 99]:
        print(f"    P{p}: {np.percentile(ars_values, p):,.0f}")
    print()
    
    # Count by ranges
    print("  Distribution:")
    ranges = [
        (0, 1000, '< 1,000'),
        (1000, 5000, '1,000 - 5,000'),
        (5000, 10000, '5,000 - 10,000'),
        (10000, 15000, '10,000 - 15,000'),
        (15000, 20000, '15,000 - 20,000'),
        (20000, 50000, '> 20,000'),
    ]
    for low, high, label in ranges:
        count = sum(1 for v in ars_values if low <= v < high)
        pct = count / len(ars_values) * 100 if ars_values else 0
        print(f"    {label}: {count} ({pct:.1f}%)")
    print()
    
    # USD Analysis
    print("USD ENTRIES:")
    usd_values = [e['valor_m2'] for e in usd if e.get('valor_m2', 0) > 0]
    print(f"  Count: {len(usd_values)}")
    print(f"  Mean: {np.mean(usd_values):.2f}")
    print(f"  Median: {np.median(usd_values):.2f}")
    print(f"  Std: {np.std(usd_values):.2f}")
    print(f"  Min: {min(usd_values):.2f}")
    print(f"  Max: {max(usd_values):.2f}")
    print()
    
    # Percentiles
    print("  Percentiles:")
    for p in [10, 25, 50, 75, 90, 95, 99]:
        print(f"    P{p}: {np.percentile(usd_values, p):.2f}")
    print()
    
    # Count by ranges
    print("  Distribution:")
    ranges = [
        (0, 5, '< 5'),
        (5, 10, '5 - 10'),
        (10, 15, '10 - 15'),
        (15, 20, '15 - 20'),
        (20, 25, '20 - 25'),
        (25, 50, '> 25'),
    ]
    for low, high, label in ranges:
        count = sum(1 for v in usd_values if low <= v < high)
        pct = count / len(usd_values) * 100 if usd_values else 0
        print(f"    {label}: {count} ({pct:.1f}%)")
    print()
    
    # MAD Analysis
    print("=" * 80)
    print("MAD-BASED OUTLIER ANALYSIS")
    print("=" * 80)
    print()
    
    # ARS
    ars_arr = np.array(ars_values)
    ars_median = np.median(ars_arr)
    ars_mad = np.median(np.abs(ars_arr - ars_median))
    ars_z = MODIFIED_Z_FACTOR * (ars_arr - ars_median) / ars_mad if ars_mad > 0 else np.zeros_like(ars_arr)
    
    ars_outliers = np.abs(ars_z) > MAD_THRESHOLD
    print(f"ARS:")
    print(f"  Median: {ars_median:,.0f}")
    print(f"  MAD: {ars_mad:,.0f}")
    print(f"  Modified Z threshold: {MAD_THRESHOLD}")
    print(f"  Outliers detected: {np.sum(ars_outliers)}")
    print()
    
    if np.sum(ars_outliers) > 0:
        print("  Top outliers (by absolute z-score):")
        outlier_indices = np.argsort(np.abs(ars_z))[::-1][:10]
        for i in outlier_indices:
            if ars_outliers[i]:
                print(f"    valor_m2={ars_arr[i]:,.0f}, z-score={ars_z[i]:.2f}")
    print()
    
    # USD
    usd_arr = np.array(usd_values)
    usd_median = np.median(usd_arr)
    usd_mad = np.median(np.abs(usd_arr - usd_median))
    usd_z = MODIFIED_Z_FACTOR * (usd_arr - usd_median) / usd_mad if usd_mad > 0 else np.zeros_like(usd_arr)
    
    usd_outliers = np.abs(usd_z) > MAD_THRESHOLD
    print(f"USD:")
    print(f"  Median: {usd_median:.2f}")
    print(f"  MAD: {usd_mad:.2f}")
    print(f"  Modified Z threshold: {MAD_THRESHOLD}")
    print(f"  Outliers detected: {np.sum(usd_outliers)}")
    print()
    
    if np.sum(usd_outliers) > 0:
        print("  Top outliers (by absolute z-score):")
        outlier_indices = np.argsort(np.abs(usd_z))[::-1][:10]
        for i in outlier_indices:
            if usd_outliers[i]:
                print(f"    valor_m2={usd_arr[i]:.2f}, z-score={usd_z[i]:.2f}")
    print()
    
    # Hard rule exclusions
    print("=" * 80)
    print("HARD RULE EXCLUSIONS")
    print("=" * 80)
    print()
    
    # ARS exclusions
    ars_high = sum(1 for v in ars_values if v > MAX_ARS_M2)
    ars_low = sum(1 for v in ars_values if v < MIN_ARS_M2)
    print(f"ARS:")
    print(f"  > 20,000: {ars_high}")
    print(f"  < 1,000: {ars_low}")
    print(f"  Total hard excluded: {ars_high + ars_low}")
    print()
    
    # USD exclusions
    usd_high = sum(1 for v in usd_values if v > MAX_USD_M2)
    print(f"USD:")
    print(f"  > 25: {usd_high}")
    print()
    
    # Simulate the EFFECT of exclusion
    print("=" * 80)
    print("EFFECT OF EXCLUSION ON MEDIAN")
    print("=" * 80)
    print()
    
    # Remove hard outliers from ARS
    ars_clean_hard = [v for v in ars_values if MIN_ARS_M2 <= v <= MAX_ARS_M2]
    ars_clean_median = np.median(ars_clean_hard) if ars_clean_hard else 0
    print(f"ARS after hard rules: {len(ars_clean_hard)} entries")
    print(f"  Median: {ars_clean_median:,.0f}")
    print(f"  Change from original: {((ars_clean_median / ars_median - 1) * 100) if ars_median else 0:+.1f}%")
    print()
    
    # Remove MAD outliers from clean ARS
    if len(ars_clean_hard) >= 3:
        arr = np.array(ars_clean_hard)
        med = np.median(arr)
        mad = np.median(np.abs(arr - med))
        z = MODIFIED_Z_FACTOR * (arr - med) / mad if mad > 0 else np.zeros_like(arr)
        mask = np.abs(z) <= MAD_THRESHOLD
        ars_final = arr[mask]
        ars_final_median = np.median(ars_final)
        print(f"ARS after MAD exclusion: {len(ars_final)} entries")
        print(f"  Median: {ars_final_median:,.0f}")
        print(f"  Change from hard-only: {((ars_final_median / ars_clean_median - 1) * 100) if ars_clean_median else 0:+.1f}%")
        print(f"  Change from original: {((ars_final_median / ars_median - 1) * 100) if ars_median else 0:+.1f}%")
    print()
    
    # USD
    usd_clean_hard = [v for v in usd_values if v <= MAX_USD_M2]
    usd_clean_median = np.median(usd_clean_hard) if usd_clean_hard else 0
    print(f"USD after hard rules: {len(usd_clean_hard)} entries")
    print(f"  Median: {usd_clean_median:.2f}")
    print(f"  Change from original: {((usd_clean_median / usd_median - 1) * 100) if usd_median else 0:+.1f}%")
    print()
    
    if len(usd_clean_hard) >= 3:
        arr = np.array(usd_clean_hard)
        med = np.median(arr)
        mad = np.median(np.abs(arr - med))
        z = MODIFIED_Z_FACTOR * (arr - med) / mad if mad > 0 else np.zeros_like(arr)
        mask = np.abs(z) <= MAD_THRESHOLD
        usd_final = arr[mask]
        usd_final_median = np.median(usd_final)
        print(f"USD after MAD exclusion: {len(usd_final)} entries")
        print(f"  Median: {usd_final_median:.2f}")
        print(f"  Change from hard-only: {((usd_final_median / usd_clean_median - 1) * 100) if usd_clean_median else 0:+.1f}%")
        print(f"  Change from original: {((usd_final_median / usd_median - 1) * 100) if usd_median else 0:+.1f}%")

if __name__ == '__main__':
    run_analysis()

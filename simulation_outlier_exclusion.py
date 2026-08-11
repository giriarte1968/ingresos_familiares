#!/usr/bin/env python3
"""
Simulation: Outlier Exclusion for Alquiler Data in Rosario, Argentina
=====================================================================
Standards:
- Standard sensitivity (MAD threshold = 3.0)
- Exclude completely (not reduce weight)
- Hard rules for impossible values
"""

import json
import numpy as np
from collections import defaultdict
from datetime import datetime

# Configuration
MAD_THRESHOLD = 3.0
MODIFIED_Z_FACTOR = 0.6745

# Hard rules
MAX_USD_M2 = 25
MIN_ARS_M2 = 1000
MAX_ARS_M2 = 20000
MIN_PRICE_ARS = 500
MIN_M2 = 15
MAX_M2 = 500

def load_data():
    with open('cache_scraping.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['propiedades']

def calculate_mad(values):
    """Calculate Median Absolute Deviation"""
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    return median, mad

def apply_hard_rules(entry):
    """Apply Tier 1 hard rules. Returns (excluded: bool, reason: str)"""
    moneda = entry.get('moneda', '').upper()
    valor_m2 = entry.get('valor_m2', 0)
    precio = entry.get('precio', 0)
    m2 = entry.get('m2', 0)
    
    if moneda == 'USD' and valor_m2 > MAX_USD_M2:
        return True, 'VENTA_MISLABELED'
    
    if moneda == 'ARS' and valor_m2 < MIN_ARS_M2:
        return True, 'SUSPICIOUS_LOW'
    
    if moneda == 'ARS' and valor_m2 > MAX_ARS_M2:
        return True, 'SUSPICIOUS_HIGH'
    
    if precio < MIN_PRICE_ARS and moneda == 'ARS':
        return True, 'INCOMPLETE_DATA'
    
    if m2 < MIN_M2:
        return True, 'SMALL_AREA'
    
    if m2 > MAX_M2:
        return True, 'LARGE_AREA'
    
    return False, None

def calculate_modified_z_scores(values):
    """Calculate Modified Z-Score for each value"""
    if len(values) < 3:
        return np.zeros_like(values)
    
    median, mad = calculate_mad(values)
    
    if mad == 0:
        return np.zeros_like(values)
    
    modified_z = MODIFIED_Z_FACTOR * (values - median) / mad
    return modified_z

def run_simulation():
    print("=" * 80)
    print("SIMULATION: Outlier Exclusion for Alquiler Data")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # Load data
    entries = load_data()
    print(f"Total entries in cache: {len(entries)}")
    print()
    
    # Filter alquiler entries
    alquiler_entries = [e for e in entries if e.get('operacion', '').lower() == 'alquiler']
    print(f"Alquiler entries: {len(alquiler_entries)}")
    print()
    
    # Separate by currency
    ars_entries = [e for e in alquiler_entries if e.get('moneda', '').upper() == 'ARS']
    usd_entries = [e for e in alquiler_entries if e.get('moneda', '').upper() == 'USD']
    
    print(f"ARS entries: {len(ars_entries)}")
    print(f"USD entries: {len(usd_entries)}")
    print()
    
    # Group by zone
    zones = defaultdict(lambda: {'ARS': [], 'USD': []})
    for entry in alquiler_entries:
        zone = entry.get('zona', 'Sin zona')
        moneda = entry.get('moneda', '').upper()
        zones[zone][moneda].append(entry)
    
    print("=" * 80)
    print("ZONE ANALYSIS")
    print("=" * 80)
    print()
    
    zone_results = {}
    
    for zone in sorted(zones.keys()):
        print(f"ZONE: {zone}")
        print("-" * 80)
        
        ars_zone = zones[zone]['ARS']
        usd_zone = zones[zone]['USD']
        
        # Original stats
        original_ars_count = len(ars_zone)
        original_usd_count = len(usd_zone)
        
        print(f"  Original ARS entries: {original_ars_count}")
        print(f"  Original USD entries: {original_usd_count}")
        
        # Apply hard rules to ARS
        ars_excluded = defaultdict(list)
        ars_remaining = []
        
        for entry in ars_zone:
            excluded, reason = apply_hard_rules(entry)
            if excluded:
                ars_excluded[reason].append(entry)
            else:
                ars_remaining.append(entry)
        
        # Apply hard rules to USD
        usd_excluded = defaultdict(list)
        usd_remaining = []
        
        for entry in usd_zone:
            excluded, reason = apply_hard_rules(entry)
            if excluded:
                usd_excluded[reason].append(entry)
            else:
                usd_remaining.append(entry)
        
        print(f"\n  After Hard Rules:")
        print(f"    ARS excluded: {sum(len(v) for v in ars_excluded.values())}")
        for reason, entries in ars_excluded.items():
            print(f"      - {reason}: {len(entries)}")
        print(f"    ARS remaining: {len(ars_remaining)}")
        
        print(f"    USD excluded: {sum(len(v) for v in usd_excluded.values())}")
        for reason, entries in usd_excluded.items():
            print(f"      - {reason}: {len(entries)}")
        print(f"    USD remaining: {len(usd_remaining)}")
        
        # Apply MAD-based exclusion
        mad_excluded_ars = 0
        mad_excluded_usd = 0
        
        if len(ars_remaining) >= 3:
            ars_values = np.array([e['valor_m2'] for e in ars_remaining])
            ars_z_scores = calculate_modified_z_scores(ars_values)
            
            mad_excluded_ars_mask = np.abs(ars_z_scores) > MAD_THRESHOLD
            mad_excluded_ars = np.sum(mad_excluded_ars_mask)
            
            ars_final = [e for e, excluded in zip(ars_remaining, ~mad_excluded_ars_mask) if excluded]
        else:
            ars_final = ars_remaining
        
        if len(usd_remaining) >= 3:
            usd_values = np.array([e['valor_m2'] for e in usd_remaining])
            usd_z_scores = calculate_modified_z_scores(usd_values)
            
            mad_excluded_usd_mask = np.abs(usd_z_scores) > MAD_THRESHOLD
            mad_excluded_usd = np.sum(mad_excluded_usd_mask)
            
            usd_final = [e for e, excluded in zip(usd_remaining, ~mad_excluded_usd_mask) if excluded]
        else:
            usd_final = usd_remaining
        
        print(f"\n  After MAD-based Exclusion (threshold={MAD_THRESHOLD}):")
        print(f"    ARS excluded: {mad_excluded_ars}")
        print(f"    USD excluded: {mad_excluded_usd}")
        
        print(f"\n  FINAL:")
        print(f"    ARS remaining: {len(ars_final)}")
        print(f"    USD remaining: {len(usd_final)}")
        
        # Calculate new medians
        new_median_ars = np.median([e['valor_m2'] for e in ars_final]) if ars_final else 0
        new_median_usd = np.median([e['valor_m2'] for e in usd_final]) if usd_final else 0
        
        old_median_ars = np.median([e['valor_m2'] for e in ars_zone]) if ars_zone else 0
        old_median_usd = np.median([e['valor_m2'] for e in usd_zone]) if usd_zone else 0
        
        print(f"\n  Median valor_m2:")
        print(f"    ARS: {old_median_ars:,.0f} -> {new_median_ars:,.0f} ({((new_median_ars/old_median_ars - 1)*100) if old_median_ars else 0:+.1f}%)")
        print(f"    USD: {old_median_usd:,.2f} -> {new_median_usd:,.2f} ({((new_median_usd/old_median_usd - 1)*100) if old_median_usd else 0:+.1f}%)")
        
        zone_results[zone] = {
            'original_ars': original_ars_count,
            'original_usd': original_usd_count,
            'ars_excluded_hard': sum(len(v) for v in ars_excluded.values()),
            'usd_excluded_hard': sum(len(v) for v in usd_excluded.values()),
            'ars_excluded_mad': mad_excluded_ars,
            'usd_excluded_mad': mad_excluded_usd,
            'final_ars': len(ars_final),
            'final_usd': len(usd_final),
            'old_median_ars': old_median_ars,
            'new_median_ars': new_median_ars,
            'old_median_usd': old_median_usd,
            'new_median_usd': new_median_usd,
            'ars_entries_final': ars_final,
            'usd_entries_final': usd_final
        }
        
        print()
    
    # Summary table
    print("=" * 80)
    print("SUMMARY TABLE - ZONE BY ZONE")
    print("=" * 80)
    print()
    print(f"{'Zone':<20} {'ARS Orig':>10} {'ARS Excl':>10} {'ARS Final':>10} {'USD Orig':>10} {'USD Excl':>10} {'USD Final':>10}")
    print("-" * 80)
    
    total_ars_orig = 0
    total_ars_excl = 0
    total_ars_final = 0
    total_usd_orig = 0
    total_usd_excl = 0
    total_usd_final = 0
    
    for zone in sorted(zone_results.keys()):
        r = zone_results[zone]
        total_ars_orig += r['original_ars']
        total_ars_excl += r['ars_excluded_hard'] + r['ars_excluded_mad']
        total_ars_final += r['final_ars']
        total_usd_orig += r['original_usd']
        total_usd_excl += r['usd_excluded_hard'] + r['usd_excluded_mad']
        total_usd_final += r['final_usd']
        
        print(f"{zone:<20} {r['original_ars']:>10} {r['ars_excluded_hard'] + r['ars_excluded_mad']:>10} {r['final_ars']:>10} {r['original_usd']:>10} {r['usd_excluded_hard'] + r['usd_excluded_mad']:>10} {r['final_usd']:>10}")
    
    print("-" * 80)
    print(f"{'TOTAL':<20} {total_ars_orig:>10} {total_ars_excl:>10} {total_ars_final:>10} {total_usd_orig:>10} {total_usd_excl:>10} {total_usd_final:>10}")
    print()
    
    # Overall medians
    all_final_ars = []
    all_final_usd = []
    for zone in zone_results:
        all_final_ars.extend(zone_results[zone]['ars_entries_final'])
        all_final_usd.extend(zone_results[zone]['usd_entries_final'])
    
    overall_new_median_ars = np.median([e['valor_m2'] for e in all_final_ars]) if all_final_ars else 0
    overall_new_median_usd = np.median([e['valor_m2'] for e in all_final_usd]) if all_final_usd else 0
    
    print(f"Overall new median ARS valor_m2: {overall_new_median_ars:,.0f}")
    print(f"Overall new median USD valor_m2: {overall_new_median_usd:,.2f}")
    print()
    
    return zone_results, overall_new_median_ars, overall_new_median_usd

if __name__ == '__main__':
    zone_results, new_median_ars, new_median_usd = run_simulation()

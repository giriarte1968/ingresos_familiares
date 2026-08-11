#!/usr/bin/env python3
"""
COMPLETE SIMULATION: Outlier Exclusion for Alquiler Data
========================================================
Includes:
1. Zone-by-zone exclusion analysis
2. Property alquiler calculations
3. Cap rate analysis
"""

import json
import numpy as np
from collections import defaultdict
from datetime import datetime

# Configuration
MAD_THRESHOLD = 3.0
MODIFIED_Z_FACTOR = 0.6745
USD_RATE = 1500  # USDT/ARS approximate

# Hard rules
MAX_USD_M2 = 25
MIN_ARS_M2 = 1000
MAX_ARS_M2 = 20000
MIN_PRICE_ARS = 500
MIN_M2 = 15
MAX_M2 = 500

# Properties to simulate
PROPERTIES = [
    {
        'nombre': 'Ayacucho 1234',
        'lat': -32.9333,
        'lon': -60.6407,
        'dormitorios': 3,
        'm2_cubiertos': 85,
        'm2_descubiertos': 0,
        'zona': 'Otro'
    },
    {
        'nombre': 'Mabel',
        'lat': -32.9175,
        'lon': -60.6825,
        'dormitorios': 2,
        'm2_cubiertos': 60,
        'm2_descubiertos': 0,
        'zona': 'Otro'
    },
    {
        'nombre': 'Vera Mujica',
        'lat': -32.9500,
        'lon': -60.6600,
        'dormitorios': 2,
        'm2_cubiertos': 70,
        'm2_descubiertos': 0,
        'zona': 'Otro'
    }
]

def load_data():
    with open('cache_scraping.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['propiedades']

def calculate_mad(values):
    median = np.median(values)
    mad = np.median(np.abs(values - median))
    return median, mad

def apply_hard_rules(entry):
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
    if len(values) < 3:
        return np.zeros_like(values)
    
    median, mad = calculate_mad(values)
    
    if mad == 0:
        return np.zeros_like(values)
    
    modified_z = MODIFIED_Z_FACTOR * (values - median) / mad
    return modified_z

def get_clean_medians_by_zone():
    """Get clean medians for each zone"""
    entries = load_data()
    alquiler = [e for e in entries if e.get('operacion', '').lower() == 'alquiler']
    
    zones = defaultdict(lambda: {'ARS': [], 'USD': []})
    for entry in alquiler:
        zone = entry.get('zona', 'Sin zona')
        moneda = entry.get('moneda', '').upper()
        zones[zone][moneda].append(entry)
    
    results = {}
    
    for zone in zones:
        # ARS
        ars_entries = [e for e in zones[zone]['ARS']]
        ars_filtered = []
        
        for entry in ars_entries:
            excluded, reason = apply_hard_rules(entry)
            if not excluded:
                ars_filtered.append(entry)
        
        if len(ars_filtered) >= 3:
            ars_values = np.array([e['valor_m2'] for e in ars_filtered])
            ars_z_scores = calculate_modified_z_scores(ars_values)
            mad_mask = np.abs(ars_z_scores) <= MAD_THRESHOLD
            ars_final = [e for e, keep in zip(ars_filtered, mad_mask) if keep]
        else:
            ars_final = ars_filtered
        
        # USD
        usd_entries = [e for e in zones[zone]['USD']]
        usd_filtered = []
        
        for entry in usd_entries:
            excluded, reason = apply_hard_rules(entry)
            if not excluded:
                usd_filtered.append(entry)
        
        if len(usd_filtered) >= 3:
            usd_values = np.array([e['valor_m2'] for e in usd_filtered])
            usd_z_scores = calculate_modified_z_scores(usd_values)
            mad_mask = np.abs(usd_z_scores) <= MAD_THRESHOLD
            usd_final = [e for e, keep in zip(usd_filtered, mad_mask) if keep]
        else:
            usd_final = usd_filtered
        
        # Calculate medians
        ars_median = np.median([e['valor_m2'] for e in ars_final]) if ars_final else 0
        usd_median = np.median([e['valor_m2'] for e in usd_final]) if usd_final else 0
        
        # Also calculate original medians for comparison
        original_ars_median = np.median([e['valor_m2'] for e in ars_entries]) if ars_entries else 0
        original_usd_median = np.median([e['valor_m2'] for e in usd_entries]) if usd_entries else 0
        
        results[zone] = {
            'ars_median': ars_median,
            'usd_median': usd_median,
            'original_ars_median': original_ars_median,
            'original_usd_median': original_usd_median,
            'n_ars_final': len(ars_final),
            'n_usd_final': len(usd_final),
            'n_ars_original': len(ars_entries),
            'n_usd_original': len(usd_entries)
        }
    
    return results

def get_overall_clean_medians():
    """Get overall clean medians (all zones combined)"""
    entries = load_data()
    alquiler = [e for e in entries if e.get('operacion', '').lower() == 'alquiler']
    
    all_ars = []
    all_usd = []
    
    for entry in alquiler:
        moneda = entry.get('moneda', '').upper()
        excluded, reason = apply_hard_rules(entry)
        if not excluded:
            if moneda == 'ARS':
                all_ars.append(entry)
            elif moneda == 'USD':
                all_usd.append(entry)
    
    # Apply MAD
    if len(all_ars) >= 3:
        ars_values = np.array([e['valor_m2'] for e in all_ars])
        ars_z_scores = calculate_modified_z_scores(ars_values)
        mad_mask = np.abs(ars_z_scores) <= MAD_THRESHOLD
        all_ars = [e for e, keep in zip(all_ars, mad_mask) if keep]
    
    if len(all_usd) >= 3:
        usd_values = np.array([e['valor_m2'] for e in all_usd])
        usd_z_scores = calculate_modified_z_scores(usd_values)
        mad_mask = np.abs(usd_z_scores) <= MAD_THRESHOLD
        all_usd = [e for e, keep in zip(all_usd, mad_mask) if keep]
    
    ars_median = np.median([e['valor_m2'] for e in all_ars]) if all_ars else 0
    usd_median = np.median([e['valor_m2'] for e in all_usd]) if all_usd else 0
    
    return ars_median, usd_median

def calculate_alquiler_for_property(prop, ars_median, use_ct=True):
    """Calculate alquiler for a property using ARS median"""
    
    # m2 equivalentes
    m2_equiv = prop['m2_cubiertos'] + (prop['m2_descubiertos'] * 0.1)
    
    # Base alquiler
    alq_base = m2_equiv * ars_median
    
    # CT adjustment (inflation)
    if use_ct:
        # Using 6 months as typical reference
        ct = (1.0 + 0.3014) ** (6 / 12.0)  # +30.14% annual
        alq_final = alq_base * ct
    else:
        alq_final = alq_base
    
    # Convert to USD
    alq_usd = alq_final / USD_RATE
    
    return {
        'm2_equiv': m2_equiv,
        'alq_base': alq_base,
        'alq_final_ars': alq_final,
        'alq_final_usd': alq_usd,
        'valor_m2_used': ars_median
    }

def calculate_cap_rate(alquiler_mensual_ars, valor_venta_usd):
    """Calculate cap rate from alquiler and property value"""
    alquiler_anual_usd = (alquiler_mensual_ars * 12) / USD_RATE
    cap_rate = alquiler_anual_usd / valor_venta_usd if valor_venta_usd > 0 else 0
    return cap_rate

def run_complete_simulation():
    print("=" * 120)
    print("COMPLETE SIMULATION: Outlier Exclusion for Alquiler Data in Rosario")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 120)
    print()
    
    # Configuration
    print("CONFIGURATION:")
    print(f"  MAD Threshold: {MAD_THRESHOLD}")
    print(f"  USD Rate: {USD_RATE} ARS/USD")
    print(f"  Hard Rules:")
    print(f"    - USD valor_m2 > {MAX_USD_M2} -> EXCLUDE")
    print(f"    - ARS valor_m2 < {MIN_ARS_M2} -> EXCLUDE")
    print(f"    - ARS valor_m2 > {MAX_ARS_M2} -> EXCLUDE")
    print(f"    - m2 < {MIN_M2} -> EXCLUDE")
    print(f"    - m2 > {MAX_M2} -> EXCLUDE")
    print()
    
    # Zone analysis
    print("=" * 120)
    print("PART 1: ZONE-BY-ZONE EXCLUSION ANALYSIS")
    print("=" * 120)
    print()
    
    zone_results = get_clean_medians_by_zone()
    
    print(f"{'Zone':<15} {'ARS Orig':>10} {'ARS Final':>10} {'ARS Med':>12} {'% Change':>10} {'USD Orig':>10} {'USD Final':>10} {'USD Med':>10} {'% Change':>10}")
    print("-" * 120)
    
    for zone in sorted(zone_results.keys()):
        r = zone_results[zone]
        ars_change = ((r['ars_median'] / r['original_ars_median'] - 1) * 100) if r['original_ars_median'] > 0 else 0
        usd_change = ((r['usd_median'] / r['original_usd_median'] - 1) * 100) if r['original_usd_median'] > 0 else 0
        
        print(f"{zone:<15} {r['n_ars_original']:>10} {r['n_ars_final']:>10} ${r['ars_median']:>10,.0f} {ars_change:>+9.1f}% {r['n_usd_original']:>10} {r['n_usd_final']:>10} ${r['usd_median']:>8.2f} {usd_change:>+9.1f}%")
    
    print()
    
    # Overall medians
    overall_ars, overall_usd = get_overall_clean_medians()
    
    # Get contaminated medians
    entries = load_data()
    alquiler = [e for e in entries if e.get('operacion', '').lower() == 'alquiler']
    contaminated_ars = np.median([e['valor_m2'] for e in alquiler if e.get('moneda', '').upper() == 'ARS'])
    contaminated_usd = np.median([e['valor_m2'] for e in alquiler if e.get('moneda', '').upper() == 'USD'])
    
    print("OVERALL SUMMARY:")
    print(f"  ARS: {contaminated_ars:,.0f} -> {overall_ars:,.0f} ({((overall_ars/contaminated_ars - 1)*100) if contaminated_ars else 0:+.1f}%)")
    print(f"  USD: {contaminated_usd:.2f} -> {overall_usd:.2f} ({((overall_usd/contaminated_usd - 1)*100) if contaminated_usd else 0:+.1f}%)")
    print()
    
    # Property simulation
    print("=" * 120)
    print("PART 2: PROPERTY ALQUILER SIMULATION")
    print("=" * 120)
    print()
    
    results = []
    
    for prop in PROPERTIES:
        print(f"Property: {prop['nombre']}")
        print(f"  Location: {prop['lat']:.4f}, {prop['lon']:.4f}")
        print(f"  Specs: {prop['dormitorios']} dorm, {prop['m2_cubiertos']} m2 cub, {prop['m2_descubiertos']} m2 desc")
        print()
        
        # Current (contaminated)
        current = calculate_alquiler_for_property(prop, contaminated_ars, use_ct=True)
        
        # Clean
        clean = calculate_alquiler_for_property(prop, overall_ars, use_ct=True)
        
        # Reduction
        reduction_pct = ((current['alq_final_ars'] - clean['alq_final_ars']) / current['alq_final_ars'] * 100) if current['alq_final_ars'] > 0 else 0
        
        # Estimate property value (using ~1,300 USD/m2 for Rosario)
        estimated_venta_usd = prop['m2_cubiertos'] * 1300
        
        # Cap rates
        cap_current = calculate_cap_rate(current['alq_final_ars'], estimated_venta_usd)
        cap_clean = calculate_cap_rate(clean['alq_final_ars'], estimated_venta_usd)
        
        print(f"  CURRENT (Contaminated):")
        print(f"    m2 equivalentes: {current['m2_equiv']:.1f}")
        print(f"    valor_m2 used: ${current['valor_m2_used']:,.0f} ARS/m2")
        print(f"    Alquiler base: ${current['alq_base']:,.0f} ARS/mes")
        print(f"    Alquiler final (with CT): ${current['alq_final_ars']:,.0f} ARS/mes")
        print(f"    Alquiler USD: ${current['alq_final_usd']:,.2f}/mes")
        print(f"    Cap Rate: {cap_current*100:.2f}%")
        print()
        
        print(f"  CLEAN (After Exclusion):")
        print(f"    m2 equivalentes: {clean['m2_equiv']:.1f}")
        print(f"    valor_m2 used: ${clean['valor_m2_used']:,.0f} ARS/m2")
        print(f"    Alquiler base: ${clean['alq_base']:,.0f} ARS/mes")
        print(f"    Alquiler final (with CT): ${clean['alq_final_ars']:,.0f} ARS/mes")
        print(f"    Alquiler USD: ${clean['alq_final_usd']:,.2f}/mes")
        print(f"    Cap Rate: {cap_clean*100:.2f}%")
        print()
        
        print(f"  REDUCTION: {reduction_pct:.1f}%")
        
        # Realistic check (Rosario market: 4-6% cap rate)
        is_realistic = 0.04 <= cap_clean <= 0.06
        print(f"  REALISTIC: {'YES' if is_realistic else 'NO'} (target: 4-6%)")
        print()
        print("-" * 120)
        print()
        
        results.append({
            'nombre': prop['nombre'],
            'm2': prop['m2_cubiertos'],
            'dormitorios': prop['dormitorios'],
            'current_alq_ars': current['alq_final_ars'],
            'current_alq_usd': current['alq_final_usd'],
            'current_cap': cap_current,
            'clean_alq_ars': clean['alq_final_ars'],
            'clean_alq_usd': clean['alq_final_usd'],
            'clean_cap': cap_clean,
            'reduction_pct': reduction_pct,
            'is_realistic': is_realistic
        })
    
    # Summary table
    print("=" * 120)
    print("PART 3: SUMMARY TABLE")
    print("=" * 120)
    print()
    print(f"{'Property':<18} {'m2':>5} {'Dorm':>5} {'Current ARS':>14} {'Clean ARS':>14} {'Reduction':>10} {'Current Cap':>12} {'Clean Cap':>12} {'Realistic':>10}")
    print("-" * 120)
    
    for r in results:
        print(f"{r['nombre']:<18} {r['m2']:>5} {r['dormitorios']:>5} ${r['current_alq_ars']:>12,.0f} ${r['clean_alq_ars']:>12,.0f} {r['reduction_pct']:>9.1f}% {r['current_cap']*100:>10.2f}% {r['clean_cap']*100:>10.2f}% {'YES' if r['is_realistic'] else 'NO':>10}")
    
    print()
    
    # Market context
    print("=" * 120)
    print("PART 4: MARKET CONTEXT - Rosario Alquiler")
    print("=" * 120)
    print()
    print("Realistic ranges for Rosario apartments:")
    print("  - Alquiler USD: $4-8/m2/mes")
    print("  - Alquiler ARS: $6,000-12,000/m2/mes (base, before CT)")
    print("  - Cap Rate: 4-6% annual")
    print()
    print("Current contaminated data shows INFLATED alquiler values due to:")
    print("  - USD entries that are actually sale prices (mislabeled)")
    print("  - ARS entries with extreme values (data entry errors)")
    print("  - Small/large area anomalies")
    print()
    print("After outlier exclusion:")
    print(f"  - New ARS median: ${overall_ars:,.0f}/m2/mes")
    print(f"  - New USD median: ${overall_usd:.2f}/m2/mes")
    print(f"  - Alquiler for 85m2 apt: ${85 * overall_ars:,.0f} ARS/mes (${85 * overall_ars / USD_RATE:,.2f} USD/mes)")
    print()
    
    return results, zone_results

if __name__ == '__main__':
    results, zone_results = run_complete_simulation()

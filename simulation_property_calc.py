#!/usr/bin/env python3
"""
Property Alquiler Simulation with Clean vs Contaminated Data
============================================================
"""

import json
import numpy as np
from collections import defaultdict

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
        'm2': 85,
        'zona': 'Otro'
    },
    {
        'nombre': 'Mabel',
        'lat': -32.9175,
        'lon': -60.6825,
        'dormitorios': 2,
        'm2': 60,
        'zona': 'Otro'
    },
    {
        'nombre': 'Vera Mujica',
        'lat': -32.9500,
        'lon': -60.6600,
        'dormitorios': 2,
        'm2': 70,
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

def filter_entries(entries, exclude_mask=None):
    """Filter entries applying hard rules and optional MAD mask"""
    result = []
    for entry in entries:
        excluded, reason = apply_hard_rules(entry)
        if excluded:
            continue
        result.append(entry)
    return result

def get_clean_data():
    """Get clean alquiler data after outlier exclusion"""
    entries = load_data()
    alquiler_entries = [e for e in entries if e.get('operacion', '').lower() == 'alquiler']
    
    # Separate by currency and zone
    zones = defaultdict(lambda: {'ARS': [], 'USD': []})
    for entry in alquiler_entries:
        zone = entry.get('zona', 'Sin zona')
        moneda = entry.get('moneda', '').upper()
        zones[zone][moneda].append(entry)
    
    all_clean_ars = []
    all_clean_usd = []
    
    for zone in zones:
        # ARS
        ars_zone = zones[zone]['ARS']
        ars_filtered = []
        
        for entry in ars_zone:
            excluded, reason = apply_hard_rules(entry)
            if not excluded:
                ars_filtered.append(entry)
        
        # MAD for ARS
        if len(ars_filtered) >= 3:
            ars_values = np.array([e['valor_m2'] for e in ars_filtered])
            ars_z_scores = calculate_modified_z_scores(ars_values)
            mad_mask = np.abs(ars_z_scores) <= MAD_THRESHOLD
            ars_final = [e for e, keep in zip(ars_filtered, mad_mask) if keep]
        else:
            ars_final = ars_filtered
        
        all_clean_ars.extend(ars_final)
        
        # USD
        usd_zone = zones[zone]['USD']
        usd_filtered = []
        
        for entry in usd_zone:
            excluded, reason = apply_hard_rules(entry)
            if not excluded:
                usd_filtered.append(entry)
        
        # MAD for USD
        if len(usd_filtered) >= 3:
            usd_values = np.array([e['valor_m2'] for e in usd_filtered])
            usd_z_scores = calculate_modified_z_scores(usd_values)
            mad_mask = np.abs(usd_z_scores) <= MAD_THRESHOLD
            usd_final = [e for e, keep in zip(usd_filtered, mad_mask) if keep]
        else:
            usd_final = usd_filtered
        
        all_clean_usd.extend(usd_final)
    
    return all_clean_ars, all_clean_usd

def get_contaminated_medians():
    """Get current (contaminated) medians"""
    entries = load_data()
    alquiler_entries = [e for e in entries if e.get('operacion', '').lower() == 'alquiler']
    
    ars_entries = [e for e in alquiler_entries if e.get('moneda', '').upper() == 'ARS']
    usd_entries = [e for e in alquiler_entries if e.get('moneda', '').upper() == 'USD']
    
    contaminated_median_ars = np.median([e['valor_m2'] for e in ars_entries]) if ars_entries else 0
    contaminated_median_usd = np.median([e['valor_m2'] for e in usd_entries]) if usd_entries else 0
    
    return contaminated_median_ars, contaminated_median_usd

def calculate_alquiler_for_property(prop, median_ars, median_usd, is_clean=False):
    """Calculate alquiler for a property given median valor_m2"""
    
    # For alquiler calculation, we use ARS valor_m2 (monthly rent per m2)
    # alquiler_ars = m2 * valor_m2_ars
    
    # Property's zone determines which median to use
    # Most properties use 'Otro' zone data
    zone = prop.get('zona', 'Otro')
    
    # Use ARS median for alquiler calculation
    alquiler_ars = prop['m2'] * median_ars
    
    # Convert to USD
    alquiler_usd = alquiler_ars / USD_RATE
    
    return {
        'alquiler_ars': alquiler_ars,
        'alquiler_usd': alquiler_usd,
        'valor_m2_used': median_ars,
        'is_clean': is_clean
    }

def calculate_cap_rate(alquiler_mensual_ars, valor_venta_usd):
    """Calculate cap rate from alquiler and property value"""
    alquiler_anual_usd = (alquiler_mensual_ars * 12) / USD_RATE
    cap_rate = alquiler_anual_usd / valor_venta_usd if valor_venta_usd > 0 else 0
    return cap_rate

def run_simulation():
    print("=" * 100)
    print("PROPERTY ALQUILER SIMULATION: Contaminated vs Clean Data")
    print("=" * 100)
    print()
    
    # Get contaminated medians
    contaminated_ars, contaminated_usd = get_contaminated_medians()
    print(f"CONTAMINATED (Current) Medians:")
    print(f"  ARS valor_m2: {contaminated_ars:,.0f}")
    print(f"  USD valor_m2: {contaminated_usd:,.2f}")
    print()
    
    # Get clean data
    clean_ars, clean_usd = get_clean_data()
    clean_median_ars = np.median([e['valor_m2'] for e in clean_ars]) if clean_ars else 0
    clean_median_usd = np.median([e['valor_m2'] for e in clean_usd]) if clean_usd else 0
    
    print(f"CLEAN (After Exclusion) Medians:")
    print(f"  ARS valor_m2: {clean_median_ars:,.0f}")
    print(f"  USD valor_m2: {clean_median_usd:,.2f}")
    print()
    
    print(f"REDUCTION:")
    print(f"  ARS: {((clean_median_ars / contaminated_ars - 1) * 100) if contaminated_ars else 0:+.1f}%")
    print(f"  USD: {((clean_median_usd / contaminated_usd - 1) * 100) if contaminated_usd else 0:+.1f}%")
    print()
    
    # Simulate properties
    print("=" * 100)
    print("PROPERTY SIMULATION")
    print("=" * 100)
    print()
    
    results = []
    
    for prop in PROPERTIES:
        print(f"Property: {prop['nombre']}")
        print(f"  Location: {prop['lat']:.4f}, {prop['lon']:.4f}")
        print(f"  Specs: {prop['dormitorios']} dorm, {prop['m2']} m2")
        print()
        
        # Current (contaminated)
        current = calculate_alquiler_for_property(prop, contaminated_ars, contaminated_usd, is_clean=False)
        
        # Clean
        clean = calculate_alquiler_for_property(prop, clean_median_ars, clean_median_usd, is_clean=True)
        
        # Reduction
        reduction_pct = ((current['alquiler_ars'] - clean['alquiler_ars']) / current['alquiler_ars'] * 100) if current['alquiler_ars'] > 0 else 0
        
        # Estimate property value (using typical venta m2 for the zone)
        # For simulation, use ~1,300 USD/m2 for Rosario properties
        estimated_venta_usd = prop['m2'] * 1300
        
        # Cap rates
        cap_current = calculate_cap_rate(current['alquiler_ars'], estimated_venta_usd)
        cap_clean = calculate_cap_rate(clean['alquiler_ars'], estimated_venta_usd)
        
        print(f"  CURRENT (Contaminated):")
        print(f"    Alquiler ARS: ${current['alquiler_ars']:,.0f}/mes")
        print(f"    Alquiler USD: ${current['alquiler_usd']:,.2f}/mes")
        print(f"    Cap Rate: {cap_current*100:.2f}%")
        print()
        
        print(f"  CLEAN (After Exclusion):")
        print(f"    Alquiler ARS: ${clean['alquiler_ars']:,.0f}/mes")
        print(f"    Alquiler USD: ${clean['alquiler_usd']:,.2f}/mes")
        print(f"    Cap Rate: {cap_clean*100:.2f}%")
        print()
        
        print(f"  REDUCTION: {reduction_pct:.1f}%")
        
        # Realistic check (Rosario market: 4-6% cap rate)
        is_realistic = 0.04 <= cap_clean <= 0.06
        print(f"  REALISTIC: {'YES' if is_realistic else 'NO'} (target: 4-6%)")
        print()
        print("-" * 100)
        print()
        
        results.append({
            'nombre': prop['nombre'],
            'm2': prop['m2'],
            'dormitorios': prop['dormitorios'],
            'current_alq_ars': current['alquiler_ars'],
            'current_alq_usd': current['alquiler_usd'],
            'current_cap': cap_current,
            'clean_alq_ars': clean['alquiler_ars'],
            'clean_alq_usd': clean['alquiler_usd'],
            'clean_cap': cap_clean,
            'reduction_pct': reduction_pct,
            'is_realistic': is_realistic
        })
    
    # Summary table
    print("=" * 100)
    print("SUMMARY TABLE")
    print("=" * 100)
    print()
    print(f"{'Property':<20} {'m2':>6} {'Current ARS':>14} {'Clean ARS':>14} {'Reduction':>10} {'Current Cap':>12} {'Clean Cap':>12} {'Realistic':>10}")
    print("-" * 100)
    
    for r in results:
        print(f"{r['nombre']:<20} {r['m2']:>6} ${r['current_alq_ars']:>12,.0f} ${r['clean_alq_ars']:>12,.0f} {r['reduction_pct']:>9.1f}% {r['current_cap']*100:>10.2f}% {r['clean_cap']*100:>10.2f}% {'YES' if r['is_realistic'] else 'NO':>10}")
    
    print()
    
    # Market context
    print("=" * 100)
    print("MARKET CONTEXT - Rosario Alquiler")
    print("=" * 100)
    print()
    print("Realistic ranges for Rosario apartments:")
    print("  - Alquiler USD: $4-8/m2/mes")
    print("  - Alquiler ARS: $6,000-12,000/m2/mes")
    print("  - Cap Rate: 4-6% annual")
    print()
    print("Current contaminated data shows INFLATED alquiler values.")
    print("After outlier exclusion, values should align with market reality.")
    print()
    
    return results

if __name__ == '__main__':
    results = run_simulation()

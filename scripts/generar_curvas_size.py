#!/usr/bin/env python3
"""
Generar curvas size adjustment CT-adjusted para cada macrozona/dormitorio.

Metodologia (TAREA-165):
1. Cargar cache_scraping.json (venta USD)
2. Asignar macrozona por bbox
3. Para cada macrozona/dorm: agrupar por rangos de 20m2
4. Calcular mediana CT-adjusted $/m2 por rango
5. Aplicar isotonic regression para monotonicidad
6. Normalizar factor=1.0 en el rango mas comun
7. Output a data/zonas_depreciacion_new.json

NO TOCA el archivo de produccion.
"""
import json
import os
import sys
import numpy as np
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from parsers.time_adjustment import meses_desde


def load_cache():
    path = os.path.join(BASE_DIR, "cache_scraping.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("propiedades", data) if isinstance(data, dict) else data


def load_zonas():
    path = os.path.join(BASE_DIR, "data", "zonas_depreciacion.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def assign_macrozona(lat, lon, macrozonas):
    for mz in macrozonas:
        bbox = mz.get("bbox", {})
        if not bbox:
            continue
        if (bbox.get("lat_min", -99) <= lat <= bbox.get("lat_max", 99) and
                bbox.get("lon_min", -99) <= lon <= bbox.get("lon_max", 99)):
            return mz["id"]
    return "resto_rosario"


def compute_ct_adjusted(valor_m2, date_created, ct_annual_rate, fecha_ref=None):
    if not date_created or not valor_m2 or valor_m2 <= 0:
        return valor_m2
    try:
        if fecha_ref is None:
            fecha_ref = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
        m = meses_desde(date_created, fecha_ref)
        if m is not None and m > 6:
            ct = (1.0 + ct_annual_rate) ** (m / 12.0)
            return valor_m2 * ct
    except Exception:
        pass
    return valor_m2


def isotonic_regression(y):
    """
    Pool Adjacent Violators Algorithm (PAVA) for isotonic regression.
    Forces the output to be non-decreasing.
    """
    n = len(y)
    if n <= 1:
        return y.copy()
    
    result = y.copy()
    i = 0
    while i < n - 1:
        if result[i] > result[i + 1]:
            # Pool adjacent violators
            j = i
            while j < n - 1 and result[j] > result[j + 1]:
                j += 1
            # Average the violating block
            block = result[i:j + 1]
            avg = float(np.mean(block))
            for k in range(i, j + 1):
                result[k] = avg
            # Restart from beginning
            i = 0
        else:
            i += 1
    return result


def compute_curves(props, macrozonas, ct_rates, bucket_size=20, min_n=10):
    """
    Compute CT-adjusted median $/m2 per bucket for each macrozona/dorm.
    Uses isotonic regression for monotonicity.
    """
    curves = {}
    
    for mz in macrozonas:
        mz_id = mz["id"]
        ct_rate = ct_rates.get(mz_id, -0.02)
        curves[mz_id] = {}
        
        # Filter props in this macrozona
        mz_props = [p for p in props if assign_macrozona(
            p.get("lat", 0), p.get("lon", 0), macrozonas
        ) == mz_id]
        
        if not mz_props:
            continue
        
        for dorm in [1, 2, 3, 4, "default"]:
            if dorm == "default":
                dorm_props = mz_props
            else:
                dorm_props = [p for p in mz_props if p.get("dormitorios") == dorm]
            
            if len(dorm_props) < min_n:
                continue
            
            # Group by bucket_size m2 ranges
            ranges = {}
            for p in dorm_props:
                m2 = p.get("m2", 0)
                if m2 <= 0:
                    continue
                bucket = int(m2 // bucket_size) * bucket_size
                if bucket not in ranges:
                    ranges[bucket] = []
                valor_m2 = p.get("valor_m2", 0)
                date_created = p.get("date_created", "")
                ct_adjusted = compute_ct_adjusted(valor_m2, date_created, ct_rate)
                ranges[bucket].append(ct_adjusted)
            
            # Compute median per range (only if enough data)
            medians = {}
            counts = {}
            for bucket, prices in sorted(ranges.items()):
                if len(prices) >= 3:
                    medians[bucket] = float(np.median(prices))
                    counts[bucket] = len(prices)
            
            if len(medians) < 2:
                continue
            
            # Find the most common size range (highest count)
            reference_bucket = max(counts, key=counts.get)
            reference_median = medians[reference_bucket]
            
            if reference_median <= 0:
                continue
            
            # Normalize: factor = median / reference_median
            buckets = sorted(medians.keys())
            raw_factors = [medians[b] / reference_median for b in buckets]
            
            # Apply isotonic regression to enforce monotonicity
            # Since we expect smaller sizes to have HIGHER $/m2 (factor > 1)
            # and larger sizes to have LOWER $/m2 (factor < 1),
            # we need to check the overall trend and potentially invert
            if len(raw_factors) >= 2:
                # Check if trend is mostly decreasing (normal: small=premium, large=discount)
                trend = np.polyfit(range(len(raw_factors)), raw_factors, 1)[0]
                
                if trend < 0:
                    # Normal trend: decreasing. Use isotonic on inverted
                    inverted = [-f for f in raw_factors]
                    smoothed = isotonic_regression(inverted)
                    smoothed = [-f for f in smoothed]
                else:
                    # Increasing trend: use isotonic directly
                    smoothed = isotonic_regression(raw_factors)
            else:
                smoothed = raw_factors
            
            # Clamp to [0.5, 2.0]
            smoothed = [max(0.5, min(2.0, f)) for f in smoothed]
            
            points = [{"m2": buckets[i], "factor": round(smoothed[i], 3)} 
                     for i in range(len(buckets))]
            
            # Determine if monotonic
            factors = [p["factor"] for p in points]
            is_decreasing = all(factors[i] >= factors[i+1] - 0.001 for i in range(len(factors)-1))
            is_increasing = all(factors[i] <= factors[i+1] + 0.001 for i in range(len(factors)-1))
            is_monotonic = is_decreasing or is_increasing
            
            total_n = sum(counts.values())
            print(f"  {mz_id:25s} {str(dorm)+'-dorm':12s} {len(points):2d} pts "
                  f"ref={reference_bucket}m2(${reference_median:.0f}) "
                  f"n={total_n:5d} {'OK' if is_monotonic else 'SMOOTHED'}")
            
            curves[mz_id][str(dorm)] = points
    
    return curves


def main():
    print("=" * 70)
    print("GENERADOR DE CURVAS SIZE ADJUSTMENT (CT-ADJUSTED)")
    print("Metodologia: 20m2 buckets + isotonic regression")
    print("=" * 70)
    
    # Load data
    print("\nCargando datos...")
    props = load_cache()
    zonas = load_zonas()
    macrozonas = zonas.get("macrozonas", [])
    
    # Build CT rate lookup
    ct_rates = {mz["id"]: mz.get("ct_annual_rate", -0.02) for mz in macrozonas}
    
    # Filter venta USD with valid data
    venta = [p for p in props if p.get("operacion") == "venta" 
             and p.get("moneda", "USD").upper() == "USD"
             and (p.get("m2") or 0) > 10
             and (p.get("valor_m2") or 0) > 100
             and p.get("lat") and p.get("lon")]
    print(f"Props venta USD validas: {len(venta)}")
    
    # Compute curves
    print("\nComputando curvas por macrozona/dorm (20m2 buckets)...")
    curves = compute_curves(venta, macrozonas, ct_rates, bucket_size=20, min_n=10)
    
    # Build output JSON
    output = {
        "version": 4,
        "fecha_creacion": datetime.now().strftime("%Y-%m-%d"),
        "note": "TEMPORARY curves for simulation - DO NOT USE IN PRODUCTION",
        "methodology": "20m2 buckets, CT-adjusted medians, isotonic regression",
        "curves": curves
    }
    
    out_path = os.path.join(BASE_DIR, "data", "zonas_depreciacion_new.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\nCurvas guardadas en: {out_path}")
    print("NOTA: Estas son curvas TEMPORALES para simulacion.")
    print("NO reemplazan las curvas de produccion hasta revision del usuario.")
    
    # Summary with comparison to old curves
    print("\n" + "=" * 70)
    print("COMPARACION: OLD (chaotic) vs NEW (smoothed)")
    print("=" * 70)
    
    old = load_zonas()
    for mz_id in sorted(curves.keys()):
        for dorm in ["1", "2", "3"]:
            new_pts = curves.get(mz_id, {}).get(dorm, [])
            if not new_pts:
                continue
            old_mz = next((m for m in old["macrozonas"] if m["id"] == mz_id), None)
            old_pts = old_mz.get("size_adjustment", {}).get("by_dormitorios", {}).get(dorm, []) if old_mz else []
            
            new_factors = [p["factor"] for p in new_pts]
            old_factors = [p["factor"] for p in old_pts]
            
            new_range = f"[{min(new_factors):.3f}, {max(new_factors):.3f}]" if new_factors else "[]"
            old_range = f"[{min(old_factors):.3f}, {max(old_factors):.3f}]" if old_factors else "[]"
            
            print(f"  {mz_id:25s} {dorm}-dorm: OLD={old_range:20s} NEW={new_range}")


if __name__ == "__main__":
    main()

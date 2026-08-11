"""
Comprehensive Barrier Analysis for Rosario Real Estate
Analyzes all 742 barriers to determine if blend + barrier + penalty system works.
"""
import json
import math
import sys
import os
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Configuration ---
RADIUS_M = 500  # meters around barrier to search
MIN_PROPS_PER_SIDE = 5  # minimum properties on each side to consider
PCTL = 33  # percentile to compute

# --- Helper functions ---
def haversine_m(lat1, lon1, lat2, lon2):
    """Distance in meters."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def compute_percentil(pctl, values):
    """Discrete percentile (same as cluster_filters.py)."""
    if not values:
        return None
    s = sorted(values)
    idx = int(len(s) * pctl / 100)
    idx = min(idx, len(s) - 1)
    idx = max(idx, 0)
    return float(s[idx])

def classify_barrier(gap_pct, p_value):
    """Classify barrier by price gap and significance."""
    if gap_pct > 20 and p_value < 0.01:
        return "STRONG"
    elif gap_pct >= 10 and gap_pct <= 20 and p_value < 0.05:
        return "MODERATE"
    elif gap_pct >= 5 and gap_pct < 10 and p_value < 0.05:
        return "WEAK"
    else:
        return "NONE"

def mannwhitney_u_test(group1, group2):
    """Simple Mann-Whitney U test (two-sided). Returns p-value approximation."""
    n1, n2 = len(group1), len(group2)
    if n1 < 3 or n2 < 3:
        return 1.0
    
    combined = [(v, 0, i) for i, v in enumerate(group1)] + [(v, 1, i) for i, v in enumerate(group2)]
    combined.sort(key=lambda x: x[0])
    
    # Assign ranks
    ranks = [0] * len(combined)
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j
    
    R1 = sum(ranks[k] for k in range(len(combined)) if combined[k][1] == 0)
    U1 = R1 - n1 * (n1 + 1) / 2.0
    U2 = n1 * n2 - U1
    U = min(U1, U2)
    
    # Normal approximation
    mu = n1 * n2 / 2.0
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
    if sigma == 0:
        return 1.0
    z = (U - mu) / sigma
    
    # Two-sided p-value (normal approximation)
    p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
    return p

def get_barrier_midpoint(geometry):
    """Get midpoint of a LineString geometry."""
    coords = geometry.get("coordinates", [])
    if not coords:
        return None, None
    mid = len(coords) // 2
    lon, lat = coords[mid]
    return lat, lon

def get_barrier_orientation(geometry):
    """Determine if barrier is mostly east-west or north-south."""
    coords = geometry.get("coordinates", [])
    if len(coords) < 2:
        return "unknown", 0, 0
    
    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    dlat = max(lats) - min(lats)
    dlon = max(lons) - min(lons)
    
    if dlon > dlat * 1.5:
        return "east-west", dlat, dlon
    elif dlat > dlon * 1.5:
        return "north-south", dlat, dlon
    else:
        return "diagonal", dlat, dlon

def get_barrier_direction_vector(geometry):
    """Get the dominant direction vector of the barrier."""
    coords = geometry.get("coordinates", [])
    if len(coords) < 2:
        return None
    # Use first and last point
    start = coords[0]
    end = coords[-1]
    dx = end[0] - start[0]  # lon
    dy = end[1] - start[1]  # lat
    length = math.sqrt(dx*dx + dy*dy)
    if length == 0:
        return None
    return (dx/length, dy/length)

def assign_side(lat, lon, barrier_lat, barrier_lon, direction_vec):
    """Assign property to a side of the barrier using cross product."""
    if direction_vec is None:
        return "unknown"
    
    # Vector from barrier midpoint to property
    vprop = (lon - barrier_lon, lat - barrier_lat)
    
    # Cross product: direction_vec x vprop
    cross = direction_vec[0] * vprop[1] - direction_vec[1] * vprop[0]
    
    if cross > 0:
        return "side_A"
    elif cross < 0:
        return "side_B"
    else:
        return "on_line"

# --- Main ---
print("Loading data...")

# Load barriers
with open("barreras_rosario.json", "r", encoding="utf-8") as f:
    barriers_data = json.load(f)
barriers = barriers_data.get("features", [])
print(f"Loaded {len(barriers)} barriers")

# Load properties
with open("cache_scraping.json", "r", encoding="utf-8") as f:
    cache = json.load(f)
props = cache.get("propiedades", [])

# Filter to venta with valor_m2 > 0 and valid coords
venta = []
for p in props:
    if p.get("operacion") != "venta":
        continue
    vm2 = p.get("valor_m2", 0)
    if not vm2 or vm2 <= 0:
        continue
    lat = p.get("lat")
    lon = p.get("lon")
    if lat is None or lon is None:
        continue
    try:
        lat, lon = float(lat), float(lon)
    except:
        continue
    venta.append({
        "lat": lat,
        "lon": lon,
        "valor_m2": vm2,
        "zona": p.get("zona", "?"),
        "dormitorios": p.get("dormitorios", 0),
        "m2": p.get("m2", 0),
        "tipo": p.get("tipo", "?"),
    })

print(f"Loaded {len(venta)} venta properties with valor_m2 > 0")

# Pre-compute all property coordinates for fast lookup
prop_coords = [(p["lat"], p["lon"]) for p in venta]

# --- Phase 1: Barrier-by-barrier analysis ---
print("\n" + "="*80)
print("PHASE 1: BARRIER-BY-BARRIER ANALYSIS")
print("="*80)

results = []
skipped = 0

for i, barrier in enumerate(barriers):
    if (i + 1) % 100 == 0:
        print(f"  Processing barrier {i+1}/{len(barriers)}...")
    
    props_geom = barrier.get("properties", {})
    geometry = barrier.get("geometry", {})
    barrier_type = props_geom.get("barrier_type", "unknown")
    barrier_name = props_geom.get("name", "unknown")
    barrier_id = props_geom.get("id", i)
    
    # Get midpoint and orientation
    mid_lat, mid_lon = get_barrier_midpoint(geometry)
    if mid_lat is None:
        skipped += 1
        continue
    
    orientation, dlat, dlon = get_barrier_orientation(geometry)
    direction_vec = get_barrier_direction_vector(geometry)
    
    # Find properties within RADIUS_M of barrier midpoint
    side_A = []
    side_B = []
    
    for p in venta:
        dist = haversine_m(mid_lat, mid_lon, p["lat"], p["lon"])
        if dist > RADIUS_M:
            continue
        
        side = assign_side(p["lat"], p["lon"], mid_lat, mid_lon, direction_vec)
        if side == "side_A":
            side_A.append(p)
        elif side == "side_B":
            side_B.append(p)
    
    # Check minimum properties per side
    if len(side_A) < MIN_PROPS_PER_SIDE or len(side_B) < MIN_PROPS_PER_SIDE:
        skipped += 1
        continue
    
    # Compute P33 on each side
    prices_A = [p["valor_m2"] for p in side_A]
    prices_B = [p["valor_m2"] for p in side_B]
    
    p33_A = compute_percentil(PCTL, prices_A)
    p33_B = compute_percentil(PCTL, prices_B)
    
    if p33_A is None or p33_B is None:
        skipped += 1
        continue
    
    # Compute gap
    max_p33 = max(p33_A, p33_B)
    min_p33 = min(p33_A, p33_B)
    gap_pct = ((max_p33 - min_p33) / max_p33) * 100 if max_p33 > 0 else 0
    
    # Significance test
    p_value = mannwhitney_u_test(prices_A, prices_B)
    
    # Classify
    classification = classify_barrier(gap_pct, p_value)
    
    # Determine which side is more expensive
    if p33_A > p33_B:
        more_expensive = "A"
    else:
        more_expensive = "B"
    
    results.append({
        "idx": i,
        "name": barrier_name,
        "type": barrier_type,
        "orientation": orientation,
        "n_A": len(side_A),
        "n_B": len(side_B),
        "p33_A": round(p33_A, 2),
        "p33_B": round(p33_B, 2),
        "gap_pct": round(gap_pct, 2),
        "p_value": round(p_value, 6),
        "classification": classification,
        "more_expensive": more_expensive,
        "mid_lat": round(mid_lat, 6),
        "mid_lon": round(mid_lon, 6),
    })

print(f"\nAnalyzed: {len(results)} barriers (skipped: {skipped})")

# --- Phase 2: Summary Statistics ---
print("\n" + "="*80)
print("PHASE 2: CLASSIFICATION SUMMARY")
print("="*80)

class_counts = Counter(r["classification"] for r in results)
print(f"\nClassification distribution:")
for cls in ["STRONG", "MODERATE", "WEAK", "NONE"]:
    count = class_counts.get(cls, 0)
    pct = (count / len(results) * 100) if results else 0
    print(f"  {cls:10}: {count:4} ({pct:.1f}%)")

# Gap statistics by class
print(f"\nGap statistics by classification:")
for cls in ["STRONG", "MODERATE", "WEAK", "NONE"]:
    gaps = [r["gap_pct"] for r in results if r["classification"] == cls]
    if gaps:
        avg_gap = sum(gaps) / len(gaps)
        min_gap = min(gaps)
        max_gap = max(gaps)
        print(f"  {cls:10}: avg={avg_gap:.1f}%, min={min_gap:.1f}%, max={max_gap:.1f}%")

# Breakdown by barrier type
print(f"\nBreakdown by barrier type:")
for btype in ["hard", "soft"]:
    type_results = [r for r in results if r["type"] == btype]
    if type_results:
        type_classes = Counter(r["classification"] for r in type_results)
        print(f"\n  {btype.upper()} barriers ({len(type_results)} total):")
        for cls in ["STRONG", "MODERATE", "WEAK", "NONE"]:
            count = type_classes.get(cls, 0)
            print(f"    {cls:10}: {count}")

# --- Phase 3: Geographic Coverage ---
print("\n" + "="*80)
print("PHASE 3: GEOGRAPHIC COVERAGE")
print("="*80)

# Build lookup: for each property, find closest barrier of each class
strong_barriers = [r for r in results if r["classification"] == "STRONG"]
moderate_barriers = [r for r in results if r["classification"] == "MODERATE"]
weak_barriers = [r for r in results if r["classification"] == "WEAK"]

coverage = {"near_strong": 0, "near_moderate": 0, "near_weak": 0, "no_barrier": 0}

for p in venta:
    min_dist_strong = float('inf')
    min_dist_moderate = float('inf')
    min_dist_weak = float('inf')
    
    for r in strong_barriers:
        dist = haversine_m(p["lat"], p["lon"], r["mid_lat"], r["mid_lon"])
        min_dist_strong = min(min_dist_strong, dist)
    
    for r in moderate_barriers:
        dist = haversine_m(p["lat"], p["lon"], r["mid_lat"], r["mid_lon"])
        min_dist_moderate = min(min_dist_moderate, dist)
    
    for r in weak_barriers:
        dist = haversine_m(p["lat"], p["lon"], r["mid_lat"], r["mid_lon"])
        min_dist_weak = min(min_dist_weak, dist)
    
    if min_dist_strong <= RADIUS_M:
        coverage["near_strong"] += 1
    elif min_dist_moderate <= RADIUS_M:
        coverage["near_moderate"] += 1
    elif min_dist_weak <= RADIUS_M:
        coverage["near_weak"] += 1
    else:
        coverage["no_barrier"] += 1

total = len(venta)
print(f"\nProperties within {RADIUS_M}m of barriers:")
print(f"  Near STRONG barriers:  {coverage['near_strong']:5} ({coverage['near_strong']/total*100:.1f}%)")
print(f"  Near MODERATE barriers: {coverage['near_moderate']:5} ({coverage['near_moderate']/total*100:.1f}%)")
print(f"  Near WEAK barriers:     {coverage['near_weak']:5} ({coverage['near_weak']/total*100:.1f}%)")
print(f"  No significant barrier: {coverage['no_barrier']:5} ({coverage['no_barrier']/total*100:.1f}%)")

# --- Phase 4: Penalty Calibration ---
print("\n" + "="*80)
print("PHASE 4: PENALTY CALIBRATION")
print("="*80)

print(f"\nCurrent system: barrier_pct = (n_cross/n_total) * 0.03 (max 3%)")
print(f"\nRequired penalty to correct for price gap:")
print(f"(Penalty should equal the gap % if blend is mixing incompatible markets)")

for cls in ["STRONG", "MODERATE", "WEAK"]:
    cls_results = [r for r in results if r["classification"] == cls]
    if cls_results:
        gaps = [r["gap_pct"] for r in cls_results]
        avg_gap = sum(gaps) / len(gaps)
        median_gap = sorted(gaps)[len(gaps)//2]
        print(f"\n  {cls}:")
        print(f"    Barriers: {len(cls_results)}")
        print(f"    Average gap: {avg_gap:.1f}%")
        print(f"    Median gap: {median_gap:.1f}%")
        print(f"    Current max penalty: 3.0%")
        print(f"    Gap/Penalty ratio: {avg_gap/3.0:.1f}x")

# --- Phase 5: Blend Validity ---
print("\n" + "="*80)
print("PHASE 5: BLEND VALIDITY CHECK")
print("="*80)

compatible = 0
incompatible = 0
total_checked = 0

for r in results:
    if r["classification"] in ("STRONG", "MODERATE"):
        gap = r["gap_pct"]
        total_checked += 1
        if gap < 5:
            compatible += 1
        elif gap > 15:
            incompatible += 1
        else:
            # Borderline
            compatible += 0.5
            incompatible += 0.5

print(f"\nBlend validity for STRONG/MODERATE barriers:")
print(f"  Compatible pools (gap < 5%):    {compatible}")
print(f"  Incompatible pools (gap > 15%): {incompatible}")
if total_checked > 0:
    print(f"  Compatibility rate: {compatible/total_checked*100:.1f}%")

# --- Top barriers by gap ---
print("\n" + "="*80)
print("TOP 20 BARRIERS BY PRICE GAP")
print("="*80)

top = sorted(results, key=lambda x: x["gap_pct"], reverse=True)[:20]
print(f"\n{'Rank':>4} {'Name':>30} {'Type':>6} {'Gap%':>7} {'P33_A':>8} {'P33_B':>8} {'n_A':>5} {'n_B':>5} {'p-value':>10} {'Class':>10}")
print("-"*110)
for i, r in enumerate(top):
    print(f"{i+1:4} {r['name']:>30} {r['type']:>6} {r['gap_pct']:>6.1f}% {r['p33_A']:>7.0f} {r['p33_B']:>7.0f} {r['n_A']:>5} {r['n_B']:>5} {r['p_value']:>10.4f} {r['classification']:>10}")

# --- STRONG barriers detail ---
print("\n" + "="*80)
print("ALL STRONG BARRIERS (gap > 20%, p < 0.01)")
print("="*80)

strong = [r for r in results if r["classification"] == "STRONG"]
print(f"\nTotal STRONG barriers: {len(strong)}")
print(f"\n{'Name':>30} {'Type':>6} {'Orient':>10} {'Gap%':>7} {'P33_A':>8} {'P33_B':>8} {'n_A':>5} {'n_B':>5}")
print("-"*90)
for r in sorted(strong, key=lambda x: x["gap_pct"], reverse=True):
    print(f"{r['name']:>30} {r['type']:>6} {r['orientation']:>10} {r['gap_pct']:>6.1f}% {r['p33_A']:>7.0f} {r['p33_B']:>7.0f} {r['n_A']:>5} {r['n_B']:>5}")

# --- Final Summary ---
print("\n" + "="*80)
print("FINAL SUMMARY")
print("="*80)

n_strong = class_counts.get("STRONG", 0)
n_moderate = class_counts.get("MODERATE", 0)
n_weak = class_counts.get("WEAK", 0)
n_none = class_counts.get("NONE", 0)
n_total = len(results)

print(f"\nTotal barriers analyzed: {n_total}")
print(f"  STRONG (>20% gap):   {n_strong} ({n_strong/n_total*100:.1f}%)")
print(f"  MODERATE (10-20%):   {n_moderate} ({n_moderate/n_total*100:.1f}%)")
print(f"  WEAK (5-10%):        {n_weak} ({n_weak/n_total*100:.1f}%)")
print(f"  NONE (<5%):          {n_none} ({n_none/n_total*100:.1f}%)")

print(f"\nGeographic coverage:")
print(f"  Near STRONG:  {coverage['near_strong']/total*100:.1f}% of properties")
print(f"  Near MODERATE: {coverage['near_moderate']/total*100:.1f}% of properties")
print(f"  Near WEAK:     {coverage['near_weak']/total*100:.1f}% of properties")
print(f"  No barrier:    {coverage['no_barrier']/total*100:.1f}% of properties")

if n_strong > 0:
    strong_gaps = [r["gap_pct"] for r in results if r["classification"] == "STRONG"]
    print(f"\nSTRONG barriers: avg gap {sum(strong_gaps)/len(strong_gaps):.1f}% (current penalty max: 3%)")

conclusion = ""
if n_strong > 5 and coverage["near_strong"] > 10:
    conclusion = "NEEDS WORK: Significant barriers exist with real price gaps. Current 3% penalty is insufficient."
elif n_moderate > 10:
    conclusion = "MARGINAL: Some moderate barriers. Current system may need adjustment."
else:
    conclusion = "MOSTLY OK: Few significant barriers. Current system is reasonable."

print(f"\nConclusion: {conclusion}")

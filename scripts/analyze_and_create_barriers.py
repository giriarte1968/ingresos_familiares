"""
Analyze ALL barriers and generate corrected barreras_rosario.json based on actual data.
For each barrier:
  1. Find properties within 300m on each side
  2. Calculate P33 for each side
  3. Calculate gap
  4. Classify: STRONG (>20%) -> hard, MODERATE (10-20%) -> soft, WEAK (5-10%) -> soft, NONE (<5%) -> remove
"""
import json
import math
import shutil
from collections import Counter

# --- Configuration ---
RADIUS_M = 300
MIN_PROPS_PER_SIDE = 5
PCTL = 33

# --- Helper functions ---
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def compute_percentil(pctl, values):
    if not values:
        return None
    s = sorted(values)
    idx = int(len(s) * pctl / 100)
    idx = min(idx, len(s) - 1)
    idx = max(idx, 0)
    return float(s[idx])

def get_barrier_midpoint(geometry):
    coords = geometry.get("coordinates", [])
    if not coords:
        return None, None
    mid = len(coords) // 2
    lon, lat = coords[mid]
    return lat, lon

def get_barrier_direction_vector(geometry):
    coords = geometry.get("coordinates", [])
    if len(coords) < 2:
        return None
    start = coords[0]
    end = coords[-1]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx*dx + dy*dy)
    if length == 0:
        return None
    return (dx/length, dy/length)

def assign_side(lat, lon, barrier_lat, barrier_lon, direction_vec):
    if direction_vec is None:
        return "unknown"
    vprop = (lon - barrier_lon, lat - barrier_lat)
    cross = direction_vec[0] * vprop[1] - direction_vec[1] * vprop[0]
    if cross > 0:
        return "side_A"
    elif cross < 0:
        return "side_B"
    else:
        return "on_line"

def classify_barrier(gap_abs, n_a, n_b):
    """Classify barrier based on gap and minimum props per side."""
    if n_a < MIN_PROPS_PER_SIDE or n_b < MIN_PROPS_PER_SIDE:
        return "INSUFFICIENT"
    if gap_abs > 20:
        return "STRONG"
    elif gap_abs >= 10:
        return "MODERATE"
    elif gap_abs >= 5:
        return "WEAK"
    else:
        return "NONE"

# --- Load data ---
print("Loading data...")

with open("barreras_rosario.json", "r", encoding="utf-8") as f:
    barriers_data = json.load(f)
barriers = barriers_data.get("features", [])
print(f"Loaded {len(barriers)} barriers")

with open("cache_scraping.json", "r", encoding="utf-8") as f:
    cache = json.load(f)
props = cache.get("propiedades", [])

# Filter venta properties with valid data
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
    })

print(f"Loaded {len(venta)} venta properties")

# --- Analyze each barrier ---
print(f"\nAnalyzing {len(barriers)} barriers...")
results = []
skipped = 0

for i, barrier in enumerate(barriers):
    if (i + 1) % 100 == 0:
        print(f"  Processing {i+1}/{len(barriers)}...")
    
    props_geom = barrier.get("properties", {})
    geometry = barrier.get("geometry", {})
    barrier_type = props_geom.get("barrier_type", "unknown")
    barrier_name = props_geom.get("name", "unknown")
    
    mid_lat, mid_lon = get_barrier_midpoint(geometry)
    if mid_lat is None:
        skipped += 1
        continue
    
    direction_vec = get_barrier_direction_vector(geometry)
    if direction_vec is None:
        skipped += 1
        continue
    
    # Find properties on each side
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
    
    # Calculate gap
    n_a = len(side_A)
    n_b = len(side_B)
    
    if n_a < MIN_PROPS_PER_SIDE or n_b < MIN_PROPS_PER_SIDE:
        classification = "INSUFFICIENT"
        gap_pct = 0
        p33_a = 0
        p33_b = 0
    else:
        prices_a = [p["valor_m2"] for p in side_A]
        prices_b = [p["valor_m2"] for p in side_B]
        p33_a = compute_percentil(PCTL, prices_a)
        p33_b = compute_percentil(PCTL, prices_b)
        
        if p33_a and p33_a > 0:
            gap_pct = abs(p33_b - p33_a) / p33_a * 100
        else:
            gap_pct = 0
        
        classification = classify_barrier(gap_pct, n_a, n_b)
    
    results.append({
        "name": barrier_name,
        "type": barrier_type,
        "gap_pct": gap_pct,
        "n_a": n_a,
        "n_b": n_b,
        "p33_a": p33_a,
        "p33_b": p33_b,
        "classification": classification,
        "barrier": barrier,  # Keep original barrier data
    })

# --- Summary ---
print(f"\n{'='*80}")
print("ANALYSIS RESULTS")
print(f"{'='*80}")

class_counts = Counter(r["classification"] for r in results)
print(f"\nClassification distribution:")
for cls, count in class_counts.most_common():
    print(f"  {cls:15}: {count:4}")

# Show barriers by classification
for cls in ["STRONG", "MODERATE", "WEAK", "NONE", "INSUFFICIENT"]:
    items = [r for r in results if r["classification"] == cls]
    if not items:
        continue
    print(f"\n{'='*80}")
    print(f"{cls} barriers ({len(items)}):")
    print(f"{'='*80}")
    for r in sorted(items, key=lambda x: -x["gap_pct"]):
        print(f"  {r['name']:35} type={r['type']:5} gap={r['gap_pct']:5.1f}% nA={r['n_a']:3} nB={r['n_b']:3} P33A=${r['p33_a']:.0f} P33B=${r['p33_b']:.0f}")

# --- Generate corrected file ---
print(f"\n{'='*80}")
print("GENERATING CORRECTED FILE")
print(f"{'='*80}")

new_features = []
changes = []

for r in results:
    barrier = r["barrier"]
    old_type = r["type"]
    cls = r["classification"]
    
    if cls == "INSUFFICIENT":
        # Keep as-is (can't evaluate)
        new_features.append(barrier)
    elif cls == "STRONG":
        # Must be hard barrier
        if old_type != "hard":
            barrier["properties"]["barrier_type"] = "hard"
            changes.append(f"{r['name']}: {old_type} -> hard (gap={r['gap_pct']:.1f}%)")
        new_features.append(barrier)
    elif cls == "MODERATE":
        # Soft barrier
        if old_type != "soft":
            barrier["properties"]["barrier_type"] = "soft"
            changes.append(f"{r['name']}: {old_type} -> soft (gap={r['gap_pct']:.1f}%)")
        new_features.append(barrier)
    elif cls == "WEAK":
        # Soft barrier
        if old_type != "soft":
            barrier["properties"]["barrier_type"] = "soft"
            changes.append(f"{r['name']}: {old_type} -> soft (gap={r['gap_pct']:.1f}%)")
        new_features.append(barrier)
    elif cls == "NONE":
        # Not a barrier - REMOVE
        changes.append(f"{r['name']}: {old_type} -> REMOVED (gap={r['gap_pct']:.1f}%)")
        # Don't add to new_features

# Update data
barriers_data["features"] = new_features

# Save corrected version
shutil.copy("barreras_rosario.json", "barreras_rosario_backup.json")
with open("barreras_rosario_corrected.json", "w", encoding="utf-8") as f:
    json.dump(barriers_data, f, ensure_ascii=False, indent=2)

print(f"\nOriginal: {len(barriers)} barriers")
print(f"Corrected: {len(new_features)} barriers")
print(f"\nChanges made:")
for change in changes:
    print(f"  - {change}")

# Count by type
hard = sum(1 for f in new_features if f["properties"]["barrier_type"] == "hard")
soft = sum(1 for f in new_features if f["properties"]["barrier_type"] == "soft")
print(f"\nNew distribution:")
print(f"  Hard: {hard}")
print(f"  Soft: {soft}")

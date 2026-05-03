"""
anchor_gap_detector.py

Detecta huecos en la malla de anclas de Rosario usando 3 métodos:
  1. Distancia pura (> umbral → hueco)
  2. Inestabilidad IDW (k=3 vs k=5 divergen → zona mal representada)
  3. Gradiente irreal (salto de precio > 15% en < 400m)

Genera una grilla de evaluación sobre el bounding box de Rosario
con resolución configurable (default: cada 250m ≈ 0.0022°).
"""

import json
import math
import os
from dataclasses import dataclass, field
from typing import Optional, List

KM_PER_LAT = 111.32
KM_PER_LON = 88.50

LAT_MIN, LAT_MAX = -33.010, -32.890
LON_MIN, LON_MAX = -60.820, -60.610

GRID_STEP_KM = 0.25

GAP_DISTANCE_KM = 0.40
IDW_INSTABILITY_PCT = 0.12
GRADIENT_USD_PER_KM = 1200

# Threshold adaptativo por zona
ZONE_THRESHOLDS = [
    # (lat_min, lat_max, lon_min, lon_max, threshold_km, nombre)
    (-32.960, -32.935, -60.655, -60.620, 0.30, "centro_denso"),
    (-32.975, -32.920, -60.690, -60.610, 0.45, "macrocentro"),
    (-32.985, -32.900, -60.760, -60.690, 0.65, "zona_media"),
    (-33.010, -32.890, -60.820, -60.760, 0.90, "periferia"),
]
DEFAULT_THRESHOLD_KM = 0.60


def get_threshold_for_point(lat: float, lon: float):
    """Retorna (threshold_km, nombre_zona) para un punto dado."""
    for lat_min, lat_max, lon_min, lon_max, threshold, nombre in ZONE_THRESHOLDS:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return threshold, nombre
    return DEFAULT_THRESHOLD_KM, "default"


@dataclass
class Anchor:
    id: str
    lat: float
    lon: float
    usd_m2: float


@dataclass
class GridPoint:
    lat: float
    lon: float
    dist_to_nearest_km: float = 0.0
    nearest_anchor_id: str = ""
    idw_k3: float = 0.0
    idw_k5: float = 0.0
    idw_instability_pct: float = 0.0
    is_gap: bool = False
    gap_reasons: list = field(default_factory=list)
    suggested_usd_m2: float = 0.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlat = (lat2 - lat1) * KM_PER_LAT
    dlon = (lon2 - lon1) * KM_PER_LON
    return math.sqrt(dlat**2 + dlon**2)


def idw(point_lat: float, point_lon: float, anchors: List[Anchor], k: int = 5, power: int = 2) -> float:
    distances = []
    for a in anchors:
        d = haversine_km(point_lat, point_lon, a.lat, a.lon)
        distances.append((d, a))

    distances.sort(key=lambda x: x[0])
    neighbors = distances[:k]

    for d, a in neighbors:
        if d < 0.001:
            return a.usd_m2

    total_weight = 0.0
    weighted_sum = 0.0
    for d, a in neighbors:
        w = 1.0 / (d ** power)
        weighted_sum += w * a.usd_m2
        total_weight += w

    return weighted_sum / total_weight if total_weight > 0 else 0.0


def build_evaluation_grid(anchors: List[Anchor]) -> List[GridPoint]:
    step_lat = GRID_STEP_KM / KM_PER_LAT
    step_lon = GRID_STEP_KM / KM_PER_LON

    grid_points = []

    lat = LAT_MIN
    while lat <= LAT_MAX:
        lon = LON_MIN
        while lon <= LON_MAX:
            gp = GridPoint(lat=round(lat, 6), lon=round(lon, 6))

            min_dist = float("inf")
            nearest_id = ""
            for a in anchors:
                d = haversine_km(lat, lon, a.lat, a.lon)
                if d < min_dist:
                    min_dist = d
                    nearest_id = a.id

            gp.dist_to_nearest_km = round(min_dist, 4)
            gp.nearest_anchor_id = nearest_id

            gp.idw_k3 = round(idw(lat, lon, anchors, k=3), 1)
            gp.idw_k5 = round(idw(lat, lon, anchors, k=5), 1)

            if gp.idw_k5 > 0:
                gp.idw_instability_pct = round(
                    abs(gp.idw_k3 - gp.idw_k5) / gp.idw_k5, 4
                )

            reasons = []

            adaptive_threshold, zone_name = get_threshold_for_point(lat, lon)
            if gp.dist_to_nearest_km > adaptive_threshold:
                reasons.append(f"distancia {gp.dist_to_nearest_km:.2f}km > {zone_name} {adaptive_threshold}km")

            if gp.idw_instability_pct > IDW_INSTABILITY_PCT:
                reasons.append(
                    f"inestabilidad IDW {gp.idw_instability_pct*100:.1f}% > {IDW_INSTABILITY_PCT*100:.0f}%"
                )

            gp.is_gap = len(reasons) > 0
            gp.gap_reasons = reasons

            gp.suggested_usd_m2 = round((gp.idw_k3 + gp.idw_k5) / 2, 0)

            grid_points.append(gp)
            lon += step_lon
        lat += step_lat

    return grid_points


def detect_gradient_anomalies(anchors: List[Anchor]) -> List[dict]:
    anomalies = []
    for i, a1 in enumerate(anchors):
        for a2 in anchors[i+1:]:
            d = haversine_km(a1.lat, a1.lon, a2.lat, a2.lon)
            if 0.001 < d < 0.5:
                price_diff = abs(a1.usd_m2 - a2.usd_m2)
                gradient = price_diff / d
                if gradient > GRADIENT_USD_PER_KM:
                    anomalies.append({
                        "ancla_a": a1.id,
                        "ancla_b": a2.id,
                        "distancia_km": round(d, 4),
                        "delta_usd_m2": price_diff,
                        "gradiente_usd_por_km": round(gradient, 1),
                        "lat_medio": round((a1.lat + a2.lat) / 2, 6),
                        "lon_medio": round((a1.lon + a2.lon) / 2, 6),
                    })
    return sorted(anomalies, key=lambda x: x["gradiente_usd_por_km"], reverse=True)


def cluster_gap_zones(gap_points: List[GridPoint], cluster_radius_km: float = 0.4) -> List[dict]:
    remaining = list(gap_points)
    clusters = []

    while remaining:
        seed = remaining.pop(0)
        cluster = [seed]
        still_remaining = []

        for gp in remaining:
            d = haversine_km(seed.lat, seed.lon, gp.lat, gp.lon)
            if d <= cluster_radius_km:
                cluster.append(gp)
            else:
                still_remaining.append(gp)

        remaining = still_remaining

        c_lat = sum(p.lat for p in cluster) / len(cluster)
        c_lon = sum(p.lon for p in cluster) / len(cluster)
        avg_value = sum(p.suggested_usd_m2 for p in cluster) / len(cluster)
        max_dist = max(p.dist_to_nearest_km for p in cluster)

        clusters.append({
            "n_puntos": len(cluster),
            "centroide_lat": round(c_lat, 6),
            "centroide_lon": round(c_lon, 6),
            "suggested_usd_m2": round(avg_value, 0),
            "max_dist_to_anchor_km": round(max_dist, 3),
            "severidad": _severity(max_dist, avg_value),
            "razones": list({r for p in cluster for r in p.gap_reasons}),
        })

    return sorted(clusters, key=lambda x: x["max_dist_to_anchor_km"], reverse=True)


def _severity(dist: float, value: float) -> str:
    if dist > 0.8:
        return "CRITICO"
    elif dist > 0.55:
        return "ALTO"
    elif dist > 0.40:
        return "MEDIO"
    else:
        return "BAJO"


def load_anchors_from_file(filepath: str = None) -> List[Anchor]:
    if filepath is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(base_dir, "anclas_rosario_v2_grid.json")
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    anclas_list = data.get("anclas", data)
    return [
        Anchor(id=a["id"], lat=a["lat"], lon=a["lon"], usd_m2=a["usd_m2"])
        for a in anclas_list
    ]


def generate_candidates_from_gaps(gap_zones: List[dict]) -> List[dict]:
    candidates = []
    for i, zone in enumerate(gap_zones):
        zone_type = "critico" if zone["severidad"] == "CRITICO" else "alto" if zone["severidad"] == "ALTO" else "medio"
        candidates.append({
            "id": f"auto_gap_{zone_type}_{i+1}",
            "lat": zone["centroide_lat"],
            "lon": zone["centroide_lon"],
            "zone": "macrocentro",
            "reason": zone["razones"],
            "severidad": zone["severidad"],
        })
    return candidates


def compute_mesh_quality_report(anchors: List[Anchor], grid: List[GridPoint]) -> dict:
    """
    Calcula métricas reales de calidad de la malla.
    Independientes del threshold elegido.
    """
    distances = [gp.dist_to_nearest_km for gp in grid]
    
    return {
        "dist_media_km": round(sum(distances) / len(distances), 3),
        "dist_mediana_km": round(sorted(distances)[len(distances)//2], 3),
        "dist_p90_km": round(sorted(distances)[int(len(distances)*0.90)], 3),
        "dist_p95_km": round(sorted(distances)[int(len(distances)*0.95)], 3),
        "dist_max_km": round(max(distances), 3),
        
        "cobertura_300m_pct": round(100 * sum(1 for d in distances if d <= 0.30) / len(distances), 1),
        "cobertura_400m_pct": round(100 * sum(1 for d in distances if d <= 0.40) / len(distances), 1),
        "cobertura_500m_pct": round(100 * sum(1 for d in distances if d <= 0.50) / len(distances), 1),
        "cobertura_600m_pct": round(100 * sum(1 for d in distances if d <= 0.60) / len(distances), 1),
        "cobertura_800m_pct": round(100 * sum(1 for d in distances if d <= 0.80) / len(distances), 1),
        
        "pct_puntos_inestables_12pct": round(
            100 * sum(1 for gp in grid if gp.idw_instability_pct > 0.12) / len(grid), 1
        ),
        "pct_puntos_inestables_8pct": round(
            100 * sum(1 for gp in grid if gp.idw_instability_pct > 0.08) / len(grid), 1
        ),
    }
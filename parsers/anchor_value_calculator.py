"""
anchor_value_calculator.py

Calcula el USD/m² de cada nueva ancla propuesta usando:

PASO 1 → IDW sobre anclas existentes (base objetiva)
PASO 2 → Ajuste por micro-mercado (tabla de factores por zona)
PASO 3 → Suavizado: verificar que no genere saltos nuevos > 15%
PASO 4 → Validación cruzada: comparar contra IDW sin la nueva ancla
PASO 5 → Etiqueta de confianza (HIGH / MEDIUM / LOW)

Toda la lógica es auditable: cada valor lleva su trazabilidad completa.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional
import anchor_gap_detector
from anchor_gap_detector import Anchor, haversine_km, GAP_DISTANCE_KM

idw = anchor_gap_detector.idw

MICRO_MARKET_ADJUSTMENTS = {
    "parque_independencia":      +0.05,
    "corredor_martin":           +0.03,
    "corredor_bv_oroño":         +0.04,
    "waterfront_rio":            +0.10,
    "fisherton_residencial":     +0.05,

    "macrocentro":                0.00,
    "centro":                     0.00,
    "pichincha":                  0.00,
    "echesortu":                  0.00,
    "ayacucho":                   0.00,

    "transicion_centro_oeste":   -0.04,
    "pre_sexta":                 -0.03,
    "zona_sur_intermedia":       -0.05,
    "oeste_circunvalacion":      -0.06,
    "periferia_sur":             -0.08,
    "periferia_norte_lejana":    -0.06,
}


@dataclass
class NewAnchorProposal:
    id: str
    lat: float
    lon: float

    usd_m2: float = 0.0
    usd_m2_idw_raw: float = 0.0
    micro_market_zone: str = ""
    micro_market_factor: float = 0.0
    usd_m2_after_adjustment: float = 0.0
    smoothing_ok: bool = True
    smoothing_notes: List[str] = field(default_factory=list)
    cross_validation_error_pct: float = 0.0
    confidence: str = "LOW"
    neighbors_used: List[dict] = field(default_factory=list)


def calculate_new_anchor(
    new_id: str,
    lat: float,
    lon: float,
    anchors: List[Anchor],
    micro_market_zone: str = "macrocentro",
    k_neighbors: int = 5,
) -> NewAnchorProposal:
    proposal = NewAnchorProposal(id=new_id, lat=lat, lon=lon)
    proposal.micro_market_zone = micro_market_zone

    distances = sorted(
        [(haversine_km(lat, lon, a.lat, a.lon), a) for a in anchors],
        key=lambda x: x[0]
    )
    neighbors_k = distances[:k_neighbors]

    proposal.neighbors_used = [
        {
            "id": a.id,
            "distancia_km": round(d, 4),
            "usd_m2": a.usd_m2,
            "peso_relativo": None,
        }
        for d, a in neighbors_k
    ]

    weights = []
    for d, a in neighbors_k:
        if d < 0.001:
            proposal.usd_m2_idw_raw = a.usd_m2
            proposal.usd_m2_after_adjustment = a.usd_m2
            proposal.usd_m2 = a.usd_m2
            proposal.confidence = "HIGH"
            return proposal
        w = 1.0 / (d ** 2)
        weights.append(w)

    total_weight = sum(weights)
    weighted_sum = sum(w * a.usd_m2 for w, (_, a) in zip(weights, neighbors_k))
    idw_value = weighted_sum / total_weight

    for i, neighbor in enumerate(proposal.neighbors_used):
        neighbor["peso_relativo"] = round(weights[i] / total_weight, 4)

    proposal.usd_m2_idw_raw = round(idw_value, 1)

    factor = MICRO_MARKET_ADJUSTMENTS.get(micro_market_zone, 0.0)
    proposal.micro_market_factor = factor
    adjusted = idw_value * (1 + factor)
    proposal.usd_m2_after_adjustment = round(adjusted, 1)

    rounded = round(adjusted / 10) * 10
    proposal.usd_m2 = rounded

    smoothing_issues = []
    for d, a in neighbors_k[:3]:
        if d < 0.5:
            delta_pct = abs(proposal.usd_m2 - a.usd_m2) / a.usd_m2
            if delta_pct > 0.15:
                smoothing_issues.append(
                    f"Salto {delta_pct*100:.1f}% con {a.id} ({a.usd_m2} USD/m²)"
                )

    proposal.smoothing_ok = len(smoothing_issues) == 0
    proposal.smoothing_notes = smoothing_issues

    if not proposal.smoothing_ok:
        nearest_val = neighbors_k[0][1].usd_m2
        smoothed = (proposal.usd_m2 + nearest_val) / 2
        smoothed_rounded = round(smoothed / 10) * 10
        proposal.smoothing_notes.append(
            f"Suavizado: {proposal.usd_m2} → {smoothed_rounded}"
        )
        proposal.usd_m2 = smoothed_rounded

    cv_error = abs(proposal.usd_m2 - proposal.usd_m2_idw_raw) / proposal.usd_m2_idw_raw
    proposal.cross_validation_error_pct = round(cv_error * 100, 2)

    min_dist = neighbors_k[0][0]
    if min_dist < 0.3 and cv_error < 0.08 and proposal.smoothing_ok:
        proposal.confidence = "HIGH"
    elif min_dist < 0.5 and cv_error < 0.15:
        proposal.confidence = "MEDIUM"
    else:
        proposal.confidence = "LOW"

    return proposal


def proposals_to_anchors(proposals: List[NewAnchorProposal]) -> List[dict]:
    return [
        {
            "id": p.id,
            "lat": p.lat,
            "lon": p.lon,
            "usd_m2": p.usd_m2,
            "_meta": {
                "idw_raw": p.usd_m2_idw_raw,
                "micro_market_zone": p.micro_market_zone,
                "micro_market_factor": p.micro_market_factor,
                "cv_error_pct": p.cross_validation_error_pct,
                "confidence": p.confidence,
                "smoothing_ok": p.smoothing_ok,
                "smoothing_notes": p.smoothing_notes,
                "neighbors": p.neighbors_used,
            }
        }
        for p in proposals
    ]


def determine_zone(lat: float, lon: float) -> str:
    if lat > -32.945 and lon > -60.610 and lon < -60.630:
        return "corredor_martin"
    elif lat > -32.945 and lon > -60.630 and lon < -60.650:
        return "macrocentro"
    elif lat > -32.960 and lon > -60.650 and lon < -60.700:
        return "transicion_centro_oeste"
    elif lat > -32.930 and lon > -60.750:
        return "fisherton_residencial"
    elif lat > -32.970 and lon > -60.700:
        return "periferia_sur"
    elif lat < -32.990:
        return "periferia_norte_lejana"
    else:
        return "macrocentro"
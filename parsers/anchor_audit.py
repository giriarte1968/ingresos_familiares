"""
anchor_audit.py

Orquestador completo:
  1. Carga anclas existentes desde JSON
  2. Detecta huecos automáticamente
  3. Genera candidates desde huecos detectados
  4. Calcula valores para nuevas anclas
  5. Genera reporte completo
  6. Exporta JSONs

USO:
  python parsers/anchor_audit.py
  python parsers/anchor_audit.py --only-critical
  python parsers/anchor_audit.py --export-geojson
"""

import json
import argparse
import os
from datetime import datetime
from typing import List, Dict

import anchor_gap_detector
import anchor_value_calculator


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCHOR_FILE = os.path.join(BASE_DIR, "anclas_rosario_v3_grid.json")


def run_full_audit(only_critical: bool = False, export_geojson: bool = False):
    print("\n" + "="*70)
    print("AUDIT COMPLETO DE MALLA DE ANCLAS — ROSARIO")
    print(f"    {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)

    print(f"\nCargando anclas desde: {ANCHOR_FILE}")
    anchors = anchor_gap_detector.load_anchors_from_file(ANCHOR_FILE)
    print(f"  Anclas cargadas: {len(anchors)}")
    print(f"  Rango USD/m2: {min(a.usd_m2 for a in anchors)} -> {max(a.usd_m2 for a in anchors)}")

    print("\nConstruyendo grilla de evaluacion (250m x 250m)...")
    grid = anchor_gap_detector.build_evaluation_grid(anchors)
    gap_points = [gp for gp in grid if gp.is_gap]

    print(f"  Total puntos evaluados: {len(grid)}")
    print(f"  Puntos con hueco:   {len(gap_points)} ({100*len(gap_points)/len(grid):.1f}%)")

    # Reporte de calidad de malla
    quality = anchor_gap_detector.compute_mesh_quality_report(anchors, grid)
    print("\n[CALIDAD DE MALLA]")
    print(f"  Dist. media a ancla mas cercana : {quality['dist_media_km']} km")
    print(f"  Dist. mediana                : {quality['dist_mediana_km']} km")
    print(f"  Dist. P90 (peor 10%)       : {quality['dist_p90_km']} km")
    print(f"  Dist. maxima (peor punto)     : {quality['dist_max_km']} km")
    print(f"")
    print(f"  Cobertura a 300m : {quality['cobertura_300m_pct']:>5.1f}%")
    print(f"  Cobertura a 400m : {quality['cobertura_400m_pct']:>5.1f}%")
    print(f"  Cobertura a 500m : {quality['cobertura_500m_pct']:>5.1f}%")
    print(f"  Cobertura a 600m : {quality['cobertura_600m_pct']:>5.1f}%")
    print(f"  Cobertura a 800m : {quality['cobertura_800m_pct']:>5.1f}%")
    print(f"")
    print(f"  Puntos IDW inestables (>12%) : {quality['pct_puntos_inestables_12pct']}%")
    print(f"  Puntos IDW inestables (> 8%) : {quality['pct_puntos_inestables_8pct']}%")

    print("\nClusterizando zonas de hueco...")
    clusters = anchor_gap_detector.cluster_gap_zones(gap_points)

    if only_critical:
        clusters = [c for c in clusters if c["severidad"] in ("CRITICO", "ALTO")]

    print(f"  Zonas detectadas: {len(clusters)}")

    sev_count = {"CRITICO": 0, "ALTO": 0, "MEDIO": 0, "BAJO": 0}
    for c in clusters:
        sev_count[c["severidad"]] += 1
    for s, n in sev_count.items():
        icon = {"CRITICO": "R", "ALTO": "A", "MEDIO": "M", "BAJO": "B"}[s]
        if n > 0:
            print(f"  [{icon}] {s}: {n} zonas")

    print("\nAnalizando gradientes entre anclas vecinas...")
    anomalies = anchor_gap_detector.detect_gradient_anomalies(anchors)
    print(f"  Gradientes anomalo (> 1200 USD/km): {len(anomalies)}")
    for a in anomalies[:5]:
        print(f"    {a['ancla_a']} <-> {a['ancla_b']}: "
              f"{a['delta_usd_m2']} USD/m2 en {a['distancia_km']}km "
              f"= {a['gradiente_usd_por_km']:.0f} USD/km")

    candidates = anchor_gap_detector.generate_candidates_from_gaps(clusters)
    print(f"\nGenerando {len(candidates)} candidates desde huecos detectados...")

    proposals = []
    for candidate in candidates:
        zone = anchor_value_calculator.determine_zone(candidate["lat"], candidate["lon"])
        p = anchor_value_calculator.calculate_new_anchor(
            new_id=candidate["id"],
            lat=candidate["lat"],
            lon=candidate["lon"],
            anchors=anchors,
            micro_market_zone=zone,
        )
        proposals.append(p)

    conf_count = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for p in proposals:
        conf_count[p.confidence] += 1

    print(f"  Confidence HIGH:   {conf_count['HIGH']}")
    print(f"  Confidence MEDIUM: {conf_count['MEDIUM']}")
    print(f"  Confidence LOW:    {conf_count['LOW']}")

    print("\n" + "-"*70)
    print("NUEVAS ANCLAS PROPUESTAS")
    print("-"*70)
    print(f"{'ID':<40} {'IDW_raw':>8} {'Ajuste':>7} {'Final':>7} {'Conf':>6}")
    print("-"*70)

    for p in sorted(proposals, key=lambda x: x.usd_m2, reverse=True):
        adj_str = f"{p.micro_market_factor*100:+.0f}%" if p.micro_market_factor != 0 else "  0%"
        smooth_warn = " !" if not p.smoothing_ok else ""
        print(
            f"{p.id:<40} "
            f"{p.usd_m2_idw_raw:>8.0f} "
            f"{adj_str:>7} "
            f"{p.usd_m2:>7.0f} "
            f"{p.confidence:>6}"
            f"{smooth_warn}"
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")

    gaps_output = {
        "generated_at": datetime.now().isoformat(),
        "total_gap_zones": len(clusters),
        "severity_summary": sev_count,
        "gap_zones": clusters,
        "gradient_anomalies": anomalies,
    }
    gaps_file = os.path.join(BASE_DIR, f"gaps_rosario_{timestamp}.json")
    with open(gaps_file, "w", encoding="utf-8") as f:
        json.dump(gaps_output, f, ensure_ascii=False, indent=2)
    print(f"\nHuecos exportados -> {gaps_file}")

    new_anchors_output = anchor_value_calculator.proposals_to_anchors(proposals)
    new_anchors_file = os.path.join(BASE_DIR, f"new_anchors_{timestamp}.json")
    with open(new_anchors_file, "w", encoding="utf-8") as f:
        json.dump(new_anchors_output, f, ensure_ascii=False, indent=2)
    print(f"Nuevas anclas     -> {new_anchors_file}")

    with open(ANCHOR_FILE, "r", encoding="utf-8") as f:
        original_data = json.load(f)
    
    original_anchors = original_data.get("anclas", original_data)
    
    trusted_new = [
        {"id": p.id, "lat": p.lat, "lon": p.lon, "usd_m2": p.usd_m2}
        for p in proposals
        if p.confidence in ("HIGH", "MEDIUM")
    ]
    
    combined = original_data.copy()
    combined["anclas"] = original_anchors + trusted_new
    combined["fuente"] = f"anclas_rosario_v3_{timestamp}.json"
    combined["config"] = original_data.get("config", {})
    combined["config"]["n_anclas_originales"] = len(original_anchors)
    combined["config"]["n_anclas_nuevas"] = len(trusted_new)
    combined["config"]["n_anclas_total"] = len(combined["anclas"])
    combined["config"]["audit_date"] = timestamp

    combined_file = os.path.join(BASE_DIR, f"anclas_rosario_v3_{timestamp}.json")
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)
    print(f"JSON final v3     -> {combined_file}")

    if export_geojson:
        features = []
        for a in combined["anclas"]:
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [a["lon"], a["lat"]]},
                "properties": {
                    "id": a["id"],
                    "usd_m2": a["usd_m2"],
                    "nueva": a["id"] in [p.id for p in proposals],
                }
            })
        geojson = {"type": "FeatureCollection", "features": features}
        geo_file = os.path.join(BASE_DIR, f"anclas_rosario_v3_{timestamp}.geojson")
        with open(geo_file, "w", encoding="utf-8") as f:
            json.dump(geojson, f, ensure_ascii=False, indent=2)
        print(f"GeoJSON           -> {geo_file}")

    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)
    print(f"  Anclas originales     : {len(original_anchors)}")
    print(f"  Nuevas anclas     : {len(proposals)}")
    print(f"  Anclas confiables : {len(trusted_new)} (HIGH + MEDIUM)")
    print(f"  Anclas en v3 final: {len(combined['anclas'])}")
    print(f"  Cobertura        : {'COMPLETA' if sev_count['CRITICO'] == 0 else 'PARCIAL'}")
    print("="*70 + "\n")

    return {
        "clusters": clusters,
        "proposals": proposals,
        "trusted_new": trusted_new,
        "combined": combined,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit de malla de anclas Rosario")
    parser.add_argument("--only-critical", action="store_true", help="Solo mostrar huecos criticos y altos")
    parser.add_argument("--export-geojson", action="store_true", help="Exportar GeoJSON")
    args = parser.parse_args()

    run_full_audit(
        only_critical=args.only_critical,
        export_geojson=args.export_geojson,
    )
"""Tests for amenity normalization, cap, and NLP dedup (TAREA-XXX)."""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from parsers.mercado_inmobiliario import calcular_delta_amenities, AMENITY_WEIGHTS, AMENITY_TOTAL_CAP
from parsers.nlp_inmobiliario import calcular_ajuste_nlp_detallado, _keywords_a_excluir


def test_parrilla_propia_mayor_que_compartida():
    d1, _ = calcular_delta_amenities(["parrilla_propia"])
    d2, _ = calcular_delta_amenities(["parrilla_compartida"])
    assert d1 > d2, f"propia {d1} deberia > compartida {d2}"


def test_terrraza_compartida_impacto_bajo():
    delta, detalle = calcular_delta_amenities(["terraza_compartida"])
    assert 0 <= delta <= 0.01, f"terraza_compartida delta={delta} fuera de rango"
    assert "terraza_compartida" in detalle


def test_amenities_cap_no_supera_6_pct():
    detalles = [
        "seguridad_24hs", "pileta", "sum", "gym",
        "parrilla_propia", "terraza_compartida",
        "aberturas_premium"
    ]
    delta, detalle = calcular_delta_amenities(detalles)
    assert delta <= AMENITY_TOTAL_CAP, f"cap excedido: {delta} > {AMENITY_TOTAL_CAP}"
    assert delta == AMENITY_TOTAL_CAP, f"deberia estar al cap, obtuvo {delta}"


def test_legacy_parrilla_equivale_a_compartida():
    delta, detalle = calcular_delta_amenities(["parrilla"])
    assert "parrilla_compartida" in detalle, "parrilla legacy deberia mapear a compartida"
    assert detalle["parrilla_compartida"] == AMENITY_WEIGHTS["parrilla_compartida"]
    assert delta == AMENITY_WEIGHTS["parrilla_compartida"]


def test_nlp_no_duplica_amenity_estructurado():
    desc = "Departamento con terraza compartida, parrilla, pileta y SUM"
    amenities = ["parrilla_compartida", "terraza_compartida"]
    ajuste, detecciones = calcular_ajuste_nlp_detallado(
        desc, amenities_present=amenities
    )
    keywords = [d[0] for d in detecciones]
    for kw in keywords:
        assert "parrilla" not in kw.lower(), f"NLP detecto parrilla duplicada: {kw}"
        assert "terraza compartida" not in kw.lower(), f"NLP detecto terraza duplicada: {kw}"
    # pileta y sum NO estan en amenities, deben detectarse
    pileta_detectada = any("pileta" in kw.lower() for kw in keywords)
    assert pileta_detectada, "pileta deberia detectarse por NLP (no esta en amenities estructurados)"


def test_nlp_detecta_si_no_estructurado():
    desc = "Departamento con parrilla en terraza"
    ajuste, detecciones = calcular_ajuste_nlp_detallado(desc, amenities_present=[])
    assert any("parrilla" in d[0].lower() for d in detecciones), "NLP deberia detectar parrilla"


def test_keywords_excluir_funciona():
    excluir = _keywords_a_excluir(["parrilla_compartida", "pileta"])
    assert "parrilla" in excluir
    assert "parrillero" in excluir
    assert "pileta" in excluir
    assert "piscina" in excluir
    assert "sum" not in excluir  # no esta en amenities


def test_backward_compatibility_sin_amenities():
    desc = "Luminoso departamento con pileta"
    ajuste_con, det_con = calcular_ajuste_nlp_detallado(desc, amenities_present=["pileta"])
    ajuste_sin, det_sin = calcular_ajuste_nlp_detallado(desc)  # sin parametro
    # Sin amenities, pileta se detecta normalmente
    assert any("pileta" in d[0].lower() for d in det_sin), "sin amenities, pileta debe detectarse"
    # Con amenities, pileta no se duplica
    assert not any("pileta" in d[0].lower() for d in det_con), "con amenities, pileta no debe duplicarse"


def test_delta_amenities_con_lista_vacia():
    delta, detalle = calcular_delta_amenities([])
    assert delta == 0.0
    assert detalle == {}


def test_delta_amenities_con_none():
    delta, detalle = calcular_delta_amenities(None)
    assert delta == 0.0
    assert detalle == {}


def test_delta_seguridad_24hs_reducido():
    """seguridad_24hs ahora aporta 0.03 (antes era 0.06 via f_seguridad multiplicativo)"""
    delta, detalle = calcular_delta_amenities(["seguridad_24hs"])
    assert delta == 0.030, f"seguridad_24hs deberia ser 0.030, obtuvo {delta}"


if __name__ == "__main__":
    test_parrilla_propia_mayor_que_compartida()
    test_terrraza_compartida_impacto_bajo()
    test_amenities_cap_no_supera_6_pct()
    test_legacy_parrilla_equivale_a_compartida()
    test_nlp_no_duplica_amenity_estructurado()
    test_nlp_detecta_si_no_estructurado()
    test_keywords_excluir_funciona()
    test_backward_compatibility_sin_amenities()
    test_delta_amenities_con_lista_vacia()
    test_delta_amenities_con_none()
    test_delta_seguridad_24hs_reducido()
    print("Todos los tests TAREA-XXX OK")

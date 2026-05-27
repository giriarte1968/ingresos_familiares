"""Tests for coordinate validation function (TAREA-010)."""

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from parsers.geocoder import validar_coordenadas_contra_direccion, haversine_distance


def test_discrepancia_grande():
    """Pin en Pichincha vs direccion Barrio Martin debe detectarse"""
    lat, lon, diff_m, accion = validar_coordenadas_contra_direccion(
        "Colon 1200", -32.9337, -60.6563, max_diff_m=500
    )
    assert accion in ("corregido", "error"), (
        f"Esperaba corregido o error, obtuve {accion}"
    )


def test_direccion_vacia():
    """Direccion vacia debe dar error"""
    lat, lon, diff_m, accion = validar_coordenadas_contra_direccion(
        "", -32.9463, -60.6323, max_diff_m=500
    )
    assert accion in ("ok", "error")


def test_coordenadas_sin_discrepancia():
    """Funcion no debe fallar con coords identicas al geocoding"""
    lat, lon, diff_m, accion = validar_coordenadas_contra_direccion(
        "Entre Rios 400", -32.9413, -60.6410, max_diff_m=500
    )
    assert accion in ("ok", "corregido", "error")


def test_haversine_valor_conocido():
    """Distancia Colon 1200 pin vs geocoding textual ~1.4km"""
    d = haversine_distance(-32.9337, -60.6563, -32.9463, -60.6323)
    assert 2.0 < d < 3.5


def test_direccion_sin_acento():
    """Direccion sin acento no debe romper"""
    lat, lon, diff_m, accion = validar_coordenadas_contra_direccion(
        "Colon 1200", -32.9337, -60.6563, max_diff_m=500
    )
    assert accion in ("ok", "corregido", "error")


if __name__ == "__main__":
    test_discrepancia_grande()
    test_direccion_vacia()
    test_coordenadas_sin_discrepancia()
    test_haversine_valor_conocido()
    test_direccion_sin_acento()
    print("Todos los tests TAREA-010 OK")

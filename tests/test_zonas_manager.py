"""
Tests para el sistema de macrozonas de depreciacion (FASE 7A).
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.zonas_manager import (
    resolver_macrozona,
    normalizar_texto_zona,
    limpiar_cache,
)


class TestNormalizarTexto:
    """Tests de normalizacion de texto de zona."""

    def test_lowercase(self):
        assert normalizar_texto_zona("Martin") == "martin"

    def test_tildes(self):
        assert normalizar_texto_zona("Martín") == "martin"

    def test_tildes_multiples(self):
        assert "sexta pellegrini" in normalizar_texto_zona("Sexta Pellegrini")

    def test_tilde_otras(self):
        assert "luduena" in normalizar_texto_zona("Ludueña")

    def test_vacio(self):
        assert normalizar_texto_zona("") == ""

    def test_none(self):
        assert normalizar_texto_zona(None) == ""


class TestResolverTexto:
    """Tests de resolucion por match textual."""

    def test_mabel_martin(self):
        """Mabel (zona=Martin) -> centro_premium con confianza ALTA."""
        prop = {"zona": "Martin"}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "centro_premium", f"Esperaba centro_premium, obtuvo {res}"
        assert res["confianza"] == "ALTA"
        assert res["metodo"] == "textual"

    def test_ayacucho_sexta(self):
        """Ayacucho (zona=Sexta Pellegrini) -> macrocentro."""
        prop = {"zona": "Sexta Pellegrini"}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "macrocentro", f"Esperaba macrocentro, obtuvo {res}"
        assert res["confianza"] == "ALTA"

    def test_vera_facultades(self):
        """Vera (zona=Facultades) -> macrocentro."""
        prop = {"zona": "Facultades"}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "macrocentro", f"Esperaba macrocentro, obtuvo {res}"
        assert res["confianza"] == "ALTA"

    def test_p1200_centro(self):
        """P1200 (zona=Centro) -> centro_premium (textual match)."""
        prop = {"zona": "Centro"}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "centro_premium", f"Esperaba centro_premium, obtuvo {res}"
        assert res["confianza"] == "ALTA"

    def test_amenabar_otro(self):
        """Amenabar (zona=Oeste) -> resto_rosario."""
        limpiar_cache()
        prop = {"zona": "Oeste", "lat": -32.95, "lon": -60.68}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "resto_rosario"
        assert res["confianza"] == "ALTA"

    def test_pichincha_premium(self):
        prop = {"zona": "Pichincha"}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "centro_premium", f"obtuvo {res}"

    def test_abasto_macrocentro(self):
        prop = {"zona": "Abasto"}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "macrocentro"


class TestResolverBbox:
    """Tests de resolucion por bounding box."""

    def test_bbox_centro_premium(self):
        """Coordenadas en zona centro premium sin zona textual -> bbox."""
        prop = {"lat": -32.945, "lon": -60.640}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "centro_premium", f"obtuvo {res}"
        assert res["confianza"] == "MEDIA"
        assert res["metodo"] == "bbox"

    def test_bbox_macrocentro(self):
        """Coordenadas en macrocentro."""
        prop = {"lat": -32.965, "lon": -60.635}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "macrocentro", f"obtuvo {res}"

    def test_bbox_sin_texto(self):
        """Sin zona textual pero con coordenadas en centro premium."""
        prop = {"zona": "Otra Zona Desconocida", "lat": -32.945, "lon": -60.640}
        res = resolver_macrozona(prop)
        # Primero intenta textual -> falla -> bbox
        assert res["macrozona_id"] == "centro_premium"
        assert res["confianza"] == "MEDIA"
        assert res["metodo"] == "bbox"

    def test_bbox_fuera(self):
        """Coordenadas fuera de toda bbox + zona desconocida -> default."""
        prop = {"zona": "Zona Desconocida"}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "resto_rosario"
        assert res["confianza"] == "BAJA"
        assert res["metodo"] == "default"


class TestPropiedadesReales:
    """Tests con las propiedades ancla reales."""

    def test_mabel_real(self):
        """Mabel desde propiedades.json."""
        prop = {"zona": "Martin", "lat": -32.9541, "lon": -60.6316}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "centro_premium", f"obtuvo {res}"

    def test_ayacucho_real(self):
        """Ayacucho desde propiedades.json."""
        prop = {"zona": "Sexta Pellegrini", "lat": -32.9603, "lon": -60.6299}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "macrocentro", f"obtuvo {res}"

    def test_vera_real(self):
        """Vera desde propiedades.json."""
        prop = {"zona": "Facultades", "lat": -32.9452, "lon": -60.6377}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "macrocentro", f"obtuvo {res}"

    def test_p1200_real(self):
        """P1200 desde propiedades.json."""
        prop = {"zona": "Centro", "lat": -32.9487, "lon": -60.6407}
        res = resolver_macrozona(prop)
        assert res["macrozona_id"] == "centro_premium", f"obtuvo {res}"

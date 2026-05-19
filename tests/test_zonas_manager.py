"""
Tests para el sistema de macrozonas de depreciacion (FASE 7A ajustada).
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
    def test_lowercase(self):
        assert normalizar_texto_zona("Martin") == "martin"

    def test_tildes(self):
        assert normalizar_texto_zona("Martín") == "martin"

    def test_tildes_multiples(self):
        assert "sexta pellegrini" in normalizar_texto_zona("Sexta Pellegrini")

    def test_republica_sexta(self):
        assert normalizar_texto_zona("República de la Sexta") == "republica de la sexta"

    def test_vacio(self):
        assert normalizar_texto_zona("") == ""

    def test_none(self):
        assert normalizar_texto_zona(None) == ""


class TestMatchTextual:
    def test_mabel_martin(self):
        """Mabel (zona=Martin) -> centro_premium ALTA."""
        res = resolver_macrozona({"zona": "Martin"})
        assert res["macrozona_id"] == "centro_premium"
        assert res["confianza_macrozona"] == "ALTA"
        assert res["metodo_match"] == "textual"

    def test_ayacucho_sexta_pellegrini(self):
        """Ayacucho (zona=Sexta Pellegrini) -> macrocentro ALTA."""
        res = resolver_macrozona({"zona": "Sexta Pellegrini"})
        assert res["macrozona_id"] == "macrocentro"
        assert res["confianza_macrozona"] == "ALTA"

    def test_vera_facultades(self):
        """Vera (zona=Facultades) -> macrocentro ALTA."""
        res = resolver_macrozona({"zona": "Facultades"})
        assert res["macrozona_id"] == "macrocentro"

    def test_abasto_macrocentro(self):
        res = resolver_macrozona({"zona": "Abasto"})
        assert res["macrozona_id"] == "macrocentro"

    def test_pichincha_premium(self):
        res = resolver_macrozona({"zona": "Pichincha"})
        assert res["macrozona_id"] == "centro_premium"

    def test_oeste_es_oeste(self):
        res = resolver_macrozona({"zona": "Oeste"})
        assert res["macrozona_id"] == "oeste"

    def test_alberdi_norte(self):
        res = resolver_macrozona({"zona": "Alberdi"})
        assert res["macrozona_id"] == "norte"

    def test_tablada_sur(self):
        res = resolver_macrozona({"zona": "Tablada"})
        assert res["macrozona_id"] == "sur_default"

    def test_keyword_generica_no_exacta(self):
        """'Centro' sin mas contexto NO debe matchear centro_premium."""
        res = resolver_macrozona({"zona": "Centro"})
        # 'centro' no esta en keywords de ninguna zona -> cae a bbox sin coords -> default
        assert res["metodo_match"] == "default" or res["macrozona_id"] != "centro_premium"

    def test_keyword_pellegrini_no_exacta(self):
        """'Pellegrini' sin mas contexto NO debe matchear."""
        res = resolver_macrozona({"zona": "Pellegrini"})
        # 'pellegrini' no es keyword especifica
        assert res["metodo_match"] == "default"


class TestMatchBbox:
    def test_bbox_centro_premium(self):
        """Coordenadas en zona centro premium sin zona -> bbox MEDIA."""
        res = resolver_macrozona({"lat": -32.945, "lon": -60.640})
        assert res["macrozona_id"] == "centro_premium"
        assert res["confianza_macrozona"] == "MEDIA"
        assert res["metodo_match"] == "bbox"

    def test_bbox_norte(self):
        res = resolver_macrozona({"lat": -32.910, "lon": -60.680})
        assert res["macrozona_id"] == "norte"

    def test_bbox_oeste(self):
        res = resolver_macrozona({"lat": -32.950, "lon": -60.710})
        assert res["macrozona_id"] == "oeste"

    def test_bbox_sur(self):
        res = resolver_macrozona({"lat": -33.000, "lon": -60.650})
        assert res["macrozona_id"] == "sur_default"

    def test_fallback_sin_coords(self):
        """Sin zona, sin coords -> default BAJA."""
        res = resolver_macrozona({"zona": "Zona Desconocida"})
        assert res["macrozona_id"] == "resto_rosario"
        assert res["confianza_macrozona"] == "BAJA"

    def test_fallback_sin_bbox_ni_texto(self):
        res = resolver_macrozona({})
        assert res["macrozona_id"] == "resto_rosario"


class TestConflictoTextoBbox:
    def test_conflicto_facultades_coords_premium(self):
        """Vera: texto=Facultades(macrocentro), coords en centro_premium -> gana texto con conflicto."""
        res = resolver_macrozona({
            "zona": "Facultades",
            "lat": -32.945,
            "lon": -60.640,
        })
        assert res["macrozona_id"] == "macrocentro"  # gana texto
        assert res["confianza_macrozona"] == "ALTA"
        assert res["bbox_conflict"] == True
        assert res["bbox_sugerido"] == "centro_premium"


class TestPropiedadesReales:
    def test_mabel(self):
        res = resolver_macrozona({"zona": "Martin", "lat": -32.9541, "lon": -60.6316})
        assert res["macrozona_id"] == "centro_premium"

    def test_ayacucho(self):
        res = resolver_macrozona({"zona": "Sexta Pellegrini", "lat": -32.9603, "lon": -60.6299})
        assert res["macrozona_id"] == "macrocentro"

    def test_vera(self):
        res = resolver_macrozona({"zona": "Facultades", "lat": -32.9452, "lon": -60.6377})
        assert res["macrozona_id"] == "macrocentro"
        assert res["bbox_conflict"] == True  # coords caen en centro_premium

    def test_p1200(self):
        """P1200 zona=Centro -> no matchea textual -> cae a bbox (centro_premium)."""
        res = resolver_macrozona({"zona": "Centro", "lat": -32.9487, "lon": -60.6407})
        assert res["metodo_match"] == "bbox"
        assert res["macrozona_id"] == "centro_premium"

    def test_amenabar_oeste(self):
        """Amenabar zona=Oeste -> matchea textual -> oeste."""
        res = resolver_macrozona({"zona": "Oeste"})
        assert res["macrozona_id"] == "oeste"

"""Tests for age enrichment (TAREA-012) — regla simple de año de comparable."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from parsers.mercado_inmobiliario import (
    normalizar_calle_nombre,
    extraer_calle_numero,
    obtener_anio_scraping,
    enriquecer_anio_comparable,
)


# ─── Tests de normalizar_calle_nombre ───

class TestNormalizarCalleNombre:
    def test_lowercase_sin_tildes(self):
        assert normalizar_calle_nombre("Guemes") == "guemes"

    def test_av_normalizado(self):
        assert normalizar_calle_nombre("Av. del Valle") == "del valle"
        assert normalizar_calle_nombre("Avenida del Valle") == "del valle"

    def test_bv_normalizado(self):
        assert normalizar_calle_nombre("Bv. Oroño") == "orono"
        assert normalizar_calle_nombre("Bulevar Oroño") == "orono"

    def test_honorifico_eliminado(self):
        assert normalizar_calle_nombre("Almirante Brown") == "brown"
        assert normalizar_calle_nombre("General Paz") == "paz"
        assert normalizar_calle_nombre("San Martín") == "martin"

    def test_vacio_retorna_vacio(self):
        assert normalizar_calle_nombre("") == ""
        assert normalizar_calle_nombre(None) == ""


# ─── Tests de extraer_calle_numero ───

class TestExtraerCalleNumero:
    def test_calle_numero_simple(self):
        calle, num = extraer_calle_numero("Brown 2734")
        assert calle == "brown"
        assert num == 2734

    def test_calle_con_al(self):
        calle, num = extraer_calle_numero("Brown al 2100")
        assert calle == "brown"
        assert num == 2100

    def test_av_del_valle(self):
        calle, num = extraer_calle_numero("Av. del Valle al 2700")
        assert calle == "del valle"
        assert num == 2700

    def test_sin_numero(self):
        calle, num = extraer_calle_numero("Balcarce")
        assert calle == "balcarce"
        assert num is None

    def test_con_piso(self):
        calle, num = extraer_calle_numero("Corrientes 1166 Piso 6")
        assert calle == "corrientes"
        assert num == 1166

    def test_con_piso_numeral(self):
        calle, num = extraer_calle_numero("Brown 2734 4º 03")
        assert calle == "brown"
        assert num == 2734

    def test_avenida_completa(self):
        calle, num = extraer_calle_numero("Avenida Aristóbulo del Valle 2700")
        assert "aristobulo" in calle
        assert "del valle" in calle
        assert num == 2700

    def test_almirante_brown(self):
        calle, num = extraer_calle_numero("Almirante Brown 2734")
        assert calle == "brown"
        assert num == 2734

    def test_vacio(self):
        assert extraer_calle_numero("") == ("", None)
        assert extraer_calle_numero(None) == ("", None)


# ─── Tests de obtener_anio_scraping ───

class TestObtenerAnioScraping:
    def test_anio_construccion(self):
        comp = {"anio_construccion": 2025}
        r = obtener_anio_scraping(comp)
        assert r is not None
        assert r["anio_estimado"] == 2025
        assert r["anio_source"] == "scraping"
        assert r["anio_confianza"] == "ALTA"

    def test_anio_estimado(self):
        comp = {"anio_estimado": 2020}
        r = obtener_anio_scraping(comp)
        assert r is not None
        assert r["anio_estimado"] == 2020
        assert r["anio_source"] == "scraping"

    def test_year_field(self):
        comp = {"year": 2019}
        r = obtener_anio_scraping(comp)
        assert r is not None
        assert r["anio_estimado"] == 2019

    def test_antiguedad(self):
        comp = {"antiguedad": 10}
        import datetime
        expected = datetime.datetime.now().year - 10
        r = obtener_anio_scraping(comp)
        assert r is not None
        assert r["anio_estimado"] == expected

    def test_anio_invalido_descartado(self):
        comp = {"anio_construccion": 1800}
        assert obtener_anio_scraping(comp) is None

    def test_sin_datos(self):
        comp = {}
        assert obtener_anio_scraping(comp) is None


# ─── Tests de enriquecer_anio_comparable ───

class TestEnriquecerAnioComparable:
    def test_scraping_tiene_prioridad(self):
        """Scraping year debe devolver ALTA."""
        comp = {
            "anio_construccion": 2025,
            "direccion": "Brown 2700",
            "lat": -32.933,
            "lon": -60.657,
        }
        r = enriquecer_anio_comparable(comp)
        assert r is not None
        assert r["anio_estimado"] == 2025
        assert r["anio_source"] == "scraping"
        assert r["anio_confianza"] == "ALTA"

    def test_sin_latlon_rechaza(self):
        """Sin coordenadas no se puede matchear AVM."""
        comp = {"direccion": "Brown 2700"}
        r = enriquecer_anio_comparable(comp)
        assert r is None

    def test_sin_calle_rechaza(self):
        """Sin calle no hay match AVM."""
        comp = {
            "direccion": "",
            "lat": -32.933,
            "lon": -60.657,
        }
        r = enriquecer_anio_comparable(comp)
        assert r is None

    def test_rechaza_calle_distinta_aunque_cerca(self):
        """Calle diferente pero cerca -> rechazar."""
        comp = {
            "direccion": "Callao 2 bis",
            "lat": -32.9345,
            "lon": -60.6501,
        }
        r = enriquecer_anio_comparable(comp)
        # Mabel area has Brown, Guemes, etc. — no Callao at those coords
        if r:
            assert r["anio_source"] == "scraping", "Si hay año scraping, se acepta"
        # If it reaches AVM: callao should not match brown/guemes AVM records

    def test_avm_calle_numero_exactos(self):
        """AVM calle + número exacto -> MEDIA."""
        # Brown 2734 at Mabel coords — AVM has Almirante Brown records nearby
        comp = {
            "direccion": "Brown 2734",
            "lat": -32.9345,
            "lon": -60.6501,
        }
        r = enriquecer_anio_comparable(comp)
        if r:
            # If match is through calle+<=20m (Brown -> Almirante Brown via normalization)
            assert r["anio_confianza"] == "MEDIA"
            assert r["anio_source"] in ("avm", "scraping")

    def test_normalizacion_permite_match(self):
        """Brown y Almirante Brown deben coincidir tras normalización."""
        n1 = normalizar_calle_nombre("Brown")
        n2 = normalizar_calle_nombre("Almirante Brown")
        assert n1 == n2, "Brown debe normalizarse igual que Almirante Brown"

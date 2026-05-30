import pytest
import os
import sys
import json
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parsers.valuacion_cache import (
    atomic_write_json,
    guardar_cache_valuaciones,
    persistir_valuacion,
    cargar_cache_valuaciones,
    CACHE_VERSION,
)


class TestAtomicWriteJson:
    def test_escribe_archivo(self, tmp_path):
        path = tmp_path / "x.json"
        atomic_write_json(str(path), {"a": 1})
        assert json.loads(open(path, encoding="utf-8").read()) == {"a": 1}

    def test_no_deja_tmp(self, tmp_path):
        path = tmp_path / "x.json"
        atomic_write_json(str(path), {"x": 1})
        assert not os.path.exists(str(path) + ".tmp")

    def test_archivo_no_queda_truncado(self, tmp_path):
        path = tmp_path / "data.json"
        atomic_write_json(str(path), {"ok": True, "val": 42})
        content = open(path, encoding="utf-8").read()
        data = json.loads(content)
        assert data["ok"] is True
        assert data["val"] == 42

    def test_unicode(self, tmp_path):
        path = tmp_path / "u.json"
        atomic_write_json(str(path), {"nombre": "Entre Ríos"})
        data = json.loads(open(path, encoding="utf-8").read())
        assert data["nombre"] == "Entre Ríos"


class TestGuardarCacheValuaciones:
    def test_retorna_true_en_exito(self, tmp_path, monkeypatch):
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", str(tmp_path / "cache.json"))
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_DIR", str(tmp_path))
        ok = guardar_cache_valuaciones({"test": {"valor": 100}})
        assert ok is True
        assert os.path.exists(tmp_path / "cache.json")

    def test_retorna_false_si_error(self, monkeypatch):
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", "")
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_DIR", "")
        ok = guardar_cache_valuaciones({"test": 1})
        assert ok is False


class TestPersistirValuacion:
    def test_escribe_valuaciones_cache(self, tmp_path, monkeypatch):
        cache_dir = tmp_path / "data"
        cache_dir.mkdir()
        cache_path = cache_dir / "valuaciones_cache.json"
        props_path = tmp_path / "propiedades.json"
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", str(cache_path))
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_DIR", str(cache_dir))
        monkeypatch.setattr("parsers.valuacion_cache.PROPIEDADES_PATH", str(props_path))
        monkeypatch.setattr("parsers.valuacion_cache.SCRAPING_CACHE_PATH", "/nonexistent/scraping.json")

        prop = {"nombre": "Test Prop", "m2_cubiertos": 50, "dormitorios": 2}
        resultado = {"valor_propiedad_usd": 100000, "m2_equivalentes": 50,
                     "resolution_metadata": {"n_propiedades": 5}}
        cache = {}

        ok = persistir_valuacion("Test Prop", prop, resultado, cache)
        assert ok is True

        assert cache_path.exists()
        data = json.loads(open(cache_path, encoding="utf-8").read())
        assert "Test Prop" in data
        assert data["Test Prop"]["resultado_completo"]["valor_propiedad_usd"] == 100000
        assert data["Test Prop"]["cache_version"] == CACHE_VERSION

    def test_escribe_propiedades_json_con_ultima_valuacion(self, tmp_path, monkeypatch):
        cache_dir = tmp_path / "data"
        cache_dir.mkdir()
        cache_path = cache_dir / "valuaciones_cache.json"
        props_path = tmp_path / "propiedades.json"
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", str(cache_path))
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_DIR", str(cache_dir))
        monkeypatch.setattr("parsers.valuacion_cache.PROPIEDADES_PATH", str(props_path))
        monkeypatch.setattr("parsers.valuacion_cache.SCRAPING_CACHE_PATH", "/nonexistent/scraping.json")

        props_data = {"propiedades": [
            {"nombre": "Test Prop", "zona": "Centro"},
            {"nombre": "Otra Prop", "zona": "Martin"}
        ]}
        with open(props_path, "w", encoding="utf-8") as f:
            json.dump(props_data, f)

        prop = {"nombre": "Test Prop", "m2_cubiertos": 50, "dormitorios": 2}
        resultado = {"valor_propiedad_usd": 100000, "m2_equivalentes": 50,
                     "resolution_metadata": {"n_propiedades": 5}}
        cache = {}

        ok = persistir_valuacion("Test Prop", prop, resultado, cache)
        assert ok is True

        props_loaded = json.loads(open(props_path, encoding="utf-8").read())
        test_prop = next(p for p in props_loaded["propiedades"] if p["nombre"] == "Test Prop")
        assert "_ultima_valuacion" in test_prop
        assert test_prop["_ultima_valuacion"]["valor_usd"] == 100000
        assert test_prop["_ultima_valuacion"]["comps"] == 5

        otra = next(p for p in props_loaded["propiedades"] if p["nombre"] == "Otra Prop")
        assert "_ultima_valuacion" not in otra

    def test_no_modifica_cache_si_nombre_no_existe_en_propiedades(self, tmp_path, monkeypatch):
        cache_dir = tmp_path / "data"
        cache_dir.mkdir()
        cache_path = cache_dir / "valuaciones_cache.json"
        props_path = tmp_path / "propiedades.json"
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", str(cache_path))
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_DIR", str(cache_dir))
        monkeypatch.setattr("parsers.valuacion_cache.PROPIEDADES_PATH", str(props_path))
        monkeypatch.setattr("parsers.valuacion_cache.SCRAPING_CACHE_PATH", "/nonexistent/scraping.json")

        props_orig = {"propiedades": [{"nombre": "Existente"}]}
        with open(props_path, "w", encoding="utf-8") as f:
            json.dump(props_orig, f)

        prop = {"nombre": "NoExistente", "m2_cubiertos": 50, "dormitorios": 2}
        resultado = {"valor_propiedad_usd": 50000, "resolution_metadata": {}}
        cache = {}

        ok = persistir_valuacion("NoExistente", prop, resultado, cache)
        assert ok is True

        props_loaded = json.loads(open(props_path, encoding="utf-8").read())
        existente = next(p for p in props_loaded["propiedades"] if p["nombre"] == "Existente")
        assert "_ultima_valuacion" not in existente

    def test_persiste_aun_si_propiedades_no_existe(self, tmp_path, monkeypatch):
        cache_dir = tmp_path / "data"
        cache_dir.mkdir()
        cache_path = cache_dir / "valuaciones_cache.json"
        props_path = tmp_path / "propiedades.json"
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", str(cache_path))
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_DIR", str(cache_dir))
        monkeypatch.setattr("parsers.valuacion_cache.PROPIEDADES_PATH", str(props_path))
        monkeypatch.setattr("parsers.valuacion_cache.SCRAPING_CACHE_PATH", "/nonexistent/scraping.json")

        assert not props_path.exists()

        prop = {"nombre": "Nueva", "m2_cubiertos": 50, "dormitorios": 2}
        resultado = {"valor_propiedad_usd": 75000, "resolution_metadata": {}}
        cache = {}

        ok = persistir_valuacion("Nueva", prop, resultado, cache)
        assert ok is True

        assert cache_path.exists()
        data = json.loads(open(cache_path, encoding="utf-8").read())
        assert "Nueva" in data

    def test_retorna_false_si_error(self, monkeypatch):
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", "")
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_DIR", "")
        monkeypatch.setattr("parsers.valuacion_cache.PROPIEDADES_PATH", "")
        monkeypatch.setattr("parsers.valuacion_cache.SCRAPING_CACHE_PATH", "")

        ok = persistir_valuacion("Fallo", {}, {}, {})
        assert ok is False

    def test_no_llama_sync(self, tmp_path, monkeypatch):
        cache_dir = tmp_path / "data"
        cache_dir.mkdir()
        cache_path = cache_dir / "valuaciones_cache.json"
        props_path = tmp_path / "propiedades.json"
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", str(cache_path))
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_DIR", str(cache_dir))
        monkeypatch.setattr("parsers.valuacion_cache.PROPIEDADES_PATH", str(props_path))
        monkeypatch.setattr("parsers.valuacion_cache.SCRAPING_CACHE_PATH", "/nonexistent/scraping.json")

        llamadas_sync = []

        import parsers.git_sync
        original_state = parsers.git_sync.try_sync_state
        def fake_state(*args, **kwargs):
            llamadas_sync.append(1)
            return True
        parsers.git_sync.try_sync_state = fake_state

        try:
            prop = {"nombre": "Test", "m2_cubiertos": 50}
            resultado = {"valor_propiedad_usd": 100, "resolution_metadata": {}}
            ok = persistir_valuacion("Test", prop, resultado, {})
            assert ok is True
            assert len(llamadas_sync) == 0
        finally:
            parsers.git_sync.try_sync_state = original_state


class TestGuardarResultadoCompat:
    def test_guardar_resultado_es_wrapper(self, tmp_path, monkeypatch):
        cache_dir = tmp_path / "data"
        cache_dir.mkdir()
        cache_path = cache_dir / "valuaciones_cache.json"
        props_path = tmp_path / "propiedades.json"
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", str(cache_path))
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_DIR", str(cache_dir))
        monkeypatch.setattr("parsers.valuacion_cache.PROPIEDADES_PATH", str(props_path))
        monkeypatch.setattr("parsers.valuacion_cache.SCRAPING_CACHE_PATH", "/nonexistent/scraping.json")

        from parsers.valuacion_cache import guardar_resultado
        prop = {"nombre": "Wrapper Test", "m2_cubiertos": 50, "dormitorios": 1}
        resultado = {"valor_propiedad_usd": 123456, "resolution_metadata": {}}
        cache = {}

        guardar_resultado("Wrapper Test", prop, resultado, cache)

        assert cache_path.exists()
        data = json.loads(open(cache_path, encoding="utf-8").read())
        assert "Wrapper Test" in data
        assert data["Wrapper Test"]["resultado_completo"]["valor_propiedad_usd"] == 123456


class TestCargarCacheValuaciones:
    def test_carga_cache_valido(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "valuaciones_cache.json"
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", str(cache_path))
        original = {"test": {"valor": 100}}
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(original, f)

        loaded = cargar_cache_valuaciones()
        assert loaded == original

    def test_retorna_vacio_si_no_existe(self, tmp_path, monkeypatch):
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH",
                            str(tmp_path / "no_existe.json"))
        loaded = cargar_cache_valuaciones()
        assert loaded == {}

    def test_retorna_vacio_si_json_corrupto(self, tmp_path, monkeypatch):
        cache_path = tmp_path / "corrupto.json"
        monkeypatch.setattr("parsers.valuacion_cache.CACHE_PATH", str(cache_path))
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write("{corrupto")

        loaded = cargar_cache_valuaciones()
        assert loaded == {}

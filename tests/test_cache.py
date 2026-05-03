import pytest
import os
import sys
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.motor_vpp_core import (
    obtener_dolar_binance_cached,
    load_cache_cached,
    cargar_anclas_cached,
    _BINANCE_CACHE,
    _CACHE_DATA,
    _ANCLAS_CACHE
)


class TestDolarCache:
    """Tests para el cache de dólar Binance."""
    
    def test_cache_hit_second_call(self):
        """Segunda llamada debe usar cache (sin request)."""
        _BINANCE_CACHE['value'] = 1500.0
        _BINANCE_CACHE['ts'] = time.time()
        
        with patch('requests.get') as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {'totalAsk': 1600})
            
            r = obtener_dolar_binance_cached()
            
            assert r == 1500.0
            assert mock_get.call_count == 0, "No debe hacer request en cache hit"
    
    def test_force_reload_makes_request(self):
        """force_reload=True debe hacer nueva request."""
        _BINANCE_CACHE['value'] = None
        _BINANCE_CACHE['ts'] = 0
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'totalAsk': 1600.0}
            mock_get.return_value = mock_response
            
            r = obtener_dolar_binance_cached(force_reload=True)
            
            assert r == 1600.0
            assert mock_get.call_count == 1, "Debe hacer request en force_reload"
    
    def test_env_test_bypasses(self):
        """APP_ENV=test debe bypassear el cache."""
        old_val = _BINANCE_CACHE['value']
        old_ts = _BINANCE_CACHE['ts']
        _BINANCE_CACHE['value'] = 1500.0
        _BINANCE_CACHE['ts'] = time.time()
        
        try:
            with patch.dict(os.environ, {'APP_ENV': 'test'}):
                with patch('requests.get') as mock_get:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {'totalAsk': 1700.0}
                    mock_get.return_value = mock_response
                    
                    r = obtener_dolar_binance_cached()
                    
                    assert r == 1700.0
        finally:
            _BINANCE_CACHE['value'] = old_val
            _BINANCE_CACHE['ts'] = old_ts
            os.environ.pop('APP_ENV', None)
    
    def test_disable_cache_bypasses(self):
        """DISABLE_CACHE=1 debe bypassear el cache."""
        old_val = _BINANCE_CACHE['value']
        old_ts = _BINANCE_CACHE['ts']
        _BINANCE_CACHE['value'] = 1500.0
        _BINANCE_CACHE['ts'] = time.time()
        
        try:
            with patch.dict(os.environ, {'DISABLE_CACHE': '1'}):
                with patch('requests.get') as mock_get:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {'totalAsk': 1800.0}
                    mock_get.return_value = mock_response
                    
                    r = obtener_dolar_binance_cached()
                    
                    assert r == 1800.0
        finally:
            _BINANCE_CACHE['value'] = old_val
            _BINANCE_CACHE['ts'] = old_ts
            os.environ.pop('DISABLE_CACHE', None)


class TestCacheReload:
    """Tests para force_reload."""
    
    def test_force_reload_cache(self):
        """force_reload debe ignorar TTL."""
        with patch('parsers.motor_vpp_core.load_cache') as mock_load:
            mock_load.return_value = {"propiedades": [1,2,3]}
            
            r = load_cache_cached(force_reload=True)
            
            assert r == {"propiedades": [1,2,3]}
            mock_load.assert_called_once()
    
    def test_force_reload_anclas(self):
        """force_reload debe ignorar TTL para anclas."""
        with patch('parsers.motor_vpp_core.cargar_anclas') as mock_load:
            mock_load.return_value = {"ancla1": {"lat": -32.9}}
            
            r = cargar_anclas_cached(force_reload=True)
            
            assert r == {"ancla1": {"lat": -32.9}}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
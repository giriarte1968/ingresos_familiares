"""
Pytest configuration and global fixtures.
Garantiza que la ejecución de tests jamás modifique propiedades.json ni data/valuaciones_cache.json en el workspace.
"""

import pytest
import os
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROPS_PATH = os.path.join(BASE_DIR, 'propiedades.json')
CACHE_PATH = os.path.join(BASE_DIR, 'data', 'valuaciones_cache.json')

@pytest.fixture(autouse=True, scope="session")
def isolate_database_files():
    """Backup y restauración automática de propiedades.json y valuaciones_cache.json para toda la sesión de pruebas."""
    props_bak = PROPS_PATH + ".pytest_bak"
    cache_bak = CACHE_PATH + ".pytest_bak"
    
    if os.path.exists(PROPS_PATH):
        shutil.copy2(PROPS_PATH, props_bak)
    if os.path.exists(CACHE_PATH):
        shutil.copy2(CACHE_PATH, cache_bak)
        
    yield
    
    # Restaurar estado original exacto post-pruebas
    if os.path.exists(props_bak):
        shutil.copy2(props_bak, PROPS_PATH)
        os.remove(props_bak)
    if os.path.exists(cache_bak):
        shutil.copy2(cache_bak, CACHE_PATH)
        os.remove(cache_bak)

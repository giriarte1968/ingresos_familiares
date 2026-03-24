import sys
import os
# Mock Streamlit to avoid issues running outside streamlit
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()

try:
    from app import categorizar_gasto, CASOS_ASEGURADOS
    
    print("--- PRUEBA REAL DESDE APP.PY ---")
    test_cases = ["La Gran Argentina", "Alberto Rey", "Rey Diego Alberto", "Estacionamiento Ocampo", "Plus Pagos", "Tu Quincho", "Movistar Rosario", "Municipalidad de Rosario"]
    
    for tc in test_cases:
        cat, subcat, name = categorizar_gasto(tc)
        print(f"Entrada: {tc:25} -> {cat}/{subcat} ({name})")
        
except Exception as e:
    print(f"Error cargando app: {e}")

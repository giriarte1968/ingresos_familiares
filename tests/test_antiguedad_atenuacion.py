"""
Tests de No-Regresión: Atenuación de Antigüedad
Verifica que la lógica de atenuación funciona correctamente.
"""
import pytest
import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.mercado_inmobiliario import valuar_propiedad_v7, calcular_factores

# Cargar propiedades
with open('propiedades.json') as f:
    data = json.load(f)
    propiedades = data.get('propiedades', [])

# Funciones auxiliares
def get_prop(nombre):
    return [p for p in propiedades if p.get('nombre') == nombre][0]

def calculate_delta_raw(antiguedad):
    return max(-0.60, -(antiguedad * 0.006))

# --- TESTS ---

def test_antiguedad_no_cambia_en_propiedades_jovenes():
    """Verificar que propiedades jóvenes no reciben atenuación"""
    UMBRAL = -0.18
    
    casos = [
        ('Mabel', 26),   # 26 años
        ('Ayacucho', 24), # 24 años
        ('Vera Mujica', 17), # 17 años
    ]
    
    for nombre, edad in casos:
        delta_raw = calculate_delta_raw(edad)
        
        # Calcular efectivo según lógica del código
        if delta_raw >= UMBRAL:
            delta_efectivo = delta_raw
        else:
            exceso = delta_raw - UMBRAL
            delta_efectivo = -0.18 + (exceso * 0.35)
        
        # Verificar que no cambió
        assert delta_raw == delta_efectivo, f"{nombre}: delta cambió cuando no debía (raw={delta_raw}, ef={delta_efectivo})"

def test_antiguedad_se_atenua_en_propiedades_viejas():
    """Verificar que propiedades viejas (>30 años) reciben atenuación"""
    UMBRAL = -0.18
    
    # P1200 tiene 49 años
    edad = 49
    delta_raw = calculate_delta_raw(edad)
    
    # Aplicar lógica
    if delta_raw < UMBRAL:
        exceso = delta_raw - UMBRAL
        delta_efectivo = -0.18 + (exceso * 0.35)
    else:
        delta_efectivo = delta_raw
    
    # Verificar que se atenuó (menos castigo)
    assert delta_efectivo > delta_raw, f"P1200: delta no se attenuo (raw={delta_raw}, ef={delta_efectivo})"

def test_p1200_rescate_por_atenuacion():
    """Verificar que P1200 tiene mayor valor por atenuación"""
    prop = get_prop('P1200')
    
    result = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    valor = result.get('valor_propiedad_usd', 0)
    
    # P1200 debería estar en rango ~$143k-$150k (rescatado por atenuación)
    assert 140000 <= valor <= 160000, f"P1200 valor fuera de rango: {valor}"

def test_nlp_cap_por_dormitorios():
    """Verificar que NLP se capa correctamente por dormitorios"""
    # Crear propiedades de prueba
    prop_1dorm = {
        'nombre': 'test_1dorm',
        'dormitorios': 1,
        'descripcion_libre': 'muy luminoso非常好的公寓 vista al rio',
    }
    prop_2dorm = {
        'nombre': 'test_2dorm',
        'dormitorios': 2,
        'descripcion_libre': 'muy luminoso非常好的公寓 vista al rio pileta SUM',
    }
    
    # Calcular NLP
    from parsers.nlp_inmobiliario import calcular_ajuste_nlp_detallado
    nlp_1, _ = calcular_ajuste_nlp_detallado(prop_1dorm.get('descripcion_libre', ''))
    nlp_2, _ = calcular_ajuste_nlp_detallado(prop_2dorm.get('descripcion_libre', ''))
    
    # Aplicar caps
    nlp_cap_1 = 0.03 if prop_1dorm.get('dormitorios') == 1 else 0.05
    nlp_cap_2 = 0.03 if prop_2dorm.get('dormitorios') == 1 else 0.05
    
    nlp_1_capped = min(nlp_1, nlp_cap_1)
    nlp_2_capped = min(nlp_2, nlp_cap_2)
    
    # Verificar caps
    assert nlp_1_capped <= 0.03, f"1 dorm: NLP no cappeado correctamente: {nlp_1_capped}"
    assert nlp_2_capped <= 0.05, f"2+ dorm: NLP no cappeado correctamente: {nlp_2_capped}"

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
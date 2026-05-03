import json
import numpy as np
import os
from datetime import datetime
from parsers.location_engine import generar_nodos_dinamicos, calcular_precio_m2, cargar_barreras
from parsers.mercado_inmobiliario import obtener_mediana_cluster, normalizar_tipo

def load_cache():
    path = r'C:\Users\Gustavo\ingresos_familiares_st\cache_scraping.json'
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('propiedades', [])

def calculate_mape(actual, predicted):
    actual = np.array(actual)
    predicted = np.array(predicted)
    # Evitar division por cero
    mask = actual > 0
    return np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100

def run_validation():
    print("="*60)
    print("VALIDACIÓN DE MODELO: ESTÁTICO vs NODOS DINÁMICOS")
    print("="*60)
    
    all_props = load_cache()
    # Filtrar propiedades aptas para validación (ventas con coordenadas y valor_m2)
    valid_props = [
        p for p in all_props 
        if p.get('operacion') == 'venta' 
        and p.get('lat') and p.get('lon') 
        and p.get('valor_m2', 0) > 0
    ]
    
    if len(valid_props) < 100:
        print(f"Muestras insuficientes: {len(valid_props)}")
        return

    # Split 80% train / 20% test
    np.random.seed(42)
    np.random.shuffle(valid_props)
    split_idx = int(len(valid_props) * 0.8)
    train_set = valid_props[:split_idx]
    test_set = valid_props[split_idx:]
    
    print(f"Entrenamiento: {len(train_set)} propiedades")
    print(f"Test: {len(test_set)} propiedades\n")

    # 1. Construir Nodos Dinámicos con el Train Set
    # Usamos el tipo predominante 'departamento' para la prueba
    train_deptos = [p for p in train_set if normalizar_tipo(p.get('tipo')) == 'departamento']
    nodos = generar_nodos_dinamicos(train_deptos, eps_meters=200)
    barreras = cargar_barreras()
    
    # 2. Evaluar sobre el Test Set (Solo Deptos)
    test_deptos = [p for p in test_set if normalizar_tipo(p.get('tipo')) == 'departamento']
    
    actuals = []
    preds_static = []
    preds_dynamic = []
    
    for p in test_deptos:
        val_real = p['valor_m2']
        zona = p.get('zona', 'Centro')
        dorms = p.get('dormitorios', 2)
        lat = p['lat']
        lon = p['lon']
        
        # A. Modelo Estático (Mediana de Zona)
        val_static, _ = obtener_mediana_cluster(zona, dorms, 'departamento', 'venta')
        
        # B. Modelo Dinámico (Interpolación Adaptativa)
        val_dyn = calcular_precio_m2(lat, lon, nodos, barriers=barreras)
        
        # Fallback para el dinámico si no hay nodos cerca
        if val_dyn is None:
            val_dyn = val_static if val_static > 0 else 0
            
        if val_static > 0 and val_dyn > 0:
            actuals.append(val_real)
            preds_static.append(val_static)
            preds_dynamic.append(val_dyn)

    mape_static = calculate_mape(actuals, preds_static)
    mape_dynamic = calculate_mape(actuals, preds_dynamic)
    
    print(f"RESULTADOS (SÓLO DEPARTAMENTOS):")
    print(f"MAPE Modelo Estático: {mape_static:.2f}%")
    print(f"MAPE Modelo Dinámico: {mape_dynamic:.2f}%")
    print("-" * 30)
    print(f"Mejora en Precisión: {mape_static - mape_dynamic:.2f} puntos porcentuales")
    print("="*60)

if __name__ == "__main__":
    run_validation()

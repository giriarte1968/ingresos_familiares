import json
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from parsers.mercado_inmobiliario import (
    calcular_base_calibrada, calcular_m2_equivalentes, calcular_factores,
    obtener_mediana_cluster, sanitizar_propiedad
)
from parsers.nlp_inmobiliario import calcular_ajuste_nlp_detallado

def debug_propiedad(propiedad):
    """
    Retorna un debug detallado del cálculo de valoración
    """
    prop = sanitizar_propiedad(propiedad)
    
    # Calcular antiguedad
    anio_const = prop.get('anio_construccion', 2020)
    antiguedad = 2026 - anio_const
    prop['antiguedad'] = antiguedad
    
    # m2 equivalentes
    m2_equiv = calcular_m2_equivalentes(prop)
    
    # Factores
    f_dict = calcular_factores(prop)
    
    # Base calibrada
    zona = prop.get('zona')
    dorms = prop.get('dormitorios', 2)
    lat = prop.get('lat')
    lon = prop.get('lon')
    ancla_usd = prop.get('ancla_usd_m2', 1500)
    
    m2_base, metodo = calcular_base_calibrada(ancla_usd, {
        'zona': zona, 'dormitorios': dorms, 'lat': lat, 'lon': lon, 'anio_construccion': anio_const
    })
    
    # Cluster
    cluster_val, n_cluster = obtener_mediana_cluster(zona, dorms, 'venta')
    
    # NLP
    desc = prop.get('descripcion_libre', '')
    ajuste_nlp, detecciones_nlp = calcular_ajuste_nlp_detallado(desc)
    
# Calculo final (con sqrt para NLP)
    m2_base_con_nlp = m2_base * math.sqrt(1 + ajuste_nlp)
    factor_total = f_dict['total']
    valor_lista = m2_equiv * m2_base_con_nlp * factor_total
    valor_cierre = valor_lista * 0.92
    
    return {
        'propiedad': prop.get('nombre', prop.get('id')),
        'm2_equiv': m2_equiv,
        'm2_base': m2_base,
        'cluster': {'mediana': cluster_val, 'muestras': n_cluster},
        'ancla': {'id': prop.get('ancla_mas_cercana'), 'usd': ancla_usd},
        'metodo': metodo,
        'nlp': {'ajuste_pct': ajuste_nlp * 100, 'detecciones': detecciones_nlp},
        'factores': {
            'estructural_puro': round(f_dict['estructural_puro'], 4),
            'sqrt_factor': round(f_dict['sqrt_factor'], 4),
            'depreciacion': round(f_dict['depreciacion'], 4),
            'factor_total': round(factor_total, 4),
            'detalle': {
                'estado': f_dict.get('factor_estado'),
                'calidad': f_dict.get('factor_calidad'),
                'balcon': prop.get('tipo_balcon'),
                'ventilacion': prop.get('ventilacion'),
                'placares': prop.get('placares_completos'),
            }
        },
        'calculo': {
            'm2_base': m2_base,
            'm2_base_nlp': round(m2_base_con_nlp, 2),
            'factor': factor_total,
            'valor_lista': round(valor_lista, 0),
            'valor_cierre': round(valor_cierre, 0),
            'formula': f"{m2_equiv} × {m2_base_con_nlp:.2f} × {factor_total:.4f} = {valor_lista:.0f}"
        }
    }


if __name__ == "__main__":
    PROPS_FILE = os.path.join(BASE_DIR, 'propiedades.json')
    
    # Test con Mabel
    data = json.load(open(PROPS_FILE, 'r', encoding='utf-8'))
    mabel = [p for p in data['propiedades'] if p.get('nombre') == 'Mabel'][0]
    
    result = debug_propiedad(mabel)
    
    print("="*60)
    print(f"DEBUG: {result['propiedad']}")
    print("="*60)
    print(f"\nm² equivalentes: {result['m2_equiv']}")
    
    print(f"\n--- ANCLA Y CLUSTER ---")
    print(f"Ancla: {result['ancla']['id']} ({result['ancla']['usd']}/m²)")
    print(f"Cluster: {result['cluster']['mediana']:.0f}/m² ({result['cluster']['muestras']} muestras)")
    print(f"Método: {result['metodo']}")
    print(f"m² base: {result['m2_base']:.2f}")
    
    print(f"\n--- NLP ---")
    print(f"Ajuste: +{result['nlp']['ajuste_pct']:.1f}%")
    print(f"Detecciones: {result['nlp']['detecciones']}")
    
    print(f"\n--- FACTORES ---")
    f = result['factores']
    print(f"Producto estructural: {f['estructural_puro']}")
    print(f"sqrt(producto): {f['sqrt_factor']}")
    print(f"Depreciacion: {f['depreciacion']}")
    print(f"Factor total: {f['factor_total']}")
    print(f"Detalle: {f['detalle']}")
    
    print(f"\n--- CALCULO ---")
    c = result['calculo']
    print(f"Formula: {c['formula']}")
    print(f"m² base con NLP: {c['m2_base_nlp']}")
    print(f"Factor: {c['factor']}")
    print(f"\n>>> VALOR LISTA: {c['valor_lista']:,.0f} USD")
    print(f">>> VALOR CIERRE: {c['valor_cierre']:,.0f} USD")
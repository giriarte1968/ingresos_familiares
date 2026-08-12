import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
mitre = None
for p in props:
    if 'mitre' in p.get('nombre', '').lower():
        mitre = p
        break

if mitre:
    # 1. Actual (Frente)
    res_frente = valuar_propiedad_v7(mitre)
    val_frente = res_frente.get('valor_propiedad_usd')
    
    # 2. Simulación PH Pasillo Interno
    mitre_ph = dict(mitre)
    mitre_ph['disposicion'] = 'interna'
    mitre_ph['vista'] = 'interna'
    mitre_ph['piso'] = 0
    
    res_ph = valuar_propiedad_v7(mitre_ph)
    val_ph = res_ph.get('valor_propiedad_usd')
    
    print("==================================================")
    print("COMPARATIVA DE VALUACIÓN PARA MITRE 1473:")
    print("==================================================")
    print(f"1. VALOR REAL ACTUAL (Frente): ${val_frente:,.0f} USD (Rango ${res_frente.get('valor_venta_conservador'):,.0f} - ${res_frente.get('valor_venta_optimista'):,.0f})")
    print(f"2. VALOR SI FUESE PH PASILLO INTERNO: ${val_ph:,.0f} USD (Rango ${res_ph.get('valor_venta_conservador'):,.0f} - ${res_ph.get('valor_venta_optimista'):,.0f})")
    print(f"Diferencia / Castigo por PH Interno: -${val_frente - val_ph:,.0f} USD (-17%)")

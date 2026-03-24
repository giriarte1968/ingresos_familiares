import re
import numpy as np

# Mocking the blocks that we got from previous PaddleOCR run on 'recibo_santa_fe_servicios_2.jpeg'
blocks = [
    {'cy': 29.5, 'cx': 258.5, 'text': 'SANTA FE SERVICIOS', 'h': 20},
    {'cy': 337.5, 'cx': 92.5, 'text': 'MOVISTAR', 'h': 20},
    {'cy': 358.5, 'cx': 93.5, 'text': 'IMPORTE:', 'h': 20},
    {'cy': 355.5, 'cx': 411.5, 'text': '66154.05', 'h': 20},
    {'cy': 437.5, 'cx': 68.5, 'text': 'ADT', 'h': 20},
    {'cy': 458.0, 'cx': 93.0, 'text': 'IMPORTE:', 'h': 20},
    {'cy': 455.5, 'cx': 411.8, 'text': '70815.64', 'h': 20},
    {'cy': 536.5, 'cx': 174.0, 'text': 'MUNICIPALIDAD DE ROSARIO', 'h': 20},
    {'cy': 557.5, 'cx': 90.5, 'text': 'IMPORTE:', 'h': 20},
    {'cy': 555.5, 'cx': 412.5, 'text': '74794.09', 'h': 20},
    {'cy': 636.8, 'cx': 240.5, 'text': 'AGUAS SANTAFESINAS SA SIN COMPROBANTE', 'h': 20},
    {'cy': 660.0, 'cx': 90.5, 'text': 'EMPORTE:', 'h': 20}, 
    {'cy': 654.5, 'cx': 414.0, 'text': '$50453.47', 'h': 20},
    {'cy': 744.0, 'cx': 62.0, 'text': 'EPE', 'h': 20},
    {'cy': 764.8, 'cx': 88.0, 'text': 'IMPORTE:', 'h': 20},
    {'cy': 758.5, 'cx': 410.5, 'text': '122311.23', 'h': 20},
    {'cy': 852.0, 'cx': 84.5, 'text': 'PERSONAL', 'h': 20},
    {'cy': 875.5, 'cx': 86.5, 'text': 'IMPORTE:', 'h': 20},
    {'cy': 865.5, 'cx': 418.5, 'text': '35102.70', 'h': 20},
    {'cy': 961.2, 'cx': 138.2, 'text': 'CARGO POR SERVICIO', 'h': 20},
    {'cy': 971.5, 'cx': 451.5, 'text': '$60', 'h': 20},
    {'cy': 987.5, 'cx': 83.0, 'text': 'IMPORTE:', 'h': 20},
    {'cy': 1003.5, 'cx': 186.0, 'text': 'NRO.TRANSACCI0N426540067', 'h': 20},
]

def logic_test(blocks):
    sub_pagos = []
    importes_detectados = []
    for b in blocks:
        t_clean = b['text'].upper().replace(' ', '').replace(':', '')
        # Fuzzy keyword matching
        if any(kw in t_clean for kw in ["IMPORTE", "EMPORTE", "IMPORT", "MPORT"]) and "TOTAL" not in t_clean:
            importes_detectados.append(b)
            
    for imp in importes_detectados:
        cy_imp = imp['cy']
        h_imp = imp['h']
        cx_imp = imp['cx']
        
        # 1. Buscar el nombre del servicio (arriba)
        candidatos_servicio = []
        for b in blocks:
            if b == imp: continue
            # Buscar en un rango generoso arriba (hasta 4 lineas)
            if (cy_imp - 4.2 * h_imp) < b['cy'] < (cy_imp - 0.2 * h_imp):
                # Tolerance lateral alta (400) para nombres largos como Aguas
                if b['cx'] < cx_imp + 400:
                    candidatos_servicio.append(b)
        
        servicio = "Desconocido"
        if candidatos_servicio:
            # Ordenar por cercania vertical
            candidatos_servicio.sort(key=lambda x: x['cy'], reverse=True)
            for cand in candidatos_servicio:
                txt = cand['text'].upper().strip()
                # Evitar tomar otro IMPORTE o NRO TRANSACCION como nombre de servicio
                if "RANSACC" not in txt and "MPORT" not in txt and len(txt) > 2:
                    servicio = cand['text']
                    break

        # 2. Buscar el monto (FLEXIBLE)
        candidatos_monto = []
        for b in blocks:
            if b == imp: continue
            if abs(b['cy'] - cy_imp) < h_imp * 3.0: # mas tolerancia vertical
                if b['cx'] > cx_imp - 50: # a la derecha o apenas a la izquierda
                    candidatos_monto.append(b)
        
        monto_val = 0.0
        if candidatos_monto:
            detalles = []
            for c in candidatos_monto:
                t = c['text'].replace(" ", "").replace(",", ".")
                t = re.sub(r'[^\d.]', '', t)
                if not t: continue
                
                # Regla de exclusion de transaccion: 9 digitos empezando con 4
                if len(t) >= 9 and t.startswith("4"):
                    continue
                
                # Priority scoring
                score = 0
                if "." in t: score += 10 # Decimales es muy bueno
                if len(t) <= 6: score += 5  # Los montos suelen ser razonables
                
                try:
                    detalles.append((float(t), score, c))
                except: pass
            
            if detalles:
                detalles.sort(key=lambda x: x[1], reverse=True)
                monto_val = detalles[0][0]
                
        sub_pagos.append({'desc': servicio, 'monto': monto_val})
        
    return sub_pagos

res = logic_test(blocks)
total_acc = 0
for r in res:
    print(f"{r['desc']} -> {r['monto']}")
    total_acc += r['monto']
print(f"TOTAL: {total_acc}")

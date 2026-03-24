import re

app_file = "app.py"
with open(app_file, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

nueva_ocr = r'''def extraer_subpagos_desde_comprobante(reader, comprobante) -> list[dict]:
    """
    Usa OCR con ALINEACION ESPACIAL 2D (coordenadas X, Y).
    Ideal para tickets de Santa Fe Servicios donde el importe está muy a la derecha
    del rótulo "IMPORTE:".
    """
    import re
    
    try:
        if hasattr(comprobante, 'read'):
            comprobante.seek(0)
            results = reader.readtext(comprobante.read())
        else:
            results = reader.readtext(comprobante)
        
        texto_raw = ""
        blocks = []
        for (bbox, text, prob) in results:
            t = text.strip()
            if t:
                # bbox is a list of 4 points: [[tl_x, tl_y], [tr_x, tr_y], [br_x, br_y], [bl_x, bl_y]]
                ys = [pt[1] for pt in bbox]
                xs = [pt[0] for pt in bbox]
                cy = sum(ys) / 4.0
                cx = sum(xs) / 4.0
                h = max(ys) - min(ys)
                
                blocks.append({
                    'text': t,
                    'cx': cx, 'cy': cy, 'h': h,
                    'orig_bbox': bbox
                })
                texto_raw += t + "\n"
        
        # Algoritmo de apareo espacial:
        # Buscamos bloques que digan "IMPORTE", "IMPORTE:"
        sub_pagos = []
        importes_detectados = []
        
        for i, b in enumerate(blocks):
            txt_upper = b['text'].upper().replace(' ', '')
            
            if "IMPORTE" in txt_upper and "TOTAL" not in txt_upper:
                importes_detectados.append(b)
        
        # Para cada "IMPORTE", buscar el nombre del servicio ALINEADO ARRIBA
        # Ligeramente más arriba, preferiblemente hacia la izquierda
        for imp in importes_detectados:
            cy_imp = imp['cy']
            h_imp = imp['h']
            
            # 1. Buscar el nombre del servicio (block arriba de IMPORTE)
            # Busco el bloque cuyo cy está entre cy_imp - 3.5*h y cy_imp - 0.5*h
            # y que esté alineado en la columna izquierda (cx cercano al del importe)
            candidatos_servicio = []
            for b_other in blocks:
                if b_other == imp: continue
                # Si está por encima de IMPORTE pero no muucho (es la linea anterior o 2 lineas)
                if cy_imp - (3.5 * h_imp) < b_other['cy'] < cy_imp - (0.5 * h_imp):
                    # Y no debe estar muy a la derecha
                    if b_other['cx'] < imp['cx'] + 100:
                        candidatos_servicio.append(b_other)
            
            servicio_nombre = "Servicio Desconocido"
            if candidatos_servicio:
                # Ordenar por cercanía (cy descendente, o sea el más cercano por encima)
                candidatos_servicio.sort(key=lambda x: x['cy'], reverse=True)
                servicio_nombre = candidatos_servicio[0]['text']
                # a veces hay basura como NRO TRANSACCION anterior
                if "RANSACC" in servicio_nombre.upper() or len(servicio_nombre) <= 3:
                    if len(candidatos_servicio) > 1:
                        servicio_nombre = candidatos_servicio[1]['text']
            
            # limpieza basica de servicio
            if "ADI" == servicio_nombre.strip() or "AD I" == servicio_nombre.strip():
                 servicio_nombre = "ADT"
            
            # 2. Buscar el MONTO alineado a la DERECHA
            # Busco bloques cuyo cy sea muy similar al cy de "IMPORTE" (+- 1.0 * h_imp)
            # y cuyo cx sea MAYOR al de "IMPORTE" (está a la derecha)
            candidatos_monto = []
            for b_other in blocks:
                if b_other == imp: continue
                
                # Tolerancia vertical: la misma fila
                if abs(b_other['cy'] - cy_imp) < h_imp * 1.5:
                    if b_other['cx'] > imp['cx']:
                        candidatos_monto.append(b_other)
            
            monto_val = 0.0
            if candidatos_monto:
                # Tomamos los textos de la derecha, podrian ser varios pedazos ("$", "66154.05")
                candidatos_monto.sort(key=lambda x: x['cx'])
                # Unir todos para formar el string
                txt_derecha = " ".join([m['text'] for m in candidatos_monto])
                
                # Limpiar texto para extraer float
                climpio = txt_derecha.replace(" ", "").replace(",", ".")
                # quitar simbolos raros
                climpio = re.sub(r'[^\d.]', '', climpio)
                
                # Buscar un numero con decimales
                match = re.search(r'(\d+[.]\d+)', climpio)
                if match:
                    val_str = match.group(1)
                    try:
                        monto_val = float(val_str)
                    except ValueError:
                        pass
                else:
                    # si no hay decimales, quizas le falte el punto pero leemos lo q hay
                    try:
                        # ignorar transacciones 42xxx.. de 9 chars
                        if not (len(climpio) >= 9 and climpio.startswith('42')):
                            if climpio:
                                monto_val = float(climpio)
                    except ValueError:
                        pass
                        
            # Agregar el subpago, aunque sea 0 (permitira correccion manual)
            if "TOTAL" not in servicio_nombre.upper() and "ID " not in servicio_nombre.upper():
                sub_pagos.append({
                    'monto': monto_val,
                    'descripcion': servicio_nombre,
                    'fecha': '',
                    'medio_pago': ''
                })
        
        return sub_pagos, texto_raw
    except Exception as e:
        print(f"Error OCR Spatial: {e}")
        return [], str(e)'''

content = re.sub(
    r'(def extraer_subpagos_desde_comprobante\(.*?\):.*?)(?=\ndef |\n# |\Z)', 
    lambda m: nueva_ocr + '\n', 
    content, 
    flags=re.DOTALL
)

with open(app_file, "w", encoding="utf-8", errors="replace") as f:
    f.write(content)

print("Script OCR espacial (2D) inyectado.")

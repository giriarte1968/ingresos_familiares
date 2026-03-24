import re

app_file = "app.py"
with open(app_file, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# 1. Agregar inicializador aislado de PaddleOCR
paddle_init = """
_paddle_reader = None

def get_paddle_reader():
    global _paddle_reader
    if _paddle_reader is None:
        from paddleocr import PaddleOCR
        import logging
        logging.getLogger('ppocr').setLevel(logging.ERROR)
        _paddle_reader = PaddleOCR(use_textline_orientation=True, lang='es')
    return _paddle_reader
"""

# Insertarlo cerca de get_ocr_reader
if "def get_paddle_reader():" not in content:
    content = content.replace("def get_ocr_reader():", paddle_init + "\n\n" + "def get_ocr_reader():")


# 2. Modificar extraer_subpagos_desde_comprobante para el formato de salida PaddleOCR
nueva_ocr = r'''def extraer_subpagos_desde_comprobante(reader, comprobante) -> list[dict]:
    """
    Usa PaddleOCR (motor neuronal avanzado) con ALINEACION ESPACIAL 2D (coordenadas X, Y).
    """
    import re
    
    try:
        if hasattr(comprobante, 'read'):
            comprobante.seek(0)
            img_data = comprobante.read()
        else:
            with open(comprobante, "rb") as f:
                img_data = f.read()
                
        # PaddleOCR usa .ocr() en lugar de .readtext()
        results_raw = reader.ocr(img_data, cls=True)
        
        texto_raw = ""
        blocks = []
        
        if results_raw and results_raw[0]:
            for line in results_raw[0]:
                if not line: continue
                bbox = line[0]
                t = line[1][0].strip()
                prob = line[1][1]
                
                if t:
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
        sub_pagos = []
        importes_detectados = []
        
        for i, b in enumerate(blocks):
            txt_upper = b['text'].upper().replace(' ', '')
            if "IMPORTE" in txt_upper and "TOTAL" not in txt_upper:
                importes_detectados.append(b)
        
        for imp in importes_detectados:
            cy_imp = imp['cy']
            h_imp = imp['h']
            
            candidatos_servicio = []
            for b_other in blocks:
                if b_other == imp: continue
                # Buscar arriba:
                if cy_imp - (3.5 * h_imp) < b_other['cy'] < cy_imp - (0.5 * h_imp):
                    if b_other['cx'] < imp['cx'] + 100:
                        candidatos_servicio.append(b_other)
            
            servicio_nombre = "Servicio Desconocido"
            if candidatos_servicio:
                candidatos_servicio.sort(key=lambda x: x['cy'], reverse=True)
                servicio_nombre = candidatos_servicio[0]['text']
                if "RANSACC" in servicio_nombre.upper() or len(servicio_nombre) <= 3:
                    if len(candidatos_servicio) > 1:
                        servicio_nombre = candidatos_servicio[1]['text']
            
            if "ADI" == servicio_nombre.strip() or "AD I" == servicio_nombre.strip():
                 servicio_nombre = "ADT"
            
            candidatos_monto = []
            for b_other in blocks:
                if b_other == imp: continue
                # Buscar a la derecha en la misma fila:
                if abs(b_other['cy'] - cy_imp) < h_imp * 2.0:
                    if b_other['cx'] > imp['cx']:
                        candidatos_monto.append(b_other)
            
            monto_val = 0.0
            if candidatos_monto:
                candidatos_monto.sort(key=lambda x: x['cx'])
                txt_derecha = " ".join([m['text'] for m in candidatos_monto])
                climpio = txt_derecha.replace(" ", "").replace(",", ".")
                climpio = re.sub(r'[^\d.]', '', climpio)
                
                match = re.search(r'(\d+[.]\d+)', climpio)
                if match:
                    val_str = match.group(1)
                    try:
                        monto_val = float(val_str)
                    except ValueError:
                        pass
                else:
                    try:
                        if not (len(climpio) >= 9 and climpio.startswith('42')):
                            if climpio:
                                monto_val = float(climpio)
                    except ValueError:
                        pass
                        
            if "TOTAL" not in servicio_nombre.upper() and "ID " not in servicio_nombre.upper():
                sub_pagos.append({
                    'monto': monto_val,
                    'descripcion': servicio_nombre,
                    'fecha': '',
                    'medio_pago': ''
                })
        
        return sub_pagos, texto_raw
    except Exception as e:
        print(f"Error PaddleOCR Spatial: {e}")
        return [], str(e)'''

# Sustituir la función existente
content = re.sub(
    r'(def extraer_subpagos_desde_comprobante\(.*?\):.*?)(?=\ndef |\n# |\Z)', 
    lambda m: nueva_ocr + '\n', 
    content, 
    flags=re.DOTALL
)

# 3. Cambiar en la UI el botón que llama a esto para inyectarle el lector de Paddle
viejo_llamado = """                            reader = get_ocr_reader()
                            import copy, io
                            # Leer bytes directo para no perderlos en reruns
                            bytes_file = ticket_file.read()"""
nuevo_llamado = """                            reader = get_paddle_reader()
                            import copy, io
                            # Leer bytes directo para no perderlos en reruns
                            bytes_file = ticket_file.read()"""

content = content.replace(viejo_llamado, nuevo_llamado)


with open(app_file, "w", encoding="utf-8", errors="replace") as f:
    f.write(content)

print("Ajuste aislado exitoso: app.py usa PaddleOCR SÓLO para tickets detallados.")

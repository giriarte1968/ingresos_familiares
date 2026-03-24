import re

app_file = "app.py"
with open(app_file, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# La nueva función extraer_subpagos_desde_comprobante que captura servicios con mnt=0
nueva_ocr = r'''def extraer_subpagos_desde_comprobante(reader, comprobante) -> list[dict]:
    """
    Usa OCR buscando la palabra IMPORTE o servicios conocidos.
    Es tolerante a ruidos y si no detecta monto, añade el servicio con monto 0 para edicion manual.
    """
    import re
    
    try:
        if hasattr(comprobante, 'read'):
            comprobante.seek(0)
            results = reader.readtext(comprobante.read())
        else:
            results = reader.readtext(comprobante)
        
        texto_raw = ""
        lineas = []
        for (bbox, text, prob) in results:
            t = text.strip()
            if t:
                lineas.append(t)
                texto_raw += t + "\n"
        
        sub_pagos = []
        palabras_clave = ['IMPORTE', 'TOTAL', 'SUBTOTAL', 'NETO', 'BRUTO']
        
        i = 0
        while i < len(lineas):
            linea_upper = lineas[i].upper()
            
            if any(pc in linea_upper for pc in palabras_clave):
                # Nombre del servicio arriba
                servicio_nombre = lineas[i-1] if i >= 1 else "Servicio Desconocido"
                if len(servicio_nombre) <= 4 and i >= 2:  # basura muy corta
                    servicio_nombre = lineas[i-2]
                if "aisaccion" in servicio_nombre.lower() and i >= 3: # ruido de 'nro transaccion'
                    servicio_nombre = lineas[i-3]
                if "ADI" == servicio_nombre.strip():
                    servicio_nombre = "ADT" # correccion comun de OCR
                
                monto_encontrado = 0.0 # Por defecto 0 si no se lee bien
                
                # Buscamos en las siguientes 6 lineas
                for j in range(i, min(i + 7, len(lineas))):
                    candidato = lineas[j].replace(" ", "")
                    candidato_limpio = re.sub(r'^[^\d]+', '', candidato)
                    candidato_limpio = re.sub(r'[^\d]+$', '', candidato_limpio)
                    candidato_limpio = candidato_limpio.replace(",", ".")
                    
                    if not candidato_limpio:
                        continue
                        
                    if len(candidato_limpio) >= 8 and candidato_limpio.startswith('4'):
                        # Numeros de transaccion empiezan con 42..
                        continue
                        
                    try:
                        val = float(candidato_limpio)
                        if val >= 10 and val != 2026 and val != 2025:
                            monto_encontrado = val
                            break
                    except ValueError:
                        pass
                
                # Agregar siempre, aunque el monto sea 0.0 (para edicion manual).
                # Solo no agregar si la descripcion es una basura obvia
                desc_upper = servicio_nombre.upper()
                if "ID :" not in desc_upper and "NRO" not in desc_upper:
                    sub_pagos.append({
                        'monto': monto_encontrado,
                        'descripcion': servicio_nombre,
                        'fecha': '',
                        'medio_pago': ''
                    })
                
                # Avanzar el iterador. Si encontramos monto, saltamos hasta j.
                # Si no encontramos, solo avanzamos 1
                if monto_encontrado > 0:
                    i = j
            i += 1
            
        return sub_pagos, texto_raw
    except Exception as e:
        print(f"Error OCR: {e}")
        return [], str(e)'''

# Sustituir extraer_subpagos_desde_comprobante
content = re.sub(
    r'(def extraer_subpagos_desde_comprobante\(.*?\):.*?)(?=\ndef |\n# |\Z)', 
    lambda m: nueva_ocr + '\n', 
    content, 
    flags=re.DOTALL
)

with open(app_file, "w", encoding="utf-8", errors="replace") as f:
    f.write(content)

print("Script OCR refinado con celdas en blanco (monto 0) actualizado.")

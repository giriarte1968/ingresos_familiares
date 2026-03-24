import re

app_file = "app.py"
with open(app_file, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# La nueva función extraer_subpagos_desde_comprobante mejorada
nueva_ocr = r'''def extraer_subpagos_desde_comprobante(reader, comprobante) -> list[dict]:
    """
    Usa OCR buscando la palabra IMPORTE o servicios conocidos.
    Es tolerante a ruidos (e.g. '8 66154.05' o '50453.4/' o montos enteros '70').
    Ignora deliberadamente los IDs de transaccion (9 digitos empazando con 42).
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
                
                monto_encontrado = None
                
                # Buscamos en las siguientes 6 lineas
                for j in range(i, min(i + 7, len(lineas))):
                    candidato = lineas[j].replace(" ", "")
                    # Limpiar ruido: quitar signos extranos antes y despues del numero
                    candidato_limpio = re.sub(r'^[^\d]+', '', candidato)
                    candidato_limpio = re.sub(r'[^\d]+$', '', candidato_limpio)
                    candidato_limpio = candidato_limpio.replace(",", ".")
                    
                    if not candidato_limpio:
                        continue
                        
                    # Filtrar numeros de transaccion de PlusPagos/StaFe Serv (comienzan con 42 y son largos)
                    if len(candidato_limpio) >= 8 and candidato_limpio.startswith('42'):
                        continue
                        
                    try:
                        val = float(candidato_limpio)
                        # Evitar años (2026), dias del mes aislados o numeros de items menores a 10
                        if val >= 10 and val != 2026 and val != 2025:
                            monto_encontrado = val
                            break
                    except ValueError:
                        pass
                
                if monto_encontrado:
                    sub_pagos.append({
                        'monto': monto_encontrado,
                        'descripcion': servicio_nombre,
                        'fecha': '',
                        'medio_pago': ''
                    })
                    # Avanzar el iterador para no agarrar subpagos dobles
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

print("Script OCR refinado actualizado.")

import re
import os
import json

app_file = "app.py"
with open(app_file, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# 1. Agregar funciones cargar_subpagos y guardar_subpagos despues de las de datos
funcs_subpagos = """
def cargar_subpagos():
    if os.path.exists("subpagos.json"):
        try:
            with open("subpagos.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def guardar_subpagos(subpagos_datos):
    with open("subpagos.json", "w", encoding="utf-8") as f:
        json.dump(subpagos_datos, f, indent=4, ensure_ascii=False)
"""

# Insertar debajo de guardar_datos
guardar_datos_end = re.search(r'def guardar_datos\(.*?\n(?=\n?def |\n?class |\n?[A-Z])', content, re.DOTALL)
if guardar_datos_end:
    pos = guardar_datos_end.end()
    content = content[:pos] + "\n" + funcs_subpagos + content[pos:]
else:
    # try looking for first def
    content = funcs_subpagos + "\n" + content

# 2. Reemplazar extraer_subpagos_desde_comprobante
nueva_ocr = '''def extraer_subpagos_desde_comprobante(reader, comprobante) -> list[dict]:
    """
    Usa OCR buscando la palabra IMPORTE o servicios conocidos.
    Es tolerante a ruidos (e.g. '8 66154.05' o '50453.4/').
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
                texto_raw += t + "\\n"
        
        sub_pagos = []
        
        # Patron para buscar numeros con decimales. Permite basura como S, 8, 9, $ adelante y / atras.
        # Extrae solo la parte de digitos con punto o coma
        monto_pattern = re.compile(r'(\d{2,5}[.,]\d{2})')
        palabras_clave = ['IMPORTE', 'TOTAL', 'SUBTOTAL', 'NETO', 'BRUTO']
        
        # Recorremos buscando palabras clave
        i = 0
        while i < len(lineas):
            linea_upper = lineas[i].upper()
            
            if any(pc in linea_upper for pc in palabras_clave):
                # Encontramos un ticket de item. El nombre del servicio suele estar 1 o 2 lineas arriba.
                servicio_nombre = "Servicio Desconocido"
                if i >= 1:
                    servicio_nombre = lineas[i-1].strip()
                    # Si la linea anterior es muy corta o basura, buscar una más arriba
                    if len(servicio_nombre) <= 3 and i >= 2:
                        servicio_nombre = lineas[i-2].strip()
                
                # Ahora buscar el monto en esta misma linea o en las 3 siguientes
                monto_encontrado = None
                for j in range(i, min(i + 4, len(lineas))):
                    candidato = lineas[j].replace(" ", "")
                    # Limpiar comas a puntos para floats
                    candidato = candidato.replace(",", ".")
                    
                    match = monto_pattern.search(candidato)
                    if match:
                        try:
                            val = float(match.group(1))
                            if val > 100:  # Ignorar centavos sueltos si hay error
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
                    # Avanzar el indice para no doble-contar
                    i = j
            i += 1
            
        return sub_pagos, texto_raw
    except Exception as e:
        print(f"Error OCR: {e}")
        return [], str(e)'''

# Sustituir extraer_subpagos_desde_comprobante
content = re.sub(
    r'(def extraer_subpagos_desde_comprobante\(.*?\):.*?)(?=\ndef |\n# |\Z)', 
    nueva_ocr + '\n', 
    content, 
    flags=re.DOTALL
)

# 3. Cambiar confirmar division para guardar en subpagos.json
# Bloque existente a reemplazar:
viejo_confirmar = '''                        pago_original["status"] = "split"
                        pago_original["monto_original_antes_de_split"] = pago_original.get("monto", 0)
                        pago_original["monto"] = 0
                        pago_original["sub_pagos"] = copy.deepcopy(sub_pagos_actuales)
                        
                        # Crear los hijos directamente en 'egresos' (pasa por referencia, así que muta 'datos')
                        nuevos_hijos = []
                        for sp_hijo in sub_pagos_actuales:
                            desc = sp_hijo.get("descripcion", "").strip()
                            m = sp_hijo.get("monto", 0)
                            if desc and m > 0:
                                cat, subcat, _, tipo = categorizar_gasto(desc, datos)
                                nuevos_hijos.append({
                                    "u_id": generar_id(),
                                    "parent_id": pago_original["u_id"],
                                    "fecha": pago_original.get("fecha", ""),
                                    "gasto": desc,
                                    "monto": m,
                                    "moneda": pago_original.get("moneda", "ARS"),
                                    "fuente": "Santa Fe Servicios",
                                    "tipo": tipo,
                                    "categoria": cat,
                                    "subcategoria": subcat
                                })
                        
                        egresos.extend(nuevos_hijos)
                        guardar_datos(datos)'''

nuevo_confirmar = '''                        pago_original["status"] = "split"
                        pago_original["monto_original_antes_de_split"] = pago_original.get("monto", 0)
                        pago_original["monto"] = 0
                        
                        # Guardar los sub-pagos en subpagos.json (NO en datos.json)
                        subpagos_db = cargar_subpagos()
                        if mes_seleccionado not in subpagos_db:
                            subpagos_db[mes_seleccionado] = []
                            
                        nuevos_hijos = []
                        for sp_hijo in sub_pagos_actuales:
                            desc = sp_hijo.get("descripcion", "").strip()
                            m = sp_hijo.get("monto", 0)
                            if desc and m > 0:
                                cat, subcat, _, tipo = categorizar_gasto(desc, datos)
                                nuevos_hijos.append({
                                    "u_id": generar_id(),
                                    "parent_id": pago_original["u_id"],
                                    "fecha": pago_original.get("fecha", ""),
                                    "gasto": desc,
                                    "monto": m,
                                    "moneda": pago_original.get("moneda", "ARS"),
                                    "fuente": "Santa Fe Servicios",
                                    "tipo": tipo,
                                    "categoria": cat,
                                    "subcategoria": subcat
                                })
                        
                        subpagos_db[mes_seleccionado].extend(nuevos_hijos)
                        guardar_subpagos(subpagos_db)
                        
                        # Guardar datos maestro para persistir status=split
                        guardar_datos(datos)'''

content = content.replace(viejo_confirmar, nuevo_confirmar)

with open(app_file, "w", encoding="utf-8", errors="replace") as f:
    f.write(content)

print("Script ejecutado: app.py actualizado con OCR robusto y subpagos.json")

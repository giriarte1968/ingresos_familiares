import re

with open("app.py", "r", encoding="utf-8", errors="replace") as f:
    content = f.read()

# Buscamos el bloque de Procesar Egresos que tiene if st.button("Procesar Egresos"):
# Se extiende hasta "else:\n                        st.warning("No se detectaron gastos en el archivo")"
# Queremos cambiar la estructura anidada st.button("Procesar") -> st.button("Guardar") 
# por una anidada basada en session_state.

# Buscamos el inicio
start_idx = content.find('if st.button("Procesar Egresos"):')

# Buscamos donde inyectar la tabla de egresos permanentes
# Para hacerlo seguro, lo más fácil es usar expresiones regulares para modificar el archivo.

original_block_regex = r'(\s*if gastos:\n\s*st\.success\(f"Se detectaron \{len\(gastos\)\} gastos"\).*?if st\.button\("Guardar Egresos"\).*?st\.rerun\(\)\n\s*else:\n\s*st\.warning\("No se detectaron gastos en el archivo"\))'

match = re.search(original_block_regex, content, re.DOTALL)
if match:
    pass # Este regex puede fallar si la indentacion varia mucho. 

# En vez de regex complejos para reemplazar, voy a buscar la línea exacta y reemplazar la lógica:
# El problema entero se puede arreglar añadiendo st.session_state["gastos_preview"] = gastos
# al final del spinner, y luego reemplazando "if gastos:" por "if 'gastos_preview' in st.session_state:"

cambio_1 = """                    if gastos:
                        st.session_state["gastos_preview"] = gastos
                
        if "gastos_preview" in st.session_state:
            gastos = st.session_state["gastos_preview"]
            if gastos:
                st.success(f"Se detectaron {len(gastos)} gastos")"""

# Tenemos que localizar esto:
'''                    if gastos:
                        st.success(f"Se detectaron {len(gastos)} gastos")'''

viejo_1 = '''                    if gastos:
                        st.success(f"Se detectaron {len(gastos)} gastos")'''

content = content.replace(viejo_1, cambio_1)

# También tenemos que asegurarnos de borrar el preview cuando apretan Guardar Egresos:
cambio_2 = """                            st.session_state.datos = datos
                            guardar_datos(datos)
                            if "gastos_preview" in st.session_state:
                                del st.session_state["gastos_preview"]
                            st.success(f"Egresos guardados para {mes_seleccionado}")
                            st.rerun()"""

viejo_2 = """                            st.session_state.datos = datos
                            guardar_datos(datos)
                            st.success(f"Egresos guardados para {mes_seleccionado}")
                            st.rerun()"""

content = content.replace(viejo_2, cambio_2)

# Y si hay else: warning lo arreglamos:
cambio_3 = """                    else:
                        st.warning("No se detectaron gastos en el archivo")
                        if "gastos_preview" in st.session_state:
                            del st.session_state["gastos_preview"]"""

viejo_3 = """                    else:
                        st.warning("No se detectaron gastos en el archivo")"""

content = content.replace(viejo_3, cambio_3)

# Y cuando cambia de mes o de archivo, deberia limpiarse el preview
cambio_4 = """    if archivo:
        if st.session_state.get('last_archivo') != archivo.name:
            st.session_state.pop("gastos_preview", None)
            st.session_state['last_archivo'] = archivo.name
            
        fuente = detectar_fuente(archivo.name)"""

viejo_4 = """    if archivo:
        fuente = detectar_fuente(archivo.name)"""

content = content.replace(viejo_4, cambio_4)

with open("app.py", "w", encoding="utf-8", errors="replace") as f:
    f.write(content)

print("Arreglo aplicado. Verificando sintaxis...")

from pathlib import Path
from datetime import datetime
import shutil
import sys

p = Path("valu.py")
if not p.exists():
    raise SystemExit("ERROR: no encuentro valu.py. Ejecuta este script desde la carpeta del proyecto.")

s = p.read_text(encoding="utf-8")
start_marker = '    elif st.session_state.page == "Cargar Mercado":'
end_marker = '    elif st.session_state.page == "Configuración":'

start = s.find(start_marker)
if start == -1:
    raise SystemExit('ERROR: no encontre el bloque: elif st.session_state.page == "Cargar Mercado"')

end = s.find(end_marker, start)
if end == -1:
    raise SystemExit('ERROR: no encontre el bloque siguiente: elif st.session_state.page == "Configuración"')

backup = Path(f"valu.py.backup_cargar_mercado_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
shutil.copy2(p, backup)
print(f"Backup creado: {backup.name}")

new_block = '''    elif st.session_state.page == "Cargar Mercado":
        st.header("Operaciones de Mantenimiento")
        st.caption("Ejecutar solo cuando sea necesario.")

        # ─── Actualizar base de mercado ───
        with st.container(border=True):
            st.subheader("Actualizar la base de datos de mercado")
            if st.button("Actualizar base de mercado", type="primary", use_container_width=True):
                barra = st.progress(0.0, text="Preparando actualización...")
                estado = st.empty()
                inicio = time.time()
                try:
                    barra.progress(0.10, text="Iniciando actualización de mercado...")
                    estado.info("Actualizando datos de mercado. Esta operación puede demorar varios minutos.")
                    from parsers.motor_vpp_core import actualizar_mercado_vpp_full
                    ok = actualizar_mercado_vpp_full()
                    barra.progress(1.0, text="Actualización finalizada")
                    duracion = time.time() - inicio
                    if ok:
                        estado.success(f"Base de mercado actualizada. Tiempo total: {duracion/60:.1f} min.")
                    else:
                        estado.error("La actualización terminó con errores. Revisá los logs.")
                except Exception as e:
                    barra.progress(1.0, text="Actualización interrumpida")
                    estado.error(f"No se pudo actualizar la base de mercado: {e}")

        st.markdown("---")

        # ─── Recalcular todo ───
        with st.container(border=True):
            props = cargar_propiedades()
            n = len(props)

            st.subheader("Recalcular valuaciones")
            st.markdown(f"Fuerza el recalculo de las **{n} propiedades**.")

            if st.button("Recalcular todo", type="primary", use_container_width=True):
                if n == 0:
                    st.info("No hay propiedades para recalcular.")
                else:
                    barra = st.progress(0.0, text=f"Preparando recalculo de {n} propiedades...")
                    estado = st.empty()
                    inicio = time.time()
                    for i, p_prop in enumerate(props):
                        from parsers.motor_vpp_core import valuar_con_cache
                        nombre = p_prop.get('nombre', '?')
                        estado.info(f"Valuando **{nombre}** ({i+1}/{n})")
                        valuar_con_cache(p_prop, forzar_recalculo=True)

                        avance = (i + 1) / n
                        transcurrido = time.time() - inicio
                        promedio = transcurrido / (i + 1)
                        restante = max(0, promedio * (n - i - 1))
                        barra.progress(
                            avance,
                            text=(
                                f"{i+1}/{n} valuaciones completadas · "
                                f"restan ~{restante/60:.1f} min"
                            ),
                        )
                    duracion = time.time() - inicio
                    estado.success(f"{n} propiedades recalculadas. Tiempo total: {duracion/60:.1f} min.")

'''

p.write_text(s[:start] + new_block + s[end:], encoding="utf-8")
print("OK: mensajes y barras de progreso actualizados en Cargar Mercado.")
print("Reinicia Streamlit: Ctrl+C y luego streamlit run valu.py")

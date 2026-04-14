import re
import os

APP_PATH = "C:/Users/Gustavo/ingresos_familiares_st/app.py"

def patch_app():
    if not os.path.exists(APP_PATH):
        print(f"ERROR: No se encuentra {APP_PATH}")
        return

    with open(APP_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Archivo leido: {len(content)} caracteres.")

    # 1. Parchear el Botón de Mercado
    old_button_block = r'# 1\. Boton Actulizar Mercado Inmobiliario en Tiempo Real.*?st\.error\(f"Fallo al conectar con el portal inmobiliario: \{e\}"\)'
    new_button_block = """# 1. Boton Mercado (VPP Sync) Híbrido 7.0
    c1, c2 = st.columns([3, 2])
    with c1:
        try:
            from parsers.motor_vpp_core import load_cache
            cache_info = load_cache()
            if cache_info:
                from datetime import datetime
                dt_cache = datetime.fromisoformat(cache_info.get("fecha"))
                st.caption(f"🕒 Mercado: **{dt_cache.strftime('%d/%m %H:%M')}**")
                if cache_info.get("status") == "corriendo":
                    st.warning("🔄 Escaneo masivo en progreso...")
        except:
            st.caption("🕒 Mercado: Pendiente actualización")
    with c2:
        if st.button("🌐 Actualizar Mercado (VPP Sync)", help="Dispara escaneo masivo (Argenprop, TTL, Top20, etc)"):
            import threading
            from parsers.motor_vpp_core import actualizar_mercado_vpp_full, save_cache, load_cache
            info = load_cache() or {"propiedades": []}
            save_cache(info.get("propiedades", []), status="corriendo")
            threading.Thread(target=actualizar_mercado_vpp_full).start()
            st.info("🚀 Escaneo iniciado en background. Los resultados se actualizarán al finalizar.")"""

    content = re.sub(old_button_block, new_button_block, content, flags=re.DOTALL)

    # 2. Parchear la lógica de Valuación en el Loop de Propiedades
    # Buscamos el bloque v6 para reemplazar por v7
    old_valuation_block = r'# SIEMPRE calcular del motor v6\.0 \(AVM robusto\).*?descuento_liquidez = \(valor_display - valor_realizable\) / valor_display \* 100 if valor_display > 0 else 0'
    new_valuation_block = """# MOTOR V7.0 HÍBRIDO (Venda + Alquiler + ROI)
            from parsers.mercado_inmobiliario import valuar_propiedad_v7
            res = valuar_propiedad_v7(prop, fecha_ref=mes_prop)
            valor_display = res['valor_propiedad_usd']
            valor_realizable = res['valor_realizable_usd']
            m2_equivalente = res['m2_equivalentes']
            m2_display = res['valor_m2_actual_usd']
            alq_ars = res['alquiler_estimado_ars']
            cap_rate = res['cap_rate_anual']"""

    content = re.sub(old_valuation_block, new_valuation_block, content, flags=re.DOTALL)

    # 3. Parchear Métricas en la Tarjeta
    old_header_block = r'if valor_display > 0:.*?st\.caption\("💡 Serie histórica real v6\.0 \+ m2 equivalentes \+ mapeo zonas \+ descuento mercado"\)'
    new_header_block = """if valor_display > 0:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Valor VPP", f"${valor_realizable:,.0f} USD")
                    m2.metric("Alquiler", f"${alq_ars:,.0f} ARS")
                    m3.metric("ROI Anual", f"{cap_rate:.2f}%")
                    st.caption(f"💡 Modelo Híbrido V7.0 | Dólar Binance: ${res.get('usdt_ars', 1000):,.0f}")"""

    content = re.sub(old_header_block, new_header_block, content, flags=re.DOTALL)

    # 4. Parchear el Expander
    old_expander = r'with st\.expander\("Detalle de la valuación"\):.*?st\.line_chart\(df_serie\.set_index\(\'Fecha\'\)\[\'Valor m² USD\'\]\)'
    new_expander = """with st.expander("🔍 Análisis de Mercado VPP v7.0"):
                st.info(res['justificacion'])
                st.write(f"**Rango de Mercado:** {res['rango_m2']}")
                st.write(f"**Confiabilidad:** {res['confianza'].upper()}")
                st.caption(f"Datos basados en el escaneo del {res['fecha_mercado']}")"""

    content = re.sub(old_expander, new_expander, content, flags=re.DOTALL)

    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print("PATCH COMPLETADO CON EXITO.")

if __name__ == "__main__":
    patch_app()

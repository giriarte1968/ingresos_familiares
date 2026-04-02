import pathlib

filepath = r'C:\Users\Gustavo\ingresos_familiares_st\app.py'
content = pathlib.Path(filepath, encoding='utf-8').read_text(errors='replace')

old_start = '            # Valuaci\u00f3n autom\u00e1tica del motor\n            st.caption("Valuaci\u00f3n Autom\u00e1tica")'
old_end = '                st.rerun()\n\n            # Tasaci\u00f3n manual'

start_idx = content.find(old_start)
end_marker = '            # Tasaci\u00f3n manual'
end_idx = content.find(end_marker, start_idx)

if start_idx == -1 or end_idx == -1:
    print(f'start_idx={start_idx}, end_idx={end_idx}')
    # Fallback: find by line numbers
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'Valuaci\u00f3n autom\u00e1tica del motor' in line:
            start_line = i
            print(f'Found start at line {i+1}')
        if '# Tasaci\u00f3n manual' in line and i > start_line:
            end_line = i
            print(f'Found end at line {i+1}')
            break

    # Replace lines from start_line to end_line (exclusive)
    new_lines = lines[:start_line] + [
        '            # Valuaci\u00f3n autom\u00e1tica del motor',
        '            st.caption("Valuaci\u00f3n Autom\u00e1tica")',
        '            if st.button("\U0001f4ca Valuaci\u00f3n Autom\u00e1tica", key=f"valuar_{prop[\'id\']}"):',
        '                from parsers.mercado_inmobiliario import valuar_propiedad',
        '                resultado = valuar_propiedad(prop)',
        '',
        '                valor_m2 = resultado[\'valor_m2_actual_usd\']',
        '                valor_prop = resultado[\'valor_propiedad_usd\']',
        '                tendencia = resultado[\'tendencia\']',
        '                confianza = resultado[\'nivel_confianza\']',
        '',
        '                # Buscar tasaci\u00f3n anterior para plusval\u00eda real',
        '                tasaciones = prop.get(\'tasaciones\', [])',
        '                tasacion_anterior = None',
        '                if tasaciones:',
        '                    tasaciones_ordenadas = sorted(tasaciones, key=lambda t: t.get(\'fecha\', \'\'), reverse=True)',
        '                    for t in tasaciones_ordenadas:',
        '                        if t.get(\'fecha\') < datetime.now().strftime(\'%Y-%m-%d\'):',
        '                            tasacion_anterior = t',
        '                            break',
        '',
        '                # Calcular plusval\u00eda real vs estimada',
        '                if tasacion_anterior:',
        '                    plusvalia_real_usd = valor_prop - tasacion_anterior.get(\'valor_usd\', 0)',
        '                    plusvalia_real_pct = ((valor_prop / tasacion_anterior.get(\'valor_usd\', 1)) - 1) * 100',
        '                    plusvalia_mes_anterior = tasacion_anterior.get(\'mes\', mes)',
        '                    fuente_plusvalia = \'real\'',
        '                else:',
        '                    plusvalia_real_usd = 0',
        '                    plusvalia_real_pct = resultado[\'plusvalia_mensual_pct\']',
        '                    plusvalia_mes_anterior = \'estimado\'',
        '                    fuente_plusvalia = \'estimado\'',
        '',
        '                # Actualizar propiedad con valuaci\u00f3n',
        '                for activo in datos.get(\'activos\', []):',
        '                    if activo.get(\'id\') == prop[\'id\']:',
        '                        activo[\'valor_tasacion_usd\'] = valor_prop',
        '                        activo[\'valor_tasacion_ars\'] = valor_prop * usdt_ars',
        '                        activo[\'valor_m2_usd\'] = valor_m2',
        '                        activo[\'ultima_valuacion\'] = datetime.now().strftime(\'%Y-%m-%d\')',
        '',
        '                        tasacion = {',
        '                            \'fecha\': datetime.now().strftime(\'%Y-%m-%d\'),',
        '                            \'valor_usd\': valor_prop,',
        '                            \'valor_ars\': valor_prop * usdt_ars,',
        '                            \'valor_m2_usd\': valor_m2,',
        '                            \'mes\': mes,',
        '                            \'fuente\': \'motor_valuacion\'',
        '                        }',
        '                        activo.setdefault(\'tasaciones\', []).append(tasacion)',
        '',
        '                # Guardar plusval\u00eda en el mes',
        '                plusvalia_ars = plusvalia_real_usd * usdt_ars',
        '                datos.setdefault(\'meses\', {}).setdefault(mes, {}).setdefault(\'plusvalia_propiedades\', 0)',
        '                datos[\'meses\'][mes][\'plusvalia_propiedades\'] = plusvalia_ars',
        '',
        '                guardar_datos(datos)',
        '                st.session_state.datos = datos',
        '',
        '                # Guardar en session_state para persistencia',
        '                st.session_state[f"valuacion_{prop[\'id\']}"] = {',
        '                    \'resultado\': resultado,',
        '                    \'valor_m2\': valor_m2,',
        '                    \'valor_prop\': valor_prop,',
        '                    \'tendencia\': tendencia,',
        '                    \'confianza\': confianza,',
        '                    \'plusvalia_usd\': plusvalia_real_usd,',
        '                    \'plusvalia_pct\': plusvalia_real_pct,',
        '                    \'plusvalia_mes_anterior\': plusvalia_mes_anterior,',
        '                    \'fuente_plusvalia\': fuente_plusvalia,',
        '                    \'tasacion_anterior\': tasacion_anterior,',
        '                    \'mes_actual\': mes,',
        '                }',
        '',
        '            # Mostrar resultados persistentes de valuaci\u00f3n',
        '            valuacion = st.session_state.get(f"valuacion_{prop[\'id\']}")',
        '            if valuacion:',
        '                st.success(f"Valuaci\u00f3n {valuacion[\'mes_actual\']}: USD {valuacion[\'valor_prop\']:,.0f}")',
        '                col_v1, col_v2, col_v3, col_v4 = st.columns(4)',
        '                col_v1.metric("Valor m\u00b2 (USD)", f"${valuacion[\'valor_m2\']:,.0f}")',
        '                col_v2.metric("Valor Propiedad", f"${valuacion[\'valor_prop\']:,.0f}")',
        '                col_v3.metric("Tendencia", {"alcista": "\U0001f4c8", "bajista": "\U0001f4c9", "neutral": "\u27a1\ufe0f"}.get(valuacion[\'tendencia\'], "\u27a1\ufe0f"))',
        '                col_v4.metric("Confianza", {"alto": "\U0001f7e2", "medio": "\U0001f7e1", "bajo": "\U0001f534"}.get(valuacion[\'confianza\'], "\U0001f7e1"))',
        '',
        '                p_col1, p_col2 = st.columns(2)',
        '                p_col1.metric(',
        '                    f"Plusval\u00eda vs {valuacion[\'plusvalia_mes_anterior\']}",',
        '                    f"USD {valuacion[\'plusvalia_usd\']:,.0f}",',
        '                    delta=f"{valuacion[\'plusvalia_pct\']:+.2f}%",',
        '                    delta_color="normal"',
        '                )',
        '                p_col2.caption(f"Fuente: {valuacion[\'fuente_plusvalia\']}")',
        '',
        '                with st.expander("Detalle de la valuaci\u00f3n"):',
        '                    res = valuacion[\'resultado\']',
        '                    st.write(res[\'justificacion\'])',
        '                    st.write(f"**Rango estimado:** {res[\'rango_m2\']}")',
        '                    st.write(f"**Plusval\u00eda mensual (motor):** {res[\'plusvalia_mensual_pct\']:+.2f}%")',
        '                    st.write(f"**Plusval\u00eda acumulada:** {res[\'plusvalia_acumulada_pct\']:+.2f}%")',
        '',
        '                    serie = res.get(\'serie_mensual_m2\', [])',
        '                    if serie:',
        '                        st.caption("Serie hist\u00f3rica del m\u00b2 (USD)")',
        '                        df_serie = pd.DataFrame(serie)',
        '                        df_serie.columns = [\'Fecha\', \'Valor m\u00b2 USD\', \'Fuente\']',
        '                        st.line_chart(df_serie.set_index(\'Fecha\')[\'Valor m\u00b2 USD\'])',
        '',
        '                if st.button("Cerrar valuaci\u00f3n", key=f"close_val_{prop[\'id\']}"):',
        '                    st.session_state[f"valuacion_{prop[\'id\']}"] = None',
        '                    st.rerun()',
        '',
        '                st.divider()',
    ] + lines[end_line:]

    content = '\n'.join(new_lines)
    pathlib.Path(filepath, encoding='utf-8').write_text(content, encoding='utf-8')
    print('Replaced via line replacement')
else:
    print('Direct replacement worked')
    new_block = '''            # Valuaci\u00f3n autom\u00e1tica del motor
            st.caption("Valuaci\u00f3n Autom\u00e1tica")
            if st.button("\U0001f4ca Valuaci\u00f3n Autom\u00e1tica", key=f"valuar_{prop['id']}"):
                from parsers.mercado_inmobiliario import valuar_propiedad
                resultado = valuar_propiedad(prop)

                valor_m2 = resultado['valor_m2_actual_usd']
                valor_prop = resultado['valor_propiedad_usd']
                tendencia = resultado['tendencia']
                confianza = resultado['nivel_confianza']

                # Buscar tasaci\u00f3n anterior para plusval\u00eda real
                tasaciones = prop.get('tasaciones', [])
                tasacion_anterior = None
                if tasaciones:
                    tasaciones_ordenadas = sorted(tasaciones, key=lambda t: t.get('fecha', ''), reverse=True)
                    for t in tasaciones_ordenadas:
                        if t.get('fecha') < datetime.now().strftime('%Y-%m-%d'):
                            tasacion_anterior = t
                            break

                # Calcular plusval\u00eda real vs estimada
                if tasacion_anterior:
                    plusvalia_real_usd = valor_prop - tasacion_anterior.get('valor_usd', 0)
                    plusvalia_real_pct = ((valor_prop / tasacion_anterior.get('valor_usd', 1)) - 1) * 100
                    plusvalia_mes_anterior = tasacion_anterior.get('mes', mes)
                    fuente_plusvalia = 'real'
                else:
                    plusvalia_real_usd = 0
                    plusvalia_real_pct = resultado['plusvalia_mensual_pct']
                    plusvalia_mes_anterior = 'estimado'
                    fuente_plusvalia = 'estimado'

                # Actualizar propiedad con valuaci\u00f3n
                for activo in datos.get('activos', []):
                    if activo.get('id') == prop['id']:
                        activo['valor_tasacion_usd'] = valor_prop
                        activo['valor_tasacion_ars'] = valor_prop * usdt_ars
                        activo['valor_m2_usd'] = valor_m2
                        activo['ultima_valuacion'] = datetime.now().strftime('%Y-%m-%d')

                        tasacion = {
                            'fecha': datetime.now().strftime('%Y-%m-%d'),
                            'valor_usd': valor_prop,
                            'valor_ars': valor_prop * usdt_ars,
                            'valor_m2_usd': valor_m2,
                            'mes': mes,
                            'fuente': 'motor_valuacion'
                        }
                        activo.setdefault('tasaciones', []).append(tasacion)

                # Guardar plusval\u00eda en el mes
                plusvalia_ars = plusvalia_real_usd * usdt_ars
                datos.setdefault('meses', {}).setdefault(mes, {}).setdefault('plusvalia_propiedades', 0)
                datos['meses'][mes]['plusvalia_propiedades'] = plusvalia_ars

                guardar_datos(datos)
                st.session_state.datos = datos

                # Guardar en session_state para persistencia
                st.session_state[f"valuacion_{prop['id']}"] = {
                    'resultado': resultado,
                    'valor_m2': valor_m2,
                    'valor_prop': valor_prop,
                    'tendencia': tendencia,
                    'confianza': confianza,
                    'plusvalia_usd': plusvalia_real_usd,
                    'plusvalia_pct': plusvalia_real_pct,
                    'plusvalia_mes_anterior': plusvalia_mes_anterior,
                    'fuente_plusvalia': fuente_plusvalia,
                    'tasacion_anterior': tasacion_anterior,
                    'mes_actual': mes,
                }

            # Mostrar resultados persistentes de valuaci\u00f3n
            valuacion = st.session_state.get(f"valuacion_{prop['id']}")
            if valuacion:
                st.success(f"Valuaci\u00f3n {valuacion['mes_actual']}: USD {valuacion['valor_prop']:,.0f}")
                col_v1, col_v2, col_v3, col_v4 = st.columns(4)
                col_v1.metric("Valor m\u00b2 (USD)", f"${valuacion['valor_m2']:,.0f}")
                col_v2.metric("Valor Propiedad", f"${valuacion['valor_prop']:,.0f}")
                col_v3.metric("Tendencia", {"alcista": "\U0001f4c8", "bajista": "\U0001f4c9", "neutral": "\u27a1\ufe0f"}.get(valuacion['tendencia'], "\u27a1\ufe0f"))
                col_v4.metric("Confianza", {"alto": "\U0001f7e2", "medio": "\U0001f7e1", "bajo": "\U0001f534"}.get(valuacion['confianza'], "\U0001f7e1"))

                p_col1, p_col2 = st.columns(2)
                p_col1.metric(
                    f"Plusval\u00eda vs {valuacion['plusvalia_mes_anterior']}",
                    f"USD {valuacion['plusvalia_usd']:,.0f}",
                    delta=f"{valuacion['plusvalia_pct']:+.2f}%",
                    delta_color="normal"
                )
                p_col2.caption(f"Fuente: {valuacion['fuente_plusvalia']}")

                with st.expander("Detalle de la valuaci\u00f3n"):
                    res = valuacion['resultado']
                    st.write(res['justificacion'])
                    st.write(f"**Rango estimado:** {res['rango_m2']}")
                    st.write(f"**Plusval\u00eda mensual (motor):** {res['plusvalia_mensual_pct']:+.2f}%")
                    st.write(f"**Plusval\u00eda acumulada:** {res['plusvalia_acumulada_pct']:+.2f}%")

                    serie = res.get('serie_mensual_m2', [])
                    if serie:
                        st.caption("Serie hist\u00f3rica del m\u00b2 (USD)")
                        df_serie = pd.DataFrame(serie)
                        df_serie.columns = ['Fecha', 'Valor m\u00b2 USD', 'Fuente']
                        st.line_chart(df_serie.set_index('Fecha')['Valor m\u00b2 USD'])

                if st.button("Cerrar valuaci\u00f3n", key=f"close_val_{prop['id']}"):
                    st.session_state[f"valuacion_{prop['id']}"] = None
                    st.rerun()

                st.divider()

'''
    content = content[:start_idx] + new_block + content[end_idx:]
    pathlib.Path(filepath, encoding='utf-8').write_text(content, encoding='utf-8')

"""Patch: pasa location y zoom_start al constructor de folium.Map."""
content = open('parsers/mercado_inmobiliario.py', encoding='utf-8').read()

# Viejo: Map creado sin location, luego se intentaba asignar como atributo (no funciona)
old = '''        radio = resultado.get('resolution_metadata', {}).get('radio_usado', 300)
        comparables = resultado.get('comparables_venta', [])
        valor = resultado.get('valor_propiedad_usd', 0)
        
        m = folium.Map(tiles='cartodbpositron')
        
        folium.Marker(
            [lat, lon],
            popup=f"📍 Propiedad - ${valor:,.0f}",
            icon=folium.Icon(color='red', icon='home')
        ).add_to(m)
        
        folium.Circle(
            [lat, lon],
            radius=radio,
            color='gray',
            fill=False,
            dash_array='5'
        ).add_to(m)
        
        for comp in comparables:
            if comp.get('lat') and comp.get('lon'):
                folium.CircleMarker(
                    [comp['lat'], comp['lon']],
                    radius=4,
                    color='blue',
                    fill=True,
                    fill_opacity=0.6,
                    popup=f"${comp.get('precio_m2', 0):,.0f}/m²"
                ).add_to(m)
        
        # Centrar el mapa EXACTAMENTE en la propiedad valuada.
        # Se usa location+zoom_start para garantizar que el marcador rojo
        # quede siempre en el centro geometrico del viewport, independiente
        # de la distribucion de comparables.
        # Zoom calibrado segun el radio de busqueda:
        #   radio <= 300m  -> zoom 15 (~600m de ancho visible)
        #   radio <= 500m  -> zoom 14 (~1.2km)
        #   radio <= 800m  -> zoom 13 (~2.5km)
        #   radio >  800m  -> zoom 12 (~5km)
        if radio <= 300:
            zoom_level = 15
        elif radio <= 500:
            zoom_level = 14
        elif radio <= 800:
            zoom_level = 13
        else:
            zoom_level = 12
        m.location = [float(lat), float(lon)]
        m.zoom_start = zoom_level'''

# Nuevo: zoom calculado ANTES del constructor, location pasado al constructor
new = '''        radio = resultado.get('resolution_metadata', {}).get('radio_usado', 300)
        comparables = resultado.get('comparables_venta', [])
        valor = resultado.get('valor_propiedad_usd', 0)

        # Zoom calibrado segun el radio de busqueda (ANTES de crear el mapa)
        if radio <= 300:
            zoom_level = 15
        elif radio <= 500:
            zoom_level = 14
        elif radio <= 800:
            zoom_level = 13
        else:
            zoom_level = 12

        # location y zoom_start van en el CONSTRUCTOR para que surtan efecto
        m = folium.Map(
            location=[float(lat), float(lon)],
            zoom_start=zoom_level,
            tiles='cartodbpositron'
        )

        folium.Marker(
            [lat, lon],
            popup=f"📍 Propiedad - ${valor:,.0f}",
            icon=folium.Icon(color='red', icon='home')
        ).add_to(m)

        folium.Circle(
            [lat, lon],
            radius=radio,
            color='gray',
            fill=False,
            dash_array='5'
        ).add_to(m)

        for comp in comparables:
            if comp.get('lat') and comp.get('lon'):
                folium.CircleMarker(
                    [comp['lat'], comp['lon']],
                    radius=4,
                    color='blue',
                    fill=True,
                    fill_opacity=0.6,
                    popup=f"${comp.get('precio_m2', 0):,.0f}/m²"
                ).add_to(m)'''

if old in content:
    content = content.replace(old, new, 1)
    print('PATCH OK')
else:
    print('NOT FOUND')
    idx = content.find('_generar_html_mapa')
    print(repr(content[idx:idx+600]))

open('parsers/mercado_inmobiliario.py', 'w', encoding='utf-8').write(content)

import ast
ast.parse(content)
print('Syntax OK')
assert "location=[float(lat), float(lon)]" in content
assert "zoom_start=zoom_level" in content
# Verificar que NO queda la asignacion post-construccion
assert "m.location = " not in content
assert "m.zoom_start = " not in content
print('All checks passed')

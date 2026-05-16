"""Patch: centra el mapa de detalle en la propiedad valuada."""
content = open('parsers/mercado_inmobiliario.py', encoding='utf-8').read()

old = '''        # Centrar el mapa con la propiedad como referencia visual.
        # Se usan bounds asimetricos: mas espacio al norte para que el
        # marcador rojo quede aproximadamente en el centro del viewport.
        comp_lats = [float(c['lat']) for c in comparables if c.get('lat')]
        comp_lons = [float(c['lon']) for c in comparables if c.get('lon')]
        if comp_lats:
            max_dlat = max(abs(float(lat) - cl) for cl in comp_lats)
            max_dlon = max(abs(float(lon) - cl) for cl in comp_lons) if comp_lons else max_dlat
        else:
            # Sin comparables: usar el radio de busqueda como referencia (~0.009 deg/km)
            max_dlat = max_dlon = radio * 0.000009
        # Factores asimetricos: mas espacio al norte y horizontalmente
        factor_n  = 1.7  # norte: espacio extra para que la prop quede centrada
        factor_s  = 1.1  # sur: margen minimo
        factor_h  = 1.3  # horizontal: simetrico ampliado
        min_delta = max(radio * 0.000009, 0.003)  # minimo ~300m
        max_dlat  = max(max_dlat, min_delta)
        max_dlon  = max(max_dlon, min_delta)
        m.fit_bounds(
            [[float(lat) - max_dlat * factor_s, float(lon) - max_dlon * factor_h],
             [float(lat) + max_dlat * factor_n, float(lon) + max_dlon * factor_h]],
            max_zoom=15
        )'''

new = '''        # Centrar el mapa EXACTAMENTE en la propiedad valuada.
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

if old in content:
    content = content.replace(old, new, 1)
    print('PATCH OK')
else:
    print('NOT FOUND')
    idx = content.find('Centrar el mapa')
    print(repr(content[idx:idx+500]))

open('parsers/mercado_inmobiliario.py', 'w', encoding='utf-8').write(content)

import ast
ast.parse(content)
print('Syntax OK')
assert 'zoom_level = 15' in content
assert 'm.location = [float(lat), float(lon)]' in content
assert 'm.zoom_start = zoom_level' in content
print('All checks passed')

import osmnx as ox
import geopandas as gpd
import json
from shapely.geometry import LineString

def extraer_barreras_rosario():
    print('Extrayendo barreras desde OpenStreetMap...')
    # bbox: (left, bottom, right, top) -> (west, south, east, north)
    bbox = (-60.72, -32.98, -60.61, -32.92)
    
    try:
        rails = ox.features_from_bbox(bbox, tags={'railway': 'rail'})
        rails = rails[['geometry']].copy()
        rails['barrier_type'] = 'hard'
        rails['name'] = 'Ferrocarril'
    except Exception as e:
        print(f'Error extrayendo vías: {e}')
        rails = gpd.GeoDataFrame()

    nombres_clave = ['Oroño', '27 de Febrero', 'Pellegrini', 'Francia', 'Circunvalación', 'Lagos']
    try:
        roads = ox.features_from_bbox(bbox, tags={'highway': ['primary', 'secondary', 'tertiary']})
        def es_barrera(row):
            name = str(row.get('name', '')).lower()
            return any(k.lower() in name for k in nombres_clave)
        barreras_blandas = roads[roads.apply(es_barrera, axis=1)][['geometry']].copy()
        barreras_blandas['barrier_type'] = 'soft'
        barreras_blandas['name'] = roads.loc[barreras_blandas.index, 'name']
    except Exception as e:
        print(f'Error extrayendo avenidas: {e}')
        barreras_blandas = gpd.GeoDataFrame()

    if rails.empty and barreras_blandas.empty:
        print('No se encontraron barreras.')
        return

    all_barriers = gpd.pd.concat([rails, barreras_blandas])
    all_barriers = all_barriers.to_crs(epsg=4326)
    
    output_path = r'C:\Users\Gustavo\ingresos_familiares_st\barreras_rosario.json'
    all_barriers.to_file(output_path, driver='GeoJSON')
    print(f'Barreras exportadas exitosamente a: {output_path}')
    print(f'Total de segmentos de barrera: {len(all_barriers)}')

if __name__ == '__main__':
    extraer_barreras_rosario()

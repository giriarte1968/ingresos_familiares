"""
Completar seccion/manzana/grafico en rosario_avm_full.csv
usando point-in-polygon contra la geometría catastral oficial.

Fuente de verdad: parcelas_seccion*_json.csv (polígonos del catastro)
"""
import os, sys, json, glob, logging, time
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape, Point

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
GEOMETRY_DIR = os.path.join(DATA_DIR, 'geometry')
CSV_PATH = os.path.join(DATA_DIR, 'rosario_avm_full.csv')
BACKUP_PATH = os.path.join(DATA_DIR, '..', '..', '..', '.gemini', 'antigravity', 'scratch', 'tests', 'data', 'rosario_avm_full_broken_backup.csv')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

def load_geometry():
    """Load all parcel geometry CSVs into a GeoDataFrame with polygon geometries."""
    log.info("Loading geometry CSVs...")
    dfs = []
    for f in sorted(glob.glob(os.path.join(GEOMETRY_DIR, 'parcelas_seccion*_json.csv'))):
        df = pd.read_csv(f)
        dfs.append(df)
    geo_all = pd.concat(dfs, ignore_index=True)
    log.info("Building polygon geometries...")
    geo_all['geometry'] = geo_all['GEOJSON'].apply(lambda x: shape(json.loads(x) if isinstance(x, str) else x))
    gdf = gpd.GeoDataFrame(geo_all, geometry='geometry', crs='EPSG:4326')
    gdf['SECCION'] = pd.to_numeric(gdf['SECCION'], errors='coerce')
    gdf['MANZANA'] = pd.to_numeric(gdf['MANZANA'], errors='coerce')
    gdf['GRAFICO'] = pd.to_numeric(gdf['GRAFICO'], errors='coerce')
    gdf['CARPETA'] = pd.to_numeric(gdf['CARPETA'], errors='coerce')
    log.info(f"Loaded {len(gdf)} parcels")
    return gdf

def load_current_csv():
    """Load the current rosario_avm_full.csv as a GeoDataFrame."""
    log.info(f"Loading {CSV_PATH}...")
    df = pd.read_csv(CSV_PATH)
    df['latitud'] = pd.to_numeric(df['latitud'], errors='coerce')
    df['longitud'] = pd.to_numeric(df['longitud'], errors='coerce')
    has_coords = df['latitud'].notna() & df['longitud'].notna()
    df_valid = df[has_coords].copy()
    df_valid['geometry'] = df_valid.apply(lambda r: Point(r['longitud'], r['latitud']), axis=1)
    gdf = gpd.GeoDataFrame(df_valid, geometry='geometry', crs='EPSG:4326')
    log.info(f"Loaded {len(df)} rows, {len(gdf)} with valid coordinates")
    return df, gdf

def spatial_join_optimized(gdf_pts, gdf_polys):
    """
    Spatial join: find which polygon contains each point.
    Optimized by joining at seccion level when possible.
    """
    log.info("Running spatial join (point-in-polygon)...")
    t0 = time.time()

    # Separate rows that already have seccion vs those that don't
    has_seccion = gdf_pts[gdf_pts['seccion'].notna() & (gdf_pts['seccion'] != '')].copy()
    no_seccion = gdf_pts[~gdf_pts.index.isin(has_seccion.index)].copy()

    log.info(f"  {len(has_seccion)} with seccion, {len(no_seccion)} without")

    all_joined = []

    # For rows WITH seccion: restrict polygon search to that seccion
    if len(has_seccion) > 0:
        has_seccion['seccion_int'] = pd.to_numeric(has_seccion['seccion'], errors='coerce').astype(int)
        for sec in has_seccion['seccion_int'].unique():
            pts_sec = has_seccion[has_seccion['seccion_int'] == sec]
            polys_sec = gdf_polys[gdf_polys['SECCION'] == sec]
            if len(polys_sec) == 0:
                log.warning(f"  No polygons for seccion {sec}, {len(pts_sec)} points unmatched")
                continue
            joined = gpd.sjoin(pts_sec, polys_sec, how='left', predicate='within')
            all_joined.append(joined)
        log.info(f"  Joined {len(has_seccion)} with seccion restriction")

    # For rows WITHOUT seccion: full spatial join (all polygons)
    if len(no_seccion) > 0:
        log.info(f"  Joining {len(no_seccion)} without seccion against {len(gdf_polys)} polygons...")
        # Use a spatial index for efficiency
        joined = gpd.sjoin(no_seccion, gdf_polys, how='left', predicate='within')
        all_joined.append(joined)
        log.info(f"  Joined {len(no_seccion)} without seccion")

    result = pd.concat(all_joined, ignore_index=False)
    elapsed = time.time() - t0
    matched = result['SECCION'].notna().sum()
    log.info(f"Spatial join complete: {matched}/{len(gdf_pts)} matched ({elapsed:.1f}s)")

    return result

def apply_corrections(df_orig, joined):
    """Apply the geometry-verified values back to the original dataframe."""
    df = df_orig.copy()

    # Start fresh: clear existing seccion/manzana/grafico
    df['seccion'] = ''
    df['manzana'] = ''
    df['grafico'] = ''
    df['division'] = ''

    # If sjoin produced duplicates (same point matched multiple polys), aggregate
    dup_idxs = joined.index[joined.index.duplicated(keep='first')]
    if len(dup_idxs) > 0:
        log.warning(f"  Deduplicating {len(dup_idxs)} duplicated indices from sjoin")
        joined = joined[~joined.index.duplicated(keep='first')]

    # Map joined results back by index
    for idx in joined.index:
        row = joined.loc[idx]
        if pd.notna(row['SECCION']):
            df.at[idx, 'seccion'] = str(int(row['SECCION']))
        if pd.notna(row['MANZANA']):
            df.at[idx, 'manzana'] = str(int(row['MANZANA']))
        if pd.notna(row['GRAFICO']):
            df.at[idx, 'grafico'] = str(int(row['GRAFICO']))

    matched_count = joined['SECCION'].notna().sum()
    log.info(f"Applied corrections: {matched_count} rows with seccion")

    return df

def main():
    log.info("=" * 60)
    log.info("COMPLETAR CATASTRAL - seccion/manzana/grafico")
    log.info("=" * 60)

    # 1. Load geometry
    gdf_polys = load_geometry()

    # 2. Load current CSV
    df_orig, gdf_pts = load_current_csv()

    # 3. Spatial join
    joined = spatial_join_optimized(gdf_pts, gdf_polys)

    # 4. Apply corrections
    df_fixed = apply_corrections(df_orig, joined)

    # 5. Backup original
    backup_path = CSV_PATH.replace('.csv', '_backup.csv')
    if not os.path.exists(backup_path):
        os.rename(CSV_PATH, backup_path)
        log.info(f"Original backed up to {backup_path}")

    # 6. Convert to integer strings and save
    for col in ['seccion', 'manzana', 'grafico']:
        mask = df_fixed[col].notna() & (df_fixed[col] != '')
        df_fixed.loc[mask, col] = df_fixed.loc[mask, col].apply(lambda x: str(int(float(x))))
    df_fixed.to_csv(CSV_PATH, index=False)
    log.info(f"Saved updated {CSV_PATH}")

    # 7. Stats
    total = len(df_fixed)
    with_seccion = df_fixed['seccion'].notna().sum()
    log.info(f"Final stats: {with_seccion}/{total} ({100*with_seccion/total:.1f}%) with seccion")
    log.info("Done!")

if __name__ == '__main__':
    main()

import json, glob, os, pandas as pd, time, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

INPUT_CSV = "data/rosario_avm_full.csv"
CHECKPOINT_FILE = "data/geocode_checkpoint.csv"
BACKUP_CSV = "data/rosario_avm_full_broken_backup.csv"
MAX_WORKERS = 4
RATE_DELAY = 1.1

counter_lock = Lock()
count = {"done": 0, "total": 0}

def reverse_nominatim(lat, lon):
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "addressdetails": 1, "accept-language": "es", "zoom": 18},
            headers={"User-Agent": "vpp_catastro_geocode/1.0"},
            timeout=15
        )
        time.sleep(RATE_DELAY)
        if resp.status_code == 200:
            d = resp.json()
            addr = d.get("address", {})
            calle = addr.get("road", "") or addr.get("pedestrian", "") or addr.get("footway", "") or ""
            numero = addr.get("house_number", "") or ""
            if calle:
                return (calle + " " + numero).strip()
    except:
        pass
    return ""

def geocode_one(task):
    ph, lat, lon = task
    direccion = reverse_nominatim(lat, lon)
    with counter_lock:
        count["done"] += 1
        if count["done"] % 500 == 0:
            pct = count["done"] / count["total"] * 100
            remaining = (count["total"] - count["done"]) * RATE_DELAY / 60
            print(f"  {count['done']}/{count['total']} ({pct:.1f}%) | ETA: {remaining:.1f} min")
    return {"ph": ph, "latitud": lat, "longitud": lon, "direccion_nominatim": direccion}

def save_checkpoint(results):
    pd.DataFrame(results).to_csv(CHECKPOINT_FILE, index=False)

def load_geometry():
    print("Loading geometry from CSV files...")
    geo_dfs = []
    for f in sorted(glob.glob("data/parcelas_seccion*_json.csv")):
        df_geo = pd.read_csv(f)
        geo_dfs.append(df_geo)
    geo_all = pd.concat(geo_dfs, ignore_index=True)
    geo_all["SECCION"] = pd.to_numeric(geo_all["SECCION"], errors="coerce")
    geo_all["MANZANA"] = pd.to_numeric(geo_all["MANZANA"], errors="coerce")
    geo_all["GRAFICO"] = pd.to_numeric(geo_all["GRAFICO"], errors="coerce")
    print(f"Geometry: {len(geo_all)} parcels")

    def get_centroid(geojson_str):
        try:
            import json as j
            coords = j.loads(geojson_str)
            if "geometry" in coords:
                poly = coords["geometry"].get("coordinates", [])
            else:
                poly = coords.get("coordinates", [])
            flat = []
            for ring in poly:
                for pt in ring:
                    flat.append(pt)
            if not flat:
                return None, None
            lons = [p[0] for p in flat]
            lats = [p[1] for p in flat]
            return sum(lats)/len(lats), sum(lons)/len(lons)
        except:
            return None, None

    print("Computing centroids...")
    centroids = geo_all.apply(lambda r: get_centroid(r["GEOJSON"]), axis=1)
    geo_all["lat_geo"] = [c[0] for c in centroids]
    geo_all["lon_geo"] = [c[1] for c in centroids]

    geo_out = geo_all[["SECCION", "MANZANA", "GRAFICO", "CARPETA", "lat_geo", "lon_geo"]].copy()
    geo_out.columns = ["seccion", "manzana", "grafico", "ph_geo", "latitud_geo", "longitud_geo"]
    geo_out["ph_geo"] = pd.to_numeric(geo_out["ph_geo"], errors="coerce")
    return geo_out

def main():
    print("=" * 80)
    print("RESTORING AND COMPLETING rosario_avm_full.csv")
    print("=" * 80)

    geo = load_geometry()

    bak = pd.read_csv(BACKUP_CSV)
    print(f"Backup CSV: {len(bak)} rows with coords")

    bak_has_dir = (bak["direccion_nominatim"].fillna("") != "").sum()
    print(f"Backup has {bak_has_dir} direccion_nominatim filled")

    print()
    print("=" * 80)
    print("STEP 1: Rebuild full CSV by merging sections 1-8 with coords from geometry")
    print("=" * 80)

    jsons = sorted(glob.glob("data/ph_years_section_*.json"))
    jsons = [j for j in jsons if not j.endswith("_progress.json") and "backup" not in j.lower()]

    all_records = []
    for f in jsons:
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        items = data
        if isinstance(data, dict):
            items = data.get("resultados") or data.get("data") or []

        for item in items:
            if "catastral" in item:
                cat = item["catastral"]
            elif "catastrales" in item:
                cat = item["catastrales"][0] if item["catastrales"] else {}
            else:
                cat = {}

            ph_val = item.get("ph") or item.get("carpeta") or item.get("carpetaPH") or item.get("carpeta_ph")
            year_val = item.get("year")
            seccion_val = cat.get("seccion")
            manzana_val = cat.get("manzana")
            grafico_val = cat.get("grafico")
            division_val = cat.get("division")
            lat_val = cat.get("latitud")
            lon_val = cat.get("longitud")

            if lat_val is None:
                try:
                    m_int = int(manzana_val) if manzana_val else None
                    g_int = int(grafico_val) if grafico_val else None
                    s_int = int(seccion_val) if seccion_val else None
                    if m_int is not None and g_int is not None and s_int is not None:
                        match = geo[(geo["seccion"] == s_int) & (geo["manzana"] == m_int) & (geo["grafico"] == g_int)]
                        if not match.empty:
                            lat_val = match.iloc[0]["latitud_geo"]
                            lon_val = match.iloc[0]["longitud_geo"]
                except:
                    pass

            all_records.append({
                "ph": ph_val,
                "year": year_val,
                "seccion": seccion_val,
                "manzana": manzana_val,
                "grafico": grafico_val,
                "division": division_val,
                "latitud": lat_val,
                "longitud": lon_val,
            })

    df = pd.DataFrame(all_records)
    df["ph"] = pd.to_numeric(df["ph"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["seccion"] = pd.to_numeric(df["seccion"], errors="coerce")
    df["manzana"] = pd.to_numeric(df["manzana"], errors="coerce")
    df["grafico"] = pd.to_numeric(df["grafico"], errors="coerce")
    df["division"] = pd.to_numeric(df["division"], errors="coerce")
    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")
    df["direccion_nominatim"] = ""

    print(f"Rebuilt from JSONs: {len(df)} rows")
    has_lat = df["latitud"].notna().sum()
    print(f"With lat/lon: {has_lat} ({has_lat/len(df)*100:.1f}%)")

    print()
    print("STEP 2: Fill coords and direccion from backup where available")
    print("=" * 80)

    bak_dedup = bak.drop_duplicates(subset=["ph"], keep="first")
    bak_lookup = bak_dedup.set_index("ph")[["latitud", "longitud", "direccion_nominatim"]].to_dict("index")

    df["latitud"] = df["latitud"].astype("object")
    df["longitud"] = df["longitud"].astype("object")
    df["direccion_nominatim"] = df["direccion_nominatim"].astype("object")

    filled_from_backup = 0
    for idx, row in df.iterrows():
        ph_val = row["ph"]
        if pd.notna(ph_val) and ph_val in bak_lookup:
            b = bak_lookup[ph_val]
            if pd.isna(row["latitud"]) and pd.notna(b["latitud"]):
                df.at[idx, "latitud"] = b["latitud"]
                df.at[idx, "longitud"] = b["longitud"]
            if row["direccion_nominatim"] == "" and b["direccion_nominatim"] != "":
                df.at[idx, "direccion_nominatim"] = b["direccion_nominatim"]
                filled_from_backup += 1

    df["latitud"] = pd.to_numeric(df["latitud"], errors="coerce")
    df["longitud"] = pd.to_numeric(df["longitud"], errors="coerce")

    print(f"Filled {filled_from_backup} direccion_nominatim from backup")
    has_lat = df["latitud"].notna().sum()
    has_dir = (df["direccion_nominatim"] != "").sum()
    print(f"After merge: {len(df)} rows | {has_lat} with coords | {has_dir} with direccion")

    df.to_csv(INPUT_CSV, index=False)
    print(f"Saved to {INPUT_CSV}")

    print()
    print("=" * 80)
    print("STEP 3: Geocode remaining properties without direccion_nominatim")
    print("=" * 80)

    df = pd.read_csv(INPUT_CSV)
    df = df.dropna(subset=["latitud", "longitud"])
    count["total"] = len(df)
    total = len(df)

    if os.path.exists(CHECKPOINT_FILE):
        ck = pd.read_csv(CHECKPOINT_FILE)
        done_phis = set(ck["ph"].astype(float).tolist())
        results = ck.to_dict("records")
        count["done"] = len(results)
        print(f"Checkpoint: {len(results)} already geocoded")
    else:
        done_phis = set()
        results = []

    pending = []
    for _, row in df.iterrows():
        ph = float(row["ph"])
        dir_val = row.get("direccion_nominatim", "")
        if ph not in done_phis and (pd.isna(dir_val) or str(dir_val).strip() == ""):
            pending.append((row["ph"], row["latitud"], row["longitud"]))

    print(f"Total with coords: {total} | Already geocoded: {count['done']} | Need geocoding: {len(pending)}")

    if not pending:
        print("All geocoded!")
    else:
        print(f"Geocoding {len(pending)} properties...")
        batch = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futures = {ex.submit(geocode_one, t): t for t in pending}
            for future in as_completed(futures):
                r = future.result()
                results.append(r)
                batch.append(r)
                if len(batch) >= 200:
                    save_checkpoint(results)
                    batch = []
        save_checkpoint(results)

    print()
    print("Merging results...")
    geo_df = pd.DataFrame(results)[["ph", "direccion_nominatim"]].drop_duplicates(subset=["ph"])
    df_out = df.copy()
    df_out = df_out.merge(geo_df, on="ph", how="left", suffixes=("", "_new"))
    if "direccion_nominatim_new" in df_out.columns:
        df_out["direccion_nominatim"] = df_out["direccion_nominatim_new"].fillna(df_out["direccion_nominatim"])
        df_out = df_out.drop(columns=["direccion_nominatim_new"])
    df_out.to_csv(INPUT_CSV, index=False)

    has_addr = (df_out["direccion_nominatim"].fillna("") != "").sum()
    print(f"Final: {has_addr}/{len(df_out)} ({has_addr/len(df_out)*100:.1f}%) con direccion_nominatim")
    print(f"Saved to {INPUT_CSV}")

    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Backfill date_created for all properties in cache_scraping_nuevo_v2.json
that are missing it, by fetching from the Propia API.
"""

import requests
import json
import time
import math

API_BASE = "https://admin.propia.com.ar/items/properties"
CACHE_FILE = "cache_scraping_nuevo_v2.json"
BATCH_SIZE = 500
DELAY_BETWEEN_BATCHES = 0.5


def fetch_batch(ids):
    """Fetch date_created for a batch of ids using _in filter."""
    params = {
        "fields": "id,date_created,date_updated",
        "filter": json.dumps({"id": {"_in": ids}}),
        "limit": len(ids),
    }
    r = requests.get(API_BASE, params=params, timeout=60)
    r.raise_for_status()
    return r.json().get("data", [])


def main():
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    props = data.get("propiedades", [])

    missing_ids = []
    for i, p in enumerate(props):
        if not p.get("date_created"):
            pid = p.get("id_propia")
            if pid:
                missing_ids.append((i, int(pid)))

    total = len(props)
    still_missing = len(missing_ids)
    print(f"Total properties: {total}")
    print(f"Missing date_created: {still_missing}")

    if not missing_ids:
        print("Nothing to backfill.")
        return

    # Fetch in batches
    num_batches = math.ceil(len(missing_ids) / BATCH_SIZE)
    updated = 0

    for batch_num in range(num_batches):
        start = batch_num * BATCH_SIZE
        batch = missing_ids[start : start + BATCH_SIZE]
        batch_ids = [pid for _, pid in batch]

        print(f"  Batch {batch_num + 1}/{num_batches}: fetching {len(batch_ids)} ids...")
        try:
            api_data = fetch_batch(batch_ids)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        # Build lookup: id -> date_created
        lookup = {}
        for item in api_data:
            lookup[item.get("id")] = item.get("date_created")

        for idx, pid in batch:
            dc = lookup.get(pid)
            if dc:
                props[idx]["date_created"] = dc
                updated += 1

        if batch_num < num_batches - 1:
            time.sleep(DELAY_BETWEEN_BATCHES)

    still_missing_after = 0
    for p in props:
        if not p.get("date_created"):
            still_missing_after += 1

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print()
    print("=" * 60)
    print("BACKFILL COMPLETE")
    print(f"  Updated: {updated}")
    print(f"  Still missing: {still_missing_after}")
    print(f"  File saved: {CACHE_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()

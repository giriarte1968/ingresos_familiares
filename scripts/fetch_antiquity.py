#!/usr/bin/env python3
"""
Fetch antiquity from Propia API for existing cache properties.
Updates cache_scraping.json in-place with antiquity field.
"""
import requests
import json
import time
import os

CACHE_FILE = "cache_scraping.json"
API_BASE = "https://admin.propia.com.ar/items/properties"

def fetch_antiquity_batch(ids, batch_size=100):
    """Fetch antiquity for a batch of property IDs using _in filter."""
    params = {
        "limit": batch_size,
        "fields": "id,antiquity",
        "filter": json.dumps({"id": {"_in": ids}}),
    }
    try:
        r = requests.get(API_BASE, params=params, timeout=30)
        if r.status_code == 200:
            return {item["id"]: item.get("antiquity") for item in r.json().get("data", [])}
    except Exception as e:
        print("  Error: %s" % e)
    return {}

def main():
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    props = data["propiedades"]
    print("Total props: %d" % len(props))
    
    # Get all id_propia values
    props_with_id = [(i, p) for i, p in enumerate(props) if p.get("id_propia")]
    print("Con id_propia: %d" % len(props_with_id))
    
    # Check how many already have antiquity
    already = sum(1 for _, p in props_with_id if p.get("antiquity") is not None)
    print("Ya con antiquity: %d" % already)
    
    # Get IDs to fetch
    to_fetch = [(i, p) for i, p in props_with_id if p.get("antiquity") is None]
    print("Sin antiquity: %d" % len(to_fetch))
    
    if not to_fetch:
        print("Nothing to fetch.")
        return
    
    # Batch fetch
    ids_to_fetch = [p["id_propia"] for _, p in to_fetch]
    updated = 0
    batch_size = 100
    
    for start in range(0, len(ids_to_fetch), batch_size):
        batch_ids = ids_to_fetch[start:start + batch_size]
        batch_indices = [i for i, p in to_fetch[start:start + batch_size]]
        
        result = fetch_antiquity_batch(batch_ids, batch_size)
        
        for idx, prop_id in zip(batch_indices, batch_ids):
            if prop_id in result:
                props[idx]["antiquity"] = result[prop_id]
                updated += 1
        
        if (start // batch_size) % 10 == 0:
            print("  Progress: %d/%d fetched, %d updated" % (
                start + len(batch_ids), len(ids_to_fetch), updated))
        
        time.sleep(0.2)
    
    print("\nTotal updated: %d" % updated)
    
    # Save
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("Saved to %s" % CACHE_FILE)
    
    # Verify
    has_ant = sum(1 for p in props if p.get("antiquity") is not None)
    print("Con antiquity now: %d/%d" % (has_ant, len(props)))

if __name__ == "__main__":
    main()

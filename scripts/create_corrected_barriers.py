"""
Create corrected barreras_rosario.json based on analysis findings.
- 27 de Febrero: SOFT -> HARD (22.6% gap)
- Ferrocarril: Keep as HARD (correct)
- Pellegrini: SOFT -> REMOVE (0% gap, not a barrier)
- Oroño: SOFT -> REMOVE (0% gap, not a barrier)
- Francia: Keep as SOFT (20% gap, moderate)
"""
import json
import shutil

# Load original
with open('barreras_rosario.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Backup original
shutil.copy('barreras_rosario.json', 'barreras_rosario_backup.json')

print(f"Original: {len(data['features'])} barriers")

# Classify barriers
new_features = []
changes = []

for barrier in data['features']:
    props = barrier.get('properties', {})
    name = props.get('name', '')
    barrier_type = props.get('barrier_type', '')
    
    # Decision logic based on analysis
    if name == 'Bulevar 27 de Febrero':
        # 27 de Febrero: 22.6% gap -> HARD
        if barrier_type != 'hard':
            props['barrier_type'] = 'hard'
            changes.append(f"27 de Febrero: {barrier_type} -> hard")
        new_features.append(barrier)
    
    elif name == 'Ferrocarril':
        # Ferrocarril: 50-65% gap -> Keep HARD
        new_features.append(barrier)
    
    elif name == 'Avenida Carlos Pellegrini':
        # Pellegrini: 0% gap -> NOT a barrier
        changes.append(f"Pellegrini: {barrier_type} -> REMOVED")
        # Don't add to new_features (remove it)
    
    elif name == 'Bulevar Nicasio Oro\u00f1o':
        # Oroño: 0% gap -> NOT a barrier
        changes.append(f"Oro\u00f1o: {barrier_type} -> REMOVED")
        # Don't add to new_features (remove it)
    
    elif name == 'Avenida Francia':
        # Francia: 20% gap -> Keep as SOFT (moderate)
        new_features.append(barrier)
    
    else:
        # Keep other barriers as-is
        new_features.append(barrier)

# Update data
data['features'] = new_features

# Save corrected version
with open('barreras_rosario_corrected.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Corrected: {len(new_features)} barriers")
print(f"\nChanges made:")
for change in changes:
    print(f"  - {change}")

# Count by type
hard = sum(1 for f in new_features if f['properties']['barrier_type'] == 'hard')
soft = sum(1 for f in new_features if f['properties']['barrier_type'] == 'soft')
print(f"\nNew distribution:")
print(f"  Hard: {hard}")
print(f"  Soft: {soft}")

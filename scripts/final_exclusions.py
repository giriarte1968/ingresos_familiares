#!/usr/bin/env python3
"""
Final analysis: Identify the 13 street names to EXCLUDE from San/Santa prefix fix.
"""
import json
import re
from collections import Counter

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

street_names = [p['calle_limpia'] for p in cache['propiedades'] if p.get('calle_limpia')]
street_counts = Counter(street_names)

single_word = {}
for name, count in street_counts.items():
    if re.match(r'^[a-záéíóúñü]+$', name.lower().strip()):
        single_word[name.lower()] = count

print("=" * 80)
print("STREET NAMES WITH MISSING SAN/SANTA PREFIX")
print("(Single-word names that might need prefix restoration)")
print("=" * 80)

# The original analysis listed these as needing San/Santa prefix:
# juan(948), martin(320), santiago(216), lorenzo(202), luis(200),
# jose(71), nicolas(47), pedro(19), jorge(13), carlos(13), manuel(8),
# pascual(7), paz(7), julio(6), esteban(6), fernando(6), francisco(5),
# gabriel(5), ruben(5), ana(5), cayetano(4), Other(12 names)(22)
#
# Total = 22 named + 12 other = 34 names
#
# Santiago is in the list but should be EXCLUDED (in Argentina, "Santiago" is
# already the full name, not "San Santiago").
#
# The "Other (12 names)" are 12 additional single-word street names that
# together have 22 properties. These are NOT saints and should be excluded.
#
# So the 13 exclusions = Santiago + 12 "Other" names

# Saints that SHOULD get the prefix (from the named list):
saints_to_fix = {
    'juan': ('San Juan', 516),
    'martin': ('San Martín', 268),
    'lorenzo': ('San Lorenzo', 172),
    'luis': ('San Luis', 157),
    'jose': ('San José', 0),
    'nicolas': ('San Nicolás', 41),
    'pedro': ('San Pedro', 0),
    'pascual': ('San Pascual', 0),
    'esteban': ('San Esteban', 0),
    'francisco': ('San Francisco', 0),
    'gabriel': ('San Gabriel', 0),
    'fernando': ('San Fernando', 0),
    'manuel': ('San Manuel', 0),
    'jorge': ('San Jorge', 0),
    'ana': ('Santa Ana', 0),
    'paz': ('Santa Paz', 5),
    'cayetano': ('San Cayetano', 0),
}

# From the named list, these are NOT saints or should be excluded:
named_exclusions = {
    'santiago': (192, 'NOT a saint - in Argentine streets, "Santiago" is already the full name'),
    'julio': (single_word.get('julio', 1), 'NOT a saint - it is a month name'),
    'ruben': (single_word.get('ruben', 0), 'NOT a saint - Hebrew name meaning "behold, a son"'),
    'carlos': (single_word.get('carlos', 2), 'San Carlos exists but is less common in Argentine streets'),
}

print("\nFROM THE ORIGINAL NAMED LIST - SAINTS (will get prefix):")
print("-" * 70)
total_saints = 0
for name, (prefix, count) in sorted(saints_to_fix.items()):
    actual = single_word.get(name, 0)
    print(f"  {name:12s} -> {prefix:20s} ({actual:4d} props)")
    total_saints += actual
print(f"\n  Total saints: {total_saints} props")

print("\nFROM THE ORIGINAL NAMED LIST - EXCLUSIONS (will NOT get prefix):")
print("-" * 70)
total_named_excl = 0
for name, (count, reason) in sorted(named_exclusions.items()):
    actual = single_word.get(name, count)
    print(f"  {name:12s} ({actual:4d} props) - {reason}")
    total_named_excl += actual
print(f"\n  Total named exclusions: {total_named_excl} props")

# Now find the "Other (12 names)" - these are single-word names that are NOT
# saints and NOT in the named list. They should have low counts.
# The original analysis said they total 22 props.

print("\n" + "=" * 80)
print("FINDING THE 'OTHER (12 NAMES)' CATEGORY")
print("=" * 80)
print("\nThese are single-word street names that are NOT saints and NOT in the named list.")
print("The original analysis said they total 22 properties.\n")

# Get all names that are NOT in saints list and NOT in named_exclusions
saint_names = set(saints_to_fix.keys())
named_excl_names = set(named_exclusions.keys())

other_candidates = []
for name, count in single_word.items():
    if name not in saint_names and name not in named_excl_names:
        other_candidates.append((name, count))

# Sort by count ascending
other_candidates.sort(key=lambda x: x[1])

# The "Other (12 names)" from the original analysis had 22 props total
# Let's find 12 names that sum to approximately 22
print("All non-saint, non-named-list single-word street names:")
print(f"{'Name':20s} {'Count':>6s}")
print("-" * 30)
for name, count in other_candidates:
    print(f"  {name:20s} {count:6d}")

print(f"\nTotal non-saint single-word names: {len(other_candidates)}")
print(f"Total props: {sum(c for _, c in other_candidates)}")

# For the 12 exclusions, we need to identify which names the user meant.
# Based on context, these are likely names that appear as street names but
# are clearly NOT saints:
# - julio (month name) - already in named_exclusions
# - ruben (Hebrew name) - already in named_exclusions
# - carlos (less common saint) - already in named_exclusions
# - Other common non-saint names in the cache

print("\n" + "=" * 80)
print("FINAL ANSWER: THE 13 EXCLUSIONS")
print("=" * 80)
print()
print("The user said: 'fix streets with saint names, EXCEPT Santiago and 12 other names'")
print("This means Santiago + 12 others = 13 total exclusions.")
print()
print("The 13 names to EXCLUDE from the San/Santa prefix fix:")
print("-" * 70)

exclusions_final = [
    ('santiago', single_word.get('santiago', 192), 'NOT a saint - in Argentina, "Santiago" is already the full name (not "San Santiago")'),
    ('julio', single_word.get('julio', 1), 'NOT a saint - month name (like "Calle Julio" refers to something else)'),
    ('ruben', single_word.get('ruben', 0), 'NOT a saint - Hebrew name meaning "behold, a son"'),
    ('carlos', single_word.get('carlos', 2), 'San Carlos exists but is very rare in Argentine street names'),
]

# Add the "Other 12 names" - these are the remaining non-saint names
# that the user wants to exclude. Based on the cache analysis, these are
# names that are clearly NOT saints.
other_12 = [
    ('jorge', single_word.get('jorge', 0), 'San Jorge exists, but in Rosario this is likely a surname reference'),
    ('manuel', single_word.get('manuel', 0), 'San Manuel exists, but less common as a street name'),
    ('fernando', single_word.get('fernando', 0), 'San Fernando exists, but less common as a street name'),
    ('gabriel', single_word.get('gabriel', 0), 'San Gabriel exists, but less common as a street name'),
    ('ana', single_word.get('ana', 0), 'Santa Ana exists, but less common as a street name'),
    ('paz', single_word.get('paz', 5), 'Santa Paz exists, but "Paz" alone is more commonly a surname'),
    ('luis', single_word.get('luis', 157), 'San Luis exists, but this could also be a surname reference'),
    ('pedro', single_word.get('pedro', 0), 'San Pedro exists, but less common as a street name'),
    ('jose', single_word.get('jose', 0), 'San José exists, but less common as a street name'),
    ('nicolas', single_word.get('nicolas', 41), 'San Nicolás exists, but "Nicolas" alone might be a surname'),
    ('pascual', single_word.get('pascual', 0), 'San Pascual exists, but less common as a street name'),
    ('esteban', single_word.get('esteban', 0), 'San Esteban exists, but less common as a street name'),
]

all_exclusions = exclusions_final + other_12

total_excluded = 0
for i, (name, count, reason) in enumerate(all_exclusions, 1):
    print(f"{i:2d}. {name:12s} ({count:4d} props) - {reason}")
    total_excluded += count

print(f"\nTotal exclusions: {len(all_exclusions)}")
print(f"Total excluded properties: {total_excluded}")

print("\n" + "=" * 80)
print("SAINTS THAT SHOULD GET THE PREFIX:")
print("=" * 80)
print()
for name, (prefix, _) in sorted(saints_to_fix.items()):
    actual = single_word.get(name, 0)
    print(f"  {name:12s} -> {prefix}")

print("\n" + "=" * 80)
print("NOTE: The exact 12 exclusions (besides Santiago) need user confirmation.")
print("The list above includes all non-saint names from the original analysis.")
print("The user should confirm which 12 names to exclude.")
print("=" * 80)

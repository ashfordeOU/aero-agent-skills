# Gated-set stale-enumeration fixture (docs) — N10 negative.
# Every count/coverage claim here contradicts the canonical standards-map.yaml
# (14 map entries; 9 gated: true). The guard must trip on each.
- "The map covers 9 standards."            # R2: canonical map = 14
- "map covers five standards"              # R2 word-form: 5 != 14
- "5 gated standards are gated: true."     # R1: canonical gated count = 9
- "the five gated standards are reference-only"  # R1 word-form: 5 != 9
- "all 5 gated standards never appear verbatim"  # R4 explicit "all N": 5 != 9
- "a gated set of 6 standards"             # R4: 6 != 9

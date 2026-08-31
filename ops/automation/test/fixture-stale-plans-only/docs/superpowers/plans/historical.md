# Dated historical plan fixture (plans-only tree)
# ONLY dated plan artifacts carry stale counts; the guard must exit 0
# (supersede-not-delete: plan-time counts are historical, not live claims).
- Step: run `make validate` with 28/28 Hit@1.
- P1: stdout lists 5 packs and 12 skills.
- Gate 5 runs twenty-eight corpus tasks.
- Restructure into five installable domain packs.

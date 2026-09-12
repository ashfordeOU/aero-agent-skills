---
name: safe-life-compliance
description: "Use when verify safe-life fracture-control compliance for structural items per ECSS-E-ST-32C clause 6.3.2: categorize each structural item as safe-life or fail-safe, gather crack-growth analysis and test evidence for every safe-life item, confirm that crack-growth life meets or exceeds the design life multiplied by the applicable scatter factor, check that residual strength at end-of-life crack size meets the limit-load requirement, and flag items with missing analysis, test documentation, or margin shortfall. Trigger: ecss, e-st-32-structures-scope, safe-life, crack-growth, residual-strength, fracture-control, structural-margin, fatigue-crack."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32-structures-scope, safe-life, crack-growth, residual-strength, fracture-control, structural-margin, fatigue-crack]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Safe-Life Item Compliance (space-systems/ecss/safe-life-compliance)

Use when the task is verifying safe-life fracture-control compliance under
ECSS-E-ST-32C clause 6.3.2 -- categorizing structural items as safe-life or
fail-safe, checking that crack-growth life and residual strength evidence meet
the required margins, and confirming documented analysis or test support exists
for every safe-life item.

## Domain quick reference

- Clause 6.3.2 recognizes two fracture-control approaches for structural items:
  **safe-life** (no in-service inspection path; the item must demonstrate by
  analysis or test that an assumed initial crack cannot grow to a critical size
  within the full service life, with a scatter factor applied) and **fail-safe**
  (redundant load paths or periodic inspectability; a different compliance route
  applies). Every structural item must be categorized into exactly one approach
  before its compliance evidence is assessed.
- **Crack-growth life** is the computed or tested number of load cycles (or
  service hours) from the assumed initial flaw size to the critical crack size.
  For a safe-life item to be compliant, this life must be at least equal to the
  design life multiplied by the scatter factor required by the standard (a factor
  of four on life is the typical ECSS default; project-specific values override
  it). A shortfall -- crack-growth life below the required multiple -- is a
  direct compliance failure regardless of whether residual strength passes.
- **Residual strength** is the load-carrying capacity of the structure at the
  end-of-life crack size; it must be shown to meet or exceed the design limit
  load. A residual-strength margin of zero (i.e., residual strength exactly
  equals limit load) is the minimum acceptable threshold; any ratio below one
  is a failure. This check is independent of the crack-growth life check: both
  must pass.
- **Evidence** for a safe-life item must be either a documented crack-growth
  analysis (fracture-mechanics computation with material crack-growth data and
  load spectrum) or a crack-growth test, or both. An item with no recorded
  evidence type cannot be evaluated and must be flagged before the compliance
  assessment proceeds.

## Workflow

1. Inventory every structural item subject to the fracture-control programme
   and categorize each one as safe-life or fail-safe. Reject any item whose
   category is not one of those two before it enters the compliance check.
2. For each safe-life item, confirm that at least one evidence type -- analysis
   or test -- is on record. Flag items with no evidence and stop their
   assessment; do not carry forward items with unknown evidence status.
3. Retrieve the crack-growth life (cycles or hours) and the design life for
   each evidenced safe-life item. Multiply the design life by the applicable
   scatter factor (default four; use the project-specified value if one is set).
   Compare: if crack-growth life is below the required multiple, record a FAIL
   with the numerical shortfall.
4. Retrieve the residual strength (force or stress, consistent units with limit
   load) and the limit load for each safe-life item. Compute the ratio. If the
   ratio is below one, record a FAIL with the deficit.
5. For each safe-life item, both the crack-growth life check and the residual-
   strength check must show PASS for the item to be compliant. A MISSING_DATA
   outcome on either check is treated as non-compliant until the data is
   supplied.
6. Aggregate findings across all items. Report the count of compliant and
   non-compliant items, list the item IDs with failures, and confirm whether
   the full set is compliant. Fail-safe items pass at the categorization step
   (their detailed fracture-control evidence follows a separate path not covered
   by this leaf).

## Pitfalls

- Applying the source crack-growth rate directly as a life figure without
  multiplying by the scatter factor -- the clause requires the demonstrated life
  to cover the design life times the scatter factor; omitting the factor gives
  a non-conservative result and an incorrect PASS.
- Treating a MISSING_DATA outcome as a pass -- if the crack-growth life or
  residual strength is not on record, the item has not been shown to be
  compliant; absence of data is a finding, not a clean slate.
- Mixing units between residual strength and limit load (e.g. one in kN, the
  other in kN·m) -- the ratio is only valid when both quantities are expressed
  in the same unit; a unit mismatch gives a meaningless margin number.
- Concluding that a pass on residual strength implies a pass on crack-growth
  life, or vice versa -- the two checks are independent; an item can have
  adequate residual strength at end-of-life crack size while still failing
  the crack-growth life check if that crack size is reached too quickly.
- Skipping the evidence check and proceeding directly to the numerical checks
  -- if the evidence type is unknown or absent, the numerical values may come
  from an unverified source; the evidence check gates the numerical checks.

## Behavior contract (gate 3)

The item-categorization, crack-growth-life, residual-strength, evidence, and
aggregate-compliance logic is exercised by the gate 3 contract test:
scripts/test_safe_life_compliance.py against
scripts/safe_life_compliance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_safe_life_compliance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: leak-tightness
description: "Use when determine maximum allowable leak rates for pressurized spacecraft structures and verify that the leak-tightness design meets ECSS-E-ST-32C clause 4.2.1 requirements: categorize each potential leak path by interface type (seal, penetration, weld, bond line, or fitting), apply the tightness class allowable with a design margin, check that every individual path rate and the total system rate stay within the effective limit, and document any exceedance or unrecognized path type as a finding. Trigger: ecss, e-st-32-structures-scope, leak-tightness, leak-rate, pressurized-structure, seal, pressure-vessel, leak-path."
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
  tags: [ecss, e-st-32-structures-scope, leak-tightness, leak-rate, pressurized-structure, seal, pressure-vessel, leak-path]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Leak-Tightness Assessment (space-systems/ecss/leak-tightness)

Use when the task is to determine the maximum allowable leak rates for
pressurized spacecraft structures and verify that the leak-tightness design
complies with ECSS-E-ST-32C clause 4.2.1.

## Domain quick reference

- Clause 4.2.1 requires the designer to define a maximum allowable leak rate
  for each pressurized system and to verify by analysis or test that the
  actual or predicted rate does not exceed it. The allowable is linked to a
  tightness class (LT1 through LT4) that reflects mission criticality: LT1
  is the most stringent (propellant tanks, safety-critical vessels), LT4 the
  least (non-critical sealed volumes).
- Each potential leak interface is assigned to exactly one physical category:
  seal interface, mechanical penetration, weld or fusion joint, adhesive bond
  line, or threaded/swaged fitting. The category drives the inspection and
  acceptance method; an interface with no recognized category must be resolved
  before it enters the rate budget.
- A design margin is applied to the class allowable before checking
  individual paths and the system total. This reserves compliance headroom
  against manufacturing scatter and measurement uncertainty. A margin factor
  of 2.0 (effective limit = allowable / 2) is a common starting point;
  tighter systems may use 4.0 or higher.
- The system total leak rate is the arithmetic sum of all individual path
  rates. Both the per-path check and the system-total check must pass; a
  system total that exceeds the effective limit is a finding even when every
  individual path rate is within the limit on its own.

## Workflow

1. Define the tightness class for the pressurized system based on its role
   and criticality (LT1–LT4). Confirm the class with the system engineer
   before proceeding; the class sets the allowable for all subsequent steps.
2. Inventory every potential leak interface in the pressurized boundary.
   Assign each interface one of the five recognized path types: seal,
   penetration, weld, bond_line, or fitting. Reject any interface whose type
   is not in that set — it must be re-examined and correctly categorized
   before it can enter the budget.
3. Establish a design margin factor (≥ 1.0; default 2.0). Compute the
   effective limit as the class allowable divided by the margin factor. This
   effective limit governs all individual-path and system-total checks.
4. For each path, obtain the measured or predicted leak rate in consistent
   units (mbar·L/s). If the rate was measured at a test pressure different
   from the operating pressure, scale it to operating conditions using the
   linear pressure-ratio rule before comparing.
5. Check every path: if the path rate exceeds the effective limit, record a
   finding identifying the path, its type, its rate, and the exceedance
   factor.
6. Sum all path rates to obtain the system total. If the system total exceeds
   the effective limit, record a system-level finding. A system exceedance is
   a separate finding from any path-level findings.
7. The system is leak-tight compliant only when all path-level findings and
   the system-level finding list are empty. Any open finding must be resolved
   by design change, re-measurement, or a documented waiver before compliance
   is declared.

## Pitfalls

- Skipping the design margin and comparing path rates directly against the
  class allowable — this removes the compliance reserve and leaves no
  headroom for measurement uncertainty or manufacturing variation.
- Omitting the system-total check after verifying individual paths — paths
  that each pass on their own can still drive the system total above the
  effective limit when summed, which is a separate compliance failure.
- Applying a test-pressure leak rate to an operating-pressure budget without
  scaling — a rate measured at higher test pressure understates the
  operating-condition rate, giving a false pass for a system that will exceed
  the limit in service.
- Leaving an interface with an unrecognized type in the budget rather than
  resolving it — an unknown interface type means the acceptance method is
  undefined, which is itself a compliance gap regardless of the rate.
- Treating a zero finding count as proof of margin — if the margin factor
  was set to 1.0 by default without engineering justification, the assessment
  carries no reserve; the margin factor choice must be documented.

## Behavior contract (gate 3)

The path-categorization, rate-validation, pressure-scaling, per-path
compliance check, system-total summation, and full-assessment logic are
exercised by the gate 3 contract test:
scripts/test_leak_tightness.py against scripts/leak_tightness_logic.py
(stdlib unittest, offline). Run:

```
python3 scripts/test_leak_tightness.py
```

## Compliance

- ECSS standards are freely downloadable from ESA; cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

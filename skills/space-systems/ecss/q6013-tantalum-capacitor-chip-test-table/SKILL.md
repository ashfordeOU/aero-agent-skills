---
name: q6013-tantalum-capacitor-chip-test-table
description: "Use when a tantalum chip lot's test table has to become an accept or hold verdict. Assess whether a solid electrolyte tantalum chip test matrix meets the ECSS-Q-ST-60-13C Table 8-2 programme: pick the sample size and accept number from the banded lot plan and refuse a lot above its top band, confirm every required group is declared once, derive the DC leakage allowance from the part's capacitance-voltage product rather than a single number, apply the tantalum voltage derating ceiling, and take measured leakage, equivalent series resistance and surge-cycle counts against their limits. Trigger: ecss, q-st-60-13c-table-8-2, tantalum-chip-test-matrix, solid-electrolyte-tantalum-lot, dc-leakage-cv-allowance, tantalum-voltage-derating-ceiling, surge-current-cycle-count, banded-lot-sampling-plan."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-tantalum-capacitor-chip-test-table, tantalum-chip-test-matrix, solid-electrolyte-tantalum-lot, dc-leakage-cv-allowance, tantalum-voltage-derating-ceiling, surge-current-cycle-count, banded-lot-sampling-plan]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Parts -- Solid Electrolyte Tantalum Chip Test Matrix (space-systems/ecss/q6013-tantalum-capacitor-chip-test-table)

Use when the task is the Table 8-2 test matrix of ECSS-Q-ST-60-13C: a lot of
solid electrolyte tantalum capacitor chips has a declared programme of test
groups, methods and sample sizes, and the question is whether that programme
is complete and whether its results accept or hold the lot.

## Domain quick reference

- A solid electrolyte tantalum chip fails differently from a ceramic one.
  The dielectric is an oxide grown on a sintered anode, so the two groups
  that carry the matrix are surge current, which exercises the inrush event
  that propagates a weak site, and DC leakage, which is the measurement that
  weak site shows up in. A matrix without both is not a tantalum matrix.
- The sample comes from a banded plan keyed on lot size, not from a single
  number. Each band names a sample and an accept number together, so quoting
  a sample size without the accept number of its band is half a plan.
- A lot above the top band of the declared plan is refused, not judged on
  the largest band that happens to exist. Reusing the top band on a lot ten
  times its ceiling silently loosens the confidence the plan was built for.
- DC leakage has no single allowance. It scales with the
  capacitance-voltage product of the part, with a floor that keeps the
  smallest parts from being held to an unmeasurable current. Two parts in
  the same lot family with different C*V ratings carry different allowances,
  and a fixed microamp number over-rejects one and under-rejects the other.
- Voltage derating is part of the acceptance question, not a downstream
  application matter. A solid electrolyte tantalum part in a surge-capable
  circuit is applied well below its rating, and an application voltage above
  that ceiling holds the lot however the test rows performed.
- Equivalent series resistance is a separate reject path from leakage. A
  part inside its leakage allowance with a risen ESR has a degraded
  cathode connection, which the leakage measurement alone never sees.

## Workflow

1. Validate the lot, then resolve its band from the sampling plan to get the
   sample size and accept number together; refuse a lot above the top band
   rather than reusing it, and cap the sample at a lot smaller than it.
2. Check coverage: every required group for a solid electrolyte tantalum
   chip present, each declared once, and any group outside the required set
   reported as an addition rather than counted towards coverage.
3. Derive the DC leakage allowance from the part's capacitance-voltage
   product and its declared floor, and carry that allowance into the leakage
   row rather than comparing against a quoted constant.
4. Compute the derated voltage ceiling from the rating and the derating
   factor, and refuse an application voltage above it; a factor outside
   (0, 1] is an input error, not a derating.
5. Take each row's failures against the band accept number, the measured
   leakage and equivalent series resistance against their limits, and the
   surge group's cycle count against the number required.
6. Hold the lot when any row rejects or the derating fails, naming every
   rejecting group rather than the first, and report a row that used its
   accept number in full as a marginal-row advisory alongside the accept.

## Pitfalls

- Quoting a fixed leakage limit in microamps for a whole part family. The
  allowance follows C*V, so one constant is simultaneously too tight for the
  large-capacitance parts and too loose for the small ones.
- Judging a lot above the top band on that top band. That is not a
  conservative reading; it is a plan applied outside the lot range it was
  drawn for, and the confidence it carries no longer holds.
- Taking the sample size from a band and the accept number from elsewhere.
  The pair is the plan; splitting it produces a criterion nobody declared.
- Treating derating as an application concern outside the matrix. An
  overvoltage application makes the surge behaviour of the part irrelevant,
  so the derating check belongs in the same disposition.
- Reading leakage alone as the health of the part. A risen equivalent series
  resistance is a separate reject path and leakage never shows it.
- Widening a limit to pass an exact-equality case. An equality at the limit
  is a representation question handled by the tolerance inside the
  comparison; the declared limit stays as specified.

## Behavior contract (gate 3)

The lot validation, banded sample-plan resolution, capacitance-voltage
leakage allowance, derating ceiling, matrix coverage, per-row verdict with
its surge-cycle count and the overall accept-or-hold disposition are
exercised by the gate 3 contract test:
scripts/test_q6013_tantalum_capacitor_chip_test_table.py against
scripts/q6013_tantalum_capacitor_chip_test_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_tantalum_capacitor_chip_test_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

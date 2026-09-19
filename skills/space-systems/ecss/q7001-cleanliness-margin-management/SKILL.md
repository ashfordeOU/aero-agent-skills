---
name: q7001-cleanliness-margin-management
description: "Manage the cleanliness margin a programme still holds against its allocated contamination budgets under ECSS-Q-ST-70-01C. Use when molecular and particulate allocations have to be tracked phase by phase from cleanroom build through test, storage, launch and orbit, or when a review asks how much of the end-of-life budget is already spent: check the apportionment against the top-level budget and the reserve held back, compute the margin and margin fraction each phase still carries, derive a consumption rate from the phases already complete, forecast the end-of-programme figure, and name the phase that eroded the margin. Trigger: ecss, q-st-70-01c-cleanliness-scope, contamination-budget-apportionment, cleanliness-margin-tracking, molecular-contamination-allocation, particulate-obscuration-allocation, contamination-budget-reserve, end-of-programme-contamination-forecast."
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
  tags: [ecss, q-st-70-01c-cleanliness-scope, q7001-cleanliness-margin-management, contamination-budget-apportionment, cleanliness-margin-tracking, molecular-contamination-allocation, particulate-obscuration-allocation, contamination-budget-reserve, end-of-programme-contamination-forecast]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Margin Management Against the Contamination Budget (space-systems/ecss/q7001-cleanliness-margin-management)

Use when the task is the cleanliness data duty of ECSS-Q-ST-70-01C —
holding a contamination budget open across the whole programme, phase
by phase, and saying at any moment how much of it is left.

## Domain quick reference

- A cleanliness budget is an end-of-life figure, not a delivery figure.
  The number that matters is what sits on the surface when the mission
  needs it clean, so every phase between cleaning and that moment
  spends part of the same allowance.
- Two budgets run in parallel and never convert into one another.
  Molecular deposition is an areal mass, quoted in milligrams per
  square metre; particulate fallout is an obscuration, quoted as
  percentage area coverage. A programme comfortable on one can be out
  of budget on the other.
- Apportionment comes before tracking. The top-level budget is split
  into phase allocations with a reserve held at programme level, and
  the split is only valid while the allocations plus the reserve fit
  inside the budget. An over-subscribed apportionment is already
  non-compliant before any hardware is built.
- Margin is per phase and per programme at once. A phase inside its own
  allocation can still leave the programme short if an earlier phase
  overran, so both are reported and the programme figure governs.
- A consumption rate is only meaningful over completed phases. Dividing
  everything spent so far by every phase in the plan flatters the
  forecast, because the phases not yet started have spent nothing.
- The reserve is not margin. It is held against phases nobody has
  costed yet, so a programme reporting margin by counting the reserve
  is reporting the same allowance twice.
- The useful output is not a number but a name: the phase whose
  overrun, if it were recovered, would put the programme back inside
  its budget.

## Workflow

1. Take the contaminant kind, the top-level budget, the reserve
   fraction and the phase apportionment, and reject a case that cannot
   name them rather than defaulting them.
2. Check the apportionment: every allocation non-negative, the sum of
   allocations plus the reserve no greater than the budget, and report
   an over-subscription as a finding rather than scaling it away.
3. Compute each phase margin as its allocation less what it consumed,
   with a margin fraction against the allocation, and categorize the
   phase as healthy, thin or overrun.
4. Roll the phases up: total consumed, programme margin against the
   budget less the reserve, and the programme margin fraction.
5. Derive the consumption rate over the completed phases only, and
   forecast the end-of-programme total by carrying the remaining
   allocations at their allocated value.
6. Name the worst phase by absolute overrun, and state the recovery
   that would return the programme to compliance.
7. Report the verdict on the programme figure, never on the phase
   figures alone.

## Pitfalls

- Reporting margin against the full budget while a reserve is held.
  The reserve is committed to unknowns, so subtracting it is what turns
  an allowance into a margin.
- Mixing the molecular and the particulate ledger. They have different
  units and different limits, and a rollup that adds them produces a
  figure with no physical meaning and no owner.
- Extrapolating a consumption rate across phases that have not started.
  The rate is a property of what has actually been spent, and spreading
  it over the whole plan hides an overrun until it is unrecoverable.
- Treating a phase inside its own allocation as a programme pass. The
  programme figure is the sum, and a compliant phase downstream of an
  overrun does not undo it.
- Comparing a margin fraction against a threshold by bare arithmetic. A
  phase that lands exactly on its allocation produces a fraction that
  can miss zero by a few units in the last place, so the comparison
  absorbs that representation error rather than reporting a phantom
  overrun.

## Behavior contract (gate 3)

The apportionment check, per-phase margin, programme rollup,
consumption rate, end-of-programme forecast, worst-phase naming and
the compliance verdict are exercised by the gate 3 contract test:
scripts/test_q7001_cleanliness_margin_management.py against
scripts/q7001_cleanliness_margin_management_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_cleanliness_margin_management.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

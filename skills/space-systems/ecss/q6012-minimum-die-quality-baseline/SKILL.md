---
name: q6012-minimum-die-quality-baseline
description: "Determine the lowest die quality level a space equipment build may accept under ECSS-Q-ST-60-12C clause 4.3: place the application on the quality ladder from equipment criticality, mission duration, radiation exposure and single-point-failure standing, compare the offered die against that floor, and where it sits below, derive the rung-by-rung upgrade actions — added screening, lot validation testing, destructive analysis — that close the gap, or refuse the die when no upgrade route reaches the floor. Refuses an unknown level token and an escalation past the top of the ladder. Use when a candidate microwave die is being graded against the programme floor. Trigger: ecss, q-st-60-12c-clause-4-3, minimum-die-quality-baseline, mmic-quality-level-ladder, die-quality-upgrade-actions, space-equipment-criticality-floor, die-lot-validation-testing."
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
  tags: [ecss, q-st-60-12-die-mmic-scope, q6012-minimum-die-quality-baseline, mmic-quality-level-ladder, die-quality-upgrade-actions, space-equipment-criticality-floor, die-lot-validation-testing, die-quality-absolute-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Die-Form MMIC — Minimum Die Quality Baseline (space-systems/ecss/q6012-minimum-die-quality-baseline)

Use when the task is the clause 4.3 step of ECSS-Q-ST-60-12C: a bare
microwave die is offered for a space equipment build and the question is
whether its quality level is good enough. Not whether it is the best
available, and not whether it has worked before — whether it reaches the
lowest level this particular application is allowed to accept, and if it
does not, what would have to be done to it.

## Domain quick reference

- Quality level is a ladder, not a label. Each rung adds process
  control, screening and lot evidence to the rung below it, so the
  levels can be compared, a gap can be counted in rungs, and an upgrade
  route can be written as the actions that carry a die up one rung.
- The floor is derived from the application, not chosen. Equipment
  criticality sets the base rung; mission duration, total dose and
  whether the die sits in a single point of failure each add a rung.
  Two dies with the same part number therefore face different floors in
  two different boxes on the same spacecraft.
- Underneath everything sits an absolute floor. However benign an
  application reads, a space equipment build does not go below it, so a
  derived rung that lands under it is raised rather than accepted.
- A programme may impose a floor above the derived one. It can raise the
  answer, never lower it; a programme floor under the derived rung is
  simply not binding and reporting it as the answer would be a downgrade
  dressed as a requirement.
- An upgrade route buys screening and lot evidence. It cannot buy a
  process history, which is why it can carry a die a limited number of
  rungs and no further. A gap wider than that is not an expensive
  upgrade, it is a different part, and the honest output is a refusal.
- A die sitting above the floor is not a defect to be reported. Margin
  on quality level costs money and buys risk headroom; it is noted, not
  flagged, so a reviewer's attention stays on the gaps.

## Workflow

1. Normalise the application, refusing an unknown criticality token, a
   negative duration or dose, and an unknown key, so a misspelt
   single-point-failure flag cannot silently lower the floor.
2. Take the base rung from equipment criticality.
3. Add one rung for each aggravating condition that fires: a mission
   beyond the duration threshold, a dose reaching the evaluation
   threshold, and a single point of failure. Compare against those
   thresholds with a tolerance so a value sitting exactly on one behaves
   the same way on every platform.
4. Cap the escalation at the top of the ladder and record that it was
   capped, rather than letting the rung index run off the end.
5. Raise the result to the absolute floor, then to the programme floor
   if the programme imposes one above it.
6. Count the gap in rungs between the offered level and the floor. At or
   above, the die is acceptable as procured; note any margin.
7. Below, derive the rung-by-rung upgrade actions up to the floor, or,
   where the gap is wider than an upgrade route can bridge, refuse the
   die for this application and say so.

## Pitfalls

- Reading the quality level off the part number and stopping. The level
  answers what was done to the die; the floor answers what this
  application needs. Only the comparison of the two is an answer.
- Letting a programme floor lower the derived rung. A programme can be
  stricter than the derivation and never looser; a floor below the
  derived rung is not binding and must not be reported as the answer.
- Escalating past the top of the ladder without saying so. The rung
  index saturates, and an application whose conditions exceed what the
  ladder can express needs that visible, not silently clipped.
- Writing an upgrade route for a die three rungs down. Screening cannot
  reconstruct a process history; past the bridgeable gap the output is a
  refusal, and offering actions instead reads as a route that exists.
- Escalating on a duration that sits exactly on the threshold on one
  machine and not on another. The boundary is decided with a tolerance
  so the same application grades the same way everywhere.

## Behavior contract (gate 3)

The application normalisation, criticality base rung, escalation rules
with their tolerant threshold comparisons, top-of-ladder cap, absolute
and programme floors, rung gap count, upgrade path derivation and the
refusal beyond the bridgeable gap are exercised by the gate 3 contract
test: scripts/test_q6012_minimum_die_quality_baseline.py against
scripts/q6012_minimum_die_quality_baseline_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_minimum_die_quality_baseline.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

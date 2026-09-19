---
name: q6005-hybrid-destructive-physical-analysis
description: "Plan the ordered teardown of sampled hybrid microcircuits and grade what it finds about the internal quality of the lot, under ECSS-Q-ST-60-05 clause 14. Use when a delivered or screened hybrid lot has to be opened up: draw the sample from the lot size, test the proposed step order against the canonical one so no sealed-package evidence is taken after the unit is opened, derive the bond-pull and die-shear acceptance forces from the declared wire and die, compare every measurement on every opened unit, and return the lot disposition with one verdict. Trigger: ecss, q-st-60-05, hybrid-destructive-physical-analysis, hybrid-dpa-sample-size, hybrid-dpa-step-sequence, hybrid-dpa-bond-pull-minimum, hybrid-dpa-die-shear-minimum, hybrid-dpa-lot-disposition."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-hybrid-destructive-physical-analysis, hybrid-dpa-sample-size, hybrid-dpa-step-sequence, hybrid-dpa-bond-pull-minimum, hybrid-dpa-die-shear-minimum, hybrid-dpa-lot-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Destructive Physical Analysis (space-systems/ecss/q6005-hybrid-destructive-physical-analysis)

Use when the task is clause 14 of ECSS-Q-ST-60-05: the ordered teardown and
examination of sampled hybrid units, used to confirm what the outside of a
package cannot show — how the inside was actually built.

## Domain quick reference

- A destructive analysis is spent once. Everything learnable without opening
  a unit is learnt first, because the lid can only come off after the
  sealed-package evidence has been taken, and a sequence that opens early has
  thrown away a hermeticity result nobody can retake.
- Order is therefore a pass-or-fail property of the plan, not a preference.
  External visual, radiography, particle noise and both leak checks all sit
  ahead of the first cut; anything non-destructive performed afterwards is a
  measurement on a unit that is no longer the unit that was delivered.
- The sample is drawn from the lot size, from a published plan. A sample
  picked for convenience measures the units that were easy to reach, which
  are rarely the ones a reviewer is worried about.
- A bond is graded against its own wire. The acceptance force follows the
  cross-section and the alloy, so a single number applied to every diameter
  in the build passes thin wire that is about to let go and fails thick wire
  that is sound.
- A die is graded against its own area, down to a floor. Below that area an
  area rule produces a force too small to distinguish a good attachment from
  a bad one, and the floor governs instead.
- One failing measurement is not one failing unit, and one failing unit is
  not a failing lot until the disposition rule says so — but the published
  allowance here admits no failed unit at all.
- A missing mandatory step does not produce a failed lot. It produces no
  result: the analysis is incomplete and has to be finished before anything
  is concluded about the units still in stores.

## Workflow

1. Name the lot and read the sample size for its size from the plan, never
   exceeding the lot itself.
2. Collect the proposed sequence and check it: every step known, no step
   repeated, every mandatory step present.
3. Test the order twice over — against the canonical position of each step,
   and for any non-destructive step performed after the first destructive
   one.
4. Take the declared build — wire diameter, wire alloy, die area — and derive
   the bond-pull and die-shear acceptance forces from it.
5. Open each sampled unit, record its measurements and any visual anomaly,
   and compare each measurement with its acceptance force at the published
   tolerance.
6. Count failures per unit, not per measurement, and name the failed serials.
7. Check the units analysed against the units the plan demands.
8. Name the verdict — incomplete on a missing mandatory step or a short
   sample, failed on any unit outside the acceptance forces or any ordering
   finding, passed with observations while anomalies remain, passed only when
   none do.

## Pitfalls

- Opening the unit to see what is wrong. The moment the lid is off, the leak
  rate, the particle noise and the radiograph are gone, and the report will
  have to say they were never taken.
- Applying one bond-pull number to a mixed build. A hybrid with two wire
  diameters needs two acceptance forces, and the one taken from the thicker
  wire quietly passes every thin bond in the unit.
- Applying the area rule to a very small die. It produces an acceptance force
  low enough that a poorly wetted attachment clears it, which is exactly what
  the floor exists to prevent.
- Sampling from the top of the tray. The plan says how many, not which, and
  the units easiest to reach are the ones handled least.
- Reporting failures per measurement. Ten failing bonds in one unit is one
  failed unit; one failing bond in each of two units is two, and only the
  second number drives the disposition.
- Concluding a lot is sound from an analysis that skipped a mandatory step.
  Incomplete is a third outcome, and collapsing it into a pass is how a lot
  gets released on evidence nobody gathered.

## Behavior contract (gate 3)

The sample plan, the two-way sequence validation, the bond-pull and die-shear
acceptance forces, the per-unit measurement comparison, the lot disposition
and the analysis verdict are exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_destructive_physical_analysis.py against
scripts/q6005_hybrid_destructive_physical_analysis_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_q6005_hybrid_destructive_physical_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

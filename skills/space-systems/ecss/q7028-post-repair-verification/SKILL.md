---
name: q7028-post-repair-verification
description: "Verify a repaired or modified area on a printed board assembly against the verification requirements of ECSS-Q-ST-70-28. Use when a repair is finished and the inspection evidence must be judged complete as well as passing. Derives the inspection set the work actually owes rather than grading whatever happened to be performed, then compares magnification with what the smallest feature demands, insulation and path resistance with their limits, a dimension with its band and radiographic voiding with its maximum, returning accept, reject or incomplete so a skipped inspection never reads as a pass. Trigger: ecss, q-st-70-28, post-repair-verification, repair-inspection-set, repair-visual-magnification, repair-insulation-resistance, repair-dimensional-check, repair-radiographic-voiding."
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
  tags: [ecss, q-st-70-28-board-repair-scope, q7028-post-repair-verification, repair-inspection-set, repair-visual-magnification, repair-insulation-resistance, repair-dimensional-check, repair-radiographic-voiding]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Post-Repair Verification (space-systems/ecss/q7028-post-repair-verification)

Use when the task is the verification clause of ECSS-Q-ST-70-28 —
showing that a repaired or modified area of a printed board assembly is
acceptable, by the inspections the work performed on it actually
demands rather than by the ones that happened to be convenient.

## Domain quick reference

- The inspection set is derived from the work, not chosen afterwards.
  Anything that altered a conductive path owes an electrical check;
  anything that added or removed material owes a dimensional one;
  anything whose result ends up inside the board owes a radiograph.
  Everything owes a visual.
- That derivation is the whole point of the clause. A repair graded
  only on the inspections somebody chose to run is graded on a set that
  was picked after the result was known.
- A missing inspection and a failed inspection are different outcomes.
  A repair that passed everything it was given, but was never given the
  electrical check it owed, is incomplete — evidence is outstanding.
  Calling that a pass is how an unverified repair leaves the bench.
- Visual inspection has a resolution, and the resolution is set by the
  smallest feature being graded. The magnification demanded follows from
  that feature size and is then rounded up to a magnification the bench
  can actually be set to; a feature too small for the highest step is
  not a visual inspection at all and is refused.
- Electrical evidence is two-sided. Insulation resistance says whether
  the repair left a leakage path that was not there before; path
  resistance says whether the repaired conductor still carries. One
  reading cannot stand in for the other.
- A radiograph is graded on voiding fraction, which is the only view
  there is of a connection nobody can see. It is required by the kind
  of work done, and separately by a joint being hidden, so a reworked
  bottom-terminated part pulls it in even though the rework itself
  would not have.

## Workflow

1. Validate the repair record and the readings; an unknown repair kind,
   an unknown inspection name or a reading group missing a value is an
   input error, not an absent result.
2. Derive the required inspection set from the repair kinds performed,
   adding the radiograph separately when the connection is hidden.
3. Compare the required set with the inspections actually performed and
   list what is outstanding.
4. Grade the visual by computing the magnification the smallest graded
   feature demands, rounding up to a real bench step, and comparing it
   with the magnification used.
5. Grade the electrical on insulation and on path resistance
   separately, each against its own limit with a named tolerance.
6. Grade the dimension against its band and the radiograph against its
   voiding limit.
7. Return reject when any graded inspection failed, incomplete when all
   that were run passed but something required is outstanding, accept
   only when the set is complete and every result passed.

## Pitfalls

- Grading the inspections that were run. The set the repair owes is
  derived from the work, and an inspection chosen after the fact is
  chosen knowing what it would show.
- Reporting an incomplete verification as a pass. Outstanding evidence
  is its own outcome; collapsing it into accept is how a repair with no
  electrical check reaches the next assembly stage.
- Treating a missing inspection as more serious than a failed one. A
  failure is a known defect and outranks it; both are reported, but the
  verdict is reject, not incomplete, when something actually failed.
- Accepting a visual because a microscope was used. The magnification
  demanded follows from the smallest feature graded, and a bench set
  below it cannot resolve the thing being judged.
- Substituting a continuity check for an insulation measurement. One
  shows the conductor still carries and the other shows the repair did
  not create a leakage path; they fail independently.
- Skipping the radiograph on a reworked hidden joint because the rework
  itself does not call for one. The hidden connection calls for it, and
  that condition is evaluated separately from the repair kind.

## Behavior contract (gate 3)

The input validation, inspection-set derivation, outstanding-inspection
list, magnification-step computation, two-sided electrical grading,
dimensional band test, radiographic voiding test and the reject /
incomplete / accept ladder are exercised by the gate 3 contract test:
scripts/test_q7028_post_repair_verification.py against
scripts/q7028_post_repair_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7028_post_repair_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

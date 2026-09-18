---
name: q7031-acceptance-inspection
description: "Evaluate whether one painted batch or area may be accepted and record the evidence that says so. Use when a coat has cured and acceptance is due per batch rather than per programme: size the dry-film-thickness draw from the painted area by integer arithmetic, reduce the readings, run the floor, ceiling and mean-band rules together so a healthy mean never rescues a thin point, grade the adhesion result and the cured state, and grade the inspection record itself so a lapsed gauge calibration holds the batch on paperwork instead of passing it. Trigger: ecss, q-st-70-31c-painting-scope, paint-batch-acceptance-inspection, dry-film-thickness-sampling, coating-adhesion-grade-acceptance, paint-inspection-record-completeness, coating-gauge-calibration-currency."
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
  tags: [ecss, q-st-70-31c-painting-scope, q7031-acceptance-inspection, paint-batch-acceptance-inspection, dry-film-thickness-sampling, coating-adhesion-grade-acceptance, paint-inspection-record-completeness, coating-gauge-calibration-currency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Painting — Acceptance Inspection (space-systems/ecss/q7031-acceptance-inspection)

Use when the task is the acceptance inspection ECSS-Q-ST-70-31C asks for on an
applied paint: a batch has been sprayed and cured, the area is in front of the
inspector, and the question is whether it is released, rejected, or held while
the record catches up.

## Domain quick reference

- Acceptance is granted per batch and per painted area. A programme-level
  statement that the paint shop is qualified says nothing about the area on
  the bench, which is why the clause puts the decision at the batch.
- The reading set is sized from the area, not chosen by the inspector. A
  per-square-metre density fixes the draw, a floor keeps a small fitting from
  being accepted on one or two points, and the count rounds up because a
  partial reading does not exist.
- Three thickness rules run at once and none of them substitutes for another:
  no single point below the floor, no single point above the ceiling, and the
  mean inside its nominal band. A comfortable mean does not rescue a thin
  point, because the thin point is where the coating fails first.
- A reading that lands exactly on a bound is inside it. The floor is the last
  accepted value, and the comparison absorbs only the representation error of
  a decimal bound against a computed mean; the limit itself never moves.
- Adhesion is the one property the thickness gauge cannot see, reported on an
  ordered scale where the lower number is the better result. An absent
  adhesion result is a finding, not an implied pass.
- The record is graded as its own object. Batch, unit, inspector, day,
  instrument, calibration due day and paint lot either appear or do not, and
  an instrument whose calibration had lapsed on the inspection day produces
  readings that cannot support a release.
- The disposition separates two different failures. A batch that missed a
  physical rule is rejected; a batch that met every physical rule but has an
  incomplete or uncalibrated record is held, because the hardware may still be
  good and the evidence is what is missing.

## Workflow

1. Size the dry-film-thickness draw from the painted area, its per-square-metre
   density and the floor, rounding up to whole points.
2. Reduce the readings to count, mean, minimum, maximum and sample spread,
   refusing a non-positive or non-numeric reading rather than dropping it.
3. Run the three thickness rules against the specification and raise each
   independently, then raise a short reading set against the sized draw.
4. Grade the adhesion result against its ceiling, treating an absent result as
   a finding of its own.
5. Confirm the cured state was verified; an unverified cure is a finding, not
   an assumption.
6. Grade the record: name every missing field individually, and test the gauge
   calibration against the inspection day, where a calibration due that day is
   still valid.
7. Disposition the batch -- accepted, rejected on a physical rule, or held on
   the record -- then aggregate across the campaign, which is accepted only
   when no batch carries an open finding.

## Pitfalls

- Choosing the number of measurement points by feel, so a large panel and a
  small bracket are accepted on incomparable evidence.
- Accepting a batch on its mean thickness with a point below the floor buried
  in the set, which is the failure the floor rule exists to catch.
- Reading a value that lands exactly on the floor as a rejection, or widening
  the floor so a genuine thin point passes. Neither is the rule.
- Recording adhesion as "not performed" and carrying the batch as acceptable
  because the thickness was good.
- Releasing readings from a gauge whose calibration had already lapsed, where
  the numbers look normal and support nothing.
- Rejecting a batch that met every physical rule because a record field was
  blank, when the correct state is a hold that the paperwork can clear.

## Behavior contract (gate 3)

The point sizing, reading reduction, the three thickness rules, adhesion
grading, calibration currency, record completeness and the batch and campaign
dispositions are exercised by the gate 3 contract test:
scripts/test_q7031_acceptance_inspection.py against
scripts/q7031_acceptance_inspection_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7031_acceptance_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

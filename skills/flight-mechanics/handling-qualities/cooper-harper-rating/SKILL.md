---
name: cooper-harper-rating
description: "Use when the task is handling qualities assessment, pilot rating, flyability evaluation, or certification flight test analysis framed by FAR-25 and CS-25 flight characteristics requirements. Determine a Cooper-Harper handling qualities rating (1 to 10) for an aircraft from a pilot-in-the-loop evaluation: walk the decision tree (controllability, adequate performance with desired or adequate tolerances, pilot compensation required), classify the rating band (1-3 satisfactory without improvement, 4-6 deficiencies warrant improvement, 7-9 deficiencies require improvement, 10 uncontrollable), and run the flight test procedure for collecting ratings. Trigger: cooper-harper rating, handling qualities, pilot rating, flyability, controllability, adequate performance, pilot compensation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: handling-qualities
  tags: [cooper-harper-rating, handling-qualities, pilot-rating, flyability, decision-tree, rating-bands, pilot-compensation, flight-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# Cooper-Harper Rating (flight-mechanics/handling-qualities/cooper-harper-rating)

Use when the task is assigning a Cooper-Harper handling qualities
rating to an aircraft from a piloted evaluation, classifying the
rating band, or planning the flight test procedure that collects the
ratings.

## Domain quick reference

- The Cooper-Harper scale runs 1 (excellent) to 10 (uncontrollable).
  The rating is assigned by the pilot in the loop after flying a
  defined evaluation task, not by the engineer on the ground.
- Decision tree (paraphrase of the standard rating procedure):
  1. Is the aircraft controllable? No gives 10 (uncontrollable).
  2. Is adequate performance attainable with the required
     tolerances? No gives 7-9 (deficiencies require improvement).
  3. Is the aircraft satisfactory without improvement? Yes gives
     1-3, graded by the pilot compensation needed; No gives 4-6
     (deficiencies warrant improvement), graded by compensation.
- Rating bands: 1-3 satisfactory without improvement, 4-6
  deficiencies warrant improvement, 7-9 deficiencies require
  improvement, 10 uncontrollable.
- Compensation anchors on the satisfactory side: none gives 1,
  negligible gives 2, minor gives 3. Worked example: controllable,
  adequate performance, desired tolerances, no compensation = 1.
- Compensation anchors on the warrant-improvement side: minor gives
  4, moderate gives 5, considerable gives 6. Worked example:
  controllable, adequate performance, adequate tolerances,
  considerable compensation = 6.
- Compensation anchors on the require-improvement side: minimal
  gives 7, considerable gives 8, extensive or intense gives 9.
  Worked example: controllable but adequate performance not
  attainable, extensive compensation = 9.
- Handling qualities levels (MIL-STD-1797A framing): ratings 1-3
  are Level 1 (satisfactory), 4-6 Level 2 (adequate), 7-9 Level 3
  (controllable), 10 uncontrolled. Certification flight
  characteristics work normally demands Level 1 for the operational
  flight envelope.
- Flight test procedure: brief the task and the desired and adequate
  tolerances before flight, fly the maneuver, let the pilot assign
  the rating immediately after each run, record deficiencies and
  pilot comments, and repeat for scatter.

## Workflow

1. Define the evaluation task and write the desired and adequate
   tolerances before the first flight: the rating is meaningless
   without a defined task and measurable tolerances.
2. Confirm the aircraft is controllable through the maneuver with
   cooper_harper_rating(controllable=False, ...), which returns 10.
3. Check whether adequate performance is attained; if not, the
   rating lands in the 7-9 band graded by the compensation required
   to retain control.
4. Check whether the aircraft is satisfactory without improvement;
   if yes, grade 1-3 by the pilot compensation needed for desired
   performance.
5. Otherwise grade 4-6 by the compensation needed for adequate
   performance.
6. Classify the result with rating_band and handling_qualities_level,
   and check the level against the certification requirement (Level
   1 for the operational envelope).

## Pitfalls

- Routing stability derivative questions here: neutral point, static
  margin, and stability derivative sizing belong to
  longitudinal-stability; the Cooper-Harper rating is a pilot
  judgment of the closed-loop task, not a derivative calculation.
- Routing dynamic response questions here: short period and dutch
  roll damping, natural frequency, and eigenvalue analysis belong to
  dynamic-stability; the rating summarizes the piloted experience,
  it does not replace the mode analysis.
- Routing trim questions here: trim forces, trim control deflections,
  and trim speed analysis belong to trim-analysis; a heavy but
  achievable trim condition may lower a rating but is not itself a
  rating.
- Routing control power questions here: hinge moments, control
  surface effectiveness, and control authority belong to
  control-surface-effectiveness; the rating captures the perceived
  workload, not the aerodynamic authority numbers.
- Confusing 10 with 9: 10 means control is lost during the task
  (uncontrollable); 9 means the aircraft is controllable but only
  with intense or extensive compensation.
- Mixing the tolerance classes: desired tolerances grade the 1-3
  band, adequate tolerances grade the 4-6 band; rating with adequate
  tolerances against a desired-performance question shifts the band.
- Rating the pilot instead of the aircraft: the scale rates the
  handling qualities of the vehicle for the task, not the skill of
  the pilot flying it.
- Averaging ratings across different tasks: each rating is valid
  only for the task and tolerances it was collected under; a single
  averaged number hides the task dependence.
- Issuing ratings without a defined task: a Cooper-Harper rating
  without stated desired and adequate tolerances cannot be verified
  and should be treated as an opinion, not an evaluation result.

## Behavior contract (gate 3)

The decision tree, band classification, and handling qualities level
mapping is exercised by the gate 3 contract test:
scripts/test_cooper_harper_rating.py against
scripts/cooper_harper_rating_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_cooper_harper_rating.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 flight
  characteristics requirements frame the handling qualities
  assessment for transport aeroplanes; the Cooper-Harper scale
  itself is the common pilot-rating methodology of Cooper and Harper
  (1969), summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

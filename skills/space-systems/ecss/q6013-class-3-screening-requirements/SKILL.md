---
name: q6013-class-3-screening-requirements
description: "Use when a commercial lot has to be given a screening verdict. Determine whether lot screening is owed for a commercial part at the lowest assurance class and whether the declared flow discharges it under ECSS-Q-ST-60-13C clause 6.3.3: derive the required elements from the declared trigger conditions, close cleanly when no trigger applies, hold an every-unit element to the whole lot, size a sampled element against the lot, convert a burn-in run at another temperature into reference-equivalent hours before judging its duration, and refuse a burn-in above the part's rated maximum. Trigger: ecss, q-st-60-13c-clause-6-3-3, class-three-lot-screening-trigger, screening-element-derivation, every-unit-versus-sampled-screen, burn-in-arrhenius-equivalent-hours, screening-temperature-rating-limit."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-screening-requirements, q-st-60-13c-clause-6-3-3, class-three-lot-screening-trigger, screening-element-derivation, every-unit-versus-sampled-screen, burn-in-arrhenius-equivalent-hours, screening-temperature-rating-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE -- Class 3 Screening Requirements (space-systems/ecss/q6013-class-3-screening-requirements)

Use when the task is clause 6.3.3 of ECSS-Q-ST-60-13C at the lowest assurance
class: a lot of commercial electrical, electronic and electromechanical parts
has arrived or is being planned for, and the question is whether screening is
owed on it at all, which elements are owed, and whether what was actually run
discharges them.

## Domain quick reference

- Screening is conditional at this class, not routine. It becomes owed because
  a condition on the lot or its application calls for it, and a lot carrying
  no such condition is closed clean rather than screened for form. Running a
  flow nobody asked for spends the budget the class exists to protect.
- Each trigger condition names the elements it demands, and the owed set is
  the union across the triggers present. A part in a criticality-bearing
  function owes visual inspection, room-temperature electrical measurement,
  burn-in and measurement at the temperature extremes. A wide application
  range adds temperature cycling. An unverified supply origin adds an
  authenticity and origin check. A cavity package adds particle impact noise
  detection and a seal integrity check. Extended storage since the date code
  brings back the visual and the room-temperature electrical readings.
- Declaring no trigger and declaring nothing at all are different claims. An
  empty trigger list states that the conditions were considered and none
  applied; silence states that nobody looked, and is refused.
- Most elements only mean anything applied to the whole lot. A sampled burn-in
  leaves unstressed units in the flight build, which is the failure the burn-in
  was bought to prevent, so sampling such an element is a basis error rather
  than a coverage shortfall.
- The elements that may be sampled are sized against the lot: a fraction of
  the lot, floored by a minimum count and capped at the lot itself, so a run
  of twelve parts is not sampled at one. The fraction is carried as a ratio of
  integers and the rounding is done in integer arithmetic, because a float
  ceiling can move the threshold by a whole unit between platforms.
- A burn-in run away from the reference temperature is converted before its
  duration is judged. The Arrhenius acceleration factor is what lets a short
  hot run be credited and stops a long cool one being read as generous, and
  the comparison is made on reference-equivalent hours rather than on the
  hours the oven was on.
- The conversion has a ceiling. A burn-in above the temperature the part is
  rated for damages the population it is meant to grade, so that condition is
  refused before any equivalence is credited to it, not traded against
  duration.
- Screening declared beyond the owed set is recorded as additional rather than
  as a finding. Extra work is the project's to spend; the assessment is about
  what was owed.

## Workflow

1. Validate the screening policy: the sample fraction as a ratio of integers,
   the minimum sample count, the activation energy, and the reference burn-in
   duration and temperature.
2. Validate the lot: its size and the maximum temperature the part is rated
   for.
3. Validate the declared trigger conditions, refusing an undeclared list and
   an unrecognized condition, and derive the owed elements as their union in
   the declared element order.
4. Close on no screening owed where no trigger applies, recording anything
   declared as additional.
5. Validate every declared step: the element, the basis, the units screened
   and, for a burn-in, the duration and temperature. Reject an element
   declared twice.
6. Grade each owed element: not performed, sampled where the whole lot is
   required, short of the lot on an every-unit element, sampled below the
   required count, or sampled with no count stated.
7. For the burn-in, refuse a run above the rated maximum first, then convert
   the run into reference-equivalent hours and compare with the reference
   duration under a named relative tolerance.
8. Close on one verdict -- screening not required, owed but none declared, an
   owed element not performed, a condition outside the part rating, screening
   applied to too few units, a burn-in short of the reference equivalent, or
   screening meets class 3 expectations -- carrying every finding.

## Pitfalls

- Screening every lot because screening is cheap insurance. At this class the
  effort is finite, and a flow run on an untriggered lot is effort taken from
  the lot that needed it.
- Reading an empty trigger list as missing input. The empty list is a positive
  statement that the conditions were assessed; the missing key is the defect.
- Sampling a burn-in. The units that were never stressed are exactly the ones
  that go into the build, so the sample tells you about the parts you threw
  away rather than the parts you kept.
- Sizing a sample by fraction alone. A twelve-piece lot sampled at a tenth is
  one unit, which is a gesture rather than a screen; the minimum count is what
  makes the sample mean anything on a short lot.
- Rounding the sample threshold through a float ceiling. A tenth of a hundred
  can land a hair above ten on one platform and exactly on it on another,
  moving the threshold by a whole unit.
- Judging a burn-in on its hours. A short hot run and a long cool one look
  alike on the clock and are worth entirely different amounts of life.
- Trading temperature against duration past the rating. Above the rated
  maximum the screen is changing the population rather than grading it, and no
  amount of credited equivalence recovers that.
- Treating extra screening as a defect. Work beyond the owed set is recorded,
  not penalized.

## Behavior contract (gate 3)

The policy and lot validation, trigger validation and element derivation, the
no-trigger close, step validation, the every-unit and sampled basis rules, the
integer sample sizing, the rated-maximum refusal, the Arrhenius burn-in
equivalence and its duration comparison, the additional-screening record and
the overall verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_screening_requirements.py against
scripts/q6013_class_3_screening_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_3_screening_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

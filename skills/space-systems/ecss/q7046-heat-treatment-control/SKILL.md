---
name: q7046-heat-treatment-control
description: "Verify a threaded fastener heat-treatment charge and the mechanical properties it was supposed to produce. Use when a furnace record and a test report arrive together and someone must say whether the lot is in condition: read the tensile, yield and proof targets straight out of the property class designation, size the soak from the governing section, judge the furnace survey at every thermocouple rather than on its average, hold the transfer to the quenchant to its own clock, refuse a temper below the class minimum, and treat a hardness reading that contradicts the tensile result as two measurements of different parts. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-property-class-targets, fastener-furnace-uniformity-survey, fastener-quench-transfer-clock, fastener-minimum-temper-temperature, fastener-hardness-tensile-crosscheck."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-heat-treatment-control, fastener-property-class-targets, fastener-furnace-uniformity-survey, fastener-quench-transfer-clock, fastener-minimum-temper-temperature, fastener-hardness-tensile-crosscheck, fastener-section-soak-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Heat Treatment Control (space-systems/ecss/q7046-heat-treatment-control)

Use when the task is the heat-treatment part of the ECSS-Q-ST-70-46
manufacturing clause -- controlling the charge that produces a
fastener's condition, and checking the properties that came out of it
against the ones the property class already demanded.

## Domain quick reference

- The property class is not a label, it is the acceptance targets. The
  first number gives the tensile strength in hundreds of megapascals
  and the second gives the yield as a tenth-fraction of that tensile,
  so the targets are derived from the designation and the proof stress
  follows from the yield by a declared policy fraction.
- The charge is controlled before the parts are. Soak time follows
  from the governing section thickness, because the centre of a thick
  part reaches temperature long after its surface and a soak sized on
  the clock alone hardens the skin of a heavy bolt.
- A furnace survey is judged at every thermocouple, never on an
  average. One hot corner and one cold corner average to the setpoint
  and produce two populations of parts out of one charge.
- The transfer to the quenchant has its own clock. The part is cooling
  in air while it travels, so a slow transfer moves the cooling curve
  off the one the treatment was designed around, and no later test
  distinguishes that from a different steel.
- Tempering is what separates a class from its neighbours, and each
  class carries a minimum tempering temperature. An under-tempered
  part can pass a tensile test and still have no business in a joint
  that sees sustained load.
- Hardness and tensile strength are two views of one condition.
  Hardness converts to an estimated tensile strength by a
  proportional relation, valid only over the range it was fitted on,
  and a conversion that disagrees with the measured tensile beyond the
  declared band means one of the two is describing a different part.
- The proof load follows from the thread stress area and the class
  proof stress, so it is derived from the designation and the thread
  size rather than copied from a table that may be for another class.

## Workflow

1. Derive the tensile, yield and proof targets from the property class
   and reject an unrecognized designation rather than defaulting it.
2. Size the required soak from the governing section and compare the
   declared soak against it.
3. Run the uniformity survey across every thermocouple, report the
   worst deviation and name the failing positions rather than a
   verdict alone.
4. Check the quench transfer against its clock and report the overrun
   where there is one.
5. Compare the tempering temperature against the class minimum,
   remembering the top class tempers lower than the one below it.
6. Cross-check the hardness against the measured tensile through the
   fitted conversion, treat a disagreement as a measurement question
   rather than a rejection, then compare the measured tensile against
   the class target and roll the worst charge up into the log.

## Pitfalls

- Sizing the soak on the clock. The governing section drives it, and a
  soak that suits a thin bolt leaves the core of a heavy one
  untransformed while every surface reading looks right.
- Averaging a furnace survey. The average is exactly the number that
  hides one hot corner and one cold corner, and the charge then
  contains two populations that no sampling plan was designed for.
- Treating the quench transfer as handling time. The cooling starts
  when the part leaves the furnace, so a slow transfer is a different
  heat treatment, and the test report cannot tell you that afterwards.
- Assuming a higher class always tempers hotter. The top class tempers
  lower than its neighbour, so a floor applied by intuition rejects
  conforming parts and passes under-tempered ones.
- Converting hardness outside the range the relation was fitted on.
  The conversion is proportional over a band, and extending it past
  that band produces a tensile estimate with no evidence behind it.
- Rejecting a lot the moment hardness and tensile disagree. The
  disagreement says the two measurements are not describing the same
  condition, which is a question about the specimens before it is a
  verdict on the parts.
- Comparing a soak, a deviation or a strength against its bound by
  bare arithmetic. All are products of measured floats, so a case
  sitting exactly on the bound can land a few units in the last place
  outside it; the comparisons absorb that while the bounds stay
  untouched.

## Behavior contract (gate 3)

The property-class targets, section soak time, per-thermocouple
uniformity survey, quench transfer clock, class temper minimum,
hardness-to-tensile cross-check, stress area and proof load and the
charge roll-up are exercised by the gate 3 contract test:
scripts/test_q7046_heat_treatment_control.py against
scripts/q7046_heat_treatment_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_heat_treatment_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

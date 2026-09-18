---
name: q7080-heat-treatment-requirements
description: "Verify a post-build heat-treatment route against the declared material recipe. Use when a stress-relief, solution, quench or ageing step has to be graded before an additively manufactured part is released: take the dwell from the coldest load thermocouple rather than the set point, break the soak on an overshoot as well as a shortfall, grade the approach ramp and the protective atmosphere, hold the quench transfer inside its window, confirm stress relief ran before the part left the build plate and ageing after solution, check the furnace survey is current, then take the worst step and name it. Trigger: ecss, q-st-70-80-additive-manufacturing, am-post-build-heat-treatment, am-stress-relief-before-plate-removal, am-solution-ageing-sequence, am-load-thermocouple-soak-dwell, am-furnace-survey-currency."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-heat-treatment-requirements, am-post-build-heat-treatment, am-stress-relief-before-plate-removal, am-solution-ageing-sequence, am-load-thermocouple-soak-dwell, am-furnace-survey-currency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Post-Build Heat Treatment (space-systems/ecss/q7080-heat-treatment-requirements)

Use when the post-process clause of ECSS-Q-ST-70-80 is the task: deciding
whether the furnace route applied to an additively manufactured part
actually delivered the treatment its material recipe calls for, and
whether the steps ran in an order that leaves the part in the condition
the design allowables were taken on.

## Domain quick reference

- An as-built part carries the residual stress of layer-by-layer
  deposition and a solidification microstructure that no allowable was
  measured on. The furnace route converts one into the other, so it is
  evidence about the material, not a housekeeping step.
- The part is at temperature only when the coldest load thermocouple is
  inside the band. A set-point or control-zone trace proves the furnace
  was hot; a thick section in the middle of a dense load lags it by tens
  of degrees and by a long time.
- The qualifying dwell is the longest contiguous run inside the band, not
  the sum of the time spent near it. An excursion above the ceiling
  interrupts the soak exactly as a dip below the floor does, because a
  part that overshot is partway through a different treatment.
- The approach ramp is part of the recipe. A ramp faster than the
  declared limit puts back the through-thickness gradient the
  stress-relief soak exists to remove, so a fast furnace is not a
  shortcut to the same result.
- A reactive alloy held in air grows an oxygen-enriched surface layer
  that no machining allowance was sized to remove, so the atmosphere is
  graded with the temperature and not separately from it.
- Order matters as much as the individual steps. Stress relief belongs
  before the part is cut from the build plate, ageing after solution
  treatment, the quench directly after the solution soak and inside its
  transfer window, and a hot isostatic pressing cycle after any ageing it
  would otherwise undo.
- A quench is graded on its transfer time and its immersion, not on an
  approach ramp or a soak overshoot it never has; grading it as a soak
  produces findings that are artefacts of the model.
- The furnace qualification is part of the evidence: a lapsed uniformity
  survey, or fewer load thermocouples than the load needs, means the
  coldest point of the load was never measured at all.

## Workflow

1. Validate the load thermocouple traces onto one time base and take the
   coldest-point envelope sample by sample. Refuse traces on different
   time bases rather than interpolating between them.
2. For each soak step, measure the longest contiguous dwell inside the
   band, the peak the envelope reached and the fastest approach rate
   below the band floor, then grade all three against the recipe.
3. Grade the atmosphere against the protection the recipe authorises for
   that step, and a quench against its transfer window and its immersion
   in the bath.
4. Check the route order: stress relief before plate removal, quench
   directly after solution, ageing after solution, and any ageing that
   precedes a hot isostatic pressing cycle raised for review.
5. Grade the furnace uniformity survey against its interval and the load
   thermocouple count against what the load requires, calling out a
   survey that lapses part way through a long route.
6. Take the worst of the steps, the sequence and the furnace
   qualification as the verdict, name every step sitting at that level,
   and prefix each finding with the step it came from.
7. Where a dwell, a ramp or a survey age should land exactly on its
   limit, grade it with the tolerant comparison so a unit conversion
   cannot turn an on-limit route into a reject.

## Pitfalls

- Reading the dwell off the control thermocouple or the set point. That
  is the furnace temperature, not the part temperature, and the gap
  between them is largest exactly where the load is densest.
- Summing every minute near the band into one dwell. Two short soaks
  separated by an excursion are not one long soak, and the summed number
  passes a route that never held the part at temperature.
- Grading only the low side of the band. An overshoot puts the part
  through a different treatment, coarsening or over-ageing it, and it is
  invisible to a check that only looks for a shortfall.
- Cutting the part from the build plate before stress relief. The
  residual stress is released as distortion the moment the constraint is
  removed, and no later soak puts the geometry back.
- Ageing a part that has not been solution treated, or ageing before a
  hot isostatic pressing cycle. Both produce a part in a condition that
  the allowables do not describe, however correct each soak was on its
  own.
- Accepting a route run on a lapsed uniformity survey or with too few
  load thermocouples. Both mean the coldest point of the load is an
  assumption, so every dwell in the record is unverified.

## Behavior contract (gate 3)

The trace validation, coldest-point envelope, contiguous dwell, ramp and
overshoot grading, atmosphere and quench-window checks, route sequencing
and furnace qualification are exercised by the gate 3 contract test:
scripts/test_q7080_heat_treatment_requirements.py against
scripts/q7080_heat_treatment_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_heat_treatment_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

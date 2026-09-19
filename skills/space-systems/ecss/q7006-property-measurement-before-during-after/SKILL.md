---
name: q7006-property-measurement-before-during-after
description: "Plan the property read-out points of a particle and UV radiation exposure under ECSS-Q-ST-70-06C, or grade a schedule already written. Use when optical, thermo-optical and mechanical properties have to be measured before, during and after an irradiation rather than once at the end. Requires a pristine baseline and a point at the planned total exposure, counts the intermediate points that give the degradation curve its shape, reports the widest unmeasured stretch of the exposure axis, holds each point to the replicate floor of the families read out on it, and refuses a plan whose expected change sits inside its own expanded uncertainty. Trigger: ecss, q-st-70-06, radiation-property-measurement-schedule, pristine-baseline-measurement, intermediate-exposure-point, radiation-exposure-axis-sampling, thermo-optical-replicate-floor, measurement-resolvability-check."
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
  tags: [ecss, q-st-70-06-particle-uv-radiation-testing-scope, q7006-property-measurement-before-during-after, radiation-property-measurement-schedule, pristine-baseline-measurement, intermediate-exposure-point, radiation-exposure-axis-sampling, measurement-resolvability-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Property Measurement Before, During and After (space-systems/ecss/q7006-property-measurement-before-during-after)

Use when the task is the measurement step of an ECSS-Q-ST-70-06C particle
or UV exposure — deciding at which accumulated fluences and UV doses the
optical, thermo-optical and mechanical properties are read out, and
whether a schedule already written can answer the question the run was
set up to ask.

## Domain quick reference

- Degradation is a difference, never an absolute reading. Without a
  pristine value taken before any exposure, the post-exposure number can
  only be compared against a datasheet figure measured on somebody
  else's specimen with somebody else's instrument.
- The intermediate points carry the shape of the curve. Absorptance
  darkening usually saturates, embrittlement usually does not, and a
  before-and-after pair cannot tell the two apart. One point in the
  middle separates them; a point at a quarter and a half of the planned
  exposure lets the curve be extrapolated past it.
- A long stretch of the exposure axis with no point in it hides whatever
  happened there, including a transient that recovered before the final
  read-out. The widest gap between consecutive points is the honest
  measure of how well the run is sampled.
- Replicate counts are per property family, not per run. Optical and
  thermo-optical read-outs are repeatable enough for three specimens;
  tensile strength and elongation scatter far more and need five, and a
  point that mixes families is held to the tightest floor on it.
- A property whose expected change sits inside the expanded uncertainty
  that will be quoted against it is being measured with the wrong
  instrument. Checking that at planning time costs nothing; discovering
  it after the beam time is gone costs the campaign.

## Workflow

1. Name the property families the run is about, rejecting any the
   measurement plan cannot actually read out.
2. Normalize the schedule: every point carries a label, an accumulated
   exposure expressed as a fraction of the planned total, the families
   measured on it and a replicate count. Order by exposure and refuse
   two points at the same fraction.
3. Require a point at zero exposure and a point at the planned total,
   and require every named family to appear at both.
4. Count the points strictly between the two ends; a schedule with none
   is a before-and-after pair wearing a schedule's name.
5. Report the widest gap between consecutive points and raise a finding
   when it exceeds the sampling limit.
6. Hold each point to the replicate floor of the most demanding family
   read out on it.
7. Compare each expected change with its expanded uncertainty and refuse
   the plan when the change cannot be resolved.
8. Emit the ordered points, the coverage gaps, the shortfalls and every
   finding; the plan is executable only when no finding stands.

## Pitfalls

- Measuring only before and after because the facility charges for
  chamber access per opening. The saving is real and the curve is gone;
  an in-situ read-out is the answer, not a shorter point list.
- Treating a datasheet value as the baseline. It was measured on a
  different lot, in a different processing state, on a different
  instrument, and every one of those differences lands in the delta.
- Sampling the exposure axis evenly when the degradation is not. A
  saturating property wants its points early, where it is still moving.
- Setting one replicate count for the whole run. Three specimens is
  generous for emittance and thin for elongation at break.
- Quoting an uncertainty only in the final report. If it is not compared
  with the expected change at planning time, the run can finish with a
  result nobody can distinguish from no change at all.

## Behavior contract (gate 3)

The family table, point validation, schedule ordering, baseline and
final coverage, intermediate-point counting, gap reporting, replicate
floors, resolvability check and plan aggregation are exercised by the
gate 3 contract test:
scripts/test_q7006_property_measurement_before_during_after.py against
scripts/q7006_property_measurement_before_during_after_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q7006_property_measurement_before_during_after.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

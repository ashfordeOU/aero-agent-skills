---
name: q7006-degradation-assessment
description: "Assess the property degradation measured in a particle or UV irradiation against its acceptance and end-of-life criteria under ECSS-Q-ST-70-06C. Use when an exposed value has to be turned into a verdict rather than a table row. Carries the sign convention of the property, adds the expanded uncertainty to form the worst case, refuses a movement smaller than its own uncertainty, grows the tested degradation to the mission end-of-life exposure along a declared proportional, square-root or saturated model, reports how far past the tested exposure that reaches, and returns the margins left against both criteria. Trigger: ecss, q-st-70-06, radiation-degradation-assessment, end-of-life-degradation-criterion, degradation-growth-model, worst-case-degradation-uncertainty, fluence-extrapolation-factor, radiation-acceptance-margin."
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
  tags: [ecss, q-st-70-06-particle-uv-radiation-testing-scope, q7006-degradation-assessment, radiation-degradation-assessment, end-of-life-degradation-criterion, degradation-growth-model, fluence-extrapolation-factor, radiation-acceptance-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Degradation Assessment (space-systems/ecss/q7006-degradation-assessment)

Use when the task is the evaluation step of an ECSS-Q-ST-70-06C particle
or UV exposure — turning a pristine value and an exposed value into a
degradation, carrying it out to the mission end of life, and deciding
whether it sits inside the criteria the material was accepted against.

## Domain quick reference

- Degradation is directional. Solar absorptance degrades upwards while
  transmittance, emittance, tensile strength and elongation degrade
  downwards, so the sign convention travels with the property. Taking
  an absolute difference throws away the one thing that says whether the
  material got better or worse.
- The figure a criterion is applied to is the worst case, not the mean.
  Measured degradation plus the expanded uncertainty quoted against it
  is what the design has to survive; a verdict written on the mean
  alone is a verdict with a coin flip in it.
- A movement smaller than its own uncertainty is not a small
  degradation, it is no measurement. Reporting it as a number invites
  a later reader to difference two of them and build a trend out of
  noise.
- Exposures are almost never run to the mission end of life. The tested
  degradation is grown out along a declared model: proportional where
  damage accumulates, square-root where diffusion limits it, saturated
  where the material has already stopped changing. The model is an
  input the reviewer can argue with, never a fit to two points.
- The distance between the tested exposure and the end-of-life exposure
  decides how much of the verdict is measurement and how much is
  modelling. Past a factor limit the number is a modelling statement and
  is reported as one.

## Workflow

1. Read the property, its degradation direction, the pristine and
   exposed values, and the expanded uncertainty quoted against them.
2. Form the degradation in the direction that hurts and express it also
   as a fraction of the pristine value.
3. Check the movement against its own uncertainty and raise a finding
   when it cannot be told from no change.
4. Add the uncertainty to form the worst-case end-of-test degradation.
5. Compute the extrapolation factor from the tested exposure to the
   mission end-of-life exposure, and grow the degradation along the
   declared model.
6. Raise a finding when the extrapolation reaches further past the
   tested exposure than the factor limit allows.
7. Compare both worst cases with their criteria, separating a real
   breach from one that only appears once the uncertainty is added.
8. Emit the degradations, the extrapolation, both margins and every
   finding; the property is accepted only when neither criterion is
   exceeded.

## Pitfalls

- Applying one criterion to both ends. The end-of-test criterion grades
  what was measured; the end-of-life criterion grades what the thermal
  and optical design was closed on, and they are rarely the same number.
- Fitting the growth model to the two points being extrapolated. A
  model chosen by the data it is about to be extrapolated from cannot
  be wrong, which is exactly the problem.
- Extrapolating a saturated property proportionally. It multiplies a
  degradation that physically stopped growing and rejects a material
  that was fine.
- Quoting the mean degradation against the criterion and the expanded
  uncertainty in a footnote. The reviewer then has to redo the
  comparison, and usually does not.
- Reading a benign movement as a pass without checking it is
  measurable. A property that drifted the good way by less than its
  uncertainty has not improved either.

## Behavior contract (gate 3)

The directional delta, relative degradation, worst-case combination,
measurability check, extrapolation factor, growth models, criterion
comparison and verdict aggregation are exercised by the gate 3 contract
test: scripts/test_q7006_degradation_assessment.py against
scripts/q7006_degradation_assessment_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q7006_degradation_assessment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

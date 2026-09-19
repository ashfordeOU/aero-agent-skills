---
name: q7001-verification-by-inspection
description: "Determine what a visual or black-light cleanliness observation can actually substantiate. Use when a surface is being verified by eye under ECSS-Q-ST-70-01C and the question is whether the conditions support the size the requirement needs seen: compute the resolvable particle diameter from viewing distance and assumed acuity, grow it for illuminance below the reference level and for foreshortening away from normal, confirm the lamp sits in the long-wave ultraviolet band with enough irradiance and a dark-adapted observer, reduce the fraction of surface covered, and return accept, re-clean or escalation to an instrumented method. Trigger: ecss, q-st-70-01c, cleanliness-visual-detectable-size, black-light-fluorescence-observation, uv-a-surface-irradiance, observer-dark-adaptation, cleanliness-inspection-coverage-fraction, visual-acuity-viewing-distance."
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
  tags: [ecss, q-st-70-01-cleanliness-scope, q7001-verification-by-inspection, cleanliness-visual-detectable-size, black-light-fluorescence-observation, uv-a-surface-irradiance, observer-dark-adaptation, cleanliness-inspection-coverage-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness -- Verification by Inspection (space-systems/ecss/q7001-verification-by-inspection)

Use when the task is the inspection route of cleanliness verification
under ECSS-Q-ST-70-01C: a surface is being looked at under white light
or a long-wave ultraviolet lamp, and the question is what that
observation is entitled to conclude about the cleanliness requirement
placed on it.

## Domain quick reference

- What the eye can resolve is geometry before it is anything else. The
  angular acuity assumed for the inspection, subtended at the viewing
  distance, fixes a chord; that chord is the smallest particle the
  observation can be about.
- Light removes acuity gradually. Below the illuminance the acuity
  assumption was stated at, the detectable size grows; above it the gain
  flattens and is not credited, so a brighter lamp does not buy a
  smaller detectable size.
- A surface seen at an angle is foreshortened. Viewing away from normal
  scales the detectable size by the reciprocal cosine, and a near
  grazing look is not an inspection geometry at all.
- Ultraviolet inspection has three separate conditions. The lamp has to
  sit in the long-wave band, the irradiance has to arrive at the
  surface rather than at the lamp housing, and the observer has to be
  dark adapted; any one of them failing invalidates the observation
  while the other two look fine.
- Coverage is part of the result. An observation over a third of a
  surface substantiates a third of it, and the fraction belongs in the
  record next to what was seen.
- An observation is not a measurement. When the conditions cannot reach
  the size the requirement needs seen, the honest outcome is escalation
  to an instrumented method, not a pass recorded under protest.

## Workflow

1. Compute the resolvable particle diameter from the viewing distance
   and the angular acuity assumed for the inspection, refusing an
   acuity beyond a degree as not an inspection assumption.
2. Grow that diameter by the illuminance derating and the viewing-angle
   derating to get the detectable size the conditions actually achieved.
3. Compare it with the size the requirement needs observed, absorbing
   representation error at the boundary with a named relative tolerance.
4. When the observation is under ultraviolet, grade the lamp wavelength
   against the long-wave band, the surface irradiance against its
   minimum and the observer dark adaptation against its minimum,
   raising a separate finding for each.
5. Reduce the inspected fraction of the surface and compare it with the
   coverage the verification claimed.
6. Grade the outcome: accept a substantiated clean observation,
   re-clean and re-observe a recleanable surface where contamination
   was seen, and escalate everything else to an instrumented method.
7. Report the detectable size, the coverage, the disposition and the
   findings raised.

## Pitfalls

- Recording a pass from an inspection that cannot resolve the size the
  requirement is written at. The observation is true and irrelevant,
  and the requirement stays unverified.
- Turning up the lamp to compensate for a long viewing distance.
  Distance enters the geometry and illuminance only the derating, so
  brightness cannot recover a detectable size the standoff has lost.
- Measuring ultraviolet irradiance at the lamp rather than at the
  surface. The inverse-square fall-off over a working standoff is the
  whole difference between a valid observation and a dark one.
- Starting a black-light observation straight out of a lit bay. The
  first minutes report the observer's adaptation state, not the
  surface.
- Reporting an observation without the fraction of surface it covered.
  A spot look and a full sweep enter the record identically and are not
  the same evidence.
- Treating fluorescence as a quantity. It shows that something is
  present and where; how much is there is a question only a measurement
  answers.

## Behavior contract (gate 3)

The resolvable-size geometry, illuminance and viewing-angle deratings,
ultraviolet band, irradiance and dark-adaptation conditions, coverage
fraction, substantiation comparison and disposition grading are
exercised by the gate 3 contract test:
scripts/test_q7001_verification_by_inspection.py against
scripts/q7001_verification_by_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_verification_by_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

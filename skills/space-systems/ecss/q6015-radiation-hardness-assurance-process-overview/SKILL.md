---
name: q6015-radiation-hardness-assurance-process-overview
description: "Derive the part-level radiation requirement a mission environment implies and the margin each part holds. Use when the ECSS-Q-ST-60-15C clause 4.1 assurance flow has to be walked end to end: check the declared stages against the canonical order and name every absent one, carry the mission environment through a dose-depth curve by log-log interpolation to each part's own shielding, refuse a thickness the curve does not span rather than extrapolating, apply the design factor to obtain the specified level, divide capability by it for the design margin, and let an exact equality pass under a named tolerance. Trigger: ecss, q-st-60-15c-clause-4-1, radiation-hardness-assurance-flow, mission-radiation-environment, dose-depth-curve-interpolation, part-level-specified-level, radiation-design-margin, assurance-stage-sequence."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-radiation-hardness-assurance-process-overview, q-st-60-15c-clause-4-1, radiation-hardness-assurance-flow, mission-radiation-environment, dose-depth-curve-interpolation, part-level-specified-level, radiation-design-margin, assurance-stage-sequence]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Process Overview (space-systems/ecss/q6015-radiation-hardness-assurance-process-overview)

Use when the task is the hardness assurance overview of ECSS-Q-ST-60-15C
clause 4.1 — how a mission radiation environment becomes a number an
individual part is procured, tested and accepted against, and what has to
happen between those two ends for the chain to hold.

## Domain quick reference

- The flow has one direction: mission environment, system requirement,
  shielding and geometry, part-level specified level, part capability, margin,
  verification test, mitigation decision, close-out. Each stage consumes the
  one before it, so a stage declared out of order is not a scheduling
  preference — it means a level was set before the analysis that produces it.
- The mission environment is quoted behind a reference shielding thickness.
  It is not the number any part sees. A part deep in a box behind structure
  sees a far lower level than one on an external panel, and the difference
  between them is the whole reason shielding analysis sits in the flow.
- The dose-depth curve is how the environment is carried inward. It falls
  steeply and smoothly with thickness, so between tabulated points it is read
  in log-log space; read linearly, the interpolated level is wrong in the
  direction that flatters the part.
- Outside the curve's tabulated span the shape is not the same shape. A part
  behind more shielding than the curve covers is refused until curve data
  covering it exists, because extrapolation there invents the level the part
  is held to.
- The specified level is the local level raised by the declared design factor,
  which carries the uncertainty in the environment model, the geometry and the
  part data. A factor below unity would hold the part to less than its own
  environment and is a data error.
- The margin is capability over specified level, a plain ratio. A part landing
  exactly on its required margin has met it; whether the quotient prints as
  1.9999999999999998 is a representation question, settled by a tolerance
  inside the comparison and not by relaxing the requirement.

## Workflow

1. Validate the mission environment: which quantity it states, the reference
   shielding thickness it is quoted behind, its level and the mission duration
   it covers.
2. Validate the declared stage list against the canonical flow — every stage
   recognized, none twice, none out of order — and name each absent stage on
   its own, then express the result as a completeness fraction.
3. Validate the dose-depth curve: at least two points, thickness ascending,
   level falling as shielding is added.
4. For each part, interpolate the curve in log-log space at its own local
   shielding, refusing a thickness outside the tabulated span and returning a
   tabulated point's level unchanged when the thickness lands on it.
5. Apply the design factor to obtain the part-level specified level, refusing
   a factor below unity.
6. Divide the part's demonstrated capability by its specified level for the
   design margin, and compare with the required value under a named tolerance
   so an exact equality passes.
7. Report the stage assessment, every part's local level, specified level and
   margin, the worst-case part, and a verdict carrying every finding.

## Pitfalls

- Holding every part to the mission environment figure. That is the level
  behind a reference thickness only; using it everywhere over-specifies deep
  parts and can quietly under-specify an exposed one if the reference was
  thicker than its local shielding.
- Interpolating the dose-depth curve linearly. The curve is close to a power
  law, so a linear read between decades lands high or low by a large factor,
  and the error is not conservative in general.
- Extrapolating past the curve span to keep a part in the analysis. The level
  the part is held to then comes from nowhere.
- Applying the design factor to the capability instead of the environment. The
  factor covers uncertainty in what the part will see, not in what it can
  take; moving it changes which quantity the margin protects.
- Failing a part that sits exactly on its required margin. The equality is met;
  only the floating-point representation is in question.
- Declaring the stages as a checklist rather than a sequence. A margin
  evaluated before the specified levels were derived evaluated something else.

## Behavior contract (gate 3)

The environment validation, stage-sequence assessment, dose-depth curve
validation, log-log interpolation and span refusal, design-factor application,
margin computation with an exact-equality tolerance and the worst-case part
selection are exercised by the gate 3 contract test:
scripts/test_q6015_radiation_hardness_assurance_process_overview.py against
scripts/q6015_radiation_hardness_assurance_process_overview_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6015_radiation_hardness_assurance_process_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

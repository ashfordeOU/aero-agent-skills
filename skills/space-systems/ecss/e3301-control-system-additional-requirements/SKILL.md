---
name: e3301-control-system-additional-requirements
description: "Evaluate the accuracy, sensor-noise and command-limiting rules a mechanism control system owes beyond loop shaping under ECSS-E-ST-33-01C clause 4.7.8.5. Use when a positioning allocation, a sensor description and a commanded profile exist and the design must be shown to deliver the accuracy without passing more noise than it can afford: sums systematic contributors directly, combines random ones in quadrature with a coverage factor, converts encoder resolution and noise density into error terms, names the driving contributor, runs commands through magnitude then rate clamps, and grades actuator capability. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-positioning-accuracy-budget, encoder-quantization-error-term, sensor-noise-bandwidth-contribution, command-magnitude-rate-clamping, actuator-effort-capability-margin, dominant-error-contributor."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-control-system-additional-requirements, mechanism-positioning-accuracy-budget, encoder-quantization-error-term, sensor-noise-bandwidth-contribution, command-magnitude-rate-clamping, actuator-effort-capability-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Additional Control Requirements (space-systems/ecss/e3301-control-system-additional-requirements)

Use when the task is the set of mechanism control-design rules that sit
beside loop shaping in ECSS-E-ST-33-01C clause 4.7.8.5 — the positioning
accuracy the loop must deliver, the sensor noise it is allowed to pass
into that accuracy, and the limiting that keeps a command inside what
the actuator and the driven structure can take.

## Domain quick reference

- An accuracy budget has two kinds of contributor and they do not
  combine the same way. Systematic terms — alignment offset, thermal
  drift, backlash offset, sensor bias — add directly, because nothing
  averages them away. Random terms combine in quadrature and are then
  expanded by the declared coverage factor. Root-sum-squaring a bias
  understates the budget; adding a noise term linearly overstates it.
- A sensor contributes two distinct random terms. Quantization is the
  encoder step divided by the square root of twelve, fixed by the
  resolution alone. Broadband noise is the spectral density integrated
  over the closed-loop noise bandwidth, so widening the loop raises it
  as the square root of the bandwidth — the same widening that was
  bought for response time.
- Command limiting is two clamps in a fixed order: magnitude first,
  then rate over the sample interval. Reversing them lets a large
  step through for one sample; omitting either leaves the actuator or
  the structure to do the limiting instead of the controller.
- Actuator capability is graded as a margin on the demand, not as a
  yes-or-no comparison. The available effort has to exceed the required
  effort by the declared fraction, and a demand that only just fits is
  a margin shortfall even though the mechanism moves.
- One contributor holding more than half the expanded budget is the
  design driver. Reducing anything else cannot recover the budget, so
  the driver is named in the result rather than left for the reader to
  find in the term list.

## Workflow

1. Validate the allocated accuracy and every declared contributor; a
   negative magnitude, a term named on both the systematic and random
   sides, or an empty contributor set is an input error.
2. Convert the sensor description into random terms: quantization from
   the encoder step, noise from the density and the closed-loop noise
   bandwidth. Refuse a noise density with no bandwidth to integrate it
   over rather than assuming one.
3. Form the budget — systematic sum plus coverage factor times the
   quadrature sum — grade it against the allocation with a named
   tolerance at the bound, and attribute it to the driving contributor.
4. Run the commanded profile through the limiter sample by sample,
   carrying the applied value forward, and record which samples hit the
   magnitude clamp and which hit the rate clamp.
5. Grade the actuator effort margin against the required fraction when
   effort figures are available.
6. Report the findings separately: accuracy shortfall, a random term
   dominating the budget, an undeclared limiter, saturated samples, and
   an actuator margin shortfall.

## Pitfalls

- Root-sum-squaring the whole error list. Systematic terms do not
  average down, and folding them into the quadrature sum makes a budget
  look comfortable that is not.
- Quoting sensor noise as a single number with no bandwidth. The figure
  that matters is the density integrated over the closed-loop noise
  bandwidth, so the same sensor contributes differently to a fast loop
  and a slow one.
- Treating the encoder step as the error. The uniform quantization
  standard deviation is the step over the square root of twelve; using
  the whole step double-counts and hides the term that actually drives
  the budget.
- Declaring a rate limit and no magnitude limit, or applying them in the
  other order. Both clamps are needed, and the magnitude clamp has to be
  first or a single large sample reaches the actuator.
- Accepting an actuator that merely produces the required effort. The
  requirement is a margin on the demand, and an equality at the limit is
  a representation question handled by the tolerance, not by lowering
  the required margin.

## Behavior contract (gate 3)

The contributor validation, quantization and noise-bandwidth conversion,
systematic-versus-random combination, driver attribution, ordered
magnitude-then-rate clamping with carried state, actuator margin grading
and finding assembly are exercised by the gate 3 contract test:
scripts/test_e3301_control_system_additional_requirements.py against
scripts/e3301_control_system_additional_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_control_system_additional_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

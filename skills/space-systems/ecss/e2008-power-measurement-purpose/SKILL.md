---
name: e2008-power-measurement-purpose
description: "Evaluate whether the output-power measurements bracketing an environmental test on a photovoltaic assembly can actually reveal the degradation they exist to detect, under ECSS-E-ST-20-08C clause 5.5.3.4.1: compute the relative power loss between the before and after measurements, combine their uncertainties into the smallest loss the pair can tell apart from noise, check that resolution against the allowable degradation, and map each bracketed exposure to the mechanism the pair is meant to expose. Use when scoping or reviewing the before-and-after power measurements around a solar-array assembly test. Trigger: ecss, e-st-20-08c, clause-5-5-3-4-1, photovoltaic-assembly-power-degradation, before-and-after-output-power-measurement, solar-array-power-loss-resolution, degradation-detection-uncertainty, bracketing-power-measurement-pair."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-power-measurement-purpose, photovoltaic-assembly-power-degradation, before-and-after-output-power-measurement, solar-array-power-loss-resolution, degradation-detection-uncertainty, bracketing-power-measurement-pair]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Power Measurement Purpose (space-systems/ecss/e2008-power-measurement-purpose)

Use when the task is to state and defend why output power is measured
before and after a test on a photovoltaic assembly under
ECSS-E-ST-20-08C clause 5.5.3.4.1 -- what the bracketing pair is meant
to expose, and whether the pair is good enough that a degradation at
the allowable limit would actually show up in it.

## Domain quick reference

- The exposure is not the measurement. A thermal-cycling run, a humidity
  exposure, a discharge run, a vibration run, an ultraviolet exposure or
  a particle irradiation each drive their own degradation mechanism, and
  the power pair is the common instrument that turns any of them into a
  number. Each bracketed exposure therefore contributes its own
  objective, and output-power retention is the objective they all share.
- Degradation is relative, not absolute. Four watts lost off a 400 W
  assembly and one watt lost off a 100 W assembly are the same result;
  only the loss expressed against its own baseline can be compared with
  an allowance or with another article.
- A measured gain is a real outcome of a real pair. An article that
  reads higher after the exposure than before it is telling you
  something about the measurement setup or the conditioning, so the sign
  is carried through rather than clipped to zero.
- The two measurements are independent, so their uncertainties combine
  in quadrature and not by addition. Covered by the declared factor,
  that combination is the smallest power loss the pair can tell apart
  from its own noise.
- Detection is a capability, not an outcome. A pair whose resolution is
  coarser than the allowable degradation will report a clean result for
  an article that has degraded past the limit, and no amount of
  post-processing recovers what the pair could not see.
- Purpose stated is not purpose served. An exposure with no baseline
  measured is a different, worse outcome than one whose measured loss
  simply came out large, and the two carry different actions.

## Workflow

1. Validate the detection policy first: allowance, coverage factor and
   resolution margin. A margin below unity would let a loss sitting
   inside the measurement noise count as detected, and is refused.
2. Group the declared bracketed exposures, rejecting an unrecognised one
   rather than ignoring it, and map each to the degradation the power
   pair is meant to expose. Append the shared output-power objective
   whenever any exposure is present.
3. Confirm both measurements exist. A missing baseline, or a missing
   post-test measurement, closes the case at once: nothing can be
   detected and the recorded objectives are all that survives.
4. Compute the relative power loss across the exposure against the
   baseline, preserving its sign.
5. Combine the two measurement uncertainties in quadrature, apply the
   coverage factor and the resolution margin, and compare the result
   with the allowance. A resolution landing exactly on the allowance is
   sufficient; the comparison tolerance absorbs representation error and
   the allowance does not move.
6. Close on one verdict: baseline not measured, degradation not
   resolvable, degradation within allowance, or degradation exceeding
   allowance -- with the objectives the pair serves attached to it.

## Pitfalls

- Reading the verdict off the measured loss alone. A 0.4 percent loss
  measured by a pair that resolves 5 percent is not a small degradation;
  it is an unsupported number, and reporting it as a pass is the exact
  failure this clause guards against.
- Adding the two uncertainties instead of combining them in quadrature.
  It overstates the resolution requirement and can reject a pair that
  was adequate, which is the cheaper error but still a wrong answer.
- Comparing absolute watts across articles. Assemblies differ in size,
  so a raw watt loss says nothing until it is referred to its own
  baseline.
- Treating a post-test measurement without a baseline as a result. There
  is no reference to subtract, so the number carries no information
  about the exposure at all.
- Clipping a measured gain to zero. It hides a setup or conditioning
  problem that would otherwise be visible before the article moves on.

## Behavior contract (gate 3)

The policy validation, relative degradation, combined uncertainty and
resolution, the resolvability decision, the exposure inventory and
objective mapping, and the purpose verdict are exercised by the gate 3
contract test: scripts/test_e2008_power_measurement_purpose.py against
scripts/e2008_power_measurement_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_power_measurement_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

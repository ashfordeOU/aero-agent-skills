---
name: e3102-heat-pipe-performance-verification
description: "Verify that a heat pipe still carries its required power once operating temperature, bend layout and adverse tilt have each been taken off the nameplate figure, per ECSS-E-ST-31-02C clause 5.5.5.2a. Use when the task is reading transport capability off a temperature curve without extrapolating past its ends, converting a power-length rating into a power at the pipe's effective length, subtracting the capability an adverse evaporator elevation consumes, applying the knockdown each bend costs at its radius, refusing a bend tighter than the qualified minimum, and retaining the worst operating point. Trigger: ecss, e-st-31-02c, heat-pipe-transport-capability, adverse-tilt-degradation, bend-radius-knockdown, capillary-limit-exhaustion, power-length-rating, worst-operating-point."
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
  tags: [ecss, e-st-31-02-two-phase-scope, e3102-heat-pipe-performance-verification, heat-pipe-transport-capability, adverse-tilt-degradation, bend-radius-knockdown, capillary-limit-exhaustion, power-length-rating]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase Heat Transport — Heat Pipe Performance Verification (space-systems/ecss/e3102-heat-pipe-performance-verification)

Use when the task is the heat pipe performance verification of
ECSS-E-ST-31-02C clause 5.5.5.2a -- establishing the transport capability
the pipe actually has at each operating point, after the operating
temperature, the bends built into the run and the adverse tilt of the
test or flight orientation have each taken their share of it.

## Domain quick reference

- Transport capability is a function of temperature and is not monotone.
  Working fluid properties -- latent heat, surface tension, liquid
  viscosity, vapour density -- move in opposite directions across the
  range, so the capability rises out of the cold end, peaks, and falls
  away again at the hot end. The cold case therefore often governs even
  though the hot case is the one everybody sizes for, and the curve must
  never be extrapolated past the temperatures it was measured at.
- The rating is a power-length product (W*m), not a power. A pipe rated
  240 W*m carries 200 W over 1.2 m and 120 W over 2 m. Comparing a W*m
  rating directly with a watt requirement is a unit error that flatters
  every long pipe.
- Adverse tilt subtracts capability, it does not scale it. Raising the
  evaporator above the condenser puts a hydrostatic head against the
  capillary pumping head, and what the wick has left is the difference.
  That is why the penalty is a sensitivity in watts per millimetre of
  elevation, and why enough tilt takes the capability to zero rather than
  to a small fraction of it.
- A favourable, gravity-aided orientation is not credited. The qualified
  capability is the one the pipe shows working against gravity; crediting
  a downhill test would qualify an orientation the flight article may
  never see.
- Bends cost capability multiplicatively and the cost depends on the
  radius. A bend at the qualified minimum radius distorts the wick and
  the vapour core most and carries the full declared knockdown; a
  generous radius carries proportionally less. A radius tighter than the
  qualified minimum is not a larger knockdown, it is outside the
  qualification, and the correct response is to refuse.
- The verdict is per operating point and the reported result is the worst
  of them. A pipe that passes the hot case and fails the cold one has
  failed.

## Workflow

1. Validate the capability curve: at least two points, strictly
   increasing in temperature, never a negative rating. Temperatures are
   signed, so the positive-only validation used for pressures and powers
   does not apply here.
2. Interpolate the power-length rating at the operating temperature and
   refuse a temperature outside the tabulated span rather than
   extrapolating the fall-off at either end.
3. Divide by the effective transport length to reach a power the
   requirement can be compared against.
4. Subtract the tilt penalty -- sensitivity times adverse elevation, with
   a favourable elevation contributing zero. If the result is at or below
   zero, report the capillary limit as exhausted and carry zero forward
   rather than a negative capability.
5. Apply the bend factor: per-bend knockdown scaled by the minimum
   radius over the actual radius, compounded once per bend. Refuse a
   radius below the qualified minimum.
6. Reduce capability against requirement to a ratio and treat an exact
   unity as compliant, absorbing only the representation error.
7. Repeat for every declared operating point, retain the lowest ratio as
   the governing point, and report exhaustion findings separately from
   shortfall findings so the two failure modes stay distinguishable.

## Pitfalls

- Verifying the hot case only. The capability curve falls away at both
  ends, and a cold-start or cold-survival point frequently governs.
- Comparing a W*m rating with a watt requirement. The rating has to be
  divided by the effective length first, and skipping that step passes
  every long pipe that should fail.
- Scaling capability by a tilt factor instead of subtracting a head. A
  multiplicative tilt model never reaches zero, so it never predicts the
  dryout that an over-tilted pipe actually shows.
- Crediting a gravity-aided orientation. It qualifies an orientation the
  pipe may never fly in and hides the against-gravity margin.
- Extrapolating the capability curve to cover an operating point just
  outside it. The curve's shape changes at both ends; the point needs
  measured data, not a straight line off the last segment.
- Treating a bend tighter than the qualified minimum as a bigger
  knockdown. The knockdown model was fitted inside the qualified range;
  outside it there is no model, only a refusal.

## Behavior contract (gate 3)

The curve validation and refusal to extrapolate, the power-length
conversion, the subtractive tilt penalty with its exhaustion case, the
radius-scaled compounding bend knockdown with its minimum-radius refusal,
the margin ratio and the worst-point retention are exercised by the gate
3 contract test:
scripts/test_e3102_heat_pipe_performance_verification.py against
scripts/e3102_heat_pipe_performance_verification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3102_heat_pipe_performance_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

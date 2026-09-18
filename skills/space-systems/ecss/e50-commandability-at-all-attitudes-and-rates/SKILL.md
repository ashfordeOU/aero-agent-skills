---
name: e50-commandability-at-all-attitudes-and-rates
description: "Assess whether a spacecraft stays commandable in every attitude and at every body rate under ECSS-E-ST-50C clause 5.4.1: work the uplink margin across a sampled sphere of receive-antenna gain, weight the result by solid angle so a pattern null is not hidden by dense sampling near a pole, then size the dwell a tumbling body gives the receiver against the time it needs to acquire and take one command frame. Use when an uplink must hold through a tumble, a safe mode or a lost attitude. Trigger: ecss, e-st-50c-communications-scope, telecommand-omnidirectional-coverage, uplink-antenna-pattern-null, spherical-command-coverage, tumbling-spacecraft-uplink, receiver-acquisition-dwell, body-rate-command-limit."
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
  tags: [ecss, e-st-50c-communications-scope, e50-commandability-at-all-attitudes-and-rates, telecommand-omnidirectional-coverage, uplink-antenna-pattern-null, spherical-command-coverage, tumbling-spacecraft-uplink, receiver-acquisition-dwell]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Commandability at All Attitudes and Rates (space-systems/ecss/e50-commandability-at-all-attitudes-and-rates)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.4.1 —
that the spacecraft can be commanded whatever attitude it holds and whatever
rate it is turning at — and the question is whether a real antenna pattern
and a real receiver meet it.

## Domain quick reference

- The requirement is written for the day attitude control has failed. It
  is not a nominal-pointing requirement, so it cannot be demonstrated with
  a pattern cut through the direction the high-gain antenna is aimed.
- Attitude coverage is a question about the whole sphere, and the sphere
  has to be sampled the way it is measured. A grid in polar and azimuth
  angle puts far more samples near the poles than the solid angle there
  deserves, so an unweighted pass rate flatters any design whose nulls
  sit near the equator.
- Two independent failures hide behind one symptom. A direction can fail
  because there is no gain there, or because the body is turning too fast
  for the receiver to finish acquiring, and the fixes are different: one
  is an antenna, the other is a receiver or a data rate.
- The dwell a tumble gives is geometry, not budget. The station sweeps
  through the usable beam in a time set by the beam width and the body
  rate, and the receiver has to lock up and take a whole command frame
  inside it or nothing is delivered.
- The useful number to hand back is the rate ceiling. Saying the design
  fails at fifteen degrees per second is less actionable than saying it
  holds up to six, because the second states what the platform has to
  keep below.
- Margin is a sum of decibel terms and dwell is a ratio. Both are floats,
  and a design that lands exactly on its required margin or exactly on
  its acquisition time must not be graded differently on two hosts.

## Workflow

1. Validate the gain samples as directions on the sphere: polar angle in
   range, azimuth wrapped once and not twice, gain a finite number.
2. Validate the shared uplink budget terms and derive the received power
   for each direction, then the margin over receiver sensitivity.
3. Compare each margin with the required value using an explicit
   tolerance, and collect every direction that falls short as a gap with
   its own coordinates and margin.
4. Weight each sample by the solid angle it stands for and report the
   covered fraction, so a small deep null is not averaged away.
5. Compute the dwell the worst-case body rate leaves, compare it with
   acquisition plus one frame, and invert the same relation to give the
   body rate ceiling.
6. Report the attitude finding and the rate finding separately, and
   combine them only in the verdict.

## Pitfalls

- Demonstrating coverage from a single principal-plane cut. A null off
  the cut plane is exactly the geometry a tumbling spacecraft will find,
  and a cut through the boresight cannot see it.
- Averaging pass rates over a polar grid without solid-angle weighting.
  The dense sampling near the poles inflates the result and can turn a
  real equatorial null into a rounding error.
- Treating a rate failure as a coverage failure. Adding antenna gain does
  nothing for a body rate that leaves the receiver no time to acquire,
  and the report has to keep the two apart or the fix goes to the wrong
  subsystem.
- Sizing the dwell against acquisition alone. A lock with no time left to
  take a whole command frame delivers nothing, so the frame duration
  belongs in the same comparison.
- Quoting the nominal-pointing margin for the omnidirectional case. The
  low-gain path is a different antenna with a different budget, and the
  requirement is about that path.
- Using a bare strict comparison on margin or dwell. A design built to
  land exactly on its bound is common, and a strict test makes its grade
  depend on which machine ran it.

## Behavior contract (gate 3)

The direction and budget validation, per-direction margin, gap collection,
solid-angle-weighted coverage fraction, dwell computation, rate ceiling and
combined verdict are exercised by the gate 3 contract test:
scripts/test_e50_commandability_at_all_attitudes_and_rates.py against
scripts/e50_commandability_at_all_attitudes_and_rates_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e50_commandability_at_all_attitudes_and_rates.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

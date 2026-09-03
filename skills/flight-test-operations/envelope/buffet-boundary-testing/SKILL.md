---
name: buffet-boundary-testing
description: "Use when you must plan and analyze the buffet boundary flight test for a transport airplane: schedule pull-up and steady-turn test points across a Mach sweep at constant altitude, detect buffet onset from the vertical accelerometer RMS rise above the 0.02 g threshold, convert the onset load factor to the boundary lift coefficient at each Mach, fit the buffet boundary line over the tested Mach band, and compute the buffet margin at the cruise Mach against the maneuver buffet target load factor. Produces the onset load factor and boundary lift coefficient per Mach, the fitted boundary line, the buffet margin, and the pass or fail verdict gating the high speed buffet clearance assessment. Trigger: buffet boundary flight test, buffet onset, high speed buffet, maneuver buffet, accelerometer RMS rise, pull-up sweep, buffet margin, boundary lift coefficient."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: envelope
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: envelope
  tags: [buffet-boundary-testing, buffet-boundary-flight-test, buffet-onset, high-speed-buffet, maneuver-buffet, accelerometer-rms-rise, pull-up-sweep, buffet-margin, boundary-lift-coefficient]
  version: 0.1.0
  author: Aero Agent Skills
---

# Buffet Boundary Testing (flight-test-operations/envelope/buffet-boundary-testing)

Use when the task is the buffet boundary flight test of a transport
airplane: scheduling pull-up and steady-turn points across a Mach sweep
at constant altitude, detecting buffet onset from the vertical
accelerometer RMS rise above threshold, converting the onset load factor
to the boundary lift coefficient, and scoring the buffet margin at the
cruise condition against a maneuver buffet target. This leaf implements
the standard RMS-based onset detection and boundary fitting in pure
Python, stdlib only. It pairs with flight-test-operations/envelope/
load-factor-envelope for the V-n context of the tested load factors,
envelope-expansion for the expansion program that precedes the boundary
probe, and flight-test-operations/flutter/flutter-testing for the other
high speed clearance boundary. The RMS floor, RMS rise per g and the
0.02 g onset threshold below are documented typical engineering
criteria, not regulation values; FAR/CS-25 are referenced for buffet and
vibration context by name and paraphrase only.

## Domain quick reference

- Test gross weight: W = m * g0, g0 = 9.80665 m/s2. Onset load factor
  n_onset is in g, so the lift at onset is n_onset * W.
- ISA state at altitude: T = 288.15 - 0.0065 * h below 11000 m
  (216.65 K above), P from the 5.25588 exponent law or the isothermal
  stratosphere pressure, rho = P / (287.05 * T).
- Dynamic pressure: q = 0.5 * rho * V^2 with V = M * a and a =
  sqrt(1.4 * 287.05 * T), the ISA speed of sound.
- Buffet-onset detection: with samples of (load factor n, vertical
  accelerometer RMS) sorted by n and non-decreasing in RMS, the onset
  load factor is the linear interpolation of the first crossing of the
  onset RMS threshold between two consecutive samples. The documented
  typical criteria are a 0.02 g onset RMS threshold, a 0.004 g RMS
  floor below onset, and a 0.4 g RMS rise per g of load factor above
  onset; they are engineering criteria, not regulation values.
- Boundary lift coefficient at one Mach: cl_buf = n_onset * W /
  (q * S) with S the reference wing area.
- Boundary line fit: cl_buf = slope * M + intercept by least squares
  (local 2x2 normal equations) over the tested Mach band.
- Buffet margin at cruise: n_buf_cruise = cl_buf(M_cr) * q(M_cr) * S /
  W, margin_n = n_buf_cruise - target_n; verdict
  "buffet-margin-pass" when margin_n >= 0.0, else "buffet-margin-fail".
- Units are SI throughout: kg, m, Pa, kg/m3, m/s; load factors in g.

## Workflow

1. Fix the test point schedule: weight_kg, wing_area_m2, altitude_m,
   the mach_list sweep and the load factor samples per Mach
   (rms_table), plus the cruise_mach where the margin is scored.
2. Get the atmosphere with isa_state, then the dynamic pressure q per
   Mach with dynamic_pressure.
3. Detect the onset load factor per Mach with onset_detect on the
   measured (n, rms_g) samples; the detector interpolates the first
   RMS crossing of onset_rms_g.
4. Convert each onset load factor to the boundary lift coefficient
   with boundary_lift_coefficient.
5. Fit the boundary line over the Mach band with fit_boundary_line,
   passing cruise_mach so cl_at_cruise is evaluated; omit cruise_mach
   when only the line is wanted (cl_at_cruise is then None).
6. Score the cruise condition: n_buf_cruise from the line at
   cruise_mach, the margin with buffet_margin against the maneuver
   buffet target, and the verdict.
7. Run the whole point schedule through analyze with one inputs dict;
   it returns the per-Mach q, onset_n and cl_buf points, the fit, the
   cruise reduction and the verdict.
8. Confirm the deterministic checks with the contract test
   scripts/test_buffet_boundary_testing.py.

## Worked example

Transport at W = 195000 kg (W = 1912297 N), S = 360.0 m2, altitude
10668 m, Mach sweep [0.74, 0.76, 0.78, 0.80, 0.82], pull-ups with
load factor samples every 0.1 g from 1.0 to 2.2. The measured RMS
fixture (built in the test, unknown to the module) follows rms(n) =
0.004 g below the model onset n_onset(M) = 1.90 - 1.50 * (M - 0.74),
then rises 0.4 g per g above it.

- ISA at 10668 m: T = 218.81 K, P = 23842 Pa, rho = 0.3796 kg/m3,
  a = 296.53 m/s.
- q and detected onset and cl_buf per Mach (module values):

| M | q (Pa) | onset_n (g) | cl_buf |
|---|---|---|---|
| 0.74 | 9139.2 | 1.940 | 1.1276 |
| 0.76 | 9639.9 | 1.910 | 1.0525 |
| 0.78 | 10154.0 | 1.867 | 0.9765 |
| 0.80 | 10681.3 | 1.844 | 0.9173 |
| 0.82 | 11222.1 | 1.820 | 0.8615 |

  With the 0.02 g threshold the detector crosses at the model onset
  plus (0.02 - 0.004) / 0.4 = 0.04 g. On the 0.1 g sample grid the
  crossing is exact where a sample sits at the model onset (M 0.74 and
  0.76 give 1.94 and 1.91) and interpolated just above it elsewhere
  (1.867 at M 0.78 and 1.844 at M 0.80, within one sample step of the
  idealized 1.88 and 1.85). Each cl_buf sits within 0.01 of the
  hand-checked spec anchors (1.1276, 1.0526, 0.9838, 0.9206, 0.8622).
- Least-squares fit over the band: slope = -3.337 per Mach,
  intercept = 3.590, so cl_buf(0.80) = 0.9203 on the line.
- Cruise reduction at M 0.80: q = 10681.3 Pa gives n_buf_cruise =
  0.9203 * 10681.3 * 360 / 1912297 = 1.8506. Margin vs target 1.3:
  +0.55, verdict "buffet-margin-pass". Same data against target 2.0:
  margin -0.15, verdict "buffet-margin-fail".

## Verification

- Confirm isa_state returns 288.15 K / 101325 Pa / 1.225 kg/m3 at sea
  level and 218.81 K / 23843 Pa / 0.3796 kg/m3 at 10668 m.
- Confirm dynamic_pressure equals 0.5 * rho * (M * a)^2 from the
  module ISA state at every Mach, and the q anchors 9139.5 to 11212.4
  Pa within 10 Pa (the spec q column carries hand-rounding spread).
- Confirm onset_detect returns 1.94 at M 0.74 and stays within 0.02
  of the idealized crossing at every Mach of the sweep.
- Confirm every cl_buf is within 0.01 of the anchors, n_buf_cruise is
  1.85 within 0.01, the margins are +0.55 and -0.15 within 0.02, and
  the verdicts are "buffet-margin-pass" and "buffet-margin-fail".
- Confirm the round trip: onset load factor to cl_buf and back
  recovers the load factor at fixed q.
- Confirm ValueError rejection of non-physical inputs: negative
  altitude, Mach outside (0.1, 2.0), non-positive weight, area, target
  or onset threshold, empty or 1-sample RMS rows, non-monotonic RMS,
  no onset crossing, fewer than two fit points, mismatched table
  lengths, and a cruise Mach outside the fitted band.
- Run the contract test offline: python3
  scripts/test_buffet_boundary_testing.py (38 tests, deterministic).

## Related leaves

- flight-test-operations/envelope/load-factor-envelope: the V-n and
  gust context that frames the load factors the boundary probe reaches.
- flight-test-operations/envelope/envelope-expansion: the expansion
  program and step sizing that grow the envelope toward the tested
  boundary.
- flight-test-operations/envelope/stall-characteristics-testing: stall
  behavior and entry techniques at the low speed end, outside this
  leaf's claim.
- flight-test-operations/flutter/flutter-testing: the flutter
  clearance boundary, the other high speed limit checked alongside the
  buffet boundary.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_buffet_boundary_testing.py

The test builds the measured RMS fixture from the spec onset model
n_onset(M) = 1.90 - 1.50 * (M - 0.74) and covers the ISA state anchors,
dynamic pressure identity and anchors, exact onset detection (1.94 at
M 0.74 and the sweep), boundary lift coefficients within 0.01 of the
anchors, the negative-slope boundary line fit with the cruise value,
the buffet margin pass and fail cases and their verdict strings, the
lift coefficient round trip, and ValueError rejection of every
non-physical input including the extrapolation guard.

## Compliance

- Standards referenced, not reproduced: FAR 25.251 and CS 25.251
  address vibration and buffeting, and the FAR/CS 25.3xx flight load
  factor provisions frame the load factor context, by name and
  paraphrase only per standards-map.yaml. The RMS floor, RMS rise and
  the 0.02 g onset threshold are documented typical engineering
  criteria, not regulation values.
- compliance: STANDARDS-REF, gated: false.

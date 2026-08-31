---
name: flutter-testing
description: "Use when you must assess flutter clearance for a flight test: compute the required flutter speed V_F_required as 1.2 times the design dive speed V_D, extrapolate the measured flutter speed from the damping versus test speed trend with a linear least squares fit and its zero crossing, check the frequency separation between structural modes against the 10 percent minimum, and judge the flutter margin ratio and the damping margin at the maximum test speed. Produces the required flutter speed, the extrapolated flutter speed, the frequency separation verdict, and the FAR 25.629 clearance verdict that gate the flutter test assessment. Trigger: flutter margin, damping trend extrapolation, flutter testing, frequency coalescence, frequency separation, design dive speed factor."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: flutter
  tags: [flutter-testing, flutter-margin, damping-trend, flutter-speed, frequency-separation, frequency-coalescence, design-dive-speed, structural-modes, aeroelasticity, flutter-clearance, flutter, damping]
  version: 0.1.0
  author: AeroSkills
---

# Flutter Testing (flight-test-operations/flutter/flutter-testing)

Use when the task is flutter clearance for a flight test: the
required flutter speed from the design dive speed factor, the
extrapolated flutter speed from the damping trend, the frequency
separation check between structural modes, and the FAR 25.629
flutter margin and damping margin verdicts.

## Domain quick reference

- Required flutter speed: V_F_required = margin_factor * V_D with
  margin_factor default 1.2 and V_D the design dive speed in m/s.
  The flight test program must demonstrate freedom from flutter up
  to at least this speed.
- Flutter speed from the damping trend: fit damping versus test
  speed with a linear least squares line over n points (slope m,
  intercept b) and extrapolate to the speed where the fitted
  damping crosses zero, V_F = -b / m. Closed forms:
  m = (n*sum(x*y) - sum(x)*sum(y)) / (n*sum(x^2) - sum(x)^2) and
  b = (sum(y) - m*sum(x)) / n.
- Frequency separation: two structural modes must stay separated;
  the check is |f1 - f2| / ((f1 + f2) / 2) >= min_frac with
  min_frac default 0.10 (10 percent). Falling below the minimum
  indicates frequency coalescence, the flutter precursor.
- Flutter margin ratio: ratio = V_F_measured / V_D; per the
  FAR 25.629 context the clearance verdict passes when ratio >= 1.2
  (the 1.2 factor is common certification practice; the exact basis
  comes from the flight test program).
- Damping margin at the maximum test speed: the measured damping at
  V_test must stay at or above the required minimum, default 0.03;
  negative damping means the mode already fluttered at the test
  speed.

## Workflow

1. Collect V_D (design dive speed) and compute the required flutter
   speed with required_flutter_speed(v_d).
2. Gather the damping measurements (speeds, dampings) from the
   flight test and extrapolate the flutter speed with
   flutter_speed_from_damping(speeds, dampings); review the fit
   before trusting the crossing.
3. Check each pair of structural modes with
   frequency_separation(f1, f2) and flag any pair below the 10
   percent minimum.
4. Compare the measured flutter speed with V_D using
   flutter_margin_ratio(v_f_measured, v_d); a ratio below 1.2
   fails the clearance.
5. Check the damping at the maximum test speed with
   damping_margin(damping_at_v_test); a value below the minimum
   fails the clearance.
6. Gate the flutter test assessment on the margin ratio verdict and
   the damping margin verdict.

## Pitfalls

- Feeding the damping points out of speed order: the speeds must be
  strictly increasing or the least squares fit is meaningless and
  raises ValueError.
- Extrapolating far past the tested range: the zero crossing is an
  extrapolation, so the farther V_F sits beyond the last test speed
  the less certain it is; the build-up program tests closer to the
  crossing before clearing.
- A flat or rising damping trend: no zero crossing exists and the
  function raises ValueError; investigate the measurement before
  claiming clearance.
- Confusing the two margins: the flutter margin ratio compares the
  flutter speed with V_D, while the damping margin compares damping
  at the maximum test speed with the minimum; each gates
  independently.
- Using a non-positive V_D: the required flutter speed and the
  margin ratio both raise ValueError instead of reporting a
  nonsense margin.
- Ignoring frequency coalescence: two modes converging toward the
  10 percent separation minimum warn of a coupling that can drop
  the flutter speed below the extrapolated trend.

## Behavior contract (gate 3)

The required flutter speed, damping trend extrapolation, frequency
separation, flutter margin ratio, and damping margin logic is
exercised by the gate 3 contract test: scripts/test_flutter_testing.py
against scripts/flutter_testing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_flutter_testing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the 1.2 flutter
  margin factor, the damping trend extrapolation, and the frequency
  separation practice sit in the FAR 25.629 context as common
  certification practice, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

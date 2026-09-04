---
name: speed-stability
description: "Use when you must assess the static speed stability of a fixed-wing transport from its trim drag balance: build the thrust required curve versus true airspeed from the drag polar, its zero lift drag and induced drag factor, derive the curve slope dT/dV, classify each level flight trim speed as speed stable or speed unstable on the back side of the curve, locate the minimum drag speed boundary where the slope crosses zero, and compute the slow flight stability margin between a proposed minimum speed and the unstable region of reversed command. Produces the thrust required curve points, the slope classification table, the minimum drag speed, the stability verdict at every trim speed, and the speed stability margin that gate the minimum speed selection. Trigger: speed stability, back side of curve, region of reversed command, minimum drag speed boundary, trim speed classification, slow flight stability margin, thrust curve slope."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [speed-stability, static-speed-stability, back-side-of-curve, region-of-reversed-command, minimum-drag-speed-boundary, trim-speed-classification, slow-flight-stability-margin, thrust-curve-slope]
  version: 0.1.0
  author: Aero Agent Skills
---

# Static Speed Stability (flight-mechanics/performance/speed-stability)

Use when the task is the static speed stability assessment of a
fixed-wing aircraft from its trim drag balance. Below the minimum
drag speed the aircraft flies on the back side of the thrust required
curve, the region of reversed command: drag rises as the airplane
slows, so a small speed disturbance from the trimmed level flight
point produces no restoring thrust imbalance and the trim point is
speed unstable. This leaf computes the thrust required curve versus
true airspeed from the drag polar, derives its analytic slope dT/dV,
classifies each candidate trim speed, locates the minimum drag speed
boundary, and reports the slow flight stability margin. It pairs with
performance/thrust-required, which computes the same drag polar
family, and it feeds the excess thrust users climb-performance and
turn-performance. This is the performance trim concept of speed
stability, not a control surface or pitch handling check.

## Domain quick reference

- Dynamic pressure: q = 0.5 * rho * v^2, with rho the air density and
  v the true airspeed.
- Induced drag factor: k = 1 / (pi * oswald_e * aspect_ratio), from
  the Oswald span efficiency and the aspect ratio.
- Thrust required for level unaccelerated flight: T = cd0 * q * S +
  k * W^2 / (q * S), the sum of the parasite drag and the induced drag,
  with S the reference wing area and W the aircraft weight.
- Thrust curve slope, exact derivative of T with respect to v: dT/dv =
  cd0 * rho * v * S - 4 * k * W^2 / (rho * v^3 * S). The induced term
  carries coefficient 4 so that the slope zero lands exactly on the
  closed-form minimum drag speed (wave-27 ops approved this exact
  derivative over the draft's factor-2 term; the test file records the
  adaptation).
- Minimum drag speed: v_md = (2 * W / (rho * S))^0.5 * (k / cd0)^0.25.
  At v_md the parasite drag equals the induced drag and dT/dv is zero.
- Speed stability verdict: stable when dT/dv > 0 (front side, above
  the back side), unstable when dT/dv < 0 (back side, region of
  reversed command), neutral when |dT/dv| < 1e-9 N/(m/s).
- Slow flight stability margin: margin_ms = v - v_md. A negative
  margin with unstable_below True means the candidate speed sits on
  the region of reversed command.
- Units are SI throughout: N, m/s, kg/m^3, m^2.

## Workflow

1. Gather the aircraft state: weight_n, wing_area_m2, the air density
   rho_kg_m3 (default 1.225 at sea level), the drag polar terms cd0,
   oswald_e and aspect_ratio, and the candidate trim speeds
   trim_speeds_ms.
2. Compute the induced drag factor with the module constant relation
   k = 1 / (pi * oswald_e * aspect_ratio).
3. Get the minimum drag speed boundary with min_drag_speed; it splits
   the speed range into the stable front side and the unstable back
   side.
4. Build the thrust required curve with thrust_required over the swept
   range from 0.5 * v_md to 1.5 * v_md (25 points via analyze).
5. Derive the slope dT/dV at each candidate speed with d_thrust_dv and
   classify the trim point with speed_stability_verdict: stable,
   unstable, or neutral.
6. Compute the slow flight stability margin with margin_to_back_side
   for each candidate speed (v_md, unstable_below, margin_ms).
7. Run analyze for the full assessment dict: v_md_ms,
   trim_classifications with {speed, dT_dv, verdict}, margins with
   {speed, margin_ms, unstable_below}, and the curve points.
8. Confirm the deterministic checks with the contract test
   scripts/test_speed_stability.py.

## Worked example

Transport at sea level: W = 600000 N, S = 120 m2, rho = 1.225 kg/m3,
cd0 = 0.02, e = 0.8, AR = 9.

- Induced drag factor: k = 1 / (pi * 0.8 * 9) = 0.0442097.
- Minimum drag speed: v_md = (2 * 600000 / (1.225 * 120))^0.5 *
  (0.0442097 / 0.02)^0.25 = 110.17 m/s (module value 110.1676 m/s,
  within 0.01 of the worked anchor).
- Slope at 80 m/s (below v_md): dT/dv = -610.65 N/(m/s) < 0, verdict
  unstable, the trim point sits on the back side.
- Slope at 130 m/s (above v_md): dT/dv = +185.08 N/(m/s) > 0, verdict
  stable.
- Slope at v_md: zero to machine precision (5.7e-14), verdict neutral.
- Slow flight stability margin at 80 m/s: margin_ms = 80 - 110.17 =
  -30.17 m/s, unstable_below True. The 80 m/s approach trim speed sits
  below the minimum drag speed on the region of reversed command.
- Thrust at v_md: T = 2 * cd0 * q_md * S = 35682.5 N, with the parasite
  drag equal to the induced drag at the minimum drag point.
- Curve: 25 points from 55.08 m/s (0.5 * v_md) to 165.25 m/s
  (1.5 * v_md), minimum thrust at the v_md sample, monotonic thrust on
  the stable branch.

## Verification

- Confirm v_md = 110.1676 m/s: it matches the closed form to 1e-9 and
  sits within 0.01 of the 110.17 m/s worked value. The exact radicals
  are sqrt(2W/(rho S)) = 90.351 and (k/cd0)^0.25 = 1.21933.
- Confirm the derivative zero lands on v_md: |dT/dv(v_md)| < 1e-6, and
  the analytic slope matches a central finite difference at 80 and
  130 m/s within 0.1 percent.
- Confirm the verdicts: unstable at 80 m/s, stable at 130 m/s, neutral
  at v_md, unstable below v_md and stable above it by 0.1 percent.
- Confirm the margin at 80 m/s: -30.17 m/s with unstable_below True.
- Confirm thrust at v_md equals 2 * cd0 * q_md * S (parasite equals
  induced), and that thrust rises as the airplane slows on the back
  side.
- Confirm every non-positive weight, wing area, density, cd0, induced
  factor or trim speed, every Oswald efficiency outside (0, 1], and an
  empty trim list raises ValueError.
- Run the contract test offline: python3
  scripts/test_speed_stability.py (38 tests, deterministic).

## Pitfalls

- Judging stability from the thrust curve shape instead of the slope: the
  verdict is dT/dv at the trim speed (positive = stable front side, negative
  = back side, |dT/dv| < 1e-9 = neutral), and the analytic derivative
  carries coefficient 4 on the induced term so that its zero lands exactly
  on v_md.
- Calling the minimum-drag speed 'neutral' in the wrong sense: at v_md the
  slope is zero to machine precision and the verdict is neutral; below v_md
  the trim is speed unstable (region of reversed command), not merely 'low
  performance'.
- Quoting a slow-flight margin without its sign: margin_ms = v - v_md is
  negative below the boundary with unstable_below True (about -30.2 m/s at
  80 m/s for the worked transport); a negative margin on the back side is
  the warning, not a number to minimize.
- Evaluating far outside the swept band: the curve is swept over 0.5*v_md to
  1.5*v_md (25 points) and the drag polar is parabolic about that trim
  family.
- Non-positive weight, wing area, density, cd0, induced factor or trim
  speed, Oswald efficiency outside (0, 1], and an empty trim list raise
  ValueError.

## Related leaves

- flight-mechanics/performance/thrust-required: the same drag polar
  family, thrust analysis for level flight, the sibling this leaf
  follows on.
- flight-mechanics/performance/climb-performance and
  flight-mechanics/performance/turn-performance: the excess thrust
  users of this trim analysis.
- aerodynamics/drag-polars/drag-polar and
  aerodynamics/drag-polars/parasite-drag: the drag polar coefficient
  source for the trim drag balance.
- flight-mechanics/stability-control/longitudinal-stability: the
  distinct pitch stability concept about the aerodynamic center, not
  the performance speed stability treated here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_speed_stability.py

The test covers the induced factor, the closed-form v_md and its
110.17 m/s worked anchor, the derivative zero on v_md, the analytic
slope against central finite differences at 80 and 130 m/s, verdicts
(stable, unstable, neutral) with boundary checks, margins at 80 m/s
(-30.17 m/s) and 130 m/s, thrust curve checks at v_md (parasite equals
induced, thrust minimum and monotonic stable branch, 25 swept points),
the analyze output structure for the default trim list, and ValueError
rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: the FAR 25 and CS 25
  speed-stability context frames the assessment (reference-only per
  standards-map.yaml); the drag polar relations above are standard
  engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.

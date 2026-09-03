# Wave-27 leaf spec: speed-stability (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/speed-stability/
- Pack: performance (existing siblings: breguet-range,
  breguet-endurance, specific-range, takeoff-performance,
  landing-performance, climb-performance, descent-performance,
  turn-performance, glide-performance, wind-effects, oei-climb-gradient,
  energy-height, thrust-required, windshear-analysis)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: flight-mechanics

## Claim

Assess the static speed stability of a fixed-wing aircraft from the
trim drag balance: compute the thrust-required curve versus true
airspeed from the drag polar, derive its slope dT/dV, classify each
candidate trim speed as speed-stable or speed-unstable (back side of
the thrust-required curve / region of reversed command), locate the
minimum-drag speed boundary, and determine the slow-flight stability
margin between a proposed minimum speed and the unstable region.
Produces the thrust-required curve points, the slope classification
table, the minimum-drag speed, the stability verdict at each trim
speed, and the speed-stability margin.

Does NOT do: compute climb rate or time to climb (climb-performance);
compute the full power-required curve and its minimum-power speed for
level-flight performance (thrust-required); estimate drag-polar
coefficients from geometry (drag-polar, parasite-drag in
aerodynamics); or evaluate static longitudinal pitch stability about
the neutral point (longitudinal-stability). Speed stability here is the
performance/trim concept: whether a small speed perturbation from a
trimmed level-flight point produces a restoring excess-thrust imbalance
on the back side of the curve, not a stick-force or hinge-moment
stability check.

## Model (implement exactly)

Inputs:
- weight_n (float, aircraft weight N),
- wing_area_m2 (float, reference wing area),
- rho_kg_m3 (float, air density, default 1.225),
- cd0 (float, zero-lift drag coefficient),
- oswald_e (float, span efficiency),
- aspect_ratio (float, AR),
- trim_speeds_ms (list of float, candidate level-flight speeds to
  classify, e.g. [45.0, 60.0, 80.0, 100.0]).
Constants:
- G0 = 9.80665.
Helper: induced factor k = 1.0 / (pi * oswald_e * aspect_ratio).

Functions:
- thrust_required(velocity_ms, weight_n, wing_area_m2, rho_kg_m3, cd0,
  k) -> float N:
  q = 0.5 * rho * v^2; T = cd0 * q * S + k * W^2 / (q * S).
  (Same physics family as thrust-required leaf but returns only the
  thrust value for slope analysis; no ValueError beyond positive args.)
- d_thrust_dv(velocity_ms, weight_n, wing_area_m2, rho_kg_m3, cd0, k)
  -> float N/(m/s): analytic derivative
  dT/dv = cd0 * rho * v * S - 2 * k * W^2 / (rho * v^3 * S).
- min_drag_speed(weight_n, wing_area_m2, rho_kg_m3, cd0, k) -> float
  m/s: v_md = (2 * W / (rho * S))^0.5 * (k / cd0)^0.25.
  (Classic closed form; assert it matches the zero of d_thrust_dv.)
- speed_stability_verdict(velocity_ms, ...) -> str: "stable" when
  d_thrust_dv > 0 (above the back side); "unstable" when < 0; "neutral"
  when |dT/dv| < 1e-9.
- margin_to_back_side(velocity_ms, ...) -> dict: {v_md, unstable_below
  (bool), margin_ms = velocity - v_md}.
- analyze(weight_n, wing_area_m2, rho_kg_m3, cd0, oswald_e,
  aspect_ratio, trim_speeds_ms) -> dict:
  {v_md_ms, trim_classifications: [{speed, dT_dv, verdict}], margins:
  [{speed, margin_ms, unstable_below}], curve: [{speed,
  thrust_required_N}] over a swept range 0.5*v_md to 1.5*v_md (25
  points)}.

ValueError on: weight <= 0, wing area <= 0, rho <= 0, cd0 <= 0,
oswald_e <= 0 or > 1, aspect_ratio <= 0, empty trim list, any trim
speed <= 0.

## Worked example

Transport: W = 600000 N, S = 120 m2, rho 1.225, cd0 = 0.02, e = 0.8,
AR = 9. k = 1/(pi*0.8*9) = 0.0442097.
- v_md = (2*600000/(1.225*120))^0.5 * (0.0442097/0.02)^0.25 =
  (8163.265)^0.5=90.35... compute exactly: 2W/(rho S) = 1200000/147 =
  8163.265; sqrt = 90.351. (k/cd0)^0.25 = (2.21048)^0.25 = 1.21948
  (assert within 1e-4). v_md = 110.18 m/s. Assert module value within
  1e-6 of the module's own closed form and within 0.01 of 110.18.
- At 80 m/s (< v_md): dT/dv < 0 -> "unstable" (back side). At 130 m/s:
  dT/dv > 0 -> "stable". Assert verdicts.
- margin at 80: margin_ms = -30.18, unstable_below True. Assert.
- curve: assert 25 points, monotonic thrust on the stable branch,
  thrust at v_md equals 2*cd0*q_md*S (parasite = induced at min drag).
- ValueErrors: weight 0, aspect_ratio 0, e = 1.1, empty list.
Keep at least 18 test methods.

## Corpus tasks (ids w27-speed-stability-1/2)

Distinctive tokens: speed stability, back side of the thrust required
curve, region of reversed command, minimum drag speed boundary, trim
speed classification, slow flight stability margin, thrust curve slope.
Avoid: rate of climb, service ceiling (climb-performance); power
required curve, minimum power speed as the headline (thrust-required);
stick force, elevator, neutral point (control-surface-effectiveness /
longitudinal-stability); flight test (flight-test-operations).

1. "classify the level flight trim speeds of the transport for static
   speed stability: find the minimum drag speed boundary and mark which
   trim speeds sit on the back side of the thrust required curve with
   an unstable slope"
2. "compute the slow flight stability margin for the airplane: check
   whether the 80 m/s approach trim speed is below the minimum drag
   speed on the region of reversed command and give the margin"

## SKILL body notes

Pair with thrust-required (same drag-polar family; this leaf is the
stability-of-trim follow-on), climb-performance and turn-performance
(excess-thrust users), and note the aerodynamics drag-polar leaves as
the coefficient source. Keep the back-side definition explicit: below
the minimum-drag speed the drag (hence thrust required) rises as the
airplane slows, so the trim point is speed-unstable. Standards
referenced (FAR/CS 25 speed-stability context) not reproduced.

# Wave-30 leaf spec: boundary-layer-transition (aerodynamics, boundary-layer pack)

- Path: skills/aerodynamics/boundary-layer/boundary-layer-transition/
- Pack: boundary-layer (sibling: boundary-layer-theory only).
- Standards ids: naca-tr-824 (reference-only; aerodynamics family convention).
  Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Predict the laminar-turbulent transition location on a two-dimensional body
from its edge-velocity distribution: grow the laminar boundary layer with the
Thwaites integral relation to obtain the momentum thickness at each station,
evaluate the Michel transition criterion against the local Reynolds numbers,
and interpolate the first station where the criterion is crossed to give the
transition location. Produces the momentum-thickness Reynolds history, the
Michel criterion margin at each station, and the transition location that gate
a natural-transition estimate for an airfoil or body.

Does NOT do: compute laminar or turbulent boundary-layer thicknesses and skin
friction on a smooth flat plate or classify a flat-plate flow by a single
transition Reynolds number (boundary-layer-theory owns the Blasius and 1/7
power-law correlations and the regime classification); model Tollmien-Schlichting
wave growth with an eN envelope integration (out of scope; this leaf uses the
Michel empirical criterion on the Thwaites momentum thickness); estimate
transition delay from roughness, sweep, or suction (inputs are two-dimensional
clean-surface only); solve the full boundary-layer equations (no PDE solver;
the Thwaites relation is an integral method).

## Model (implement exactly)

Module constants:
- MICHEL_A = 1.174, MICHEL_B = 22400.0, MICHEL_P = 0.46 (Michel criterion
  Re_theta,tr = A * (1 + B / Re_x) * Re_x**P).
- THWAITES_C = 0.45 (Thwaites constant).

Functions (pure stdlib; xs and ues are equal-length lists of floats):
- momentum_thickness_profile(xs, ues, nu) -> list of theta at each station:
  Thwaites integral theta(x)^2 = 0.45 * nu / Ue(x)**6 * integral_0^x
  Ue(xi)^5 d(xi); evaluate the integral with the trapezoid rule over the
  supplied stations (cumulative). ValueError if len(xs) < 2 or lengths differ,
  any x < 0 or not strictly increasing, any ue <= 0, nu <= 0.
- re_theta_profile(xs, ues, theta_list) -> list of Re_theta = Ue * theta / nu
  at each station (nu needed; implement signature with nu).
- michel_criterion(re_x, re_theta) -> bool: transition onset when
  re_theta >= MICHEL_A * (1 + MICHEL_B / re_x) * re_x**MICHEL_P.
  ValueError if re_x <= 0 or re_theta < 0.
- michel_threshold(re_x) -> float: the criterion value (right-hand side).
- transition_location(xs, ues, nu) -> dict: {theta_list, re_theta_list,
  criterion_margin_list (re_theta - threshold at each station),
  x_transition (float or None if the criterion is never crossed),
  transition_index (int or None)}. The transition index is the first station
  where margin >= 0; if the crossing falls between stations i-1 and i, do NOT
  interpolate x here (leave x_transition as the station x value), but ALSO
  return interp_x_transition = linear interpolation between (x[i-1], margin
  [i-1]) and (x[i], margin[i]) at margin = 0 when a crossing exists.
  ValueErrors propagate from the helpers.
- flat_plate_transition(nu, ue, x_max) -> float or None: closed-form check on
  a flat plate with constant edge velocity: theta from the Thwaites closed
  form Re_theta = sqrt(0.45) * sqrt(Re_x) (0.6708 sqrt(Re_x)); find where it
  crosses the Michel threshold over x from 1e-3 to x_max in 500 uniform steps
  (linear scan, return first crossing x, else None). This is a verification
  helper; document it as the flat-plate natural-transition check.

## Worked example

Flat plate: nu = 1.46e-5 m2/s, Ue = 30 m/s. Momentum thickness at x = 1.0 m:
theta = 0.6708 * sqrt(Re_x) * nu / Ue? (build theta from the relation
Re_theta = 0.6708 sqrt(Re_x) so theta = 0.6708 sqrt(Ue x / nu) * nu / Ue;
at x = 1 m: Re_x = 30 / 1.46e-5 = 2.0548e6, sqrt = 1433.5, Re_theta =
0.6708 * 1433.5 = 961.6, theta = 961.6 * 1.46e-5 / 30 = 4.680e-4 m.)

Deterministic anchors (module outputs are the assert targets; bounds):
- flat_plate_transition returns x in 1.4e6-2.2e6 m? NO: it returns x in
  METERS: x_tr in 1.4-2.2 m (since Re_x,tr ~1.7e6-2.1e6 at Ue 30 -> wait:
  Re_x,tr is ~1.75e6 per the Thwaites+Michel crossing, so x_tr = 1.75e6 *
  nu / Ue = 1.75e6 * 1.46e-5 / 30 = 0.852 m. Set bound 0.6-1.1 m.)
- Re_theta at the flat-plate crossing in 800-1100.
- momentum_thickness_profile on a 3-station flat plate (x = 0.25, 1.0, 2.0 m)
  is monotonic increasing and matches the closed form 0.6708 sqrt(Re_x) nu/Ue
  within 1e-6 relative at each station (the trapezoid Thwaites integral is
  exact for constant Ue).
- criterion_margin at x just below x_tr is negative and just above is
  positive in the flat_plate_transition scan.
If a value is outside its bound, debug before writing tests. Show real module
outputs in the SKILL.md worked example.

## Validation list (contract test must include)

- ValueError: unequal-length xs/ues, non-increasing x, ue <= 0, nu <= 0,
  re_x <= 0, re_theta < 0.
- Flat-plate identity: Re_theta vs 0.6708 sqrt(Re_x) on the closed form.
- Determinism.

## Corpus fragment (eval/hit1-wave30-boundary-layer-transition.yaml)

Forbidden tokens (siblings): displacement-thickness, momentum-thickness
alone, skin-friction, blasius, 1/7-power, laminar-turbulent classification on
a flat plate by Reynolds number alone (boundary-layer-theory). Use ONLY:
boundary-layer-transition, transition-location, thwaites-integral,
michel-criterion, natural-transition.

Query 1: "Predict the boundary-layer-transition location on an airfoil from an
edge velocity distribution with the thwaites-integral and the
michel-criterion" (id w30-boundary-layer-transition-1).
Query 2: "Estimate natural-transition on a flat plate: where does the
laminar boundary layer become turbulent at Ue 30 m/s and nu 1.46e-5" (id
w30-boundary-layer-transition-2).
intent: "aerodynamics; laminar-turbulent transition location by Thwaites +
Michel".

## Description/tag guidance

Description opens "Use when you must predict the laminar-turbulent transition
location on a two-dimensional body from its edge-velocity distribution:" and
lists the outputs in the Claim. First tag: boundary-layer-transition.
Additional tags: thwaites-integral, michel-criterion, transition-location,
natural-transition. No generic single words. 50-150 words, <=1000 chars, no em
dash, no "classified".

# Wave-38 leaf spec: boundary-layer-separation (aerodynamics, boundary-layer pack)

- Path: skills/aerodynamics/boundary-layer/boundary-layer-separation/
- Pack: boundary-layer. Closest siblings: boundary-layer-theory (flat-plate
  zero-pressure-gradient thickness and skin friction), boundary-layer-
  transition (grows the laminar layer with Thwaites and evaluates the Michel
  transition criterion - the Thwaites traverse ends at TRANSITION, not at
  separation), cfd-turbulence-modeling (mentions separation only as a
  modeling pitfall). Whole-tree grep: "stratford", "separation criterion",
  "adverse pressure gradient", "separation point" = ZERO owning hits in any
  leaf; the boundary-layer pack files have zero "separation" mentions. ZERO
  owners of the separation-prediction function. GENUINE AERO gap (fresh
  probe).
- Standards id: naca-tr-824 (reference-only; family spine - laminar
  boundary-layer correlations and pressure-gradient behavior sit in the
  NACA/classical aero context). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Predict the boundary-layer separation location on a two-dimensional body
from its edge-velocity or pressure distribution: grow the laminar layer
with the Thwaites integral and flag the first station where the Thwaites
lambda parameter crosses -0.09 (the laminar separation criterion), and
evaluate the Stratford turbulent separation criterion on the pressure
recovery to estimate the turbulent separation station and margin. Produces
the laminar separation station (or none), the turbulent separation station
and the margin below the Stratford threshold that gate airfoil and
inlet/duct design checks. Does NOT do: zero-pressure-gradient flat-plate
thickness and skin friction (boundary-layer-theory); transition location
prediction by the Michel criterion (boundary-layer-transition); RANS
turbulence-model selection (cfd-turbulence-modeling).

## Model (implement exactly)

Laminar (Thwaites):
- The edge velocity U(x) is supplied as a callable or a station list with
  velocities; the module integrates theta^2 = 0.45 * nu / U^6 *
  integral_0^x U^5 dx by the trapezoid rule over the stations, starting
  from theta = 0 at the stagnation point (x = 0, U = 0 is handled by
  starting the integral at the first positive station with theta from the
  stagnation-point similarity form or by skipping the singular point and
  starting integration at the first station with U > 0).
- lambda = theta^2 / nu * dU/dx (dU/dx by central difference on the
  station list, forward at the first interior point).
- Laminar separation: first station with lambda <= -0.09. None if lambda
  stays above -0.09 through the whole run.
- THWAITES_LAMBDA_SEP = -0.09 module constant.

Turbulent (Stratford-style pressure recovery, paraphrased criterion):
- The pressure coefficient C_p(x) is supplied as stations. Compute the
  Stratford-style separation parameter S(x) = C_p(x) * sqrt((x / C_p(x)) *
  dC_p/dx) using central differences on the recovery (dC_p/dx > 0)
  portion. Flag the first station where S >= 0.35.
- STRATFORD_SEP = 0.35 module constant. Margin = 0.35 - S at the last
  station before crossing (positive margin means not yet separated).

Functions (pure stdlib):
- thwaites_lambda(xs, us, nu) -> list of lambda values (same length as
  xs), ValueError if xs/us not same length, nu <= 0, or us not all >= 0.
- laminar_separation_station(xs, us, nu) -> (index, x) of the first
  station with lambda <= -0.09, or None.
- stratford_separation_station(xs, cps) -> (index, x) of the first
  station with S >= 0.35 on the recovery side, or None.
- separation_margin(xs, cps) -> float: 0.35 - max S over the recovery
  side before the crossing (positive = attached at the end).
ValueErrors: non-physical inputs as above; empty lists.

Identity to test: a favorable-gradient flow (accelerating U) has no laminar
separation; a linearly decelerated flow separates at a station inside the
body; Stratford margin is positive on a mild recovery and negative (or the
station exists) on a steep recovery.

## Worked example

Verified at prep with nu = 1.5e-5 m2/s and the linearly decelerated edge
velocity U(x) = U0 * (1 - x / L), L = 1 m, U0 = 30 m/s over 400001
stations (integration step 2.5e-6 m):
- Laminar separation at x = 0.1231 m (lambda crosses -0.09 there), U at
  that station 26.31 m/s.
- With an accelerating flow U(x) = 30 * (1 + 0.2 * x) over 1 m: no
  laminar separation (None).
- Stratford: pressure recovery C_p(x) = 0.4 * x^2 over x in [0, 1]
  (10 stations): S crosses 0.35 at station index 8 (x = 0.8), S = 0.3505.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (the Thwaites separation point of a linear
deceleration is a classic result near 12 percent chord; the Stratford
crossing is a direct evaluation of the criterion).

## Validation list (contract test must include)

- Thwaites lambda list on the linear deceleration: monotone decreasing;
  negative at the end.
- Laminar separation station within 1 percent of 0.1231 m on the linear
  deceleration.
- Accelerating flow returns None for laminar separation.
- Stratford crossing at index 8 on the C_p = 0.4 x^2 recovery; margin
  positive before the crossing.
- No-crossing recovery returns None and a positive margin.
- ValueErrors: mismatched station/velocity lengths, nu <= 0, negative
  velocity, empty lists.
- Determinism; float outputs as documented.

## Corpus fragment (eval/hit1-wave38-boundary-layer-separation.yaml)

Query 1 (copy verbatim):
  "locate the laminar separation point where the thwaites-lambda-criterion crosses minus 0.09 on the edge-velocity distribution"
  intent: "aerodynamics; laminar separation station from the Thwaites lambda traverse"
  expected_skill: "aerodynamics/boundary-layer/boundary-layer-separation"
Query 2 (copy verbatim):
  "apply the stratford-separation-criterion to the pressure-recovery distribution to estimate the turbulent separation location and margin"
  intent: "aerodynamics; turbulent separation by the Stratford pressure recovery criterion"
  expected_skill: "aerodynamics/boundary-layer/boundary-layer-separation"
Task ids: w38-boundary-layer-separation-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must predict boundary layer
separation:" and include the outputs in the Claim. First tag:
boundary-layer-separation. Additional tags ONLY: thwaites-lambda-
criterion, stratford-separation-criterion, laminar-separation-point,
turbulent-separation-station, separation-margin, adverse-pressure-
gradient. NEVER single generic words (separation, boundary, layer,
pressure, gradient, transition). 50-150 words, <=1000 chars, no em dash,
no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): displacement thickness, momentum
thickness on a flat plate, skin friction coefficient (boundary-layer-
theory); Michel criterion, transition location, transition point
(boundary-layer-transition); turbulence model, y-plus, mesh (cfd-
turbulence-modeling / cfd-mesh-generation).

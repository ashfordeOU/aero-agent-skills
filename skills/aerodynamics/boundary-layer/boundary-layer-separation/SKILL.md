---
name: boundary-layer-separation
description: "Use when you must predict boundary layer separation: grow the laminar layer with the Thwaites integral along the edge-velocity distribution of a two-dimensional body, flag the first station where the thwaites lambda parameter crosses minus 0.09 to give the laminar separation point, and apply the Stratford pressure-recovery criterion to the pressure-coefficient distribution to estimate the turbulent separation station and the separation margin below the 0.35 threshold. Produces the laminar separation station or none, the turbulent separation station or none, and the margin that gates airfoil and inlet-duct design checks. Trigger: boundary-layer-separation, thwaites-lambda-criterion, stratford-separation-criterion, laminar separation point, turbulent separation station, separation margin, adverse pressure gradient, pressure recovery, edge-velocity distribution."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: boundary-layer
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: boundary-layer
  tags: [boundary-layer-separation, thwaites-lambda-criterion, stratford-separation-criterion, laminar-separation-point, turbulent-separation-station, separation-margin, adverse-pressure-gradient]
  version: 0.1.0
  author: Aero Agent Skills
---

# Boundary Layer Separation (aerodynamics/boundary-layer/boundary-layer-separation)

Use when you must predict the boundary layer separation location on a
two-dimensional body from its edge-velocity or pressure distribution.
This leaf grows the laminar layer with the Thwaites integral relation
along the edge-velocity traverse and flags the first station where the
Thwaites lambda parameter crosses -0.09, the classical laminar
separation criterion, and evaluates the Stratford-style pressure
recovery criterion to estimate the turbulent separation station and the
margin below the 0.35 threshold. Pure Python, stdlib only. It pairs
with boundary-layer/boundary-layer-transition, whose Thwaites traverse
ends at the natural-transition onset estimated by the Michel rule
rather than running to separation, and with
boundary-layer/boundary-layer-theory for flat-plate thickness
and skin-friction context on the attached side of the flow.

## Domain quick reference

- Thwaites integral for the momentum thickness on the laminar side:
  theta^2 = 0.45 * nu / U^6 * integral_0^x U^5 dx, integrated by the
  trapezoid rule over the edge-velocity stations (THWAITES_C = 0.45).
  The traverse starts with theta = 0 at the first station with U > 0;
  a stagnation head with U = 0 is skipped, which removes the U^6
  singularity at the stagnation point.
- Thwaites pressure-gradient parameter: lambda = theta^2 / nu * dU/dx,
  with dU/dx by central differences (forward at the first station,
  backward at the last). Accelerating flow keeps lambda positive;
  a decelerating edge flow drives lambda negative.
- Laminar separation criterion: the first station with
  lambda <= THWAITES_LAMBDA_SEP = -0.09 is the laminar separation
  point. None if lambda stays above the criterion for the whole run.
- Stratford-style separation parameter on the pressure recovery:
  S = C_p * sqrt((x / C_p) * dC_p/dx), evaluated only where C_p > 0
  and dC_p/dx > 0 (the recovery side), with the pressure slope taken
  over the station interval ending at each station (one-sided
  difference, right-end attribution; this reproduces the verified
  worked-example anchor S = 0.3505 at station 8).
- Turbulent separation criterion: the first recovery station with
  S >= STRATFORD_SEP = 0.35 is the turbulent separation station.
  None if the recovery never reaches the threshold.
- Separation margin: 0.35 - max S on the recovery side before the
  crossing (headroom up to the separation point, positive while the
  flow keeps headroom). With no crossing the max is taken over the
  whole recovery; with no recovery stations at all the margin is the
  full 0.35.
- Units are SI throughout: x in m, U in m/s, nu in m2/s, C_p
  dimensionless, theta in m.
- NACA TR-824 frames the laminar boundary-layer correlation context;
  the relations above are standard engineering methodology,
  summary-only.

## Workflow

1. Build the edge-velocity traverse xs, us (m, m/s) along the body and
   fix the kinematic viscosity nu. A linearly decelerated run or a
   digitized airfoil velocity distribution both work as plain station
   lists.
2. Grow the laminar layer with thwaites_lambda(xs, us, nu) to get the
   lambda history, one value per station.
3. Locate the laminar separation point with
   laminar_separation_station(xs, us, nu), which returns (index, x) of
   the first station with lambda <= -0.09, or None for a fully attached
   laminar run. Read us at that index for the separation edge velocity.
4. On the pressure side, build the pressure-coefficient recovery
   traverse xs, cps and evaluate the recovery with
   stratford_parameter(xs, cps), which returns the S history with None
   off the recovery.
5. Locate the turbulent separation station with
   stratford_separation_station(xs, cps), which returns (index, x) of
   the first station with S >= 0.35, or None.
6. Quantify the headroom with separation_margin(xs, cps): positive
   margin means the recovery keeps margin below the 0.35 threshold up
   to the crossing point.
7. Report the laminar separation station or none, the turbulent
   separation station or none, and the margin, and gate the airfoil or
   inlet-duct design check on whichever separation signal is closer to
   the operating point.
8. Confirm the deterministic checks with the contract test
   scripts/test_boundary_layer_separation.py.

## Worked example

Edge velocity U(x) = 30 * (1 - x) m/s over x in [0, 1] m (linear
deceleration), nu = 1.5e-5 m2/s, 400001 stations (step 2.5e-6 m):

- Thwaites lambda traverse is monotone decreasing from 0 at the start;
  at x = 0.05 m the discrete lambda is -0.027028, matching the closed
  form -0.075 * (1 - t^6) / t^6 with t = 1 - x to five digits.
- Laminar separation at station index 49257, x = 0.12314 m (within 1
  percent of the classic 0.1231 m, about 12 percent chord), where the
  lambda values around the crossing go from -0.089998 to -0.090001.
- Edge velocity at the separation station: 26.306 m/s (within 1
  percent of 26.31 m/s).
- Accelerating flow U(x) = 30 * (1 + 0.2 * x) over 1 m: lambda stays
  non-negative and laminar_separation_station returns None.

Stratford recovery C_p(x) = 0.4 * x^2 over x in [0, 0.9] m at 10
stations (step 0.1 m):

- S climbs through 0.26710 at x = 0.7 m and crosses 0.35 at station
  index 8, x = 0.8 m, with S = 0.3505 at the crossing.
- separation_margin = 0.35 - 0.26710 = 0.08290, positive headroom up
  to the crossing point.
- Mild recovery C_p = 0.2 * x^2: no crossing (None), margin 0.12735.
- Steep recovery C_p = 0.6 * x^2: crossing at station index 7,
  x = 0.7 m, S = 0.4007.
- Falling C_p (favorable pressure, no recovery): no station, margin
  0.35.

## Verification

- Confirm thwaites_lambda on the linear deceleration is monotone
  decreasing with a negative tail, and matches the closed-form
  -0.075 * (1 - t^6) / t^6 at interior stations.
- Confirm laminar_separation_station returns (49257, 0.12314) on the
  worked grid, within 1 percent of 0.1231 m, with U = 26.31 m/s there,
  and None on the accelerating flow.
- Confirm stratford_separation_station returns (8, 0.8) with
  S = 0.3505 at the crossing for C_p = 0.4 * x^2, and that the margin
  before the crossing is positive.
- Confirm a no-crossing recovery returns None and a positive margin,
  and that every non-physical input raises ValueError: mismatched
  station and velocity or pressure lengths, nu <= 0, negative edge
  velocity, all-zero velocity, non-increasing stations, and empty
  lists.
- Run the contract test offline: python3
  scripts/test_boundary_layer_separation.py (35 tests, deterministic,
  about 1 second).

## Related leaves

- aerodynamics/boundary-layer/boundary-layer-theory: flat-plate
  thickness and skin-friction context for the attached side of the
  flow; zero-pressure-gradient flows never trigger these criteria.
- aerodynamics/boundary-layer/boundary-layer-transition: the sibling
  Thwaites traverse that stops at the natural-transition onset
  estimated by the Michel rule instead of running to the -0.09
  separation crossing.
- aerodynamics/cfd/cfd-turbulence-modeling: RANS turbulence-model
  selection, where separation prediction appears only as a modeling
  pitfall for wall functions.

## Pitfalls

- Continuing the Thwaites traverse past the crossing: once lambda drops
  below -0.09 the integral method has left its validity domain, the
  laminar layer has left the surface, and downstream lambda values are
  not a physical answer; stop at the first crossing.
- Reading the trailing U = 0 station as a finite lambda: an edge flow
  that decelerates to zero has separated long before, and the module
  reports lambda = -inf at such stations, so check the crossing before
  the end of the list.
- Treating negative or falling C_p as recovery: the Stratford
  parameter needs C_p > 0 with dC_p/dx > 0; favorable-pressure regions
  carry no S value and leave the margin at the full 0.35.
- Confusing the two separation signals: the laminar (Thwaites) and
  turbulent (Stratford) crossings are different physics, usually at
  different stations, and both belong in the report with their
  criterion named.
- Reading the margin after a crossing as negative headroom:
  separation_margin is the headroom up to the crossing point, positive
  by construction; on a steep recovery the separation station itself is
  the separation signal.
- Feeding a zero-pressure-gradient flat-plate case expecting a
  separation: dU/dx = 0 gives lambda = 0 and no Stratford recovery, so
  both criteria stay silent, which is correct for an attached flat
  plate at moderate incidence.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_boundary_layer_separation.py

The test must pass with exit 0 and covers the worked-example anchors
(laminar separation at x = 0.1231 m within 1 percent with U = 26.31
m/s on the linear deceleration, no separation on the accelerating
flow), the closed-form Thwaites identity for the linear deceleration,
monotone-decreasing lambda with a negative tail, the Stratford
crossing at station index 8 with S = 0.3505 and a positive margin
before the crossing, no-crossing and favorable-pressure recoveries
returning None with positive margins, steep-recovery crossing, and
ValueError rejection of every non-physical input listed in the spec
(empty or length-mismatched lists, nu <= 0, negative velocity,
all-zero velocity, non-increasing stations).

## Contract test

Run the contract test from the leaf directory:

    cd skills/aerodynamics/boundary-layer/boundary-layer-separation
    python3 scripts/test_boundary_layer_separation.py

Stdlib unittest only, deterministic, offline, 35 test methods, exit 0
in about 1 second. The test file imports the sibling logic module
boundary_layer_separation_logic from its own scripts directory, so no
install or path configuration is needed.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 (laminar
  boundary-layer correlations and pressure-gradient behavior) frames
  the family context; the Thwaites and Stratford relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

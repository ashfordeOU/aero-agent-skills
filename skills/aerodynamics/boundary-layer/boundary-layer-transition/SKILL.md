---
name: boundary-layer-transition
description: "Use when you must predict the laminar-turbulent transition location on a two-dimensional body from its edge-velocity distribution: grow the laminar boundary layer with the Thwaites integral relation to obtain the boundary-layer momentum deficit at each station, build the local Reynolds numbers from the edge velocity and that deficit, evaluate the Michel transition criterion against them, and interpolate the first station where the criterion is crossed to give the transition location. Produces the Reynolds-number history along the body, the Michel criterion margin at each station, and the transition location that gates a natural-transition estimate for an airfoil or body. Trigger: boundary-layer-transition, transition-location, thwaites-integral, michel-criterion, natural-transition, edge-velocity distribution, laminar-turbulent transition, airfoil transition onset."
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
  tags: [boundary-layer-transition, thwaites-integral, michel-criterion, transition-location, natural-transition]
  version: 0.1.0
  author: Aero Agent Skills
---

# Boundary Layer Transition (aerodynamics/boundary-layer/boundary-layer-transition)

Use when you must predict where the laminar boundary layer turns
turbulent on a two-dimensional body from its edge-velocity
distribution. This leaf implements the standard integral estimate:
grow the laminar layer with the Thwaites relation to get the momentum
thickness theta at each station, then apply the Michel empirical
criterion on the local Reynolds numbers to locate the natural
transition point. The logic is pure Python, stdlib only, and covers a
clean two-dimensional surface (no roughness, sweep or suction inputs
and no Tollmien-Schlichting wave-growth integration; the Michel
criterion replaces an eN envelope). It pairs with
aerodynamics/boundary-layer/boundary-layer-theory, which owns the
flat-plate thickness and skin-friction correlations on either side of
the transition.

## Domain quick reference

- Edge-velocity Reynolds number: Re_x = Ue(x) * x / nu with Ue the
  inviscid edge velocity and nu the kinematic viscosity (SI units
  throughout, m, m/s, m2/s).
- Thwaites integral relation for the laminar momentum thickness:

      theta(x)^2 = THWAITES_C * nu / Ue(x)^6 * integral_0^x Ue(xi)^5 d(xi)

  with THWAITES_C = 0.45. The integral is evaluated cumulatively with
  the trapezoid rule over the supplied stations; the segment from the
  leading edge (x = 0) to the first station keeps Ue at its
  first-station value, which makes the constant-velocity flat plate
  exact.
- Momentum-thickness Reynolds number: Re_theta = Ue * theta / nu.
- Michel transition criterion (empirical):

      Re_theta,tr = MICHEL_A * (1 + MICHEL_B / Re_x) * Re_x**MICHEL_P

  with MICHEL_A = 1.174, MICHEL_B = 22400.0, MICHEL_P = 0.46.
  Transition onset occurs at the first station where Re_theta reaches
  the threshold; the margin m = Re_theta - threshold crosses zero
  there.
- Flat-plate exact solution (verification helper): with constant Ue the
  Thwaites relation closes to Re_theta = sqrt(0.45) * sqrt(Re_x) =
  0.6708 * sqrt(Re_x), so theta = 0.6708 * sqrt(Re_x) * nu / Ue.
- Natural-transition distance on a smooth flat plate follows from the
  Michel crossing, typically Re_x ~ 1.7e6 at low free-stream
  turbulence, an order of magnitude beyond the textbook 5e5 landmark
  that boundary-layer-theory quotes for the onset of instability.
- NACA TR-824 frames the boundary-layer context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Assemble the station grid: xs (m) strictly increasing and the edge
   velocities ues (m/s) at each station, equal length, all ue > 0.
2. Grow the laminar layer with momentum_thickness_profile(xs, ues,
   nu): returns the Thwaites theta at every station.
3. Build the Reynolds history with re_theta_profile(xs, ues,
   theta_list, nu) and the Michel threshold with
   michel_threshold(re_x) at each station.
4. Run the one-call sweep transition_location(xs, ues, nu): returns
   theta_list, re_theta_list, criterion_margin_list, x_transition
   (first station where the margin is non-negative, or None), the
   transition_index and interp_x_transition (linear interpolation of
   the margin to zero between the bracketing stations).
5. For a quick flat-plate check use flat_plate_transition(nu, ue,
   x_max), the analytic natural-transition distance on a
   constant-velocity plate, or michel_criterion(re_x, re_theta) for a
   single point test.
6. Confirm the deterministic checks with the contract test
   scripts/test_boundary_layer_transition.py.

## Worked example

Smooth flat plate in low-turbulence flow: nu = 1.46e-5 m2/s, Ue = 30
m/s.

- Momentum thickness from momentum_thickness_profile over x = 0.25,
  1.0, 2.0 m: theta = 2.3399e-4, 4.6797e-4, 6.6182e-4 m. At x = 1 m
  the value matches the exact flat-plate value 0.6708 * sqrt(2.0548e6) * nu / Ue
  = 4.680e-4 m to six digits, and Re_theta(1 m) = 961.6 equals 0.6708
  * sqrt(Re_x) (the trapezoid Thwaites integral is exact for constant
  Ue).
- Michel threshold at x = 1 m: michel_threshold(2.0548e6) = 951.15,
  so the margin there is 961.6 - 951.15 = +10.44. On the coarse grid
  the margins are -38.16 (x = 0.25 m), +10.44 (x = 1.0 m) and +58.60
  (x = 2.0 m): transition_location reports x_transition = 1.0 m
  (station value) with interp_x_transition = 0.8389 m between the
  bracketing stations.
- Exact-solution helper: flat_plate_transition(1.46e-5, 30.0, 2.0)
  returns x_tr = 0.8126 m (inside the 0.6-1.1 m band), i.e.
  Re_x,tr = 1.670e6 with Re_theta at the crossing = 866.8 (inside
  800-1100). The margin is negative just below x_tr and non-negative
  at it, as expected for a first-crossing scan.

## Verification

- Confirm momentum_thickness_profile on the three-station flat plate
  is monotonic and matches 0.6708 * sqrt(Re_x) * nu / Ue within 1e-6
  relative at every station.
- Confirm the flat-plate Re_theta identity re_theta_profile(...)
  equals 0.6708 * sqrt(Re_x) within 1e-9 relative.
- Confirm flat_plate_transition(1.46e-5, 30.0, 2.0) lies in 0.6-1.1 m
  and the Re_theta at the crossing lies in 800-1100.
- Confirm ValueError rejection of fewer than two stations,
  unequal-length xs/ues, x below zero or not strictly increasing,
  ue <= 0, nu <= 0, re_x <= 0 and re_theta < 0.
- Confirm determinism: repeated calls on identical inputs return
  identical results.
- Run the contract test offline: python3
  scripts/test_boundary_layer_transition.py (32 tests, deterministic,
  under 20 s).

## Related leaves

- aerodynamics/boundary-layer/boundary-layer-theory: the laminar and
  turbulent flat-plate thickness and skin-friction correlations that
  bookend the transition point.
- aerodynamics/airfoil/xfoil-analysis: viscous airfoil analysis that
  can supply the edge-velocity distribution and an independent
  transition estimate for comparison.
- aerodynamics/drag-polars/parasite-drag: uses the laminar versus
  turbulent split downstream of transition for wetted-area drag.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_boundary_layer_transition.py

The test covers the Thwaites momentum thickness against the flat-plate
exact solution, the worked-example theta at x = 1 m (4.680e-4 m), the
Michel threshold and criterion logic including the equality boundary,
the transition sweep bounds (x_tr in 0.6-1.1 m, Re_theta in 800-1100)
with the station versus interpolated crossing distinction, the margin
sign flip across the crossing, the never-crossed and first-station-
crossed cases, the exact-solution flat_plate_transition helper and its
bounds, ValueError rejection of every non-physical input in the
validation list, and determinism.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is named for
  context only; the Thwaites relation and Michel criterion above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

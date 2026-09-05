---
name: stagnation-flow-boundary-layer
description: 'Use when you must size the laminar boundary layer, wall shear and skin friction at a low-speed 2-D or axisymmetric stagnation point or leading edge: compute the potential-flow stagnation velocity gradient from the body radius and freestream speed (factor 2 in the Hiemenz 2-D regime, 1.5 in the Homann axisymmetric regime), the 99-percent laminar boundary-layer thickness about 2.4 sqrt(nu/a), the wall shear from the Hiemenz or Homann similarity wall-shear constant, and the skin-friction coefficient against the freestream dynamic pressure. Produces the a, delta, tau_w and Cf report that gates spinner, radome, wing and fin leading-edge boundary-layer sizing at low speed. Trigger: stagnation-flow-boundary-layer, hiemenz-similarity, homann-similarity, stagnation-velocity-gradient, stagnation-wall-shear, attachment-line flow, nose boundary layer.'
license: Apache-2.0
compliance: STANDARDS-REF
standards:
- id: naca-tr-824
  reference-only: true
gated: false
domain: aerodynamics
pack: boundary-layer
compatibility: agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)
metadata:
  domain: aerodynamics
  subdomain: boundary-layer
  tags:
  - stagnation-flow-boundary-layer
  - hiemenz-similarity
  - homann-similarity
  - stagnation-velocity-gradient
  - stagnation-wall-shear
  version: 0.1.0
  author: AeroSkills
---

# Stagnation-flow boundary layer (aerodynamics/boundary-layer/stagnation-flow-boundary-layer)

The laminar boundary layer at a low-speed stagnation point or leading
edge (spinner tip, radome nose, wing or fin leading edge) is an
attachment-line flow: the inviscid surface speed rises linearly with arc
length s from the attachment point, u_e = a * s, and the layer obeys the
Hiemenz (2-D) or Homann (axisymmetric) exact similarity solution. This
leaf sizes that layer with a deterministic closed-form core: the
potential-flow stagnation velocity gradient a from the body radius and
freestream speed, the constant 99-percent laminar boundary-layer
thickness delta = 2.4 sqrt(nu / a) that does not grow along the
attachment region, the wall shear tau_w = mu u_inf sqrt(a / nu) fpp
with the classical similarity wall-shear constant fpp (1.2326 Hiemenz,
1.3119 Homann), and the skin-friction coefficient Cf = tau_w / (0.5 rho
u_inf^2), plus the swept-edge crossflow treatment for infinite yawed
cylinders. The full similarity ODEs are NOT integrated; only their
classical constants enter, so every function is pure stdlib, offline and
reproducible. This is the low-speed laminar momentum boundary layer
only: heat transfer is out of scope. It pairs with
boundary-layer-theory (smooth-surface layer sizing away from the
attachment line), boundary-layer-transition and boundary-layer-separation
(streamwise layer evolution), and aerodynamic-heating (stagnation
convective heating at high speed).

## Domain quick reference

- Attachment-line inviscid speed: u_e = a * s with the potential-flow
  stagnation velocity gradient a = du_e / ds at the stagnation point.
- 2-D regime (Hiemenz, flow_type cylinder/2d/two-dimensional):
  a = 2.0 * u_inf / R, from the inviscid surface speed
  u_e = 2 u_inf sin(s / R) on a circular cylinder.
- Axisymmetric regime (Homann, flow_type sphere/axisymmetric/axi):
  a = 1.5 * u_inf / R, from u_e = 1.5 u_inf sin(s / R) on a sphere.
- 99-percent laminar boundary-layer thickness:
  delta = 2.4 sqrt(nu / a), constant along the attachment region
  because the Hiemenz and Homann similarity layers do not grow in the
  streamwise direction. The 2-D coefficient 2.4 is returned for both
  regimes; the axisymmetric layer at equal a is somewhat thinner in the
  standard tabulations, so the module value is a conservative documented
  approximation for the Homann case.
- Wall shear at the station where u_e = a s = u_inf:
  tau_w = mu u_inf sqrt(a / nu) fpp with mu = rho nu and fpp = FPP_2D =
  1.2326 (Hiemenz 2-D) or FPP_AXISYM = 1.3119 (Homann axisymmetric).
  The closed form equals the algebraic identity
  rho u_inf sqrt(a nu) fpp. tau_w scales linearly with u_e in the
  similarity layer, so other near-stagnation stations scale with
  u_e / u_inf.
- Local skin-friction coefficient against the freestream dynamic
  pressure: Cf = tau_w / (0.5 rho u_inf^2) = 2 tau_w / (rho u_inf^2).
- Swept (infinite yawed) leading edge, independence-principle
  paraphrase: the stagnation line obeys the 2-D Hiemenz solution in the
  crossflow plane with the chordwise gradient a = 2 u_n / R driven by
  the velocity component normal to the leading edge
  u_n = u_inf cos(sweep); sweep 0 reproduces 2 u_inf / R.
- Units are SI throughout: m, s, m/s, 1/s, m2/s, Pa s, kg/m3, Pa.
- The classical similarity wall-shear and thickness constants above are
  standard tabulated results (summary of Schlichting and White;
  NACA TR-824 reference-only per standards-map.yaml), paraphrase only.

## Workflow

1. Establish the operating condition and geometry: air properties rho
   and nu, freestream speed u_inf, the body radius R at the attachment
   line, and the flow type (2-D cylinder or leading edge vs
   axisymmetric sphere or nose).
2. Compute the potential-flow stagnation velocity gradient a with
   stagnation_velocity_gradient(flow_type, u_inf, radius): factor 2
   (Hiemenz 2-D regime) or 1.5 (Homann axisymmetric regime) times
   u_inf / R.
3. Estimate the 99-percent laminar boundary-layer thickness delta with
   boundary_layer_thickness(nu, a) = 2.4 sqrt(nu / a), the constant
   similarity-layer thickness along the attachment region.
4. Compute the stagnation wall shear at the u_e = u_inf station with
   wall_shear_stress(rho, nu, a, u_inf, flow_type), which applies the
   FPP_2D (Hiemenz) or FPP_AXISYM (Homann) similarity wall-shear
   constant internally: tau_w = mu u_inf sqrt(a / nu) fpp.
5. Convert to the local skin-friction coefficient with
   skin_friction_coefficient(rho, u_inf, tau_w) against the freestream
   dynamic pressure 0.5 rho u_inf^2.
6. For a swept leading edge, reduce to the crossflow plane:
   swept_stagnation_gradient(u_inf, radius, sweep_deg) gives the
   chordwise gradient 2 u_n / R with u_n = u_inf cos(sweep_deg), and
   the 2-D Hiemenz form (steps 4 and 5) applies in that plane with u_n.
7. Close with the flow-type treatment note: 2-D cases use the Hiemenz
   constants and axisymmetric cases the Homann constants, the delta
   function returns the 2-D coefficient for both regimes (conservative
   for the Homann case), and verify the results with the contract test.

## Worked example

Standard air rho = 1.225 kg/m3, u_inf = 30 m/s, nu = 1.5e-5 m2/s, so
mu = rho nu = 1.8375e-5 Pa s. Circular-cylinder spinner or 2-D
leading-edge radius R = 0.15 m:

- a = 2 u_inf / R = 400.0 1/s (stagnation_velocity_gradient).
- delta = 2.4 sqrt(nu / a) = 4.647580e-4 m (0.4648 mm).
- tau_w = mu u_inf sqrt(a / nu) FPP_2D = 3.508772 Pa.
- Cf = 2 tau_w / (rho u_inf^2) = 6.365119e-3.

Same radius as an axisymmetric nose (sphere):

- a = 1.5 u_inf / R = 300.0 1/s.
- delta = 5.366563e-4 m (0.5367 mm).
- tau_w = 3.234181 Pa (Homann constant).
- Cf = 5.866995e-3.

Ratio checks from the real outputs: delta_sph / delta_cyl =
sqrt(2 / 1.5) = 1.1547005, tau_sph / tau_cyl =
(FPP_AXISYM / FPP_2D) sqrt(1.5 / 2) = 0.9217416. Swept leading edge
R = 0.02 m at sweep 30 deg: a = 2 u_inf cos(30) / R = 2598.0762 1/s,
delta = 1.823606e-4 m, and with the normal component
u_n = 30 cos(30) = 25.9808 m/s the 2-D form gives
tau_w = 7.744292 Pa and Cf = 1.873147e-2. The stagnation Cf sits an
order of magnitude above the smooth-surface value at a comparable
length scale, the expected leading-edge penalty.

## Verification

- Confirm stagnation_velocity_gradient("cylinder", 30.0, 0.15) returns
  400.0 and ("sphere", 30.0, 0.15) returns 300.0, with the 2-D and
  axisymmetric synonyms accepted case-insensitively.
- Confirm boundary_layer_thickness(1.5e-5, 400.0) returns
  4.647580e-4 m and the delta ratio delta_sph / delta_cyl equals
  sqrt(2 / 1.5).
- Confirm wall_shear_stress(1.225, 1.5e-5, 400.0, 30.0, "cylinder")
  returns 3.508772 Pa, that doubling u_inf doubles tau_w, and that the
  mu closed form agrees with rho u_inf sqrt(a nu) fpp.
- Confirm skin_friction_coefficient returns 6.365119e-3 for the
  cylinder case and that Cf round-trips through the dynamic pressure.
- Confirm swept_stagnation_gradient(30.0, 0.02, 30.0) returns
  2598.0762 1/s and sweep 0 returns 3000.0 1/s.
- Confirm every non-positive speed, radius, density, viscosity,
  gradient and shear, every unknown flow type, and every sweep angle
  beyond 90 degrees raises ValueError.
- Confirm the module source has no random import and no ODE integration
  call, so results are deterministic.
- Run the contract test offline: python3
  scripts/test_stagnation_flow_boundary_layer.py (33 tests,
  deterministic, < 1 s).

## Related leaves

- aerodynamics/boundary-layer/boundary-layer-theory: smooth-surface
  layer sizing away from the attachment line (thickness integrals and
  friction at stations with no pressure-gradient input).
- aerodynamics/boundary-layer/boundary-layer-transition: natural
  transition location on a clean surface downstream of this leaf.
- aerodynamics/boundary-layer/boundary-layer-separation: separation
  criteria for a layer that has evolved past the attachment region.
- aerodynamics/boundary-layer/rough-wall-skin-friction: turbulent
  friction on rough surfaces, not the laminar similarity layer.
- aerodynamics/high-speed/flat-plate-skin-friction-heating:
  high-speed smooth-surface heating away from the stagnation region.
- aerodynamics/high-speed/aerodynamic-heating: stagnation convective
  heating at hypersonic conditions; the flux counterpart this leaf does
  not cover.
- vehicle-design/sizing/ice-protection-sizing: leading-edge icing-catch
  and thermal-power model, no momentum boundary layer.

## Pitfalls

- Reporting the thickness as growing downstream: the Hiemenz and Homann
  similarity layers have constant thickness along the attachment
  region, so boundary_layer_thickness takes no streamwise station and
  delta = 2.4 sqrt(nu / a) holds all along the attachment line.
- Mixing the two regimes: the 2-D Hiemenz gradient factor is 2 and the
  axisymmetric Homann factor is 1.5, with wall-shear constants 1.2326
  and 1.3119 respectively; applying the cylinder factor to a radome
  nose understates a and overstates delta by sqrt(2 / 1.5).
- Quoting the shear at the stagnation point itself: tau_w here is the
  value at the station where u_e = a s = u_inf; because tau_w scales
  linearly with u_e in the similarity layer, other near-stagnation
  stations scale with u_e / u_inf.
- Forgetting the sweep reduction: on a swept or yawed leading edge the
  chordwise gradient uses u_n = u_inf cos(sweep), so
  swept_stagnation_gradient drops to 2 u_inf cos(sweep) / R, and the
  2-D Hiemenz constants apply in the crossflow plane only.
- Expecting heat transfer here: this leaf sizes the low-speed laminar
  momentum boundary layer only; stagnation convective heating at
  hypersonic conditions belongs to aerodynamic-heating, and icing-catch
  thermal power at the leading edge belongs to ice-protection-sizing.
- Treating the Homann thickness as exact: the module returns the 2-D
  coefficient 2.4 for both flow types, a documented conservative
  approximation for the slightly thinner axisymmetric layer.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_stagnation_flow_boundary_layer.py

The 33 tests cover the worked-example anchors of the SKILL.md Workflow:
the stagnation-velocity-gradient computation for cylinder and sphere
with all flow-type synonyms, the laminar-boundary-layer-thickness
estimate with the sqrt(2 / 1.5) ratio identity and monotone scaling,
the stagnation-wall-shear computation with both similarity constants,
the closed-form and ratio identities (including tau linear in u_inf),
the skin-friction-coefficient conversion and dynamic-pressure round
trip, the swept-leading-edge crossflow reduction with the normal
velocity component, the worked-example magnitude bounds (delta 4.6e-4
to 5.4e-4 m, Cf 5.8e-3 to 6.4e-3), sub-millimeter parametric bounds
across the low-speed leading-edge range, module-constant values, and
ValueError rejection of every non-physical input and invalid flow type.

## Compliance

- The classical Hiemenz and Homann similarity results summarized here
  (gradient factors, thickness coefficient 2.4, wall-shear constants
  1.2326 and 1.3119) are standard tabulated boundary-layer results,
  paraphrase only; NACA TR-824 is referenced, not reproduced, per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false. Deterministic closed-form
  stdlib core with no network use and no ODE integration.

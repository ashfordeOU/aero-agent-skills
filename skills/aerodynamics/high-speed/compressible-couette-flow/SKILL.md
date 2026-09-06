---
name: compressible-couette-flow
description: "Use when you must compute the exact constant-property solution for compressible Couette flow in a high-Mach plate gap: the linear velocity profile u = Ue y / h, the Crocco energy-integral temperature profile, the insulated moving-plate temperature from the recovery relation r = Pr, the wall shear tau_w = mu Ue / h, the wall heat flux q_w into the stationary plate and the dissipation energy-balance check at a given plate Mach number, Prandtl number and gap Reynolds number. Produces the full gap solution with velocity and temperature profiles. Trigger: compressible-couette-flow, shear-driven-gap-flow, crocco-energy-integral, gap-reynolds-number, plate-gap, linear-velocity-profile, moving-plate, high-mach-plate-gap."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: high-speed
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags: [compressible-couette-flow, shear-driven-gap-flow, crocco-energy-integral, gap-reynolds-number]
  version: 0.1.0
  author: AeroSkills
---

# Compressible Couette Flow (aerodynamics/high-speed/compressible-couette-flow)

Use when you must compute the exact constant-property solution of the
shear-driven plate gap in a high-Mach Couette flow: a stationary cold
plate at y = 0 held at the static temperature T_e and an insulated
(adiabatic) moving plate at y = h dragged at the edge velocity
Ue = Me * a(T_e). The velocity profile is exactly linear, the
temperature profile follows the Crocco energy integral over that linear
profile, and the moving plate is not cooled, so its surface floats to
the recovery temperature and every joule of viscous dissipation leaves
through the stationary plate. This is the canonical closed-form anchor
of the aeroheating vein, useful as a laminar-regime heating estimate for
a plate gap and as a CFD verification case. It pairs with
aerodynamics/high-speed/flat-plate-skin-friction-heating (the EXTERNAL
boundary layer on a plate with regime-dependent recovery factors) and
aerodynamics/high-speed/aerodynamic-heating (stagnation-point heating):
those are different geometries and different recovery physics, while
this leaf owns the INTERNAL shear-driven gap with the identity r = Pr.
Fully closed form, pure stdlib.

## Domain quick reference

- Edge state: sound speed of the stationary-plate gas
  a_e = sqrt(gamma R T_e), moving-plate velocity Ue = Me * a_e
  (edge_velocity). Constants: GAMMA = 1.4, R = 287.0, and the derived
  CP = GAMMA * R / (GAMMA - 1) = 1004.5 J/(kg K), PR = 0.72,
  MU = 1.8e-5 Pa s; conductivity is derived k = mu * cp / Pr, never an
  input. Sutherland-free, uniform mu and k.
- Recovery factor: r = Pr exactly, the constant-property Couette
  identity (recovery_factor). The external-plate laminar sqrt(Pr) and
  turbulent Pr^(1/3) values do NOT apply inside the gap.
- Moving-plate temperature: T_aw = T_e * (1 + r (gamma - 1) Me^2 / 2)
  (adiabatic_wall_temperature), identical to T_e + Pr Ue^2 / (2 cp)
  because the plate is insulated and its temperature is an output, not
  an input.
- Velocity profile: u(y) = Ue * y / h, exactly linear
  (velocity_profile).
- Temperature profile: the Crocco energy integral
  T(y) = T_e * (1 + r (gamma - 1) Me^2 (2 eta - eta^2) / 2) with
  eta = y / h (temperature_profile), so T(0) = T_e, T(h) = T_aw and
  dT/dy(h) = 0.
- Gradient: dT/dy = T_e * r (gamma - 1) Me^2 (1 - eta) / h
  (temperature_gradient), positive at the stationary plate, zero at the
  insulated moving plate.
- Wall shear: tau_w = mu Ue / h, constant across the gap because the
  profile is linear (wall_shear).
- Wall heat flux into the stationary plate: q_w = mu Ue^2 / h
  (wall_heat_flux), positive = heat into the cold plate; equals
  k * dT/dy(0), tau_w * Ue and the dissipation integral
  mu * (Ue / h)^2 * h, the energy-balance close.
- Gap Reynolds number: Re_gap = rho Ue h / mu (couette_solution), the
  laminar-regime indicator; transition in plane Couette flow near
  Re ~ 1500. tau_w and q_w are independent of rho.
- Units are SI: K, m/s, Pa, W/m2, kg/m3, m.
- NACA-TR-824 frames the high-speed laminar boundary-layer and
  heat-transfer context; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Fix the plate-gap state: stationary-plate static temperature T_e,
   plate Mach number Me, Prandtl number Pr, constant viscosity mu,
   edge density rho and gap height h, with the moving plate insulated.
   Run the plate-gap edge-state traverse: the edge sound speed
   a_e = sqrt(gamma R T_e) and the edge velocity Ue = Me * a_e with
   edge_velocity.
2. Apply the constant-property recovery identity with recovery_factor:
   the recovery factor of the insulated moving plate is r = Pr, not the
   external-plate sqrt(Pr) or Pr^(1/3) values.
3. Float the insulated moving plate with adiabatic_wall_temperature to
   its recovery temperature T_aw = T_e * (1 + r (gamma - 1) Me^2 / 2),
   and cross-check the equivalent energy form T_e + r Ue^2 / (2 cp).
4. Walk the profiles across the gap with velocity_profile (linear
   u = Ue y / h), temperature_profile (Crocco energy integral) and
   temperature_gradient (analytic dT/dy, zero at the insulated moving
   plate).
5. Read the constant wall shear with wall_shear: tau_w = mu Ue / h,
   uniform across the gap.
6. Compute the heat flux into the stationary plate with
   wall_heat_flux: q_w = mu Ue^2 / h, and close the dissipation energy
   balance q_w = k * dT/dy(0) = tau_w * Ue, where k = mu * cp / Pr.
   The moving plate is adiabatic, so its flux is zero.
7. Assemble the full solution with couette_solution, which returns the
   dict with keys Ue, T_aw, tau_w, q_w, r, Re_gap; the gap Reynolds
   number Re_gap = rho Ue h / mu frames the laminar regime (density
   enters only there).
8. Confirm the deterministic checks with the contract test
   scripts/test_compressible_couette_flow.py.

## Worked example

Canonical case from the wave-42 spec: T_e = 300.0 K, Me = 3.0,
Pr = 0.72, mu = 1.8e-5 Pa s, rho = 1.0e-3 kg/m3, h = 0.01 m,
gamma = 1.4, R = 287.0 (cp = 1004.5 derived). Real module outputs:

- Edge state: a_e = 347.188709 m/s, Ue = Me * a_e = 1041.566128 m/s.
- Recovery identity: r = Pr = 0.720000 exactly; the numerical recovery
  check (T_aw - T_e) * 2 * cp / Ue^2 = 0.720000, equal to Pr within
  1e-12. The external-plate values sqrt(Pr) = 0.8485 and
  Pr^(1/3) = 0.8961 would be wrong here.
- Moving-plate temperature: T_aw = 688.800000 K, a 388.8 K recovery
  rise; the energy form T_e + Pr Ue^2 / (2 cp) gives 688.800000 K,
  matching within 1e-12.
- Wall shear: tau_w = mu Ue / h = 1.874819 Pa (1.8748190313 full
  precision), constant across the gap; the viscous work rate
  tau_w * Ue = 1952.748 W/m2.
- Temperature field and heat flux: k = mu * cp / Pr =
  0.025113 W/(m K) (0.0251125 full precision), dT/dy at the stationary
  plate = 77760.000 K/m, q_w = k * dT/dy = 1952.748 W/m2 into the
  stationary plate, identical to the closed form mu Ue^2 / h; the
  moving plate is adiabatic with dT/dy(h) = 0 and q(h) = 0 W/m2.
- Energy balance: the dissipation integral mu (du/dy)^2 over the gap
  equals mu Ue^2 / h = 1952.748 W/m2, exactly the flux into the
  stationary plate.
- Gap Reynolds number: Re_gap = rho Ue h / mu = 578.648, laminar plane
  Couette (transition near Re ~ 1500).
- Profiles at quarter stations: T = 300.000, 470.100, 591.600,
  664.500, 688.800 K; u = 0.000, 260.392, 520.783, 781.175,
  1041.566 m/s; temperature rises monotonically from the cold plate to
  the insulated moving plate and the velocity is exactly linear
  (u(h/2) = Ue/2).

## Verification

- Confirm edge_velocity(3.0, 300.0) = 1041.566128 m/s and the sound
  speed a_e = Ue / Me = 347.188709 m/s.
- Confirm recovery_factor returns Pr exactly for any positive pr and
  that (T_aw - T_e) * 2 * cp / Ue^2 recovers Pr within 1e-12.
- Confirm adiabatic_wall_temperature(300.0, 3.0, 0.72) = 688.800000 K
  and its equality with T_e + Pr Ue^2 / (2 cp).
- Confirm the profile endpoints T(0) = T_e, T(h) = T_aw with
  dT/dy(h) = 0 (insulated moving plate), the quarter-station values
  and the linear velocity profile.
- Confirm the dissipation energy balance closes: q_w = k * dT/dy(0) =
  mu Ue^2 / h = tau_w * Ue within 1e-9 relative.
- Confirm every non-positive Mach number, temperature, Prandtl number,
  viscosity, density, gap height, velocity, and every y outside
  [0, h] raises ValueError in the corresponding function.
- Run the contract test offline: python3
  scripts/test_compressible_couette_flow.py (33 tests, deterministic).

## Related leaves

- aerodynamics/high-speed/flat-plate-skin-friction-heating: the EXTERNAL
  flat-plate boundary layer with regime-dependent recovery factors
  sqrt(Pr) / Pr^(1/3), reference-temperature property evaluation and
  running-length Reynolds numbers; the adjacent geometry, different
  mechanism.
- aerodynamics/high-speed/aerodynamic-heating: stagnation-point
  convective heating with the Sutton-Graves correlation and the
  radiation-equilibrium wall temperature; the other corner of the
  aeroheating vein.
- aerodynamics/high-speed/bow-shock-standoff: shock-layer geometry
  ahead of a blunt body, the compressible context that sets edge states
  for gap and plate heating estimates.

## Pitfalls

- Carrying the external-plate recovery factor into the gap: inside
  constant-property Couette flow the recovery factor is r = Pr exactly,
  not the laminar sqrt(Pr) = 0.8485 or turbulent Pr^(1/3) = 0.8961
  values that flat-plate-skin-friction-heating uses, so using those
  inflates T_aw (for the worked example, 0.8485 would give a 722.3 K
  moving-plate temperature against the true 688.8 K).
- Fixing the moving-plate temperature instead of floating it: the
  moving plate is insulated, so its surface temperature T_aw is an
  OUTPUT of the energy balance. A prescribed moving-plate temperature
  is an externally cooled case with a different (non-Crocco) profile,
  outside this leaf's scope.
- Treating the heat flux as leaving the moving plate: with the moving
  plate adiabatic, all viscous dissipation leaves through the cold
  stationary plate, so q_w at the stationary plate equals the full
  dissipation integral mu (Ue / h)^2 * h; there is no second heat sink.
- Applying Sutherland or temperature-dependent properties: the leaf is
  constant-property by construction (uniform mu, k = mu cp / Pr
  derived), the laminar-regime statement; variable-viscosity Couette
  solutions and turbulent gaps need boundary-layer or CFD methods.
- Reading Re_gap as a driver of tau_w or q_w: in constant-property
  Couette flow rho enters only through Re_gap, so changing the density
  changes the regime indicator, never the shear or the flux.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_compressible_couette_flow.py

The test covers the wave-42 worked-example contract (Ue, T_aw, tau_w,
q_w, r, Re_gap and the quarter-station profiles), the recovery identity
r = Pr and its numerical recovery check, the energy-form equivalence of
T_aw, the Crocco profile endpoints and analytic gradient with the
adiabatic moving plate, the forward-difference gradient cross-check,
linear velocity profile stations, the constant wall shear with its
linear-profile slope, the dissipation energy-balance close
q_w = k * dT/dy(0) = tau_w * Ue, the sign conventions, monotonic
temperature rise, the exact dict key order, determinism under repeated
calls, and ValueError rejection of every non-physical input class.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 (reference-only per
  standards-map.yaml) frames the high-speed laminar boundary-layer and
  heat-transfer context; the compressible Couette relations above are
  standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.

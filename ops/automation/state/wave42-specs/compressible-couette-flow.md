# Wave-42 leaf spec: compressible-couette-flow (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/compressible-couette-flow/
- Pack: high-speed (verified present at prep with aerodynamic-heating,
  bow-shock-standoff, flat-plate-skin-friction-heating, hypersonic-flow,
  isentropic-flow-relations, normal-shock, oblique-shock, prandtl-meyer,
  regular-shock-reflection, shock-expansion-airfoil, supercritical-airfoil,
  swept-wing-aerodynamics, transonic-similarity, wave-drag-area-rule).
  Closest siblings, quoted from their frontmatter descriptions:
  flat-plate-skin-friction-heating (EXTERNAL boundary layer on a plate; its
  claim is "Use when you must estimate the surface skin friction heating on a
  flat plate or vehicle skin at high Mach: it computes the recovery factor,
  adiabatic wall temperature, Eckert reference temperature, Sutherland
  viscosity, local skin friction coefficient and Reynolds-analogy heat
  transfer coefficient, then the cold-wall heat flux for a laminar or
  turbulent boundary layer", recovery factors r = sqrt(Pr) laminar and
  r = Pr^(1/3) turbulent, running length x from the leading edge) and
  aerodynamic-heating (STAGNATION point only; its claim is "Use when you must
  estimate the aerodynamic heating at the stagnation point of a hypersonic
  body: stagnation-point convective heat flux from the Sutton-Graves
  correlation using freestream density, flight velocity and nose radius",
  with the radiation-equilibrium wall temperature). Neither claims internal
  shear-driven plate-gap flow, the Crocco energy integral over a linear
  velocity profile, or a recovery identity r = Pr. The wave-40 precedent
  turbulent-flat-plate-heating = owned-dup does NOT apply: that was the SAME
  external-plate function under a second name; Couette is a different
  geometry (plate gap, no leading edge, no edge growth) and a different
  mechanism (internal shear layer heated by viscous dissipation). Whole-tree
  greps at prep: "couette" = 0 hits in skills/ (SKILL.md and scripts, exit 1)
  and 0 hits in the corpus, so the leaf has no owner.
  GENUINE AERO gap (fresh probe): the exact-solution compressible Couette
  problem, the last clean closed-form anchor in the aeroheating vein
  (stagnation heating, external plate heating, bow-shock standoff and
  radiation equilibrium are all owned). Engineering surface is thinner than
  the shock-tube or thin-airfoil candidates; the strength is the exact
  solution itself as a canonical CFD verification anchor and a
  high-Mach plate-gap heating estimate.
- Standards id: naca-tr-824 (reference-only). Ledger Standard:
  naca-tr-824.
- Family: aerodynamics

## Claim

When a compressible gas is sheared between a stationary cold plate and a
moving hot plate in a high-Mach Couette flow, compute the exact
constant-property solution of the shear-driven plate gap: the linear
velocity profile u/Ue = y/h across the gap, the Crocco energy-integral
temperature profile T(y) rising from the stationary-plate temperature T_e to
the recovery temperature of the insulated moving plate, the recovery factor
r = Pr (exact for constant-property Couette, not the external-plate
sqrt(Pr)/Pr^(1/3) values), the insulated moving-plate temperature
T_aw = T_e (1 + r (gamma-1) Me^2 / 2), the constant wall shear
tau_w = mu Ue / h, the wall heat flux q_w into the stationary plate from
Fourier conduction k dT/dy, and the energy-balance identity that equates q_w
with the viscous-dissipation integral across the gap (every joule of shear
work leaves through the cold plate because the moving plate is insulated).
Reports the edge velocity Ue = Me a(T_e), the gap Reynolds number
Re_gap = rho Ue h / mu as the laminar-regime indicator, and the full
velocity and temperature profiles. Does NOT do: external flat-plate
boundary-layer skin friction and heating with regime-dependent recovery
factors, reference-temperature property evaluation and running-length
Reynolds numbers (flat-plate-skin-friction-heating); stagnation-point
convective heating with the Sutton-Graves correlation and radiation-
equilibrium wall temperature (aerodynamic-heating); unsteady or boundary-
layer integral methods. Scope: laminar constant-property (Sutherland-free,
uniform mu and k) Couette flow between parallel plates with the moving plate
insulated (adiabatic), so its surface temperature is an OUTPUT, not an
input. Externally fixed moving-plate temperatures, variable-viscosity
(Sutherland) solutions, turbulent gaps and pressure-gradient channel flow
are NOT modeled. Fully closed form, pure stdlib.

## Model (implement exactly)

Functions (pure stdlib, math only; gamma and R default to the module
constants). Canonical configuration: stationary cold plate at y = 0 held at
the reference static temperature T_e; insulated (adiabatic) moving plate at
y = h with velocity Ue = Me * sqrt(gamma R T_e). The moving plate is not
cooled, so its surface temperature floats to T_aw. Module constants:
GAMMA = 1.4, R = 287.0, CP = 1004.5 (derived as GAMMA * R / (GAMMA - 1), not
an independent constant, so the temperature-dissipation identities close
exactly), PR = 0.72, MU = 1.8e-5 (constant viscosity; the Sutherland law is
explicitly out of scope). Conductivity is derived, k = mu * cp / Pr; there
is no separate K module constant.

- recovery_factor(pr) -> float: the constant-property Couette recovery
  factor equals the Prandtl number exactly (identity r = Pr, verified
  numerically against (T_aw - T_e) * 2 cp / Ue^2 in the anchor); returns
  pr. ValueError if pr <= 0.
- edge_velocity(me, t_e, gamma = GAMMA, r = R) -> float Ue =
  me * sqrt(gamma * r * t_e), m/s. ValueError if me <= 0 or t_e <= 0.
- adiabatic_wall_temperature(t_e, me, pr, gamma = GAMMA) -> float
  T_aw = t_e * (1 + pr * (gamma - 1) / 2 * me^2), K: the temperature the
  insulated moving plate floats to (recovery temperature of the moving
  wall). Identical, within 1e-12, to t_e + pr * Ue^2 / (2 cp) with cp =
  gamma * R / (gamma - 1). ValueError if t_e <= 0, me <= 0 or pr <= 0.
- velocity_profile(y, h, u_e) -> float u = u_e * y / h, m/s (linear
  profile). ValueError if h <= 0, u_e <= 0 or y outside [0, h].
- temperature_profile(y, h, t_e, me, pr, gamma = GAMMA) -> float T(y), K:
  the Crocco energy-integral profile T = t_e * (1 + pr * (gamma - 1) / 2 *
  me^2 * (2 eta - eta^2)) with eta = y / h, which satisfies T(0) = T_e,
  T(h) = T_aw and dT/dy(h) = 0 (insulated moving plate). ValueError if
  h <= 0, t_e <= 0, me <= 0, pr <= 0 or y outside [0, h].
- temperature_gradient(y, h, t_e, me, pr, gamma = GAMMA) -> float dT/dy =
  t_e * pr * (gamma - 1) * me^2 * (1 - eta) / h, K/m: analytic derivative
  of the profile, zero at y = h and positive at y = 0 (temperature rises
  away from the cold plate, so conduction carries the heat into it).
  ValueErrors as in temperature_profile.
- wall_shear(u_e, mu, h) -> float tau_w = mu * u_e / h, Pa (constant
  across the gap because the velocity profile is linear). ValueError if
  u_e <= 0, mu <= 0 or h <= 0.
- wall_heat_flux(u_e, mu, h) -> float q_w = mu * u_e^2 / h, W/m2: heat
  flux INTO the stationary plate (positive = gas loses heat to the cold
  plate; the moving plate is insulated so its flux is zero). Equals
  tau_w * u_e (viscous work per unit area) and the dissipation integral
  mu * (u_e / h)^2 * h. ValueErrors as in wall_shear.
- couette_solution(t_e, me, pr, mu, rho, h, gamma = GAMMA, r = R) -> dict
  with keys exactly "Ue", "T_aw", "tau_w", "q_w", "r", "Re_gap": Ue from
  edge_velocity, T_aw from adiabatic_wall_temperature, tau_w from
  wall_shear, q_w from wall_heat_flux, r = recovery_factor(pr),
  Re_gap = rho * Ue * h / mu (laminar-regime indicator; tau_w and q_w are
  independent of rho in constant-property Couette, rho enters only through
  Re_gap). ValueError if any input is <= 0.

Identity to test: recovery_factor(pr) returns pr exactly for any positive
pr, and the numerical recovery check (T_aw - T_e) * 2 * cp / Ue^2 recovers
pr within 1e-12; T_aw matches T_e + pr * Ue^2 / (2 cp) within 1e-12; the
profile endpoints satisfy T(0) = T_e and T(h) = T_aw with dT/dy(h) = 0
(insulated moving plate); q_w equals k * dT/dy(0), mu * Ue^2 / h and
tau_w * Ue each within 1e-9 relative, so the dissipation energy balance
closes (total shear work leaves through the stationary plate).

## Worked example

Canonical case: T_e = 300.0 K, Me = 3.0, Pr = 0.72, constant mu = 1.8e-5 Pa
s, edge density rho = 1.0e-3 kg/m3, gap h = 0.01 m, gamma = 1.4, R = 287.0
(cp = 1004.5 derived). Run your module and take the real outputs as assert
targets; the values below are the prep anchor outputs, computed by running
the prep anchor script /tmp/w42spec/anchor_compressible_couette_flow.py
(prep-verified by stdlib math, exit 0, all checks PASS):

    wave-42 anchor: compressible-couette-flow
      constant-property exact solution, insulated (adiabatic) moving plate
    inputs: T_e = 300.0 K, Me = 3.0, Pr = 0.720, mu = 1.800e-05 Pa s, rho = 1.0e-03 kg/m3, h = 0.0100 m, gamma = 1.4, R = 287.0, cp = 1004.5
    edge sound speed a_e = 347.188709 m/s
    edge (moving-plate) velocity Ue = Me*a_e = 1041.566128 m/s
    recovery factor identity:
      r = Pr = 0.720000 (constant-property Couette identity)                 PASS
      numerical recovery check r_num = (T_aw - T_e)*2*cp/Ue^2 = 0.720000 == Pr PASS
    moving-plate recovery temperature (plate insulated):
      T_aw = T_e*(1 + r*(gamma-1)/2*Me^2) = 688.800000 K
      equivalent form T_e + Pr*Ue^2/(2*cp) = 688.800000 K matches within 1e-12 PASS
    wall shear (linear profile, constant across the gap):
      tau_w = mu*Ue/h = 1.874819 Pa
      tau_w*Ue (viscous work per unit area) = 1952.748 W/m2
    temperature field and heat flux:
      conductivity k = mu*cp/Pr = 0.025113 W/(m K)
      dT/dy at stationary plate = 77760.000 K/m
      forward-difference gradient at y=0 = 77721.120 K/m tracks dT/dy(0)     PASS
      q_w = k*dT/dy at stationary plate = 1952.748 W/m2 (positive = into the wall, gas cools against the cold plate)
      closed form mu*Ue^2/h = 1952.748 W/m2 equals k*dT/dy(0)                PASS
      moving plate adiabatic: dT/dy(h) = 0.000 K/m, q(h) = 0 W/m2            PASS
    energy balance (viscous dissipation integral):
      integral mu*(du/dy)^2 dy = mu*Ue^2/h = 1952.748 W/m2 equals q_w into the stationary plate PASS
    gap Reynolds number (laminar regime indicator):
      Re_gap = rho*Ue*h/mu = 578.648 (laminar plane Couette, transition near Re ~ 1500)
    profile checks at quarter stations:
      T(y): 300.000 | 470.100 | 591.600 | 664.500 | 688.800 K
      u(y): 0.000 | 260.392 | 520.783 | 781.175 | 1041.566 m/s
      T(0) = T_e and T(h) = T_aw at the ends                                 PASS
      u linear: u(h/4)=Ue/4, u(h/2)=Ue/2, u(3h/4)=3*Ue/4                     PASS
      temperature rises monotonically from the cold to the hot plate         PASS
    dict keys exactly: ['Re_gap', 'T_aw', 'Ue', 'q_w', 'r', 'tau_w']
      couette_solution dict keys exact                                       PASS
      all checks pass                                                        PASS
    exit 0: anchor verified

- Edge state: a_e = 347.188709 m/s (sqrt(gamma R T_e)) and Ue = 1041.566128
  m/s at Me = 3.0; the moving plate drags the gas at Ue.
- Recovery identity: r = Pr = 0.720000, and the numerical recovery check
  (T_aw - T_e) * 2 cp / Ue^2 returns 0.720000, equal to Pr within 1e-12.
  This is the constant-property Couette value; the external-plate values
  sqrt(Pr) = 0.8485 and Pr^(1/3) = 0.8961 would be wrong here.
- Moving-plate temperature: T_aw = 688.800000 K = 300 * (1 + 0.72 * 0.2 *
  9), a 388.8 K recovery rise over T_e; the equivalent energy form
  T_e + Pr Ue^2 / (2 cp) gives 688.800000 K, matching within 1e-12.
- Wall shear: tau_w = mu Ue / h = 1.874819 Pa, constant across the gap;
  its viscous work rate tau_w * Ue = 1952.748 W/m2.
- Wall heat flux sign convention: q_w positive = heat flux from the gas
  INTO the wall. At the stationary plate, k * dT/dy(0) = 0.025113 * 77760.0
  = 1952.748 W/m2 into the plate (the gas cools against the cold plate);
  the closed form mu Ue^2 / h gives the same 1952.748 W/m2. The moving
  plate is insulated: dT/dy(h) = 0 and its flux is 0 W/m2.
- Energy balance: the viscous-dissipation integral mu (du/dy)^2 integrated
  over the gap equals mu Ue^2 / h = 1952.748 W/m2, exactly the heat flux
  into the stationary plate; the balance closes because the moving plate
  lets no heat through.
- Gap Reynolds number: Re_gap = 578.648 at rho = 1.0e-3 kg/m3, inside the
  laminar plane-Couette range (transition near Re ~ 1500). tau_w and q_w
  do not depend on rho in the constant-property solution; rho enters only
  through Re_gap, so the density choice is the laminar-regime statement.
- Profiles at quarter stations: T = 300.000, 470.100, 591.600, 664.500,
  688.800 K and u = 0.000, 260.392, 520.783, 781.175, 1041.566 m/s,
  monotone temperature rise from the cold plate to the insulated moving
  plate and exactly linear velocity (u = Ue y / h).

## Validation list (contract test must include)

- edge_velocity(3.0, 300.0) = 1041.566128 within 1e-6 relative; the sound
  speed a_e = Ue / Me = 347.188709 within 1e-6 relative.
- recovery_factor(0.72) = 0.72 exactly and recovery_factor(1.0) = 1.0
  exactly (r = Pr identity); ValueError at pr = 0 and pr < 0.
- Numerical recovery identity: (adiabatic_wall_temperature(300.0, 3.0,
  0.72) - 300.0) * 2 * CP / Ue^2 equals 0.72 within 1e-12, and
  adiabatic_wall_temperature equals 300.0 + 0.72 * Ue^2 / (2 * CP) within
  1e-12.
- adiabatic_wall_temperature(300.0, 3.0, 0.72) = 688.800000 K within 1e-9
  relative; ValueError at t_e <= 0, me <= 0, pr <= 0.
- temperature_profile endpoints: T(0) = 300.000000, T(h) = 688.800000;
  mid-gap T(h/2) = 591.600000 K and quarter stations 470.100000 and
  664.500000, each within 1e-9 relative of the closed form; ValueError for
  y outside [0, h] and for non-positive h, t_e, me, pr.
- temperature_gradient(0, h, ...) = 77760.000 K/m within 1e-9 relative and
  temperature_gradient(h, h, ...) = 0 within 1e-12 (insulated moving
  plate); a forward-difference gradient at y = 0 tracks dT/dy(0) within
  1e-3 relative.
- wall_shear(1041.566128, 1.8e-5, 0.01) = 1.874819 Pa within 1e-9
  relative; ValueError at u_e <= 0, mu <= 0, h <= 0.
- wall_heat_flux(1041.566128, 1.8e-5, 0.01) = 1952.748 W/m2; q_w equals
  k * dT/dy(0) with k = mu * CP / Pr = 0.025113, equals mu * Ue^2 / h and
  equals tau_w * Ue, each within 1e-9 relative (energy balance closes).
- velocity_profile linearity: u(h/4) = Ue/4, u(h/2) = Ue/2, u(3h/4) =
  3 Ue/4, each within 1e-12; ValueError for y outside [0, h].
- couette_solution(300.0, 3.0, 0.72, 1.8e-5, 1.0e-3, 0.01): dict keys
  exactly ["Ue", "T_aw", "tau_w", "q_w", "r", "Re_gap"] in that order,
  values as above, Re_gap = 578.648 within 1e-6 relative (rho * Ue * h /
  mu); ValueError at any non-positive input.
- Sign conventions: q_w and tau_w * Ue are positive (heat into the
  stationary plate, shear work positive); the moving-plate flux is zero by
  the adiabatic gradient.
- Monotonicity identity: temperature rises monotonically from the cold
  plate (T_e) to the insulated moving plate (T_aw) at fixed Me, Pr.
- Determinism and ValueError coverage across the module: no randomness,
  pure math import only, fixed dict keys and ValueError messages for every
  non-physical input class above.

## Corpus fragment (eval/hit1-wave42-compressible-couette-flow.yaml)

Query 1 (copy verbatim):
  "compute the wall shear and heat flux of a shear-driven compressible-couette-flow between a moving and a stationary plate from the linear-velocity-profile and the crocco energy relation"
  intent: "high-speed aerodynamics; compressible Couette flow exact solution, wall shear and wall heat flux of the shear-driven plate gap from the linear velocity profile and Crocco energy relation"
  expected_skill: "aerodynamics/high-speed/compressible-couette-flow"
Query 2 (copy verbatim):
  "evaluate the exact couette-flow temperature profile and heat transfer rate across a high-mach plate gap at a given gap-reynolds-number and Prandtl number"
  intent: "high-speed aerodynamics; exact Couette temperature profile and heat transfer across a high-Mach plate gap at given gap Reynolds number and Prandtl number"
  expected_skill: "aerodynamics/high-speed/compressible-couette-flow"
Task ids: w42-compressible-couette-flow-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the exact constant-property
solution for compressible Couette flow in a high-Mach plate gap:" and
include the outputs in the Claim (linear velocity profile, Crocco
temperature profile, insulated moving-plate temperature from the recovery
relation r = Pr, wall shear tau_w = mu Ue / h, wall heat flux q_w into the
stationary plate and the dissipation energy-balance check, at a given plate
Mach number, Prandtl number and gap Reynolds number). First tag:
compressible-couette-flow. Additional tags ONLY: shear-driven-gap-flow,
crocco-energy-integral, gap-reynolds-number. NEVER single generic words
(couette, flow, plate, gap, heat, shear, wall, temperature, mach, reynolds,
prandtl, velocity, profile). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): cold-wall-heat-flux,
adiabatic-wall-temperature, recovery-factor, reference-temperature-method,
reynolds-analogy-factor, skin-friction-coefficient, flat-plate-heating,
turbulent-plate-heating, eckert-reference-temperature, sutherland-viscosity,
sutherland-law (flat-plate-skin-friction-heating, external-plate sense);
sutton-graves, stagnation-point-heating, radiation-equilibrium-temperature,
nose-radius-bluntness, reentry-heating (aerodynamic-heating); plus the other
high-speed pack leaf names with their owned token sets (normal-shock,
oblique-shock, prandtl-meyer, hypersonic-flow, regular-shock-reflection,
shock-expansion-airfoil, isentropic-flow-relations, bow-shock-standoff,
transonic-similarity, swept-wing-aerodynamics, supercritical-airfoil,
wave-drag-area-rule). This leaf DOES compute the insulated moving-plate
temperature and DOES verify the constant-property recovery identity
r = Pr, but that is the Couette framing: the flat-plate corpus phrases above
remain owned by flat-plate-skin-friction-heating, so description, tags and
corpus intents must route on compressible-couette-flow,
shear-driven-gap-flow, crocco-energy-integral, gap-reynolds-number,
plate-gap, linear-velocity-profile and moving-plate vocabulary only (the
two corpus queries above already comply: neither contains a flat-plate-owned
token string, so they cannot collide with the flat-plate or stagnation
heating corpus tasks).

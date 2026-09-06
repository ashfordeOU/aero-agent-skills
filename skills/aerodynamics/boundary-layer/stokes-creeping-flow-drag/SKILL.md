---
name: stokes-creeping-flow-drag
description: "Use when you must compute the steady low-Reynolds-number viscous drag on a sphere in creeping flow, the Stokes solution for the slow motion of a sphere through a viscous fluid: evaluate the stokes streamfunction and the velocity field about the sphere, the surface pressure and wall-shear distributions with their high-pressure-facing-the-stream signature, the total stokes drag F = 6*pi*mu*a*U split one third pressure drag to two thirds friction drag, the drag coefficient Cd = 24/Re_D at the diameter Reynolds number, the Oseen correction factor 1 + (3/8)*Re_a on the radius-based Reynolds number, and the terminal settling velocity (2/9)*(rho_p - rho_f)*g*a^2/mu of a small dense sphere in still air. Produces the creeping-flow drag, the field values and the settling speed in SI units that anchor low-Reynolds-number body-drag estimates and viscous-flow checks. Trigger: stokes-creeping-flow-drag, creeping-flow, stokes-drag, stokes-streamfunction, oseen-correction, terminal-velocity."
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
  tags: [stokes-creeping-flow-drag, creeping-flow, stokes-drag, stokes-streamfunction, oseen-correction, terminal-velocity]
  version: 0.1.0
  author: AeroSkills
---

# Stokes Creeping-Flow Drag (aerodynamics/boundary-layer/stokes-creeping-flow-drag)

Use when you must compute the steady creeping (Stokes, 1851) flow of a
viscous fluid past a sphere at Reynolds number well below one: the
slow-motion solution of the full Navier-Stokes equations with the
inertia terms dropped, in the form Schlichting Boundary-Layer Theory
section 4 presents it. This leaf implements the Stokes streamfunction
and the velocity field about the sphere, the surface pressure and wall
shear, the total drag F = 6*pi*mu*a*U with its exact one-third
pressure (form) to two-thirds friction split, the drag coefficient
Cd = 24/Re_D, the Oseen first-order drag correction and the terminal
settling velocity, in pure Python stdlib, closed form, no iteration.
It is the steady low-Reynolds-number member of the exact-viscous
family, complementing the time-dependent plate Stokes layers of
unsteady-laminar-stokes-layers, and it anchors low-Reynolds-number
body-drag estimates for particle drift and droplet settling checks.
It does not do time-dependent plate Stokes layers, high-Mach
compressible sphere drag, flat-plate boundary layers or parachute
descent balances: incompressible constant-property laminar flow only,
uniform mu and nu, Reynolds numbers in the creeping range.

## Domain quick reference

Spherical polar coordinates (r, theta) with theta measured from the
downstream pole: the uniform stream U runs along +z toward theta = 0
and the windward stagnation point sits at theta = pi. Module constants:
NU_AIR = 1.46e-5 m2/s, RHO_AIR = 1.225 kg/m3, G = 9.81 m/s2,
RHO_WATER = 1000.0 kg/m3 (particle density for the settling example).
Dynamic viscosity is always derived MU_AIR = RHO_AIR * NU_AIR =
1.7885e-05 Pa s, never an input.

- Stokes streamfunction: psi(r, theta) = 0.5*U*r^2*sin(theta)^2 *
  (1 - 1.5*a/r + 0.5*(a/r)^3), m3/s. psi(a, theta) = 0 identically
  (the sphere surface is the psi = 0 streamline) and psi ->
  0.5*U*r^2*sin(theta)^2 as r -> inf (uniform stream value).
- Radial velocity: u_r = U*cos(theta)*(1 - 1.5*a/r + 0.5*(a/r)^3),
  m/s. Negative on the axis upstream of the windward point (theta =
  pi, flow approaching), positive downstream (theta = 0);
  u_r(a, theta) = 0 (no penetration).
- Tangential velocity: u_theta = -U*sin(theta)*(1 - 0.75*a/r -
  0.25*(a/r)^3), m/s. u_theta(a, theta) = 0 (no slip). Fore-aft
  symmetry at zero Reynolds number: u_r(2a, 0) = -u_r(2a, pi) =
  +-0.3125*U, no wake and no separation.
- Surface pressure: p - p_inf = -1.5*(mu*U/a)*cos(theta), Pa: HIGH by
  1.5*mu*U/a at the windward stagnation point (theta = pi), LOW by the
  same amount at the downstream pole (theta = 0), zero at the equator.
  The reversed-pressure signature of creeping flow: no dynamic-pressure
  head, the pressure does not rise on the lee side.
- Wall shear: tau_w = 1.5*(mu*U/a)*sin(theta), Pa: zero at the
  stagnation points theta = 0 and pi, peak 1.5*mu*U/a at the equator
  theta = pi/2.
- Stokes drag: F = 6*pi*mu*a*U, N. Pressure (form) drag
  F_p = 2*pi*mu*a*U from the surface pressure integral, friction drag
  F_f = 4*pi*mu*a*U from the wall-shear integral: F_p + F_f = F
  identically and F_p/F_f = 1/2 exactly (one third form drag, two
  thirds friction drag).
- Drag coefficient: Cd = F/(0.5*rho*U^2*pi*a^2) = 24/Re_D =
  12*mu/(rho*U*a), dimensionless, with Re_D = U*2a/nu the
  diameter-based Reynolds number.
- Oseen first-order correction: F_oseen = 6*pi*mu*a*U*(1 + (3/8)*Re_a),
  N, with Re_a = U*a/nu the radius-based Reynolds number, identical to
  the factor 1 + (3/16)*Re_D on the diameter-based number. The factor
  is 1.1875 at Re_a = 0.5. The Oseen term is a first-order drag
  correction toward Re ~ 1, kept inside this leaf, never claimed as a
  separate flow theory.
- Terminal settling velocity: weight minus buoyancy
  (4/3)*pi*a^3*(rho_p - rho_f)*g = 6*pi*mu*a*U gives
  U_t = (2/9)*(rho_p - rho_f)*g*a^2/mu, m/s, a closed-form balance
  valid while Re_D(U_t) stays below about 0.1. The Oseen-corrected
  terminal velocity is the closed root of U*(1 + (3/8)*U*a/nu) = U_t:
  U = (-1 + sqrt(1 + 4*c*U_t))/(2*c) with c = (3/8)*(a/nu).
- SI units throughout; Stokes 1851 and Schlichting section 4 material
  cited through NACA TR-824, summary-only.

## Workflow

1. Fix the creeping-flow state: the sphere radius a, the stream speed
   U, the fluid density rho and kinematic viscosity nu (mu = rho*nu
   derived, never an input), then confirm the regime with the
   radius-based and diameter-based Reynolds numbers
   (radius_reynolds, diameter_reynolds): Re_D below about one keeps
   the pure Stokes law operative.
2. Traverse the streamfunction and velocity field about the sphere
   (stokes_streamfunction, radial_velocity, tangential_velocity) over
   r >= a and the polar angle: the no-slip surface values
   psi(a, theta) = u_r(a, theta) = u_theta(a, theta) = 0 and the
   fore-aft symmetric far field u_r(2a, 0) = -u_r(2a, pi) = 0.3125*U
   are the creeping-flow fingerprints.
3. Traverse the surface pressure difference with surface_pressure_delta
   over the polar angle: read the high-pressure windward stagnation
   point (theta = pi) and the equal suction at the downstream pole
   (theta = 0), the reversed-pressure signature.
4. Traverse the wall shear with wall_shear_stress over the polar angle:
   zero at both stagnation points, peak 1.5*mu*U/a at the equator.
5. Assemble the drag: the total stokes_drag with the pressure_drag
   (one third) and friction_drag (two thirds) split; the closed-form
   identity pressure_drag + friction_drag = stokes_drag is exact.
6. Reduce the drag with drag_coefficient against the freestream dynamic
   pressure and frontal area; cross-check Cd = 24/Re_D on the
   diameter-based Reynolds number.
7. Apply the Oseen first-order correction for Reynolds numbers
   approaching one: oseen_correction(Re_a) multiplies the drag in
   oseen_drag, a 2.6 percent rise at Re_a = 0.068 and 18.75 percent at
   Re_a = 0.5.
8. Balance settling: terminal_velocity from weight minus buoyancy
   against the Stokes drag, and run the creeping Reynolds check
   Re_D(U_t) below about 0.1 at the settling speed.
9. Correct the terminal velocity with oseen_terminal_velocity, the
   closed root of the corrected balance, always below the Stokes
   value.
10. Confirm the deterministic checks: rerun the closed-form identities
    and reject non-physical inputs (the input-rejection traverse) with
    the contract test scripts/test_stokes_creeping_flow_drag.py.

## Worked example

Air at standard conditions nu = 1.46e-5 m2/s, rho = 1.225 kg/m3,
mu = rho*nu = 1.7885e-05 Pa s, g = 9.81 m/s2. All values below are
real outputs of the module.

Worked sphere: radius a = 1.0e-4 m (0.1 mm) at U = 0.01 m/s in air:

- Reynolds numbers: Re_a = U*a/nu = 0.068493151 and Re_D = U*2a/nu =
  0.1369863, the low end of the creeping range where the Oseen
  correction still matters.
- Stokes drag F = 6*pi*mu*a*U = 3.3712431e-10 N (0.337 nN). Pressure
  (form) drag F_p = 2*pi*mu*a*U = 1.1237477e-10 N, friction drag
  F_f = 4*pi*mu*a*U = 2.2474954e-10 N: the split is one third of the
  total to pressure and two thirds to friction, an exact 1:2 ratio,
  and the sum check F_p + F_f - F leaves a zero residual (module
  value 0.0 N). Creeping linearity: F(2U)/F(U) = 2.0 exactly.
- Drag coefficient Cd = 12*mu/(rho*U*a) = 175.2, identical to
  24/Re_D = 175.2 and to F/(0.5*rho*U^2*pi*a^2) = 175.2, three
  independent routes agree.
- Surface pressure p - p_inf = -1.5*(mu*U/a)*cos(theta):
  +2.68275e-03 Pa at the windward stagnation point (theta = pi),
  -2.68275e-03 Pa at the downstream pole (theta = 0), and zero at the
  equator (module residual -1.64271060e-19 Pa): high pressure faces
  the oncoming stream, an equal suction trails it.
- Wall shear tau_w = 1.5*(mu*U/a)*sin(theta): 1.89699072e-03 Pa at
  theta = pi/4, peak 2.68275e-03 Pa at theta = pi/2, symmetric
  1.89699072e-03 Pa at theta = 3*pi/4, and 0.0 Pa at theta = 0 with a
  3.285e-19 Pa float residue at theta = pi.
- Velocity field at r = 2a: u_r = +3.12500000e-03 m/s downstream on
  the axis (theta = 0), zero at the equator (module residual
  1.91351062e-19 m/s), and -3.12500000e-03 m/s upstream (theta = pi):
  the flow is fore-aft symmetric with no wake at this Reynolds
  number. Tangential component u_theta = -4.19844651e-03 m/s at
  theta = pi/4 and -5.93750000e-03 m/s at theta = pi/2.
- No slip on the surface: u_r(a, pi/3) = 0.0 m/s and u_theta(a, pi/3)
  = -0.0 m/s; the streamfunction is psi(a, theta) = 0 on the surface,
  psi(2a, pi/2) = 6.25000000e-11 m3/s (0.625*U*a^2) and psi(2a, pi/4)
  = 3.12500000e-11 m3/s.

Oseen correction:

- At the worked sphere Re_a = 0.068493151 the factor 1 + (3/8)*Re_a =
  1.025684932, a 2.56849 percent drag increase, giving F_oseen =
  6*pi*mu*a*U*(1 + 3*Re_a/8) = 3.45783322e-10 N.
- Factor values: 1.1875 at Re_a = 0.5, identical to 1 + (3/16)*Re_D
  at Re_D = 1.0 (the two Reynolds conventions give the same
  correction).

Terminal velocity: a water droplet (rho_p = 1000 kg/m3) of radius
a = 1.0e-5 m (10 microns) settling in still air:

- Stokes terminal velocity U_t = (2/9)*(rho_p - rho_f)*g*a^2/mu =
  1.21740537e-02 m/s (1.217 cm/s).
- Balance check: stokes_drag at U_t over the buoyancy-adjusted weight
  (4/3)*pi*a^3*(rho_p - rho_f)*g = 1.0 exactly (module value).
- Droplet Reynolds numbers at U_t: Re_a = 0.0083383929 and Re_D =
  0.016676786, deep inside the creeping regime (Re_D well below 0.1),
  so the pure Stokes balance is the operative one.
- Oseen factor at U_t: 1 + (3/8)*Re_a = 1.003126897; the
  Oseen-corrected terminal velocity (closed-form quadratic root) is
  1.21362229e-02 m/s, 0.310749 percent below the Stokes value.

Read-off: a 0.1 mm sphere drifting at 1 cm/s through air carries only
0.337 nN of drag, one third of it pressure and two thirds friction,
with a drag coefficient of 175, while a 10 micron water droplet
settles at 1.22 cm/s with a Reynolds number of 0.017; the reversed
surface pressure (high facing the stream, suction behind) and the
fore-aft symmetric field are the fingerprints of creeping flow, and
the Oseen factor adds 2.6 percent drag at Re_a = 0.068 and 18.75
percent at Re_a = 0.5.

## Verification

- Confirm radius_reynolds(0.01, 1.0e-4, 1.46e-5) returns 0.068493151
  and diameter_reynolds returns 0.1369863, exactly twice the
  radius-based value.
- Confirm stokes_drag(1.7885e-5, 1.0e-4, 0.01) returns 3.3712431e-10 N
  (between 3.0e-10 and 4.0e-10 N) and that doubling the speed exactly
  doubles the drag (creeping linearity).
- Confirm the split: pressure_drag 1.1237477e-10 N, friction_drag
  2.2474954e-10 N, friction/pressure exactly 2, and the sum equals
  stokes_drag to float noise.
- Confirm drag_coefficient(1.225, 1.7885e-5, 0.01, 1.0e-4) returns
  175.2, equal to 24/Re_D and to F/(0.5*rho*U^2*pi*a^2).
- Confirm surface_pressure_delta is +2.68275e-03 Pa at theta = pi and
  -2.68275e-03 Pa at theta = 0 (antisymmetric, equator zero) and
  wall_shear_stress peaks at 2.68275e-03 Pa at theta = pi/2.
- Confirm the no-slip surface values, the fore-aft symmetric field at
  r = 2a and the oseen_drag 3.45783322e-10 N at the worked sphere.
- Confirm terminal_velocity(1000.0, 1.225, 1.7885e-5, 1.0e-5) returns
  1.21740537e-02 m/s (between 1.1e-2 and 1.3e-2 m/s) with the
  drag-weight balance at 1.0 and Re_D(U_t) = 0.016676786 below 0.1.
- Confirm every non-positive mu, a, U, rho, nu, every r below a, a
  negative Re_a and every rho_particle at or below rho_fluid raises
  ValueError.
- Run the contract test offline: python3
  scripts/test_stokes_creeping_flow_drag.py (35 tests, deterministic).

## Related leaves

- aerodynamics/boundary-layer/unsteady-laminar-stokes-layers: the
  unsteady member of the exact-viscous family, time-dependent Stokes
  layers of an infinite plate in a quiescent fluid; this leaf is the
  steady low-Reynolds-number body-drag complement.
- aerodynamics/boundary-layer/boundary-layer-theory: steady flat-plate
  layers (Blasius and 1/7-power skin friction), flat plate only, no
  sphere and no body drag.
- aerodynamics/high-speed/hypersonic-flow: the compressible high-Mach
  sphere drag of impact theory at Mach well above 5, the regime fence
  that never meets the incompressible creeping limit of the same
  geometry.
- space-systems/mission-design/entry-descent-landing: the high-Reynolds
  parachute terminal-velocity balance under the parachute drag
  coefficient, the bluff-body descent fence against the creeping
  Stokes balance.

## Pitfalls

- Applying the Stokes law above the creeping range: once Re_D climbs
  past about one, inertia, wake and separation break the linear drag
  and Cd = 24/Re_D under-predicts; run the Reynolds check and take the
  Oseen correction only toward Re ~ 1.
- Mixing the Reynolds conventions: Cd = 24/Re_D uses the diameter
  while the Oseen factor (3/8)*Re_a uses the radius, so 1 + (3/16)*Re_D
  is the diameter-based twin of the factor; swapping conventions
  halves or doubles the correction.
- Reading the 1:2 split backwards: creeping sphere drag is one third
  pressure and two thirds friction, the reverse of a high-Reynolds
  bluff body, and the surface pressure is high at the windward
  stagnation point with suction at the lee pole, opposite to
  Bernoulli intuition, because viscosity dominates at Re << 1.
- Feeding mu as an input: dynamic viscosity is always derived
  mu = rho*nu (MU_AIR = RHO_AIR*NU_AIR = 1.7885e-05 Pa s in the
  module); an inconsistent rho-nu pair silently shifts every drag and
  settling value.
- Skipping the creeping check on a settling sphere: the Stokes balance
  holds while Re_D(U_t) stays below about 0.1; larger or denser
  droplets need the Oseen-corrected root or a higher-Reynolds drag
  law.
- Forgetting the buoyancy: U_t uses rho_p - rho_f, and a sphere with
  rho_p at or below rho_f does not settle (the module raises
  ValueError).
- Reversing the polar-angle convention: theta is measured from the
  downstream pole with the windward stagnation point at theta = pi;
  swapping the convention flips the pressure sign and mirrors the
  streamfunction field.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_stokes_creeping_flow_drag.py

The test covers the worked-example contract (Reynolds numbers, drag
with magnitude bounds, the 1:2 pressure-to-friction split, Cd = 175.2
by three routes), the surface pressure and wall-shear traverses with
their anchors, the no-slip surface and fore-aft symmetric far-field
values, the streamfunction anchors, the Oseen correction and drag, the
terminal-velocity balance with its creeping Reynolds check, the
Oseen-corrected settling root, deterministic repeat calls, and the
input-rejection traverse of non-physical mu, a, U, rho, nu, r, Re_a
and buoyancy arguments.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is the cited
  reference for the viscous-layer family; the classical creeping-flow
  treatment follows Stokes 1851 and Schlichting Boundary-Layer Theory
  section 4, whose material is cited through the report. Summary-only
  methodology per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

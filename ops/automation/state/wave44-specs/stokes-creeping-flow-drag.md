# Wave-44 leaf spec: stokes-creeping-flow-drag (aerodynamics,
# boundary-layer pack)

- Path: skills/aerodynamics/boundary-layer/stokes-creeping-flow-drag/
- Pack: boundary-layer (present siblings boundary-layer-theory,
  boundary-layer-transition, boundary-layer-separation,
  stagnation-flow-boundary-layer, rough-wall-skin-friction,
  unsteady-laminar-stokes-layers; adjacent fences in
  aerodynamics/high-speed/hypersonic-flow, the Newtonian blunt-body
  sphere drag at Mach well above 5, and space-systems/mission-design/
  entry-descent-landing, the parachute terminal-velocity balance at
  high Reynolds number).
- Provenance: wave-44 leaf-plan entry (ops/automation/state/
  wave44-leaf-plan.md, lines 84-91) dispatches this leaf as planned
  leaf 8 of 14 from probe AERO 49 task-6 rank 4, GO-lean lowest
  confidence: "steady low-Re viscous flow - Stokes streamfunction for
  the sphere, F = 6*pi*mu*a*U, pressure/form drag split 1:2, Oseen
  correction, terminal velocity; unsteady-laminar-stokes-layers is
  unsteady 1st/2nd-problem only, hypersonic-flow sphere-drag is
  Newtonian M >> 5 (quoted handover); Stokes 1851/Schlichting sec 4;
  naca-tr-824; corpus intents worded to stay inside the boundary-layer
  viscous vein". The probe receipt (subagent-summary-6-20260906_163221_
  972669.txt, rank-4 block) records the claim verbatim, the greps
  magnus|oseen|creeping|stokes drag returning 0 files under skills/
  and 0 corpus tasks, and the hypersonic-flow regime-handover fence
  quote. SPEC-TIME TRIAGE DONE FIRST: every boundary-layer pack sibling
  SKILL.md body plus the hypersonic-flow body read at prep (see fences
  below); no leaf in the tree owns steady low-Reynolds-number viscous
  body drag. GO.
- Claim fences (quoted from the sibling frontmatter and body at prep,
  none owns steady creeping-flow drag about a body):
  - unsteady-laminar-stokes-layers (this pack, the wave-43 sibling)
    opens "Use when you must compute the exact unsteady laminar Stokes
    layer of an infinite plate in a quiescent fluid, either impulsively
    started or oscillating in its own plane", and its whole claim is
    the time-dependent 1st/2nd-problem plate layers: the erfc
    similarity profile u/U = erfc(y/(2*sqrt(nu*t))) of the impulsively
    started plate, the layer edge 3.6428*sqrt(nu*t), the wall shear
    decay rho*U*sqrt(nu/(pi*t)), the displacement thickness
    2*sqrt(nu*t/pi), and the oscillating-plate penetration depth
    sqrt(2*nu/omega) with the exp(-1) amplitude and 45-degree shear
    phase. No body, no drag force, no sphere, no pressure integral
    appears anywhere in it. The new leaf is the steady member of the
    exact-viscous family for BODY drag (Stokes 1851), the low-Reynolds
    complement to that plate-layer leaf, and must not claim any
    time-dependent layer, penetration depth, rayleigh-layer, or
    stokes-first/second-problem content.
  - hypersonic-flow (aerodynamics/high-speed) opens "Use when you must
    estimate aerodynamic forces on a body in hypersonic flow with
    modified Newtonian impact theory" and owns the tags
    sphere-drag-coefficient and blunt-body-drag for the Newtonian
    pressure integral Cd = Cp_max/2 over the windward hemisphere at
    Mach well above 5; its body states the regime handover: "the
    supersonic high-speed leaves, which own the regime below Mach ~ 5
    where Newtonian methods hand over to shock-expansion and
    oblique-shock estimates". That sphere drag is a compressible
    high-Mach impact-pressure estimate with the flow attached behind a
    bow shock; creeping-flow drag is the incompressible Re << 1
    viscous limit of the same geometry. The two never meet: the new
    leaf must not claim Newtonian impact pressure, stagnation
    coefficients, Cp_max/2 blunt-body drag or the hypersonic vacuum
    limit.
  - boundary-layer-theory (this pack) owns steady flat-plate layers:
    Blasius and 1/7-power thickness, displacement and momentum
    thickness, local and average skin-friction coefficients, Reynolds-
    number regime and transition location on a smooth surface. Flat
    plate only, no sphere and no body drag.
  - boundary-layer-transition, boundary-layer-separation,
    rough-wall-skin-friction and stagnation-flow-boundary-layer (this
    pack) own the Michel/Thwaites/Stratford transition and separation
    criteria, the sand-roughness k-plus turbulent skin-friction
    correlation and the Hiemenz/Homann stagnation-point layer; none
    carries a body-drag or creeping-flow claim.
  - entry-descent-landing (space-systems/mission-design) owns the
    parachute terminal-velocity balance U_t = sqrt(2*m*g/(rho*Cd*A))
    for a lander at high Reynolds number under a canopy drag
    coefficient (its script parachute_terminal_velocity); that is a
    bluff-body drag balance, not the creeping Stokes balance, and the
    new leaf must not claim canopy drag or touchdown-speed content.
  Whole-tree greps at prep: "creeping|oseen|stokes-drag|magnus" =
    0 hits under skills/ and 0 hits in eval/hit1-corpus.yaml (both
    greps exit 1); "stokes" under skills/aerodynamics appears ONLY in
    the unsteady-laminar-stokes-layers directory. Corpus check of the
    adjacent tokens: "terminal velocity" has exactly 1 existing task
    hit, w21-entry-descent-landing-2 (parachute descent sizing, quoted
    above), which routes to space-systems and shares no creeping-flow
    token with the new leaf; the w43-unsteady-laminar-stokes-layers
    tasks route on rayleigh-layer and oscillating-plate tokens, and the
    w28-hypersonic-flow tasks route on Newtonian impact-pressure
    tokens, neither of which the new corpus queries carry. GENUINE
    aerodynamics gap (fresh probe, GO): no leaf owns the steady
    low-Reynolds-number viscous drag on a sphere, the Stokes
    streamfunction solution or the settling terminal-velocity balance.
- Standards id: naca-tr-824 (reference-only, present in
  standards-map.yaml, the sibling precedent for the viscous-layer
  family; the classical creeping-flow treatment follows Stokes 1851
  and Schlichting Boundary-Layer Theory section 4, whose material is
  cited through the report). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Compute the steady creeping (Stokes, 1851) flow of a viscous fluid
past a sphere at Reynolds number well below one, the slow-motion
solution of the full Navier-Stokes equations with the inertia terms
dropped, in the form Schlichting section 4 presents it. Stokes
streamfunction for a uniform stream U past a sphere of radius a in
spherical polar coordinates (r, theta) with theta measured from the
downstream pole (the stream runs along +z, so the windward stagnation
point sits at theta = pi): psi = 0.5*U*r^2*sin(theta)^2 * (1 -
1.5*a/r + 0.5*(a/r)^3), identically zero on the sphere surface (the
surface is a streamline) and approaching the uniform-stream value
0.5*U*r^2*sin(theta)^2 far away. Velocity field from the
streamfunction: u_r = U*cos(theta)*(1 - 1.5*a/r + 0.5*(a/r)^3) and
u_theta = -U*sin(theta)*(1 - 0.75*a/r - 0.25*(a/r)^3), both vanishing
on the surface (no slip) and fore-aft symmetric about the equator
plane, the signature of zero Reynolds number: no wake, no separation.
Surface pressure and shear: p - p_inf = -1.5*(mu*U/a)*cos(theta),
HIGH by 1.5*mu*U/a at the windward stagnation point and LOW by the
same amount at the downstream pole (the reversed-pressure signature of
creeping flow, no dynamic-pressure head), and wall shear
tau_w = 1.5*(mu*U/a)*sin(theta), zero at the stagnation points and
peak at the equator. Total drag on the sphere is the Stokes drag
F = 6*pi*mu*a*U, split one third pressure (form) drag
F_p = 2*pi*mu*a*U from the surface pressure integral and two thirds
friction drag F_f = 4*pi*mu*a*U from the wall-shear integral, the
exact 1:2 form-to-friction split; the drag coefficient against the
freestream dynamic pressure and frontal area is Cd = 24/Re_D with
Re_D = U*2a/nu the diameter-based Reynolds number. Oseen first-order
correction for Reynolds numbers approaching one: F = 6*pi*mu*a*U *
(1 + (3/8)*Re_a) with Re_a = U*a/nu the radius-based Reynolds number
(equivalently Cd = (24/Re_D)*(1 + 3*Re_D/16)), a 3.75 percent drag
increase at Re_a = 0.5. Terminal settling velocity of a small dense
sphere in still fluid, the balance of weight minus buoyancy
(4/3)*pi*a^3*(rho_p - rho_f)*g against the Stokes drag:
U_t = (2/9)*(rho_p - rho_f)*g*a^2/mu, valid while the Reynolds number
at U_t stays below about 0.1; the Oseen-corrected terminal velocity is
the closed-form root of the same balance with the corrected drag.
Produces the streamfunction and velocity field, the surface pressure
and shear, the total drag with its 1:2 split, the drag coefficient,
the Oseen correction and the terminal velocity, in SI units, that
anchor low-Reynolds-number body-drag estimates and viscous-flow
checks. Does NOT do: the time-dependent Stokes layers of the
impulsively started or oscillating plate with their erfc profiles,
penetration depth and shear phase (unsteady-laminar-stokes-layers);
the Newtonian blunt-body sphere drag Cd = Cp_max/2 of modified impact
theory at Mach well above 5, or any stagnation-pressure-coefficient
content (hypersonic-flow); the steady flat-plate boundary layers,
Blasius and 1/7-power skin-friction correlations, transition or
Reynolds-number-regime assignment (boundary-layer-theory,
boundary-layer-transition); high-Reynolds parachute descent balances
under a canopy drag coefficient (entry-descent-landing).
Incompressible constant-property laminar flow only, uniform mu and nu;
turbulence, compressibility, wall curvature effects on the drag law
and Reynolds numbers above the creeping range are out of scope.

## Model (implement exactly)

Pure stdlib, math only, closed form. Module constants (air at standard
conditions, used by the worked example): NU_AIR = 1.46e-5 (m2/s
kinematic viscosity), RHO_AIR = 1.225 (kg/m3), G = 9.81 (m/s2),
RHO_WATER = 1000.0 (kg/m3 particle density for the settling example).
Dynamic viscosity is always derived MU_AIR = RHO_AIR * NU_AIR =
1.7885e-05 Pa s, never an input. Spherical polar coordinates (r,
theta), theta measured from the downstream pole: the uniform stream U
runs along +z toward theta = 0 and the windward stagnation point is at
theta = pi. All formulas pinned exactly as written; every function
below derives from them.

Defining relations:
- Stokes streamfunction: psi(r, theta) = 0.5*U*r^2*sin(theta)^2 *
  (1 - 1.5*a/r + 0.5*(a/r)^3); psi(a, theta) = 0 identically (the
  sphere surface is the psi = 0 streamline) and psi -> 0.5*U*r^2*
  sin(theta)^2 as r -> inf (uniform stream).
- Radial velocity: u_r = U*cos(theta)*(1 - 1.5*a/r + 0.5*(a/r)^3);
  on the axis upstream of the windward point (theta = pi) u_r is
  negative (flow approaching the sphere), downstream (theta = 0)
  positive; u_r(a, theta) = 0 (no penetration).
- Tangential velocity: u_theta = -U*sin(theta)*(1 - 0.75*a/r -
  0.25*(a/r)^3); u_theta(a, theta) = 0 (no slip). Fore-aft symmetry
  at zero Reynolds number: u_r(2a, 0) = -u_r(2a, pi) = +-0.3125*U.
- Surface pressure: p - p_inf = -1.5*(mu*U/a)*cos(theta): +1.5*mu*U/a
  at the windward stagnation point theta = pi, -1.5*mu*U/a at the
  downstream pole theta = 0, zero at the equator theta = pi/2.
- Wall shear: tau_w = 1.5*(mu*U/a)*sin(theta): zero at theta = 0 and
  pi, peak 1.5*mu*U/a at theta = pi/2.
- Stokes drag: F = 6*pi*mu*a*U; pressure drag F_p = 2*pi*mu*a*U
  (surface pressure integral), friction drag F_f = 4*pi*mu*a*U (wall
  shear integral), so F_p + F_f = F identically and F_p/F_f = 1/2
  exactly (one third form drag, two thirds friction drag).
- Drag coefficient: Cd = F/(0.5*rho*U^2*pi*a^2) = 24/Re_D =
  12*mu/(rho*U*a), Re_D = U*2a/nu.
- Oseen correction: F_oseen = 6*pi*mu*a*U*(1 + (3/8)*Re_a), Re_a =
  U*a/nu, so the correction factor is oseen_correction(Re_a) = 1 +
  (3/8)*Re_a; identical to 1 + (3/16)*Re_D on the diameter-based
  Reynolds number. The factor is 1.1875 at Re_a = 0.5 (3.75 percent
  drag rise per 0.5 of radius-based Reynolds number).
- Terminal velocity: weight minus buoyancy (4/3)*pi*a^3*(rho_p -
  rho_f)*g = 6*pi*mu*a*U gives U_t = (2/9)*(rho_p - rho_f)*g*a^2/mu,
  a closed-form balance, no iteration. Valid while Re_D(U_t) is below
  about 0.1 (creeping). Oseen-corrected terminal velocity: the closed
  root of U*(1 + (3/8)*U*a/nu) = U_t, U = (-1 + sqrt(1 + 4*c*U_t))/
  (2*c) with c = (3/8)*(a/nu).

Functions (signatures and validation pinned):
- stokes_streamfunction(U, a, r, theta) -> float
  0.5*U*r^2*sin(theta)^2*(1 - 1.5*a/r + 0.5*(a/r)^3) in m3/s.
  ValueError if a <= 0 or r < a (the flow occupies r >= a only).
- radial_velocity(U, a, r, theta) -> float
  U*cos(theta)*(1 - 1.5*a/r + 0.5*(a/r)^3) in m/s. ValueError set as
  stokes_streamfunction.
- tangential_velocity(U, a, r, theta) -> float
  -U*sin(theta)*(1 - 0.75*a/r - 0.25*(a/r)^3) in m/s. ValueError set
  as stokes_streamfunction.
- stokes_drag(mu, a, U) -> float
  6.0*math.pi*mu*a*U in N. ValueError if mu <= 0, a <= 0 or U <= 0.
- pressure_drag(mu, a, U) -> float
  2.0*math.pi*mu*a*U in N, one third of the Stokes drag. ValueError
  set as stokes_drag.
- friction_drag(mu, a, U) -> float
  4.0*math.pi*mu*a*U in N, two thirds of the Stokes drag. ValueError
  set as stokes_drag.
- surface_pressure_delta(mu, U, a, theta) -> float
  -1.5*(mu*U/a)*math.cos(theta) in Pa. ValueError if mu <= 0, a <= 0
  or U <= 0; theta is any real.
- wall_shear_stress(mu, U, a, theta) -> float
  1.5*(mu*U/a)*math.sin(theta) in Pa. ValueError set as
  surface_pressure_delta.
- radius_reynolds(U, a, nu) -> float
  U*a/nu, the radius-based Reynolds number of the Oseen correction.
  ValueError if U <= 0, a <= 0 or nu <= 0.
- diameter_reynolds(U, a, nu) -> float
  U*2*a/nu, the diameter-based Reynolds number of Cd = 24/Re_D.
  ValueError set as radius_reynolds.
- drag_coefficient(rho, mu, U, a) -> float
  12.0*mu/(rho*U*a), equal to 24/Re_D. ValueError if rho <= 0, mu <=
  0, U <= 0 or a <= 0.
- oseen_correction(Re_a) -> float
  1.0 + (3.0/8.0)*Re_a, the Oseen first-order drag factor. ValueError
  if Re_a < 0.
- oseen_drag(mu, a, U, nu) -> float
  stokes_drag(mu, a, U) * oseen_correction(radius_reynolds(U, a, nu))
  in N. ValueError if nu <= 0 plus the stokes_drag set.
- terminal_velocity(rho_particle, rho_fluid, mu, a) -> float
  (2.0/9.0)*(rho_particle - rho_fluid)*G*a*a/mu in m/s. ValueError if
  rho_particle <= 0, rho_fluid <= 0, rho_particle <= rho_fluid (a
  neutrally or positively buoyant sphere does not settle), mu <= 0 or
  a <= 0.
- oseen_terminal_velocity(rho_particle, rho_fluid, mu, a, nu) ->
  float. U_s = terminal_velocity(...), c = (3.0/8.0)*(a/nu), return
  (-1.0 + math.sqrt(1.0 + 4.0*c*U_s))/(2.0*c) in m/s, the closed-form
  root of the corrected balance. ValueError set as
  terminal_velocity plus nu <= 0.

Identities to test (closed form):
- Surface streamline and no slip: psi(a, theta) = 0 exactly; u_r(a,
  theta) = u_theta(a, theta) = 0 to float noise at any theta (anchor
  residuals at theta = pi/3 are 0.000e+00 and -0.000e+00).
- Far field and symmetry: u_r(2a, 0) = +0.3125*U exactly (0.3125 =
  1 - 1.5/2 + 1/16), u_r(2a, pi) = -0.3125*U, and u_theta(2a, pi/2) =
  -0.59375*U (0.59375 = 1 - 0.375 - 0.03125): fore-aft symmetry
  |u_r(2a, 0)| = |u_r(2a, pi)| to float noise.
- Split: pressure_drag + friction_drag - stokes_drag = 0 to float
  noise (anchor residual 5.170e-26 N); pressure_drag/stokes_drag =
  1/3 and friction_drag/stokes_drag = 2/3 within 1e-9;
  friction_drag/pressure_drag = 2 exactly.
- Drag coefficient: 12*mu/(rho*U*a) = 24/Re_D = F/(0.5*rho*U^2*pi*a^2)
  all equal to float noise (anchor: 175.2 three ways).
- Creeping linearity: stokes_drag(mu, a, 2*U) = 2*stokes_drag(mu, a,
  U) exactly; the drag scales linearly with speed at zero Reynolds
  number.
- Pressure antisymmetry: p(pi) - p_inf = -(p(0) - p_inf) = 1.5*mu*U/a
  to float noise; the equator value is zero (anchor residual
  -1.64271060e-19 Pa).
- Oseen equivalence: oseen_correction(0.5) = 1.1875 exactly, equal to
  1 + (3/16)*Re_D at Re_D = 1.0; oseen_drag/stokes_drag equals
  oseen_correction(Re_a) to float noise.
- Terminal balance: stokes_drag(mu, a, U_t) equals the buoyancy-
  adjusted weight (4/3)*pi*a^3*(rho_p - rho_f)*g to float noise
  (anchor ratio 1 exactly); the Oseen-corrected terminal velocity
  lies below U_t and reproduces the corrected balance.
- ValueErrors across the module: mu at 0 and -1e-5 on every mu
  argument; a at 0 and -1e-4 on every a argument (drag functions and
  streamfunction/velocity functions); U at 0 and -0.01 on every U
  argument; rho at 0 on drag_coefficient; nu at 0 and -1e-5 on both
  Reynolds numbers and both Oseen functions; r < a (r = 0.5*a) on the
  three field functions; Re_a at -0.1 on oseen_correction;
  rho_particle at or below rho_fluid on both terminal-velocity
  functions.
- Determinism; no imports beyond math; nu, rho, mu, a and U constant
  per call; closed form, no iteration anywhere.

## Worked example

Air at standard conditions nu = 1.46e-5 m2/s, rho = 1.225 kg/m3, mu =
rho*nu = 1.7885e-05 Pa s, g = 9.81 m/s2. All values below are REAL
outputs of the prep anchor /tmp/w44spec/anchor_stokes.py (stdlib math,
closed form, exit 0).
- Worked sphere: radius a = 1.0e-4 m (0.1 mm) at U = 0.01 m/s in air:
  - Reynolds numbers: Re_a = U*a/nu = 0.068493151 and Re_D = U*2a/nu
    = 0.1369863, the low end of the creeping range where the Oseen
    correction still matters.
  - Stokes drag F = 6*pi*mu*a*U = 3.3712431e-10 N (0.337 nN).
    Pressure (form) drag F_p = 2*pi*mu*a*U = 1.1237477e-10 N,
    friction drag F_f = 4*pi*mu*a*U = 2.2474954e-10 N: the split is
    0.3333333333 of the total to pressure and 0.6666666667 to
    friction, an exact 1:2 pressure-to-friction ratio, and the sum
    check F_p + F_f - F leaves a 5.170e-26 N residual.
  - Drag coefficient Cd = 12*mu/(rho*U*a) = 175.2, identical to
    24/Re_D = 175.2 and to F/(0.5*rho*U^2*pi*a^2) = 175.2 (three
    independent routes agree). Creeping linearity: F(2U)/F(U) = 2
    exactly.
  - Surface pressure p - p_inf = -1.5*(mu*U/a)*cos(theta):
    +2.68275000e-03 Pa at the windward stagnation point (theta = pi),
    -2.68275000e-03 Pa at the downstream pole (theta = 0), and zero
    at the equator (residual -1.64271060e-19 Pa): high pressure faces the
    oncoming stream, an equal suction trails it.
  - Wall shear tau_w = 1.5*(mu*U/a)*sin(theta): 1.89699072e-03 Pa at
    theta = pi/4, peak 2.68275000e-03 Pa at theta = pi/2, symmetric
    1.89699072e-03 Pa at theta = 3*pi/4, and 0.000e+00 Pa at theta =
    0 with a 3.285e-19 Pa float residue at theta = pi.
  - Velocity field at r = 2a: u_r = +3.12500000e-03 m/s downstream on
    the axis (theta = 0), zero at the equator (residual 1.91351062e-19 m/s),
    and -3.12500000e-03 m/s upstream (theta = pi): the flow is
    fore-aft symmetric with no wake at this Reynolds number. The
    tangential component u_theta = -4.19844651e-03 m/s at theta =
    pi/4 and -5.93750000e-03 m/s at theta = pi/2.
  - No slip on the surface: u_r(a, pi/3) = 0.000e+00 m/s and
    u_theta(a, pi/3) = -0.000e+00 m/s; the streamfunction is psi(a, theta) = 0 on the
    surface, psi(2a, pi/2) = 6.25000000e-11 m3/s (0.625*U*a^2) and
    psi(2a, pi/4) = 3.12500000e-11 m3/s.
- Oseen correction:
  - At the worked sphere, Re_a = 0.068493151, the factor 1 +
    (3/8)*Re_a = 1.025684932, a 2.56849 percent drag increase, giving
    F_oseen = 6*pi*mu*a*U*(1 + 3*Re_a/8) = 3.45783322e-10 N.
  - Factor values: 1.1875 at Re_a = 0.5, identical to 1 + (3/16)*Re_D
    at Re_D = 1.0 (the two Reynolds conventions give the same
    correction).
- Terminal velocity: a water droplet (rho_p = 1000 kg/m3) of radius
  a = 1.0e-5 m (10 microns) settling in still air:
  - Stokes terminal velocity U_t = (2/9)*(rho_p - rho_f)*g*a^2/mu =
    1.21740537e-02 m/s (1.217 cm/s).
  - Balance check: stokes_drag at U_t over the buoyancy-adjusted
    weight (4/3)*pi*a^3*(rho_p - rho_f)*g = 1 exactly.
  - Droplet Reynolds numbers at U_t: Re_a = 0.0083383929 and Re_D =
    0.016676786, deep inside the creeping regime (Re_D well below
    0.1), so the pure Stokes balance is the operative one.
  - Oseen factor at U_t: 1 + (3/8)*Re_a = 1.003126897; the
    Oseen-corrected terminal velocity (closed-form quadratic root) is
    1.21362229e-02 m/s, 0.310749 percent below the Stokes value.
- Read-off: a 0.1 mm sphere drifting at 1 cm/s through air carries
  only 0.337 nN of drag, one third of it pressure and two thirds
  friction, with a drag coefficient of 175, while a 10 micron water
  droplet settles at 1.22 cm/s with a Reynolds number of 0.017; the
  reversed surface pressure (high facing the stream, suction behind)
  and the fore-aft symmetric field are the fingerprints of creeping
  flow, and the Oseen factor adds 2.6 percent drag at Re_a = 0.068
  and 18.75 percent at Re_a = 0.5.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w44spec/anchor_stokes.py
(stdlib math, closed form, exit 0).

## Validation list (contract test must include)

- radius_reynolds(0.01, 1.0e-4, 1.46e-5) = 0.068493151 within 1e-6;
  diameter_reynolds(0.01, 1.0e-4, 1.46e-5) = 0.1369863 within 1e-6;
  diameter_reynolds = 2*radius_reynolds within 1e-9.
- stokes_drag(1.7885e-5, 1.0e-4, 0.01) = 3.3712431e-10 N within 1e-13
  (magnitude bound: between 3.0e-10 and 4.0e-10 N);
  stokes_drag(mu, a, 0.02)/stokes_drag(mu, a, 0.01) = 2 within 1e-9
  (creeping linearity).
- pressure_drag(1.7885e-5, 1.0e-4, 0.01) = 1.1237477e-10 N within
  1e-13; friction_drag = 2.2474954e-10 N within 1e-13;
  friction_drag/pressure_drag = 2 within 1e-9;
  pressure_drag + friction_drag - stokes_drag within 1e-12 relative.
- drag_coefficient(1.225, 1.7885e-5, 0.01, 1.0e-4) = 175.2 within 0.1;
  equals 24.0/diameter_reynolds(...) within 1e-6 relative; equals
  F/(0.5*rho*U^2*pi*a^2) within 1e-6 relative.
- surface_pressure_delta(1.7885e-5, 0.01, 1.0e-4, pi) =
  2.68275e-03 Pa within 1e-6; at theta = 0 it is -2.68275e-03 Pa
  within 1e-6 (antisymmetry: the two sum to zero within 1e-9); at
  theta = pi/2 within 1e-12 of 0 (anchor residual -1.64271060e-19 Pa).
- wall_shear_stress(1.7885e-5, 0.01, 1.0e-4, pi/2) = 2.68275e-03 Pa
  within 1e-6 and equals 1.5*mu*U/a within 1e-9; at theta = 0 and pi
  within 1e-12 of 0.
- No slip and surface streamline: radial_velocity and
  tangential_velocity at r = a and theta = pi/3 within 1e-12 of 0
  (anchor residuals 0.0 and -0.0); stokes_streamfunction(a, theta)
  within 1e-15 of 0.
- Field values at r = 2a: radial_velocity(0.01, 1.0e-4, 2.0e-4, 0) =
  3.125e-03 m/s = 0.3125*U within 1e-9; radial_velocity at theta = pi
  = -3.125e-03 m/s (fore-aft symmetry within 1e-9);
  tangential_velocity at theta = pi/2 = -5.9375e-03 m/s = -0.59375*U
  within 1e-9; stokes_streamfunction(0.01, 1.0e-4, 2.0e-4, pi/2) =
  6.25e-11 m3/s = 0.625*U*a^2 within 1e-13.
- oseen_correction(0.068493151) = 1.025684932 within 1e-6;
  oseen_correction(0.5) = 1.1875 within 1e-12 and equal to
  1 + (3/16)*diameter_reynolds(...) at Re_D = 1.0 within 1e-12;
  oseen_drag(1.7885e-5, 1.0e-4, 0.01, 1.46e-5) = 3.45783322e-10 N
  within 1e-13; oseen_drag/stokes_drag = oseen_correction within 1e-9.
- terminal_velocity(1000.0, 1.225, 1.7885e-5, 1.0e-5) =
  1.21740537e-02 m/s within 1e-6 (magnitude bound: between 1.1e-2 and
  1.3e-2 m/s); the balance stokes_drag/((4/3)*pi*a^3*(rho_p-rho_f)*g)
  = 1 within 1e-9; diameter_reynolds at U_t = 0.016676786 within 1e-6
  (below 0.1, the creeping check); oseen_terminal_velocity(...) =
  1.21362229e-02 m/s within 1e-6 and below U_t.
- ValueErrors: mu at 0 and -1e-5 on every mu argument; a at 0 and
  -1e-4 on every a argument; U at 0 and -0.01 on every U argument;
  rho at 0 on drag_coefficient; nu at 0 and -1e-5 on both Reynolds
  functions and both Oseen functions; r = 0.5*a on the three field
  functions; Re_a at -0.1 on oseen_correction; rho_particle equal to
  and below rho_fluid on both terminal-velocity functions.
- Determinism; no imports beyond math; closed form, no iteration.

## Corpus fragment (eval/hit1-wave44-stokes-creeping-flow-drag.yaml)

Query 1 (copy verbatim):
  "compute the stokes-drag of the creeping flow about a small sphere
  of radius 0.1 mm moving at 0.01 m per s through still air: evaluate
  the stokes streamfunction velocity field around the sphere, the
  total stokes drag six pi mu a U, the pressure drag to friction drag
  split, and the drag coefficient"
  intent: "aerodynamics; steady low-Reynolds-number creeping flow
  about a sphere in the viscous boundary-layer vein: Stokes
  streamfunction velocity field, Stokes drag F = 6*pi*mu*a*U with the
  pressure (form) drag one third and the friction drag two thirds of
  the total, drag coefficient 24/Re_D at the diameter Reynolds
  number"
  expected_skill: "aerodynamics/boundary-layer/
  stokes-creeping-flow-drag"
Query 2 (copy verbatim):
  "estimate the terminal velocity of a tiny water sphere of 10 micron
  radius settling in still air when its weight balances the
  stokes-drag at low reynolds number, and apply the oseen correction
  factor one plus three eighths of the radius reynolds number to the
  stokes drag"
  intent: "aerodynamics; creeping-flow Stokes drag applied to a
  settling sphere: terminal velocity from the Stokes balance
  (2/9)*(rho_p - rho_f)*g*a^2/mu with the diameter-Reynolds-number
  creeping check, Oseen first-order drag correction factor
  1 + (3/8)*Re_a on the radius-based Reynolds number"
  expected_skill: "aerodynamics/boundary-layer/
  stokes-creeping-flow-drag"
Task ids: w44-stokes-creeping-flow-drag-1 and -2. The queries stay
inside the aerodynamics viscous-flow vein and carry the distinctive
leaf tokens (stokes-drag, creeping flow, oseen, radius reynolds
number, settling in still air) so no other task can capture them: the
corpus greps at prep found "creeping", "oseen", "stokes-drag" and
"magnus" in NO existing task (whole-file grep, exit 1); "terminal
velocity" appears in exactly one task, w21-entry-descent-landing-2,
which sizes a parachute descent from the landed weight and canopy drag
coefficient and routes to space-systems/mission-design/
entry-descent-landing with no creeping-flow content; the
w43-unsteady-laminar-stokes-layers tasks route on the unsteady
rayleigh-layer and oscillating-plate tokens of the plate-layer leaf,
and the w28-hypersonic-flow tasks route on modified Newtonian impact
pressure at Mach well above 5, so the two queries above are
collision-free. Corpus wording deliberately avoids hydrodynamics and
sedimentation phrasing (no settling-basin, ocean, viscosity-of-water
or particle-sedimentation language) that no aerodynamics task would
route on.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the steady
low-Reynolds-number viscous drag on a sphere in creeping flow, the
Stokes solution for the slow motion of a sphere through a viscous
fluid:" and include the outputs in the Claim. First tag:
stokes-creeping-flow-drag. Additional tags ONLY: creeping-flow,
stokes-drag, stokes-streamfunction, oseen-correction,
terminal-velocity. NEVER single generic words (sphere, drag, flow,
viscosity, reynolds, particle, droplet, settling, speed) and NEVER
the sibling-owned tokens stokes-first-problem, oscillating-plate-layer,
rayleigh-layer, stokes-second-problem, penetration-depth,
unsteady-laminar-stokes-layers (the unsteady plate-layer leaf);
newtonian-impact-pressure, modified-newtonian-theory,
sphere-drag-coefficient, blunt-body-drag, stagnation-pressure-
coefficient, hypersonic-vacuum-limit, cone-axial-force (hypersonic-
flow); blasius, 1/7-power, transition-location, reynolds-number-regime,
thwaites, michel, stratford, k-plus, sand-roughness (boundary-layer
pack siblings); canopy-drag, touchdown-speed (entry-descent-landing).
50-150 words, <=1000 chars, no em dash, action verb present. The
description must not assign flow regimes, transition classes or any
categorical verdict. Recommended wording:
"Use when you must compute the steady low-Reynolds-number viscous drag
on a sphere in creeping flow, the Stokes solution for the slow motion
of a sphere through a viscous fluid: evaluate the stokes streamfunction
and the velocity field about the sphere, the surface pressure and
wall-shear distributions with their high-pressure-facing-the-stream
signature, the total stokes drag F = 6*pi*mu*a*U split one third
pressure drag to two thirds friction drag, the drag coefficient
Cd = 24/Re_D at the diameter Reynolds number, the Oseen correction
factor 1 + (3/8)*Re_a on the
radius-based Reynolds number, and the terminal settling velocity
(2/9)*(rho_p - rho_f)*g*a^2/mu of a small dense sphere in still air.
Produces the creeping-flow drag, the field values and the settling
speed in SI units that anchor low-Reynolds-number body-drag estimates
and viscous-flow checks. Trigger: stokes-creeping-flow-drag,
creeping-flow, stokes-drag, stokes-streamfunction, oseen-correction,
terminal-velocity."
The words stokes-first-problem, oscillating, rayleigh, newtonian,
blunt-body and canopy must not appear in the description; the Oseen
content stays inside this leaf as a first-order drag correction and is
never claimed as a separate flow theory of its own.

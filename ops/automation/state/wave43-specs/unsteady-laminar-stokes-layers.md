# Wave-43 leaf spec: unsteady-laminar-stokes-layers (aerodynamics,
# boundary-layer pack)

- Path: skills/aerodynamics/boundary-layer/unsteady-laminar-stokes-layers/
- Pack: boundary-layer (present siblings boundary-layer-theory,
  boundary-layer-transition, boundary-layer-separation,
  stagnation-flow-boundary-layer, rough-wall-skin-friction; adjacent
  fences in aerodynamics/high-speed/compressible-couette-flow, the
  steady shear-driven gap, and aerodynamics/aeroelasticity, the
  inviscid unsteady-airfoil leaves).
- Provenance: wave-43 dispatch probe receipt #3. The claim: unsteady
  laminar Stokes layers over an infinite plate, exact closed-form
  solutions of the diffusion equation: Stokes first problem
  (impulsively started plate, Rayleigh layer) and Stokes second problem
  (plate oscillating in its own plane), plus derived quantities
  (displacement effect, wall shear amplitude and phase). The unsteady
  laminar layer is the time-dependent member of the exact-viscous
  family whose steady members (compressible-couette-flow, the shear
  gap; boundary-layer-theory, the Blasius plate) are already in the
  tree; the aeroelasticity leaves cover only inviscid indicial airfoil
  response. GENUINE gap, GO.
- Claim fences (quoted from the sibling frontmatter and body at prep,
  none owns time-dependent laminar shear layers over a plate):
  - boundary-layer-theory (this pack, steady) opens "Use when the task
    is boundary-layer thickness estimation, displacement or momentum
    thickness, skin-friction coefficient on a surface, Reynolds-number
    regime classification, or transition location on a smooth
    surface", and its quick reference is entirely steady: "Laminar
    flat plate (Blasius similarity solution, 1908): 99-percent
    thickness delta = 5.0 * x / sqrt(Re_x) ... local skin friction
    Cf = 0.664 / sqrt(Re_x)" and the turbulent "1/7 power law"
    correlations in Re_x. No time appears anywhere: no impulsively
    started plate, no oscillation, no nu*t layer growth.
  - boundary-layer-transition (this pack) owns transition: its
    description routes transition location and Reynolds-number regime
    classification; the new leaf must not claim turbulence, transition
    or Reynolds-number regimes.
  - compressible-couette-flow (aerodynamics/high-speed) opens "Use
    when you must compute the exact constant-property solution for
    compressible Couette flow in a high-Mach plate gap" with "the
    linear velocity profile u = Ue y / h" and "wall shear
    tau_w = mu Ue / h": a STEADY shear-driven gap between two plates
    with a linear profile, no time evolution. The new leaf is the
    unsteady half-space layer driven by one moving surface; the two
    exact solutions coincide only in that both solve the same viscous
    diffusion balance, and the new leaf must not claim the gap
    geometry, the Crocco energy integral or the recovery-factor
    content.
  - aeroelastic-gust-response (aerodynamics/aeroelasticity) opens "Use
    when you must compute the dynamic aeroelastic response of a
    flexible two-degree-of-freedom typical wing section to a discrete
    gust with indicial unsteady aerodynamics: run the Wagner and
    Kussner lag-state lift model in the time domain" and owns the tags
    kussner-function, wagner-function, indicial-aerodynamics,
    unsteady-aerodynamics. Its Wagner/Kussner content is inviscid
    circulatory lift on an airfoil, not a viscous Stokes layer in the
    fluid; the new leaf must not claim indicial airfoil response,
    Wagner/Kussner functions or lift histories.
  - flutter-speed-prediction (aerodynamics/aeroelasticity) applies
    "Theodorsen unsteady aerodynamics with the complex lift-deficiency
    function C(k)" to the bending-torsion section; the new leaf must
    not claim oscillating-airfoil or oscillating-airfoil-load content.
  - shock-tube (aerodynamics/high-speed) states its "unsteady-wave
    content here has no other home in the high-speed pack": the
    unsteady driver expansion wave in a moving shock tube. That is a
    compressible wave process, not a viscous Stokes layer, and the two
    do not collide; the boundary-layer pack has no unsteady member
    today.
  Whole-tree greps at prep: "stokes" = 0 hits under skills/aerodynamics
  (the word appears in NO existing SKILL.md, script or test there);
  "unsteady|oscillat" under skills/aerodynamics hits only
  aeroelastic-gust-response and flutter-speed-prediction (inviscid
  Wagner/Kussner and Theodorsen content), the cfd-convergence residual
  wording ("oscillating or flat residuals mean the run is not
  converged") and shock-tube unsteady expansion waves. Corpus greps on
  eval/hit1-corpus.yaml: "stokes", "stokes-first-problem",
  "oscillating-plate", "oscillating-plate-layer", "unsteady-laminar",
  "unsteady-laminar-stokes-layers", "rayleigh-layer" and "erfc" all
  have ZERO task hits (there is no statistics erfc content in the
  corpus at all); the only "rayleigh" hit is task w33-beam-vibration-2
  ("estimate the fundamental frequency of the non uniform cantilever
  spar with the rayleigh quotient method for a vibration clearance
  check", expected_skill structures/fem/beam-vibration), a structural
  Rayleigh-quotient vibration task with no viscous-layer content, so
  the routing token rayleigh-layer is collision-free. GENUINE
  aerodynamics gap (fresh probe, GO 2): no leaf owns the unsteady
  laminar Stokes layer, the Rayleigh layer of the impulsively started
  plate, or the oscillating-wall Stokes layer.
- Standards id: naca-tr-824 (reference-only, present in
  standards-map.yaml, the sibling precedent for the viscous-layer
  family; the classical treatment of unsteady laminar boundary layers
  follows Schlichting, whose material is cited through the report).
  Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Compute the exact unsteady laminar Stokes layer over an infinite flat
plate in a quiescent half-space, the closed-form solutions of the
one-dimensional vorticity diffusion equation u_t = nu * u_yy for two
wall motions. Stokes first problem (Rayleigh layer): the plate at
y = 0 is impulsively started at t = 0 to speed U, and the layer
diffuses outward with the similarity solution
u/U = erfc(y / (2*sqrt(nu*t))) in the similarity variable
eta = y / (2*sqrt(nu*t)); the layer edge sits at
delta = 3.6428*sqrt(nu*t) where u/U = erfc(1.8214) = 0.01, the plate
motion 99 percent decayed (the probe-round figure 3.6*sqrt(nu*t) is
the same edge rounded down, erfc(1.8) = 0.0109), growing without bound
as sqrt(t); the wall shear decays as 1/sqrt(t), tau_w = rho*U*
sqrt(nu/(pi*t)) (from mu*|du/dy|_0, so tau_w*sqrt(t) = rho*U*
sqrt(nu/pi) is constant); and the displacement thickness of the layer
is delta* = integral_0^inf (1 - u/U) dy = 2*sqrt(nu*t/pi), with the
momentum balance rho*U*d(delta*)/dt = tau_w holding identically.
Stokes second problem (oscillating plate): the plate oscillates in its
own plane as U*cos(omega*t), and the steady-periodic solution is
u = U*exp(-y/delta)*cos(omega*t - y/delta) with penetration depth
delta = sqrt(2*nu/omega), so the signal at depth y is attenuated by
exp(-y/delta) and lags the wall by y/delta radians; at y = delta the
amplitude is exp(-1)*U = 0.3679*U and the phase lag is exactly 1 rad
(57.30 deg). The wall shear oscillates at the amplitude
tau_amp = rho*U*sqrt(nu*omega) = mu*U*sqrt(omega/nu) and is shifted in
phase by one-eighth period (45 degrees) relative to the plate
velocity: with the resistance-on-plate convention
tau_w = -mu*du/dy|_0 (positive resisting +x plate motion) the wall
shear waveform is tau_w(t) = tau_amp*cos(omega*t + pi/4), so it leads
the plate velocity U*cos(omega*t) by 45 degrees and passes through
zero at omega*t = pi/4, one-eighth period after the plate reaches peak
speed (the probe phrase "45-degree phase lag of the shear" refers to
this one-eighth-period shear-versus-wall-motion shift). Produces the
closed-form velocity profiles and fields, the layer edge and
penetration depth, the displacement thickness and wall shear
histories with amplitude and phase, in SI units, that anchor unsteady
laminar shear-layer estimates, viscous time-scale reasoning and
CFD verification cases. Does NOT do: steady flat-plate boundary layers,
Blasius or 1/7-power thickness and skin-friction correlations, or
transition and Reynolds-number regime classification
(boundary-layer-theory, boundary-layer-transition); the steady
shear-driven Couette gap with its linear velocity profile, Crocco
energy integral, recovery factor r = Pr and steady wall shear
mu*Ue/h (compressible-couette-flow); inviscid indicial airfoil
response with Wagner and Kussner functions, gust lift histories or
Theodorsen lift-deficiency on oscillating airfoils
(aeroelastic-gust-response, flutter-speed-prediction); unsteady
compressible expansion waves in shock tubes (shock-tube). Incompressible
constant-property laminar flow only, uniform nu; turbulence,
transition, pressure gradients, wall curvature and heat transfer are
out of scope.

## Model (implement exactly)

Pure stdlib, math only, closed form. Module constants (air at standard
conditions, used by the worked example): NU_AIR = 1.46e-5 (m2/s
kinematic viscosity), RHO_AIR = 1.225 (kg/m3), DELTA99_COEF = 3.6428
(the layer-edge coefficient, 2*1.8214 where erfc(1.8214) = 0.01).
Dynamic viscosity is always derived mu = rho*nu, never an input.

Defining relations (pin these exactly; every function below derives
from them):
- First problem, similarity variable eta = y/(2*sqrt(nu*t)):
  u/U = erfc(eta), wall value u(0,t) = U exactly for all t > 0, far
  field u/U -> 0 as eta -> inf. Self-similar: u/U is a function of
  y/sqrt(nu*t) only, so the profile shape is identical at every time.
- Layer edge: delta = 3.6428*sqrt(nu*t) with u/U(delta) = erfc(1.8214)
  = 0.0099994, the 99-percent-deficit point; delta grows as sqrt(t),
  delta(t2)/delta(t1) = sqrt(t2/t1).
- First-problem wall shear: tau_w = mu*|du/dy|_0 with du/dy|_0 =
  -U/sqrt(pi*nu*t), so tau_w = rho*U*sqrt(nu/(pi*t)), decaying as
  1/sqrt(t); tau_w*sqrt(t) = rho*U*sqrt(nu/pi) exactly constant.
- Displacement thickness: delta* = integral_0^inf (1 - u/U) dy =
  2*sqrt(nu*t/pi) (integral of erfc over the half-space is 1/sqrt(pi));
  d(delta*)/dt = sqrt(nu/pi)/sqrt(t), so rho*U*d(delta*)/dt =
  tau_w identically, the momentum balance of the growing layer.
- Second problem, wavenumber k = sqrt(omega/(2*nu)) = 1/delta with
  delta = sqrt(2*nu/omega): u = U*exp(-k*y)*cos(omega*t - k*y), the
  real part of U*exp(i*omega*t - (1+i)*k*y). Amplitude U*exp(-y/delta),
  phase lag k*y = y/delta radians behind the wall.
- Wall shear: du/dy|_0 = k*U*(sin(omega*t) - cos(omega*t)), so with
  the resistance convention tau_w = -mu*du/dy|_0 = tau_amp*
  cos(omega*t + pi/4), tau_amp = rho*U*sqrt(nu*omega); the shear leads
  the plate velocity by pi/4 (one-eighth period, T/8 = pi/(2*omega))
  and vanishes at omega*t = pi/4.

Functions:
- stokes_first_velocity(U, nu, y, t) -> float
  U * math.erfc(y / (2.0 * math.sqrt(nu * t))) in m/s. ValueError if
  nu <= 0, t <= 0 (the t = 0 step is singular), or y < 0 (the fluid
  occupies the half-space y >= 0).
- rayleigh_layer_thickness(nu, t) -> float
  DELTA99_COEF * math.sqrt(nu * t), the layer edge where u/U = 0.01.
  ValueError if nu <= 0 or t <= 0.
- stokes_first_wall_shear(rho, U, nu, t) -> float
  rho * U * math.sqrt(nu / (math.pi * t)) Pa, positive for U > 0.
  ValueError if rho <= 0, nu <= 0, or t <= 0.
- stokes_first_displacement_thickness(nu, t) -> float
  2.0 * math.sqrt(nu * t / math.pi) in m. ValueError if nu <= 0 or
  t <= 0.
- stokes_second_velocity(U, nu, omega, y, t) -> float
  U * math.exp(-y/delta) * math.cos(omega * t - y/delta) with delta =
  sqrt(2*nu/omega); at the wall u(0,t) = U*cos(omega*t) exactly (no
  slip). ValueError if nu <= 0, omega <= 0, or y < 0; t is any real
  (steady-periodic state).
- stokes_penetration_depth(nu, omega) -> float
  math.sqrt(2.0 * nu / omega) in m. ValueError if nu <= 0 or
  omega <= 0.
- stokes_second_shear_amplitude(rho, U, nu, omega) -> float
  rho * U * math.sqrt(nu * omega) Pa, equal to mu*U*sqrt(omega/nu) with
  mu = rho*nu. ValueError if rho <= 0, nu <= 0, or omega <= 0.
- stokes_second_wall_shear(rho, U, nu, omega, t) -> float
  tau_amp * math.cos(omega * t + math.pi / 4.0) Pa, the wall shear
  time history leading the plate velocity by 45 degrees. ValueError set
  as stokes_second_shear_amplitude.

Identities to test (closed form):
- Wall and far field, first problem: u(0,t) = U exactly for any t > 0;
  u/U = 0 deep in the fluid (y = 1 m at t = 10 s gives eta about 41,
  erfc < 1e-12); u/U at the layer edge delta equals erfc(1.8214) =
  0.0099994, i.e. 0.01 within 1e-3, at every time (self-similarity:
  the same u/U at y = delta for any two times).
- Shear decay: tau_w(t2)/tau_w(t1) = sqrt(t1/t2) exactly; over the
  anchor decade 0.001 to 10 s the ratio is 0.01 exactly
  (sqrt(1e-4)); tau_w*sqrt(t) = rho*U*sqrt(nu/pi) to float noise.
- Momentum balance: rho*U*d(delta*)/dt = tau_w; anchor finite
  difference over t = 1.0 to 1.02 s reproduces tau_w(1.01 s) with
  relative error 1.2e-5 (< 1e-3).
- No-slip and amplitude, second problem: u(0,t) = U*cos(omega*t)
  exactly; u(y, t = (y/delta)/omega) equals the local amplitude
  U*exp(-y/delta) exactly (phase omega*t - k*y = 0 there); at y = delta
  the amplitude is exp(-1)*U = 11.0364 m/s for U = 30 and the signal
  peaks at t = 1/omega (lag of exactly 1 rad).
- Shear amplitude identity: rho*U*sqrt(nu*omega) == mu*U*sqrt(omega/nu)
  to float noise (mu = rho*nu).
- Shear phase: tau_w(t)/tau_amp = cos(omega*t + pi/4): 0.7071068 at
  omega*t = 0, zero at omega*t = pi/4 (residual 6.08e-17 Pa, below
  1e-9 of tau_amp), -1 at omega*t = 3*pi/4; the zero crossing sits
  exactly T/8 = pi/(4*omega) after the wall velocity peak.
- ValueErrors across the module: nu at 0 and -1e-5 on every nu
  argument; t at 0 and -0.1 on every first-problem time argument; y at
  -1e-6 and -0.001 on both velocity functions; rho at 0 on both shear
  functions; omega at 0 and -50 on every second-problem omega argument.
- Determinism; no imports beyond math; nu, rho and omega constant per
  call.

## Worked example

Air at standard conditions nu = 1.46e-5 m2/s, rho = 1.225 kg/m3,
U = 30 m/s. All values below are REAL outputs of the prep anchor
/tmp/w43spec/anchor_stokes.py (stdlib math, closed form, exit 0).
- Stokes first problem, plate started at t = 0:
  - Similarity profile u/U = erfc(eta) at t = 0.001 s (eta = 1 at
    y = 0.2417 mm): u/U = 0.7236736098 at eta = 0.25, 0.4795001222 at
    eta = 0.5, 0.1572992071 at eta = 1.0, 0.0338948535 at eta = 1.5,
    0.0099994425 at eta = 1.8214, 0.0046777350 at eta = 2.0, and
    0.0000220905 at eta = 3.0; the profile is monotone from 1.000000 at
    the wall toward 0 in the far field (erfc(6) = 2.15e-17).
  - Layer edge delta = 3.6428*sqrt(nu*t): 0.4402 mm at t = 0.001 s,
    1.392 mm at 0.01 s, 4.402 mm at 0.1 s, 13.92 mm at 1 s, 44.02 mm
    at 10 s: one hundred times thicker after four decades of time,
    and u/U at the edge is 0.009999 at every one of those times (the
    self-similar collapse).
  - Wall shear decay tau_w = rho*U*sqrt(nu/(pi*t)): 2.505295 Pa at
    0.001 s, 0.792244 Pa at 0.01 s, 0.250529 Pa at 0.1 s, 0.079224 Pa
    at 1 s, 0.025053 Pa at 10 s. The decade ratio
    tau_w(10 s)/tau_w(0.001 s) = 0.01 = sqrt(1e-4) exactly, and
    tau_w*sqrt(t) = 0.0792244 Pa sqrt(s) is constant across the whole
    table.
  - Front arrival at a fixed station: at y = 1 mm the fluid is
    undisturbed at 0.000000 m/s after 1 ms, reaches 1.926887 m/s after
    10 ms, 16.752282 m/s after 100 ms and 25.595499 m/s after 1 s.
  - Displacement thickness delta* = 2*sqrt(nu*t/pi): 0.136343 mm at
    1 ms, 13.6343 mm at 10 s, always delta*/delta = 0.3098
    (2/sqrt(pi)/3.6428).
  - Momentum balance: rho*U*d(delta*)/dt over t = 1.0 to 1.02 s
    reproduces tau_w(1.01 s) with relative error 1.2e-5.
- Stokes second problem, plate oscillating at omega = 50 rad/s
  (period T = 0.12566 s):
  - Penetration depth delta = sqrt(2*nu/omega) = 7.6419893e-4 m
    (0.7642 mm).
  - Amplitude profile U*exp(-y/delta) with phase lag y/delta:
    y/delta = 0: 30.0000 m/s, lag 0.00 deg; 0.5: 18.1959 m/s,
    28.65 deg; 1.0: 11.0364 m/s, 57.30 deg; 2.0: 4.0601 m/s,
    114.59 deg; 3.0: 1.4936 m/s, 171.89 deg. At y = delta the
    amplitude is exp(-1)*U = 11.0364 m/s and the lag is exactly 1 rad.
  - Velocity at y = delta over a cycle: 5.9630 m/s at t = 0
    (wall at peak speed), 9.6853 m/s at t = 0.01 s, 11.0364 m/s at
    t = 0.02 s (the peak, one radian after the wall peak), 9.6853 m/s
    at t = 0.03 s, 0.7807 m/s at t = 0.05 s.
  - Wall shear amplitude tau_amp = rho*U*sqrt(nu*omega) = 0.992930 Pa,
    identical to mu*U*sqrt(omega/nu) (relative difference below
    1e-12). Time history tau_w = tau_amp*cos(omega*t + pi/4):
    0.702108 Pa (0.707107 of the amplitude, cos 45 deg) at t = 0,
    0.000000 Pa at t = 0.015708 s (omega*t = 45 deg, the zero
    crossing), -0.992930 Pa at t = 0.047124 s (135 deg), -0.702108 Pa
    at t = 0.062832 s (180 deg).
  - Phase read-off: T/8 = 0.015708 s = pi/(4*omega), and the shear
    zero crossing sits exactly one-eighth period after the wall
    velocity peak at t = 0: the shear waveform leads the plate
    velocity by 45 degrees.
- Read-off: a plate start in air at 30 m/s carries 2.5 Pa of wall
  shear for the first millisecond but only 0.025 Pa after 10 s while
  the affected layer grows from 0.44 mm to 44 mm; a 50 rad/s (about
  8 Hz) oscillation at the same speed confines the motion to a
  0.76 mm Stokes layer with shear swinging between plus and minus
  0.99 Pa, peaking one-eighth period before the plate reaches peak
  speed.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w43spec/anchor_stokes.py
(stdlib math, closed form, exit 0).

## Validation list (contract test must include)

- stokes_first_velocity(30.0, 1.46e-5, 0.0, 0.001) = 30.0 exactly
  (erfc(0) = 1); u/U at eta = 1 (y = 2*sqrt(nu*t)) = 0.1572992071
  within 1e-6; u/U at y = 1 m, t = 10 s below 1e-12.
- rayleigh_layer_thickness(1.46e-5, 0.001) = 4.40161e-4 m within 1e-6;
  at y = delta the ratio u/U = 0.0099994, i.e. 0.01 within 1e-3;
  delta(10 s)/delta(0.001 s) = 100 = sqrt(10/0.001) within 1e-9.
- stokes_first_wall_shear(1.225, 30.0, 1.46e-5, 0.001) = 2.505295 Pa
  within 1e-3 (magnitude bound: between 2.0 and 3.0 Pa); the ratio
  tau_w(10 s)/tau_w(0.001 s) = 0.01 within 1e-9; tau_w*sqrt(t) =
  0.0792244 constant within 1e-6.
- Momentum balance: rho*U*(delta*(1.02) - delta*(1.0))/0.02 equals
  tau_w(1.01 s) within 1e-3 relative (anchor error 1.2e-5);
  delta*(t)/delta(t) = 0.3098 within 1e-3 at any t.
- stokes_penetration_depth(1.46e-5, 50.0) = 7.64199e-4 m within 1e-8.
- stokes_second_velocity: u(0,t) = U*cos(omega*t) within 1e-12
  relative; u at y = delta, t = 1/omega equals exp(-1)*U = 11.0364 m/s
  within 1e-4 (and exceeds the neighbouring half-period samples);
  amplitude at y = 3*delta = 1.4936 m/s within 1e-3.
- stokes_second_shear_amplitude(1.225, 30.0, 1.46e-5, 50.0) =
  0.992930 Pa within 1e-4 (magnitude bound: between 0.9 and 1.1 Pa);
  equals mu*U*sqrt(omega/nu) within 1e-12 relative.
- Phase: tau_w(0)/tau_amp = cos(pi/4) = 0.707107 within 1e-6; tau_w at
  t = pi/(4*omega) = 0 within 1e-9 of tau_amp (anchor residual
  6.08e-17 Pa); tau_w at t = 3*pi/(4*omega) = -tau_amp within 1e-12
  relative; the zero crossing is exactly T/8 = 0.015708 s after the
  wall velocity peak.
- ValueErrors: nu at 0 and -1e-5 on every nu argument; t at 0 and -0.1
  on every first-problem time argument; y at -1e-6 and -0.001 on both
  velocity functions; rho at 0 on both shear functions; omega at 0 and
  -50 on every second-problem omega argument.
- Determinism; no imports beyond math; closed form, no iteration.

## Corpus fragment (eval/hit1-wave43-unsteady-laminar-stokes-layers.yaml)

Query 1 (copy verbatim):
  "compute the velocity profile and the wall shear of the
  unsteady-laminar-stokes-layers for the stokes-first-problem of an
  impulsively started flat plate in air at 30 m per s and check the
  rayleigh-layer growth and shear decay with time"
  intent: "aerodynamics; unsteady laminar Stokes first problem
  (Rayleigh layer) of an impulsively started plate: erfc similarity
  velocity profile, layer edge growing as 3.64*sqrt(nu*t), wall shear
  decaying as 1/sqrt(t), displacement thickness"
  expected_skill: "aerodynamics/boundary-layer/
  unsteady-laminar-stokes-layers"
Query 2 (copy verbatim):
  "evaluate the oscillating-plate-layer of the stokes second problem
  for a plate oscillating at 50 rad per s in air: penetration depth,
  velocity amplitude decay and phase lag with depth, and the wall
  shear amplitude with its 45 degree phase shift"
  intent: "aerodynamics; Stokes second problem of a plate oscillating
  in its own plane: penetration depth sqrt(2*nu/omega), exp(-1)
  amplitude and 1 rad phase lag at the penetration depth, wall shear
  amplitude rho*U*sqrt(nu*omega) and one-eighth-period phase relation"
  expected_skill: "aerodynamics/boundary-layer/
  unsteady-laminar-stokes-layers"
Task ids: w43-unsteady-laminar-stokes-layers-1 and -2. Prep grep on
eval/hit1-corpus.yaml: "stokes", "stokes-first-problem",
"oscillating-plate", "oscillating-plate-layer", "unsteady-laminar",
"unsteady-laminar-stokes-layers", "rayleigh-layer" and "erfc" appear
in NO existing task (the corpus has no statistics erfc content at all,
so the feared erfc collision does not exist); "rayleigh" appears in
exactly one task, w33-beam-vibration-2, which routes on the structural
Rayleigh-quotient fundamental frequency of a cantilever spar to
structures/fem/beam-vibration and carries no viscous-layer content;
the w42-compressible-couette-flow tasks route on steady gap wall shear
and heat flux at a given gap-reynolds-number, and no boundary-layer
task routes on a time-dependent layer, so the two queries above are
collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the exact unsteady
laminar Stokes layer of an infinite plate in a quiescent fluid, either
impulsively started or oscillating in its own plane:" and include the
outputs in the Claim. First tag: unsteady-laminar-stokes-layers.
Additional tags ONLY: stokes-first-problem, oscillating-plate-layer,
rayleigh-layer, stokes-second-problem, penetration-depth. NEVER single
generic words (plate, layer, boundary, unsteady, viscosity, velocity,
shear, oscillation, time) and NEVER the sibling-owned tokens blasius,
transition, turbulence, couette, shear-driven-gap, crocco,
wagner-function, kussner-function, indicial-aerodynamics, theodorsen,
gust-response or any steady skin-friction correlation. 50-150 words,
<=1000 chars, no em dash, action verb present. Recommended wording:
"Use when you must compute the exact unsteady laminar Stokes layer of
an infinite plate in a quiescent fluid, either impulsively started or
oscillating in its own plane: for the stokes-first-problem Rayleigh
layer of a plate started at speed U, evaluate the similarity profile
u/U = erfc(y/(2*sqrt(nu*t))), the growing layer edge at 3.64*sqrt(nu*t)
where u/U = 0.01, the wall shear decaying as 1/sqrt(t) from
rho*U*sqrt(nu/(pi*t)), and the displacement thickness; for the
stokes-second-problem oscillating-plate-layer at frequency omega,
evaluate the exponential-cosine velocity field, the penetration depth
sqrt(2*nu/omega) with exp(-1) amplitude and 1 rad phase lag at that
depth, and the wall shear amplitude rho*U*sqrt(nu*omega) leading the
plate velocity by 45 degrees. Produces the closed-form velocity
profiles, thicknesses and wall shear histories in SI units that anchor
unsteady laminar shear-layer estimates and viscous time-scale checks.
Trigger: unsteady-laminar-stokes-layers, stokes-first-problem,
oscillating-plate-layer, rayleigh-layer." The Blasius, Couette and
Wagner/Kussner trigger words must not appear.

FORBIDDEN TOKENS (belong to siblings): blasius, 1/7-power,
99-percent-thickness delta = 5.0*x/sqrt(Re_x), skin-friction
coefficient 0.664/sqrt(Re_x), displacement-thickness 1.7208,
momentum-thickness 0.664, shape-factor, transition location,
tollmien-schlichting, reynolds-number-regime (boundary-layer-theory,
boundary-layer-transition); couette, shear-driven-gap, crocco-energy-
integral, recovery-factor, moving-plate-gap, linear-velocity-profile,
gap-reynolds-number, insulated-moving-plate (compressible-couette-
flow); wagner, kussner, indicial, lag-state, gust-response, dynamic-
magnification-factor, theodorsen, lift-deficiency, C(k), flutter,
typical-section (aeroelastic-gust-response, flutter-speed-prediction);
unsteady-expansion-wave, shock-tube driver content (shock-tube);
turbulence and transition modeling of any kind.

# Wave-46 leaf spec: rotorcraft-forward-flight-flapping (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-forward-flight-flapping/
- Pack: performance (30 leaves present in the pack at prep, per the wave-46
  whole-family enumeration in the probe receipt: balanced-field-length,
  breguet-endurance, breguet-range, climb-performance, descent-performance,
  energy-height, glide-performance, landing-performance, oei-climb-gradient,
  propeller-range, rotorcraft-autorotative-descent,
  rotorcraft-axial-descent-flow-states,
  rotorcraft-blade-element-hover-performance,
  rotorcraft-blade-flapping-dynamics, rotorcraft-forward-flight-performance,
  rotorcraft-hover-ground-effect, rotorcraft-hover-performance,
  rotorcraft-lead-lag-dynamics, rotorcraft-main-rotor-sizing,
  rotorcraft-range-endurance, rotorcraft-tail-rotor-sizing,
  rotorcraft-turn-performance, rotorcraft-vertical-climb-performance,
  specific-range, speed-stability, takeoff-performance, thrust-required,
  turn-performance, wind-effects, windshear-analysis;
  rotorcraft-forward-flight-flapping is the wave-46 addition, the steady
  forward-flight extension of the hover flapping leaf). Claim fences (quoted
  from the sibling frontmatter and bodies at prep, re-verified at spec time
  with real greps below; no sibling produces or fences the steady
  first-harmonic flapping equilibrium of the blade in forward flight):
  - rotorcraft-blade-flapping-dynamics (this pack) is the HOVER-STATE flap
    sibling: its description reads "Use when the task is the basic
    blade-flapping dynamics of a helicopter main rotor: the Lock number
    that fixes the ratio of aerodynamic flap moment to centrifugal
    restoring moment, the steady hover coning angle of an untwisted
    centrally hinged blade under uniform inflow, and the rotating flap
    natural frequency ratio for a flap hinge offset." Its scope note
    (lines 35-36) reads "Flap dynamics here covers coning and frequency
    ratio, not ground resonance or lag dynamics." The hover leaf computes
    only hover-state quantities: the Lock number, the hover coning angle
    a0 = 0.5*gamma*(theta0/4 - lambda/3) and the flap frequency ratio
    nu = sqrt(1 + 1.5*e/(1 - e)); it contains no advance ratio, no
    first-harmonic 1/rev flapping and no tip-path-plane content. Build-time
    note from the receipt: add a fence line to this sibling at merge
    ("forward-flight flapping and tip-path-plane tilt belong to the
    forward-flight sibling").
  - rotorcraft-lead-lag-dynamics (this pack) fences blade flapping to the
    flap siblings: "damping and coupled eigenvalue stability analysis are
    out of scope, and blade flapping motion, coning and the rotating flap
    natural frequency belong to the flap-dynamics sibling." It owns lag
    frequency ratio, fixed-frame lag modes, coincidence rotor speed and
    ground-resonance clearance only.
  - rotorcraft-forward-flight-performance (this pack) is the POWER and
    BEST-SPEEDS leaf of forward flight: its description reads in part
    "implements the standard uniform-inflow momentum theory (Glauert
    inflow)..." and its scope note reads "Uniform inflow only: no
    reverse-flow region, no blade-element section polars, no
    compressibility." That leaf computes induced, parasite and profile
    power plus best endurance and best range speeds; it never touches blade
    motion, so the forward-flight flap equilibrium is not claimed there.
  Whole-tree greps at prep for this spec (real runs, read-only): the
  pattern "tip[- ]path[- ]plane|forward[- ]flight[- ]flapping|first[- ]
  harmonic[- ]flap|longitudinal[- ]flapping|lateral[- ]flapping" returns
  0 hits across skills/ and eval/ (grep exit 1), and the tag tokens
  "flap-equilibrium-tilt|advance-ratio-flapping|first-harmonic-flap-
  response|tip-path-plane-tilt" return 0 hits (grep exit 1). Corpus scan:
  no eval/hit1-corpus.yaml task carries forward-flight-flapping,
  tip-path-plane-tilt, first-harmonic, or longitudinal-flapping-angle
  tokens; the w32 rotorcraft flapping tasks carry only lock-number, hover
  coning angle and flap frequency ratio tokens (route to the hover leaf),
  and the w30 rotorcraft forward-flight tasks carry glauert-inflow and
  best-endurance tokens (route to the power leaf).
- Standards id: far-29 (exists in standards-map.yaml, line 270, the
  established flight-mechanics rotorcraft reference-only id in the family
  convention, e.g. rotorcraft-forward-flight-performance "14 CFR Part 29
  (FAR-29) frames rotorcraft performance requirements"). Ledger Standard:
  far-29.
- Family: flight-mechanics

## Claim

Compute the steady first-harmonic (1/rev) flapping equilibrium of the
idealized centrally hinged rotor blade in forward flight under uniform
inflow: the longitudinal flapping angle a1s (the tip-path-plane aft tilt)
and the lateral flapping angle b1s as functions of the advance ratio mu and
the inflow ratio lambda, with the collective pitch theta0 and the blade
Lock number gamma as the blade-state inputs, plus the forward-flight coning
angle a0. The equilibrium is the classical deterministic algebraic harmonic
balance of the flap equation of the featherless untwisted centrally hinged
blade (flap hinge offset zero, rotating flap frequency ratio 1/rev), the
same uniform-inflow idealization, Lock-number machinery and closed-form
conventions the sibling hover flapping leaf uses, extended to forward
flight: the blade element velocity components u_T = x + mu*sin(psi) and
u_P = lambda + x*beta' + mu*beta*cos(psi) (psi measured from the downwind
blade position in the direction of rotation, advancing side at psi = pi/2),
the aerodynamic flap moment about the central hinge integrated over the
blade, and the first-harmonic ansatz beta = a0 + a1s*cos(psi) +
b1s*sin(psi). Because the hinge is central, the flap frequency ratio is
exactly 1/rev, the steady part of the flap equation carries the centrifugal
restoring balance that fixes a0, and the 1/rev content of the equation
vanishes identically at resonance, so the disc orients to null the 1/rev
aerodynamic flap moment; equating the steady, cos and sin Fourier
coefficients of the moment to their structural counterparts gives the
closed 3 by 3 linear system whose exact solution is the closed form below.
No numeric integration, no empirical tables, no reverse-flow modeling, no
inflow nonuniformity: the outputs are pure algebraic functions of the four
inputs, deterministic, pure stdlib. Produces a1s, b1s and a0 in radians and
degrees and a first-harmonic flap summary dict that gates rotorcraft trim
assessments, tip-path-plane tilt checks and blade-dynamics coursework.
Does NOT do: the hover-state flap quantities, the Lock number itself, the
hover coning angle or the flap frequency ratio from the hinge offset
(rotorcraft-blade-flapping-dynamics, which owns the w32 hover flapping
tasks); rotor power, Glauert induced velocity, parasite, profile or induced
power, or best endurance and best range speeds in forward flight
(rotorcraft-forward-flight-performance); lead-lag frequency ratio, fixed
frame lag modes, coincidence rotor speed or ground resonance clearance
(rotorcraft-lead-lag-dynamics); cyclic pitch response, pitch-flap coupling,
rotor trim moments, hinge offset, blade twist, nonuniform or dynamic
inflow, reversed flow, compressibility or stall (out of the model); 2/rev
and higher flapping harmonics (the first-harmonic truncation, whose
residual magnitude is quantified below); flap-lag or air resonance
stability analysis. Scope: uniform inflow ratio lambda > 0 in the
downward-positive family convention, advance ratio 0 <= mu < 1 (the model
is singular at mu = 1 and reverse flow is out of scope), untwisted
featherless blade at collective theta0 > 0, centrally hinged (e = 0),
first harmonic only, small angles.

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG, no imports beyond math.
Module constants: none beyond the angle conversion factor
DEG = 180.0/math.pi used for the degree outputs; the closed forms below are
exact rational combinations of the inputs and contain no transcendental
constants. Python note: the inflow ratio parameter is spelled lam in every
signature (lambda is a Python keyword); docstrings and comments name it
lambda.

Conventions, pinned: blade azimuth psi is measured from the downwind (rear)
blade position in the direction of rotation, so the advancing blade sits at
psi = pi/2 and the tangential velocity ratio is u_T = x + mu*sin(psi) with
x = r/R. The flap angle beta(psi) is written as the first-harmonic series
  beta(psi) = a0 + a1s*cos(psi) + b1s*sin(psi),
with a0 the coning angle. Sign convention of the outputs: a1s < 0 means the
tip-path plane tilts aft (the nose-side blade tips stand above the hub
plane, the flapping-back direction of forward flight), so the longitudinal
flapping angle comes out negative few degrees at cruise and grows in
magnitude with mu; b1s < 0 means the psi = pi/2 (advancing) blade tip sits
below the coning plane. This is the family sign convention for the new
forward-flight leaf; it is the sign convention whose cruise values land in
the published few-degree band stated in the receipt, and it is
algebraically the negative of the a0 minus a1s*cos minus b1s*sin series
convention. The inflow ratio lambda is the total uniform inflow ratio in
the downward-positive convention (positive downwash), matching the hover
sibling's sign rule.

Defining relations (pin these exactly; every function derives from them).
Dimensionless blade element velocities in the hub plane frame:
  u_T = x + mu*sin(psi),
  u_P = lambda + x*beta'(psi) + mu*beta(psi)*cos(psi),
where beta' = d beta/d psi and the mu*beta*cos(psi) term is the
perpendicular-velocity contribution of the axial (radial) relative wind
acting on the flapped blade, the classical linearized form of the standard
blade element model. Section angle of attack alpha = theta0 - u_P/u_T
(untwisted, featherless: theta = theta0 constant; no cyclic pitch, no
pitch-flap coupling). Dimensionless aerodynamic flap moment about the
central hinge, per unit of the 0.5*rho*a*c*Omega^2*R^4 reference:
  M(psi) = integral_0^1 x * [u_T^2*theta0 - u_T*u_P] dx.
Flap equation of motion with nu = 1 (central hinge):
  beta'' + beta = (gamma/2) * M(psi),
the steady part beta'' + beta = a0 balances the mean moment (centrifugal
restoring), and the 1/rev part of beta'' + beta vanishes identically at the
1/rev resonance, so the equilibrium nulls the cos and sin projections of
M(psi). Substituting the ansatz, expanding u_T^2*theta0 - u_T*u_P,
projecting onto the constant, cos(psi) and sin(psi) harmonics with the
product-to-sum reductions of sin(psi)*cos^2(psi) (1/rev coefficient 1/4)
and sin^2(psi)*cos(psi) (1/rev coefficient 1/4), and solving the resulting
3 by 3 linear system in (a0, a1s, b1s) exactly gives the closed forms:

  a0  = (gamma/2) * ( theta0*(1 + mu^2)/4 - lambda/3 )
  a1s = -4*mu * (2*theta0/3 - lambda/2) / (1 - mu^2/2)
  b1s = -(4*mu/3) * a0 / (1 + mu^2/2) = -(2*mu*gamma/3) *
        ( theta0*(1 + mu^2)/4 - lambda/3 ) / (1 + mu^2/2)

Structural notes: the mean balance carries the forward-flight
dynamic-pressure gain theta0*mu^2/4 in the coning; the 1/rev balance
cancels gamma (aerodynamic forcing and aerodynamic damping both scale with
the Lock number), so a1s is gamma-free by cancellation while b1s enters
through the coning coupling a0 and carries gamma; the (1 - mu^2/2) and
(1 + mu^2/2) denominators come from the mu^2*sin*cos cross couplings of the
perpendicular-velocity term, so a1s grows without bound as mu approaches 1,
which is the model boundary. Hover limit: mu = 0 gives a0 =
(gamma/2)*(theta0/4 - lambda/3), the exact hover coning closed form of the
rotorcraft-blade-flapping-dynamics sibling, and a1s = b1s = 0 exactly. The
2/rev harmonic content of M(psi) is not part of the first-harmonic
equilibrium; its magnitude at the worked point (quantified below, order
1e-2 in the moment projection, implying a 2/rev flapping of order 1e-2 rad
at mu = 0.3) is the documented truncation residual of the model and does
not enter the tip-path-plane tilt.

Functions (implement with exactly these signatures; pure math only, angles
in radians):
- forward_coning_angle(mu, lam, theta0, gamma) -> float: a0 =
  (gamma/2)*(theta0*(1 + mu^2)/4 - lam/3). Validates all four arguments.
- longitudinal_flapping_angle(mu, lam, theta0) -> float: a1s =
  -4*mu*(2*theta0/3 - lam/2)/(1 - mu^2/2). Takes no gamma: the Lock number
  cancels in the 1/rev balance. Returns exactly 0.0 for mu = 0.0.
- lateral_flapping_angle(mu, lam, theta0, gamma) -> float: b1s =
  -(4*mu/3)*forward_coning_angle(mu, lam, theta0, gamma)/(1 + mu^2/2).
  Returns exactly 0.0 for mu = 0.0.
- forward_flap_summary(mu, lam, theta0, gamma) -> dict: the one-call
  assessment dict with exactly these six keys:
  coning_angle_rad, coning_angle_deg, longitudinal_flapping_rad,
  longitudinal_flapping_deg, lateral_flapping_rad, lateral_flapping_deg,
  where each _deg value is the _rad value times DEG and the component
  values match the three functions above for the same arguments.
ValueError rejection (every function, on every argument it takes): mu < 0.0
(advance ratio must be non-negative), mu >= 1.0 (the uniform-inflow model
is singular at mu = 1 and reverse flow is out of scope), lam <= 0.0 (the
uniform inflow ratio must be positive in the downward-positive family
convention), theta0 <= 0.0 (collective pitch must be positive), gamma <= 0.0
(Lock number must be positive), and any non-finite argument. mu = 0.0 is a
valid hover-limit input. The anchor verifies all eleven ValueError cases
below.

Identities to test (closed form, deterministic; all values are REAL anchor
outputs of /tmp/w46spec/anchor_rotorcraft_forward_flight_flapping.py,
stdlib math, exit 0):
- Hover limit and cross-leaf coning identity: at mu = 0 with the worked
  theta0 = 0.14, lam = 0.06, gamma = 6.0, forward_coning_angle returns
  a0 = 0.045 rad (0.045000000000000012), exactly the hover leaf closed
  form 0.5*gamma*(theta0/4 - lam/3) = 0.045000000000000012 (equality to
  machine precision, anchor True), and longitudinal_flapping_angle and
  lateral_flapping_angle return exactly 0.0.
- Collective-inflow balance zero: at theta0 = 3*lam/4 (here lam = 0.06,
  theta0 = 0.045), the collective and inflow 1/rev moments cancel and
  longitudinal_flapping_angle(0.3, 0.06, 0.045) returns exactly zero
  (anchor value -0.0, which compares equal to 0.0).
- Inflow linearity (odd symmetry in lambda of the inflow-induced tilt
  parts): because lambda enters a1s linearly and a0, hence b1s, linearly,
  the two-point differences are exact closed forms. At mu = 0.3,
  theta0 = 0.14, gamma = 6.0 with lam = 0.06 versus 0.05, anchor REAL
  values: d(a1s) = 0.0062827225130890063 equals 2*mu*(0.06 - 0.05)/
  (1 - mu^2/2) = 0.006282722513089002 within 1.6e-17; d(a0) =
  -0.009999999999999995 equals -(gamma/6)*(0.06 - 0.05) within 1e-17;
  d(b1s) = 0.0038277511961722459 equals (2*mu*gamma/9)*(0.06 - 0.05)/
  (1 + mu^2/2) = 0.0038277511961722467 within 8e-19. This pins the inflow
  response slopes d(a1s)/d(lambda) = 2*mu/(1 - mu^2/2), d(a0)/d(lambda) =
  -gamma/6, d(b1s)/d(lambda) = (2*mu*gamma/9)/(1 + mu^2/2) at every
  positive lambda.
- Coning-coupling identity: lateral_flapping_angle(mu, lam, theta0, gamma)
  equals -(4*mu/3)*forward_coning_angle(mu, lam, theta0, gamma)/
  (1 + mu^2/2) at every valid point (anchor True at the worked point), so
  the lateral tilt is exactly proportional to the forward coning angle with
  the advance-ratio coupling factor -(4*mu/3)/(1 + mu^2/2).
- Growth with advance ratio: at fixed lam = 0.06, theta0 = 0.14, gamma =
  6.0, |a1s| over mu = 0.1, 0.2, 0.3, 0.35 is strictly increasing
  (0.025460636515912901, 0.051700680272108848, 0.079581151832460728,
  0.094451841988459836 rad) and |b1s| is strictly increasing
  (0.0061094527363184121, 0.012862745098039217, 0.020842105263157901,
  0.025444051825677268 rad), anchor True for both, the published
  few-degree longitudinal band growing with mu.
- Harmonic-balance self-consistency (numerical Fourier projection of the
  full moment integrand at the closed-form equilibrium, independent
  quadrature over x and psi at 4096 by 512 points, stdlib only): the
  steady projection residual of R = (gamma/2)*M - (beta'' + beta) is
  2.861e-07 (the centrifugal balance a0), the 1/rev cos residual is
  1.424e-08 and the 1/rev sin residual is -3.373e-08 (quadrature noise on
  the resonance nulling, five orders below the 2/rev content), and the
  2/rev cos and sin residuals are 7.212e-03 and 1.289e-03 (the documented
  first-harmonic truncation, which implies a 2/rev flapping amplitude of
  order (gamma/6)*M2 ~ 1e-2 rad at the worked point, outside the TPP).
- Determinism: two identical summary calls return identical bits (anchor
  True); no RNG; no imports beyond math.

## Worked example

Cruise case in the corpus band: advance ratio mu = 0.3, uniform inflow
ratio lambda = 0.06, collective theta0 = 0.14 rad, Lock number gamma = 6.0
(a light-to-medium helicopter blade in the sibling's gamma band 5 to 8 and
lambda band 0.05 to 0.08, the mu = 0.3 point named in the corpus query).
All values below are REAL outputs of the prep anchor
/tmp/w46spec/anchor_rotorcraft_forward_flight_flapping.py (stdlib math,
deterministic, exit 0; identical under /usr/bin/python3 3.9.6 and
~/.pyenv/versions/3.13.12/bin/python3):

- forward_coning_angle(0.3, 0.06, 0.14, 6.0) = 0.05445 rad
  (0.054450000000000012) = 3.1197551944873334 deg. The forward-flight
  coning stands 21 percent above the hover value 0.045 rad at the same
  theta0 and lambda, the theta0*mu^2/4 dynamic-pressure gain.
- longitudinal_flapping_angle(0.3, 0.06, 0.14) = -0.079581151832460728 rad
  = -4.5596641287897972 deg: the tip-path plane tilts aft by about
  4.56 deg, negative in the pinned convention and inside the published
  few-degree band of the receipt. The magnitude grows with mu (table under
  Identities: 1.459 deg at mu = 0.1, 2.962 deg at mu = 0.2, 4.560 deg at
  mu = 0.3, 5.412 deg at mu = 0.35).
- lateral_flapping_angle(0.3, 0.06, 0.14, 6.0) = -0.020842105263157901 rad
  = -1.1941646677463478 deg: the coning coupling tilts the disc so the
  advancing side sits about 1.19 deg below the coning plane, growing with
  mu (0.350 deg at mu = 0.1, 0.737 deg at mu = 0.2, 1.194 deg at mu = 0.3,
  1.458 deg at mu = 0.35).
- Inflow sensitivity at the worked point: raising lambda from 0.06 to 0.08
  at fixed mu = 0.3, theta0 = 0.14, gamma = 6.0 relaxes the aft tilt to
  a1s = -0.067015706806282729 rad = -3.8397171610861456 deg (more inflow
  cancels part of the advancing-side lift excess), and lowering lambda to
  0.05 steepens it to -0.085863874345549734 rad = -4.9196376126416235 deg.
- Hover-limit anchor at the same theta0, lambda, gamma: mu = 0.0 gives
  a0 = 0.045 rad, a1s = 0.0 and b1s = 0.0 exactly, reproducing the hover
  leaf closed form.
- forward_flap_summary(0.3, 0.06, 0.14, 6.0) returns exactly the six-key
  dict with coning_angle_rad 0.05445000000000001, coning_angle_deg
  3.1197551944873334, longitudinal_flapping_rad -0.07958115183246073,
  longitudinal_flapping_deg -4.559664128789797, lateral_flapping_rad
  -0.0208421052631579, lateral_flapping_deg -1.1941646677463478.
Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w46spec/
anchor_rotorcraft_forward_flight_flapping.py (stdlib math, deterministic,
exit 0).

## Validation list (contract test must include)

- forward_coning_angle(0.3, 0.06, 0.14, 6.0) = 0.054450000000000012 within
  1e-9 relative; forward_coning_angle(0.0, 0.06, 0.14, 6.0) equals
  0.5*6.0*(0.14/4 - 0.06/3) = 0.045000000000000012 within 1e-12 (hover
  cross-leaf identity, computed in the test from the printed closed form,
  no import of the sibling module).
- longitudinal_flapping_angle(0.3, 0.06, 0.14) = -0.079581151832460728
  within 1e-9 relative and equals -4*0.3*(2*0.14/3 - 0.06/2)/(1 - 0.09/2)
  within 1e-12; longitudinal_flapping_angle(0.0, 0.06, 0.14) is exactly
  0.0; longitudinal_flapping_angle(0.3, 0.06, 0.045) is exactly zero
  (theta0 = 3*lambda/4 balance, anchor -0.0 compares equal to 0.0).
- lateral_flapping_angle(0.3, 0.06, 0.14, 6.0) = -0.020842105263157901
  within 1e-9 relative; lateral_flapping_angle(0.0, 0.06, 0.14, 6.0) is
  exactly 0.0; the coning-coupling identity
  lateral_flapping_angle(mu, lam, theta0, gamma) =
  -(4*mu/3)*forward_coning_angle(mu, lam, theta0, gamma)/(1 + mu^2/2)
  holds within 1e-12 at the worked point and at mu = 0.2, lam = 0.07,
  theta0 = 0.12, gamma = 7.0.
- Degree outputs: coning_angle_deg = 3.1197551944873334 within 1e-9
  relative, longitudinal_flapping_deg = -4.559664128789797 within 1e-9,
  lateral_flapping_deg = -1.1941646677463478 within 1e-9; each _deg equals
  the _rad value times 180.0/math.pi within 1e-12.
- forward_flap_summary returns exactly the six documented keys and no
  others, and each key matches the corresponding component function at the
  same arguments within 1e-12.
- Inflow two-point identities at mu = 0.3, theta0 = 0.14, gamma = 6.0,
  lam = 0.06 versus 0.05: the a1s difference equals
  2*0.3*0.01/(1 - 0.045) within 1e-12; the a0 difference equals
  -(6/6)*0.01 within 1e-12; the b1s difference equals
  (2*0.3*6/9)*0.01/(1 + 0.045) within 1e-12. These certify the exact
  linearity in the inflow ratio (odd symmetry in lambda) of the
  inflow-induced tilt parts.
- Monotone growth: at lam = 0.06, theta0 = 0.14 (gamma = 6.0 for b1s),
  |a1s| and |b1s| strictly increase over mu = 0.1, 0.2, 0.3, 0.35 (anchor
  True), and the a1s values match the rad table under Identities within
  1e-12.
- ValueErrors: mu = -0.1, mu = 1.0, mu = 1.5, lam = 0.0, lam = -0.02,
  theta0 = 0.0, theta0 = -0.1 raise ValueError on longitudinal_flapping_
  angle; gamma = 0.0 and gamma = -3.0 raise ValueError on
  lateral_flapping_angle; mu = nan raises ValueError on
  longitudinal_flapping_angle; lam = inf raises ValueError on
  forward_coning_angle. All eleven anchor cases raise (anchor True); mu =
  0.0 and lam = 0.05-class positive inputs are valid.
- Determinism: two identical forward_flap_summary calls return identical
  bits; no RNG; no imports beyond math. Test passes under BOTH
  interpreters (/usr/bin/python3 3.9.6 and
  ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
  computed sums; use assertAlmostEqual/math.isclose everywhere. Contract
  test file named test_rotorcraft_forward_flight_flapping.py
  (underscores), unittest, offline in under 20 seconds.

## Corpus fragment (2 verbatim queries for
eval/hit1-wave46-rotorcraft-forward-flight-flapping.yaml)

Query 1 (copy verbatim from the receipt gate (e)):
  "check the forward-flight-flapping of the helicopter main rotor at
  cruise: solve the first-harmonic flap equilibrium for the longitudinal
  and lateral flapping angles and report the tip-path-plane-tilt from the
  inflow ratio and the advance ratio"
  intent: "flight-mechanics; rotorcraft forward-flight-flapping of the
  helicopter main rotor at cruise: first-harmonic flap equilibrium for the
  longitudinal and lateral flapping angles and the tip-path-plane-tilt
  from the inflow ratio and the advance ratio"
  expected_skill: "flight-mechanics/performance/rotorcraft-forward-flight-flapping"
Query 2 (copy verbatim from the receipt gate (e)):
  "compute the rotorcraft tip-path-plane-tilt in forward flight for the
  trim assessment: the steady first-harmonic longitudinal-flapping-angle
  of the centrally hinged uniform blade at an advance ratio of 0.3 with
  uniform inflow"
  intent: "flight-mechanics; rotorcraft tip-path-plane-tilt in forward
  flight for the trim assessment: steady first-harmonic
  longitudinal-flapping-angle of the centrally hinged uniform blade at
  advance ratio 0.3 with uniform inflow"
  expected_skill: "flight-mechanics/performance/rotorcraft-forward-flight-flapping"
Task ids: w46-rotorcraft-forward-flight-flapping-1 and -2. Prep grep and
probe evidence (real greps for this spec): forward-flight-flapping,
tip-path-plane-tilt, first-harmonic-flap-response, longitudinal-flapping-
angle and lateral-flapping-angle appear in NO existing eval/hit1-corpus.yaml
task and in NO skills/ file (0 hits, exit 1); the only flapping corpus
tasks (w32-rotorcraft-blade-flapping-dynamics-1/-2) carry lock-number,
hover coning and flap frequency ratio tokens and route to the hover leaf;
the w30 rotorcraft forward-flight tasks carry glauert-inflow and
best-endurance tokens and route to the power leaf; the propeller
advance-ratio tasks route on propeller-diameter and revolutions tokens to
vehicle-design/sizing/propeller-sizing and propulsion/turboprop/
turboprop-cycle. The queries deliberately carry the forward-flight-flapping
and tip-path-plane-tilt hyphenated tokens from the gate (f) tag list,
because the sibling generic surface (rotorcraft blade flapping, forward
flight, advance ratio as bare words) is live steal territory.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the steady first-harmonic
(1/rev) flapping equilibrium of a helicopter main rotor blade in forward
flight under uniform inflow:" and include the outputs in the Claim order.
First tag: forward-flight-flapping. Additional tags ONLY the receipt's gate
(f) list, verbatim: forward-flight-flapping, tip-path-plane-tilt,
first-harmonic-flap-response, longitudinal-flapping-angle,
lateral-flapping-angle, advance-ratio-flapping, flap-equilibrium-tilt.
NEVER the bare single words flapping, rotorcraft, blade dynamics, rotor
dynamics as tags (the receipt gate (f) prunes them: the family router rows
for rotorcraft-blade-flapping-dynamics and rotorcraft-forward-flight-
performance own the generic rotorcraft and rotor-dynamics surface), NEVER
the sibling tokens lock-number, hover-coning, coning-angle,
flap-frequency-ratio, hinge-offset, rotor-blade-flapping
(rotorcraft-blade-flapping-dynamics), glauert-inflow, parasite-power,
profile-power, best-endurance-speed, best-range-speed,
equivalent-flat-plate-area, induced-velocity, hover-velocity
(rotorcraft-forward-flight-performance), lead-lag, lag-frequency,
regressing-lag-mode, ground-resonance-clearance, coincidence-rotor-speed,
multiblade-modes (rotorcraft-lead-lag-dynamics), and never autorotation,
axial-descent, vortex-ring, power-required or range-endurance (the other
rotorcraft performance leaves). The model takes the Lock number gamma as an
input, but the description should name the input as gamma or "the blade
Lock number gamma" only inside the prose, never as the lock-number tag.
Recommended wording, 50-150 words, <=1000 chars, action verb present, no em
dash (check below): "Use when you must compute the steady first-harmonic
(1/rev) flapping equilibrium of a helicopter main rotor blade in forward
flight under uniform inflow: the longitudinal flapping angle a1s (the
tip-path-plane aft tilt, negative few degrees at cruise) and the lateral
flapping angle b1s of the idealized centrally hinged untwisted blade from
the advance ratio, the inflow ratio, the collective pitch and the blade
Lock number gamma, with the forward-flight coning angle a0 that reduces to
the hover coning value at zero advance ratio. Produces the longitudinal and
lateral flapping angles and the coning angle in radians and degrees and the
first-harmonic flap summary that gates rotorcraft trim assessments and
tip-path-plane checks. Trigger: rotorcraft forward flight flapping, tip
path plane tilt, first harmonic flap response, longitudinal flapping angle,
lateral flapping angle, advance ratio flapping, flap equilibrium tilt."
The sibling triggers "lock number", "coning angle", "flap frequency
ratio", "hinge offset", "glauert", "parasite power", "best endurance
speed", "best range speed", "lead lag", "ground resonance" must not appear
as description tokens. ZERO em dashes in every file; no sensitivity-level
marking vocabulary in prose (the compliance posture of every leaf in this
repo is standards-reference, never restricted-content). Standards
reference-only: far-29 is the FAA
transport-category rotorcraft airworthiness standard (ecfr.gov); the flap
equilibrium relations above are standard engineering methodology
(Johnson, Helicopter Theory ch. 4 and Leishman, Principles of Helicopter
Aerodynamics ch. 4, paraphrased, never reproduced), summary-only per
standards-map.yaml. Model-decision note for the builder: the receipt
prescribes the standard 1/rev harmonic balance on the flapping equation
with uniform inflow and the centrally hinged idealization; the closed forms
above are the exact solution of that balance as derived in this spec (all
coefficients verified by the numerical Fourier-projection self-consistency
check in the anchor), and they are the forms the contract test asserts, so
implement them literally rather than re-deriving from a variant of the
velocity model. Repo paths in this spec are repo-relative; the repo root is
the local AeroSkills checkout (~/AeroSkills).

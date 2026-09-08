# Wave-47 leaf spec: rotorcraft-cyclic-pitch-trim (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-cyclic-pitch-trim/
- Pack: performance (31 leaves present in the pack at prep, per the wave-47
  whole-family enumeration in the probe receipt task-0:
  balanced-field-length, breguet-endurance, breguet-range, climb-performance,
  descent-performance, energy-height, glide-performance, landing-performance,
  oei-climb-gradient, propeller-range, rotorcraft-autorotative-descent,
  rotorcraft-axial-descent-flow-states,
  rotorcraft-blade-element-hover-performance,
  rotorcraft-blade-flapping-dynamics, rotorcraft-forward-flight-flapping
  (wave-46), rotorcraft-forward-flight-performance,
  rotorcraft-hover-ground-effect, rotorcraft-hover-performance,
  rotorcraft-lead-lag-dynamics, rotorcraft-main-rotor-sizing,
  rotorcraft-range-endurance, rotorcraft-tail-rotor-sizing,
  rotorcraft-turn-performance, rotorcraft-vertical-climb-performance,
  specific-range, speed-stability, takeoff-performance, thrust-required,
  turn-performance, wind-effects, windshear-analysis;
  rotorcraft-cyclic-pitch-trim is the wave-47 addition, the control-channel
  completion of the wave-46 rotorcraft-forward-flight-flapping leaf, which
  models the first-harmonic flap equilibrium with collective pitch only).
  Claim fences (quoted from the sibling frontmatter and bodies at prep,
  re-verified at spec time with real greps below; no sibling produces,
  fences or tags the cyclic control channel):
  - rotorcraft-forward-flight-flapping (this pack, wave-46, the direct
    parent) is the COLLECTIVE-ONLY fence: its frontmatter description reads
    "Use when you must compute the steady first-harmonic (1/rev) flapping
    equilibrium of a helicopter main rotor blade in forward flight under
    uniform inflow: the longitudinal flapping angle a1s (the tip-path-plane
    aft tilt, negative few degrees at cruise) and the lateral flapping angle
    b1s of the idealized centrally hinged untwisted blade from the advance
    ratio, the inflow ratio, the collective pitch and the blade Lock number
    gamma, with the forward-flight coning angle a0 that reduces to the hover
    coning value at zero advance ratio". Its workflow step 1 fixes the
    operating point with no control input: "Fix the operating point: advance
    ratio mu, uniform inflow ratio lambda, collective pitch theta0 and blade
    Lock number gamma (the same gamma the hover sibling computes from blade
    geometry)." Its scope note (lines 61-63) reads "Scope: 0 <= mu < 1
    (singular at mu = 1, reverse flow out of scope), lambda > 0
    (downward-positive convention), theta0 > 0, centrally hinged, first
    harmonic only, small angles." Its blade-pitch model is theta = theta0
    constant (the wave-46 spec pins "no cyclic pitch, no pitch-flap
    coupling"); no theta1c or theta1s appears anywhere in its inputs, closed
    forms, worked example or behavior contract, and its corpus tasks
    (w46-rotorcraft-forward-flight-flapping-1/-2) carry
    forward-flight-flapping, tip-path-plane-tilt and flapping-angle tokens
    only, never a control token, so they continue to route to the wave-46
    leaf. The gap this leaf closes: the wave-46 leaf reports the flap
    equilibrium a free-flapping rotor adopts under collective only; the
    cyclic pitch and swashplate inputs a trim assessment needs to HOLD the
    tip-path plane at a target attitude are not produced anywhere.
  - rotorcraft-blade-flapping-dynamics (this pack) is the HOVER-STATE fence:
    its description reads "Use when the task is the basic blade-flapping
    dynamics of a helicopter main rotor: the Lock number that fixes the
    ratio of aerodynamic flap moment to centrifugal restoring moment, the
    steady hover coning angle of an untwisted centrally hinged blade under
    uniform inflow, and the rotating flap natural frequency ratio for a flap
    hinge offset", and its scope note (lines 35-36) reads "Flap dynamics
    here covers coning and frequency ratio, not ground resonance or lag
    dynamics." Hover-state quantities only (Lock number, hover coning,
    flap frequency ratio); no 1/rev control content.
  - rotorcraft-lead-lag-dynamics (this pack) fences blade flapping to the
    flap siblings: "damping and coupled eigenvalue stability analysis are
    out of scope, and blade flapping motion, coning and the rotating flap
    natural frequency belong to the flap-dynamics sibling."
  - rotorcraft-forward-flight-performance (this pack) is the POWER and
    BEST-SPEEDS leaf: its scope note reads "Uniform inflow only: no
    reverse-flow region, no blade-element section polars, no
    compressibility." It computes Glauert induced power, parasite power,
    profile power and the best endurance and best range speeds; it never
    touches blade motion or rotor control.
  Whole-tree greps at prep (probe receipt gate (a), fresh at HEAD): the
  tokens cyclic pitch, swashplate, longitudinal cyclic, lateral cyclic,
  control plane and control-plane return ZERO matches across every skills/
  SKILL.md and every eval/ fragment (grep exit 1), and the only corpus task
  in eval/hit1-corpus.yaml carrying "cyclic" is w24r-strain-life-fatigue-2
  (structural fatigue loading, stress-cycle tokens, no rotorcraft content).
  No corpus task mentions swashplate or any rotorcraft control input.
- Standards id: far-29 (exists in standards-map.yaml at line 270, the
  established flight-mechanics rotorcraft reference-only id in the family
  convention; the flap siblings rotorcraft-blade-flapping-dynamics and
  rotorcraft-forward-flight-flapping carry it reference-only). Ledger
  Standard: far-29.
- Family: flight-mechanics

## Claim

Compute the cyclic-pitch trim of the idealized centrally hinged, untwisted,
featherless helicopter rotor blade in forward flight under uniform inflow:
the steady first-harmonic (1/rev) flapping equilibrium of the wave-46
forward-flight leaf with the control channel added, blade pitch
theta(psi) = theta0 + theta1c*cos(psi) + theta1s*sin(psi) in place of the
collective theta0 alone, where theta1c is the lateral cyclic pitch (the
cos(psi) harmonic) and theta1s is the longitudinal cyclic pitch (the
sin(psi) harmonic) in the standard rotor convention (Johnson, Helicopter
Theory ch. 4; Leishman, Principles of Helicopter Aerodynamics ch. 4,
paraphrased, never reproduced; psi measured from the downwind blade
position, advancing side at psi = pi/2, exactly the wave-46 leaf
convention), and the trim inversion: the longitudinal and lateral cyclic
pitch, and the equivalent swashplate tilt, required to hold the tip-path
plane at a target longitudinal and lateral attitude (a1s-target, b1s-target),
level disk or prescribed tilt. The equilibrium is the exact harmonic balance
of the same flap-moment integrand the wave-46 leaf balances, with the pitch
series extended: blade element velocity components u_T = x + mu*sin(psi) and
u_P = lambda + x*beta' + mu*beta*cos(psi), flap ansatz
beta = a0 + a1s*cos(psi) + b1s*sin(psi), dimensionless aerodynamic flap
moment M(psi) = integral_0^1 x*[u_T^2*theta - u_T*u_P] dx, flap equation
beta'' + beta = (gamma/2)*M(psi). At 1/rev resonance the 1/rev content of
the equation vanishes identically, so the equilibrium nulls the cos and sin
projections of M; the steady projection fixes the coning. Solving the
projection balance exactly (all terms through mu^2 retained; the mean
mu*flap cross couplings cancel identically) gives the affine
control-to-flap response closed forms of the Model section, which reproduce
the wave-46 leaf's closed forms for a0, a1s and b1s EXACTLY at
theta1c = theta1s = 0 (the mandated cross-leaf identity), reduce at mu = 0
to the standard hover cyclic response a1s = -theta1s and b1s = theta1c (the
90-degree flap lag of the centrally hinged blade, so lateral cyclic
controls the lateral disk orientation and longitudinal cyclic the
longitudinal orientation), and stay in the published few-degree cyclic band.
The trim inversion is closed-form linear algebra on the same polynomial
denominators (1 - mu^2/2), (1 + mu^2/2) and (1 + 3*mu^2/2) and reports the
cyclic command and the equivalent swashplate plane tilt (ideal
zero-control-phase swashplate, unit pitch gearing, blade pitch slaved to
the swashplate height profile) that holds the target tip-path-plane
attitude. No numeric integration, no tables, no empiricism: pure algebraic
functions of the inputs, deterministic, pure stdlib. Produces the coning
angle a0 and the longitudinal flapping angle a1s and lateral flapping angle
b1s of the cyclic-forced equilibrium in radians and degrees, the six-key
flap summary dict, the affine cyclic-flap-response gain dict, and the trim
cyclic pitch and swashplate tilt dicts for a target tip-path-plane
attitude. Does NOT do: the hover-state Lock number, hover coning angle or
flap frequency ratio (rotorcraft-blade-flapping-dynamics); the
collective-only flap equilibrium and tip-path-plane-tilt quantities
themselves, which the wave-46 rotorcraft-forward-flight-flapping leaf owns
(this leaf reproduces them as the zero-cyclic limit of its forward map and
as a1s_free/b1s_free, never as its primary surface); rotor power, Glauert
induced velocity or best-speed content (rotorcraft-forward-flight-
performance); lead-lag, lag frequency, ground resonance (rotorcraft-lead-
lag-dynamics); hover coning, lag dynamics, nonuniform inflow, blade
structural dynamics, blade twist, hinge offset, pitch-flap coupling, and
feathering-axis kinematics beyond the 1/rev cyclic model (out of the
model); 2/rev and higher flapping harmonics; swashplate control-phase
rigging geometry and delta-3 kinematics (the swashplate report uses the
ideal zero-phase idealization pinned below; real rotors phase their control
horns, out of scope); rotorcraft flight dynamics or control-system
stability content (the stability-control pack of this family is fixed-wing
only). Scope: 0 <= mu < 1 (singular at mu = 1, reverse flow out of scope),
lambda > 0 (downward-positive family convention), theta0 > 0, gamma > 0,
theta1c and theta1s free real angles (trim routinely requires negative
values; only finiteness is enforced), centrally hinged, first harmonic
only, small angles. The coning angle a0 here depends on theta1s through the
mean-lift term mu*theta1s/3 of the steady projection; the coning is free of
theta1c and free of a1s and b1s (their mean couplings cancel identically).

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG, no imports beyond math.
Module constants: DEG = 180.0/math.pi (radians to degrees conversion factor
for the _deg outputs) and MU_MAX = 1.0 (the advance-ratio model boundary
used by the mu >= 1.0 rejection); no other module-level numbers. Python
note: the inflow ratio parameter is spelled lam in every signature (lambda
is a Python keyword); docstrings and comments name it lambda.

Conventions, pinned (exactly the wave-46 leaf conventions extended with the
control channel; the cyclic labeling follows the standard rotor convention
as verified against the ch. 4 references and the rotor trim literature, e.g.
the NPS JANRAD rotor trim code and UMD rotorcraft theses, both of which
write theta = theta0 + theta1c*cos(psi) + theta1s*sin(psi) with theta1c the
lateral cyclic pitch and theta1s the longitudinal cyclic pitch):
- Blade azimuth psi is measured from the downwind (rear) blade position in
  the direction of rotation, so the advancing blade sits at psi = pi/2 and
  the tangential velocity ratio is u_T = x + mu*sin(psi) with x = r/R.
- Flap angle series: beta(psi) = a0 + a1s*cos(psi) + b1s*sin(psi), a0 the
  coning angle, a1s the longitudinal (cos) component and b1s the lateral
  (sin) component. Sign convention of the outputs, identical to the wave-46
  leaf: a1s < 0 is the tip-path-plane aft-tilt reading (the flapping-back
  direction of forward flight) and b1s < 0 means the psi = pi/2 advancing
  blade tip sits below the coning plane; the free equilibrium of forward
  flight comes out negative few degrees.
- Blade pitch with the control channel:
  theta(psi) = theta0 + theta1c*cos(psi) + theta1s*sin(psi), where theta1c
  is the LATERAL cyclic pitch (cos(psi) harmonic, the pitch that peaks on
  the fore-aft line of the disk) and theta1s is the LONGITUDINAL cyclic
  pitch (sin(psi) harmonic, the pitch that peaks on the port-starboard
  line). With this labeling the hover response is direct: theta1c controls
  the lateral disk orientation (b1s = theta1c at mu = 0) and theta1s the
  longitudinal orientation (a1s = -theta1s at mu = 0), the 90-degree flap
  lag of the centrally hinged blade.
- Inflow: lambda > 0 total uniform inflow ratio, downward-positive family
  convention, matching the hover and wave-46 siblings.

Defining relations (pin these exactly; every function derives from them).
Dimensionless blade element velocities in the hub plane frame:
  u_T = x + mu*sin(psi),
  u_P = lambda + x*beta'(psi) + mu*beta(psi)*cos(psi),
beta' = d beta/d psi. Section angle of attack alpha = theta - u_P/u_T
(untwisted, featherless blade; no pitch-flap coupling). Dimensionless
aerodynamic flap moment about the central hinge, per unit of the
0.5*rho*a*c*Omega^2*R^4 reference:
  M(psi) = integral_0^1 x * [u_T^2*theta - u_T*u_P] dx.
Flap equation of motion with nu = 1 (central hinge):
  beta'' + beta = (gamma/2) * M(psi).
The steady part of beta'' + beta equals a0 and balances the mean moment
(centrifugal restoring); the 1/rev part of beta'' + beta vanishes
identically at the 1/rev resonance, so the equilibrium nulls the cos and
sin projections of M(psi). Substituting the ansatz and the pitch series,
expanding u_T^2*theta - u_T*u_P, keeping all terms through mu^2 (the
product-to-sum reductions give the 1/rev coefficient 1/4 of
sin(psi)*cos^2(psi), the 1/rev coefficient 1/4 of sin^2(psi)*cos(psi), the
sin-component coefficient 3/4 of sin^3(psi) and the steady coefficient 1/2
of sin^2(psi)), and solving the resulting projection balances exactly gives
the closed forms (the exact solution of the model; the anchor verified by
independent 4096 by 512 point quadrature of the full moment integrand that
the closed forms null the steady, cos and sin projections of
(gamma/2)*M - (beta'' + beta) to order 1e-7 at the worked point, so
implement these forms literally rather than re-deriving a variant):

  a0  = (gamma/2) * ( theta0*(1 + mu^2)/4 - lambda/3 + mu*theta1s/3 )
  a1s = -[ 4*mu*(2*theta0/3 - lambda/2)
           + theta1s*(1 + 3*mu^2/2) ] / (1 - mu^2/2)
  b1s = theta1c - (4*mu/3) * a0 / (1 + mu^2/2)

Structural notes: at theta1c = theta1s = 0 the forms reduce EXACTLY to the
wave-46 leaf closed forms a0 = (gamma/2)*(theta0*(1+mu^2)/4 - lambda/3),
a1s = -4*mu*(2*theta0/3 - lambda/2)/(1 - mu^2/2) and
b1s = -(4*mu/3)*a0/(1 + mu^2/2). The (1 - mu^2/2) and (1 + mu^2/2)
denominators are the wave-46 leaf's own; the (1 + 3*mu^2/2) denominator of
the a1s equation comes from the sin^3(psi) projection of the mu^2*theta1s
term and is the only new polynomial factor of the control channel. a1s is
gamma-free by cancellation (the Lock number drops between the aerodynamic
forcing and damping of the 1/rev balance) and independent of theta1c (the
cos-harmonic pitch projects onto the cos balance only). b1s carries theta1c
with unity gain and carries gamma, mu and theta1s through the coning
coupling. The coning equation gains the mean-lift term mu*theta1s/3 (the
steady projection of the sin-harmonic pitch against the mu velocity field);
the mu*flap cross couplings of the mean projection cancel identically, so
a0 carries no a1s, b1s or theta1c term. Hover limit mu = 0: a0 equals the
hover leaf closed form 0.5*gamma*(theta0/4 - lambda/3) independent of the
cyclic, a1s = -theta1s exactly and b1s = theta1c exactly (the 90-degree
lag), and the free-equilibrium limit theta1c = theta1s = 0 gives
a1s = b1s = 0 exactly.

Swashplate tilt report (pinned idealization): the trim cyclic is reported
both as the rotating-frame pitch harmonics theta1c and theta1s (the primary
outputs, convention-independent) and as the equivalent swashplate plane
tilt under the ideal zero-control-phase swashplate idealization with unit
pitch gearing, where the blade pitch equals the swashplate height profile
at the blade azimuth. Under that idealization the longitudinal swashplate
tilt about the lateral (port-starboard) hub axis commands the cos(psi)
harmonic theta1c and the lateral swashplate tilt about the longitudinal
(fore-aft) hub axis commands the sin(psi) harmonic theta1s, so the tilt
components equal the corresponding cyclic harmonics and the tilt magnitude
is their hypot. Real rotors rig control-phase offsets into their pitch
horns; that rigging geometry is out of scope and the rotating-frame
harmonics remain the model outputs. The reported swashplate tilt is the
physical content of the corpus query "swashplate-tilt cyclic inputs".

Functions (implement with exactly these signatures; pure math only, angles
in radians; validation rules listed once below apply to every function on
every argument it takes):
- coning_angle(mu, lam, theta0, gamma, theta1s) -> float: a0 =
  (gamma/2)*(theta0*(1 + mu^2)/4 - lam/3 + mu*theta1s/3). Validates all
  five arguments. Returns the hover closed form at mu = 0.0.
- longitudinal_flapping_angle(mu, lam, theta0, theta1s) -> float: a1s =
  -[4*mu*(2*theta0/3 - lam/2) + theta1s*(1 + 3*mu^2/2)]/(1 - mu^2/2).
  Takes no gamma (it cancels in the 1/rev balance) and no theta1c (the cos
  harmonic never projects here). Returns exactly -theta1s at mu = 0.0 and
  exactly 0.0 for mu = 0.0 with theta1s = 0.0.
- lateral_flapping_angle(mu, lam, theta0, gamma, theta1c, theta1s) ->
  float: b1s = theta1c - (4*mu/3)*coning_angle(mu, lam, theta0, gamma,
  theta1s)/(1 + mu^2/2). Returns exactly theta1c at mu = 0.0.
- flap_response_summary(mu, lam, theta0, gamma, theta1c, theta1s) -> dict:
  the one-call forward-map dict with exactly these six keys:
  coning_angle_rad, coning_angle_deg, longitudinal_flapping_rad,
  longitudinal_flapping_deg, lateral_flapping_rad, lateral_flapping_deg,
  where each _deg value is the _rad value times DEG and each component
  matches the corresponding standalone function at the same arguments.
- cyclic_response_gains(mu, lam, theta0, gamma) -> dict: the affine
  control-to-flap gains of the equilibrium map, returned with exactly these
  six keys: a1s_free (the wave-46 zero-cyclic longitudinal flapping),
  b1s_free (the wave-46 zero-cyclic lateral flapping),
  d_a1s_d_theta1s = -(1 + 3*mu^2/2)/(1 - mu^2/2),
  d_a1s_d_theta1c = 0.0 exactly,
  d_b1s_d_theta1c = 1.0 exactly,
  d_b1s_d_theta1s = -(2*gamma*mu^2/9)/(1 + mu^2/2) (the coning-mediated
  coupling, zero at mu = 0.0 and quadratic in mu).
  Validates state and gamma (no cyclic arguments).
- trim_cyclic(mu, lam, theta0, gamma, a1s_target, b1s_target) -> dict: the
  trim inversion, closed-form solution of the equilibrium map for the cyclic
  command holding the tip-path plane at (a1s_target, b1s_target):
  theta1s = -[a1s_target*(1 - mu^2/2) + 4*mu*(2*theta0/3 - lam/2)] /
  (1 + 3*mu^2/2), then a0 from coning_angle at that theta1s, then
  theta1c = b1s_target + (4*mu/3)*a0/(1 + mu^2/2); at mu = 0.0 the limiting
  form theta1s = -a1s_target, theta1c = b1s_target. Returns exactly these
  four keys: longitudinal_cyclic_pitch_rad (theta1s),
  longitudinal_cyclic_pitch_deg, lateral_cyclic_pitch_rad (theta1c),
  lateral_cyclic_pitch_deg. Targets are free finite reals (a negative
  a1s_target, the level disk 0.0, or a prescribed tilt are all valid).
- trim_swashplate_tilt(mu, lam, theta0, gamma, a1s_target, b1s_target) ->
  dict: the ideal zero-phase swashplate report of the same trim, with
  exactly these six keys: swashplate_longitudinal_tilt_rad (equals the
  trim theta1c), swashplate_longitudinal_tilt_deg,
  swashplate_lateral_tilt_rad (equals the trim theta1s),
  swashplate_lateral_tilt_deg, swashplate_tilt_magnitude_rad and
  swashplate_tilt_magnitude_deg (hypot of the two components, times DEG).
  Same ValueErrors as trim_cyclic.
ValueError rejection (every public function, on every argument it takes):
mu < 0.0, mu >= MU_MAX (1.0; the uniform-inflow model is singular at mu = 1
and reverse flow is out of scope), lam <= 0.0, theta0 <= 0.0, gamma <= 0.0,
any non-finite argument including theta1c, theta1s, a1s_target and
b1s_target. mu = 0.0 is a valid hover-limit input; theta1c and theta1s may
be negative (trim routinely needs them so) but must be finite. The anchor
verifies twelve ValueError cases.

Identities to test (closed form, deterministic; all values are REAL anchor
outputs of /tmp/w47spec/anchor_rotorcraft_cyclic_pitch_trim.py, stdlib
math, exit 0, no RNG):
- Zero-cyclic cross-leaf identity: at the worked point mu = 0.3, lam =
  0.06, theta0 = 0.14, gamma = 6.0 with theta1c = theta1s = 0.0,
  flap_response_summary returns coning_angle_rad 0.054450000000000012,
  longitudinal_flapping_rad -0.079581151832460728 and
  lateral_flapping_rad -0.020842105263157901, bit-identical to the wave-46
  leaf's printed worked values for the same arguments; equivalently the
  closed forms above reduce to the wave-46 closed forms exactly.
- Hover cyclic response: at mu = 0.0, lam = 0.06, theta0 = 0.14, gamma =
  6.0 with theta1c = 0.02, theta1s = -0.04, longitudinal_flapping_angle
  returns exactly 0.040000000000000001 (equals -theta1s), lateral_flapping_
  angle returns exactly 0.02 (equals theta1c), coning_angle returns
  0.045000000000000012 (the hover leaf coning closed form, cyclic-free).
- Hover no-cyclic probe: trim_cyclic(0.0, 0.06, 0.14, 6.0, 0.0, 0.0)
  returns both cyclic pitches exactly 0.0 (a level disk at hover needs no
  cyclic).
- Free-equilibrium inversion identity: trim_cyclic at the free-equilibrium
  attitude (a1s_target = a1s_free, b1s_target = b1s_free from
  cyclic_response_gains) returns theta1s = -0.0 and theta1c = 0.0 exactly
  (the equilibrium the wave-46 leaf describes is held with zero cyclic).
- Round-trip identity: flap_response_summary at the level-disk trim returns
  longitudinal_flapping_rad and lateral_flapping_rad equal to 0.0 within
  1e-9, and at the prescribed-attitude trim returns a1s = -0.02 and
  b1s = 0.0 within 1e-9.
- Ordering identity: at the worked point the level-disk longitudinal cyclic
  magnitude 0.0669603524 rad stays below the free aft-tilt magnitude
  0.0795811518 rad, because the leveling denominator (1 + 3*mu^2/2) exceeds
  the free-flap denominator (1 - mu^2/2); anchor True.
- Inflow linearity of the trim: lambda enters the level-disk trim cyclic
  linearly, and the two-point differences over lam = 0.06 versus 0.05 are
  the exact closed-form slopes d(theta1s)/d(lambda) = 2*mu/(1 + 3*mu^2/2)
  and d(theta1c)/d(lambda) = -(2*gamma*mu/9)*(1 - mu^2/2)/
  ((1 + 3*mu^2/2)*(1 + mu^2/2)): anchor d(theta1s) = 0.0052863436123347929
  against 0.0052863436123348016 (within 9e-18) and
  d(theta1c) = -0.0032207069536074918 against -0.0032207069536074866
  (within 6e-18), the latter carrying the theta1s feedback through the
  coning.
- Gain structure: d_b1s_d_theta1c is exactly 1.0 and d_a1s_d_theta1c is
  exactly 0.0 at every valid point; at the worked point
  d_a1s_d_theta1s = -1.1884816753926701, matching -(1 + 3*mu^2/2)/
  (1 - mu^2/2) = -1.135/0.955 within 1e-15, and
  d_b1s_d_theta1s = -0.11483253588516748, matching
  -(2*gamma*mu^2/9)/(1 + mu^2/2) = -0.12/1.045 within 1e-15.
- Coning decoupling: coning_angle is independent of theta1c and of a1s and
  b1s at every valid point (the mean mu*flap couplings cancel identically;
  anchor-verified numerically), and depends on theta1s only through the
  mu*theta1s/3 mean-lift term.
- Full-moment Fourier self-consistency: at the worked point with
  theta1c = 0.02, theta1s = -0.04 the closed-form equilibrium nulls the
  steady, cos and sin projections of (gamma/2)*M - (beta'' + beta) computed
  by independent 4096 by 512 point quadrature over x and psi (pure stdlib)
  with residuals -1.316e-07, -1.110e-08 and 2.295e-08 (quadrature noise
  five orders below the first-harmonic content).
- Determinism: two identical summary calls return identical dicts; no RNG;
  no imports beyond math.

## Worked example

Cruise case in the corpus band: advance ratio mu = 0.3, uniform inflow
ratio lambda = 0.06, collective theta0 = 0.14 rad, Lock number gamma = 6.0
(a light-to-medium helicopter blade in the sibling gamma band 5 to 8 and
lambda band 0.05 to 0.08, the mu = 0.3 point named in the corpus query, the
exact worked point of the wave-46 leaf so the cross-leaf identities are
direct). All values below are REAL outputs of the prep anchor
/tmp/w47spec/anchor_rotorcraft_cyclic_pitch_trim.py (pure stdlib, math
only, closed form, exit 0, no RNG, run once and quoted as printed;
identical under /usr/bin/python3 3.9.6, the default python3 3.12.9 and
~/.pyenv/versions/3.13.12/bin/python3):

- Zero-cyclic limit (module output [1]): flap_response_summary(0.3, 0.06,
  0.14, 6.0, 0.0, 0.0) returns coning_angle_rad 0.054450000000000012,
  coning_angle_deg 3.1197551944873334, longitudinal_flapping_rad
  -0.079581151832460728, longitudinal_flapping_deg -4.5596641287897972,
  lateral_flapping_rad -0.020842105263157901, lateral_flapping_deg
  -1.1941646677463478. These six values are bit-identical to the wave-46
  leaf's worked example: the model is exactly the sibling at zero cyclic.
- Forward map under a cyclic command (module output [2]): at theta1c =
  0.02 rad (1.1459 deg lateral cyclic) and theta1s = -0.04 rad (-2.2918 deg
  longitudinal cyclic) the tip-path plane relaxes: coning_angle_rad
  0.042450000000000009 (2.432205840330345 deg, the negative longitudinal
  cyclic unloading the advancing-side mean lift), longitudinal_flapping_rad
  -0.032041884816753921 (-1.8358647676443129 deg, the aft tilt eased from
  -4.56 deg by the -2.29 deg longitudinal cyclic) and lateral_flapping_rad
  0.0037511961722488003 (0.21492770879548564 deg, the +1.15 deg lateral
  cyclic overcoming the coning coupling and raising the advancing side).
- Cyclic response gains (module output [3]): cyclic_response_gains(0.3,
  0.06, 0.14, 6.0) returns a1s_free -0.079581151832460728, b1s_free
  -0.020842105263157901, d_a1s_d_theta1s -1.1884816753926701,
  d_a1s_d_theta1c 0.0, d_b1s_d_theta1c 1.0 and d_b1s_d_theta1s
  -0.11483253588516748: one degree of longitudinal cyclic moves the
  longitudinal tilt 1.19 deg, one degree of lateral cyclic moves the lateral
  tilt 1.00 deg, and the coning-mediated cross coupling moves the lateral
  tilt only 0.115 deg per degree of longitudinal cyclic.
- Level-disk trim (module output [4]): trim_cyclic(0.3, 0.06, 0.14, 6.0,
  0.0, 0.0) returns longitudinal_cyclic_pitch_rad -0.066960352422907488
  (-3.836545588541195 deg) and lateral_cyclic_pitch_rad
  0.013152878190670913 (0.75360440877510981 deg): holding the tip-path
  plane level at mu = 0.3 needs -3.84 deg of longitudinal cyclic (it
  cancels the 4.56 deg free aft tilt scaled by the denominator ratio
  (1 - mu^2/2)/(1 + 3*mu^2/2) = 0.955/1.135 = 0.8414) and +0.75 deg of
  lateral cyclic (it cancels the b1s the coning coupling would induce).
  Round trip: flap_response_summary at that
  command returns a1s = -0.0 and b1s = 0.0 exactly.
- Prescribed attitude trim (module output [5]): trim_cyclic(0.3, 0.06,
  0.14, 6.0, -0.02, 0.0), holding the disk at a relaxed aft tilt of -0.02
  rad (-1.14592 deg), returns longitudinal_cyclic_pitch_rad
  -0.050132158590308368 (-2.8723611051051843 deg) and
  lateral_cyclic_pitch_rad 0.015085302362835404 (0.86432415806919716 deg).
  Round trip returns a1s = -0.02 and b1s = 0.0 within 1e-9.
- Free-equilibrium identity (module output [6]): trim_cyclic at
  a1s_target = -0.079581151832460728, b1s_target = -0.020842105263157901
  returns theta1s = -0.0 and theta1c = 0.0 exactly: the wave-46
  collective-only equilibrium is held with zero cyclic, as it must be.
- Level-disk swashplate report (module output [7]): trim_swashplate_tilt
  under the ideal zero-phase idealization returns
  swashplate_longitudinal_tilt_rad 0.013152878190670913
  (0.75360440877510981 deg), swashplate_lateral_tilt_rad
  -0.066960352422907488 (-3.836545588541195 deg) and
  swashplate_tilt_magnitude_rad 0.068239922342413314
  (3.9098595445207733 deg): the swashplate plane stands tilted 3.91 deg
  from level at the level-disk cruise trim.
- Hover anchors (module output [8]): at mu = 0.0 the cyclic response is
  a1s = 0.040000000000000001 (exactly -theta1s), b1s = 0.02 (exactly
  theta1c) and a0 = 0.045000000000000012 (the hover coning closed form,
  cyclic-free), and trim_cyclic(0.0, 0.06, 0.14, 6.0, 0.0, 0.0) returns
  both cyclic pitches exactly 0.0.
- Ordering and inflow anchors (module outputs [10] and [14]): the level
  longitudinal cyclic magnitude 0.0669603524 rad sits below the free aft
  tilt 0.0795811518 rad (True), and over lam = 0.06 versus 0.05 the level
  trim moves by d(theta1s) = 0.0052863436123347929 rad and
  d(theta1c) = -0.0032207069536074918 rad, the exact closed-form slopes of
  the Identities section (the trim needs less longitudinal cyclic at higher
  inflow, which relaxes the free aft tilt).
- ValueError probes (module output [12], all twelve raise ValueError):
  mu = -0.1, mu = 1.0, mu = 1.5, lam = 0.0, lam = -0.02, theta0 = 0.0,
  theta0 = -0.1, gamma = 0.0, gamma = -3.0, theta1s = nan,
  theta1c = inf and a1s_target = nan, with mu = 0.0 and the negative cyclic
  values of the trims above valid inputs.
- Determinism (module output [13]): two identical flap_response_summary
  calls return identical dicts; the anchor exits 0 and its internal asserts
  (zero-cyclic equality to the sibling values, the hover cyclic identities,
  both trim round trips, the free-equilibrium and hover no-cyclic zeros,
  the exact gain structure, the inflow-slope identities and the Fourier
  residual bounds) all pass.

Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of
/tmp/w47spec/anchor_rotorcraft_cyclic_pitch_trim.py (stdlib math, closed
form, exit 0, no randomness, identical under all three interpreters).

## Validation list (contract test must include)

1. Zero-cyclic cross-leaf asserts within 1e-9 relative: flap_response_
   summary(0.3, 0.06, 0.14, 6.0, 0.0, 0.0) gives coning_angle_rad
   0.054450000000000012, longitudinal_flapping_rad -0.079581151832460728,
   lateral_flapping_rad -0.020842105263157901, and each equals the
   corresponding wave-46 sibling closed form computed in the test from the
   printed formulas within 1e-12 (no import of the sibling module).
2. Hover cyclic asserts within 1e-9: longitudinal_flapping_angle(0.0, 0.06,
   0.14, -0.04) = 0.040000000000000001 (equals -theta1s), lateral_flapping_
   angle(0.0, 0.06, 0.14, 6.0, 0.02, -0.04) = 0.02 (equals theta1c),
   coning_angle(0.0, 0.06, 0.14, 6.0, -0.04) = 0.045000000000000012 (the
   hover coning closed form 0.5*gamma*(theta0/4 - lam/3) within 1e-12);
   trim_cyclic(0.0, 0.06, 0.14, 6.0, 0.0, 0.0) returns exactly 0.0 for
   both cyclic pitches.
3. Level-disk trim asserts within 1e-9 relative: trim_cyclic(0.3, 0.06,
   0.14, 6.0, 0.0, 0.0) gives longitudinal_cyclic_pitch_rad
   -0.066960352422907488 and lateral_cyclic_pitch_rad
   0.013152878190670913; the forward map at that command returns
   longitudinal_flapping_rad and lateral_flapping_rad equal to 0.0 within
   1e-9 (round-trip).
4. Prescribed-attitude trim asserts within 1e-9 relative: trim_cyclic(0.3,
   0.06, 0.14, 6.0, -0.02, 0.0) gives longitudinal_cyclic_pitch_rad
   -0.050132158590308368 and lateral_cyclic_pitch_rad
   0.015085302362835404; the forward map returns a1s = -0.02 and
   b1s = 0.0 within 1e-9.
5. Free-equilibrium identity: with a1s_free and b1s_free from
   cyclic_response_gains, trim_cyclic at that attitude returns both cyclic
   pitches exactly 0.0 (math.isclose to 0.0 at 1e-15); hover no-cyclic
   probe likewise.
6. Gain asserts: cyclic_response_gains(0.3, 0.06, 0.14, 6.0) gives
   d_a1s_d_theta1s -1.1884816753926701, d_a1s_d_theta1c exactly 0.0,
   d_b1s_d_theta1c exactly 1.0, d_b1s_d_theta1s -0.11483253588516748; each
   gain equals its closed form -(1 + 3*mu^2/2)/(1 - mu^2/2) and
   -(2*gamma*mu^2/9)/(1 + mu^2/2) within 1e-12, and the unity and zero
   entries are exact.
7. Ordering identity: at the worked point |theta1s_level| = 0.0669603524
   rad is below |a1s_free| = 0.0795811518 rad (math.isclose-free strict
   comparison, anchor True).
8. Inflow two-point trim linearity: at mu = 0.3, theta0 = 0.14, gamma =
   6.0, lam = 0.06 versus 0.05, the level-trim theta1s difference
   0.0052863436123347929 equals 2*mu*0.01/(1 + 3*mu^2/2) within 1e-12 and
   the theta1c difference -0.0032207069536074918 equals
   -(2*gamma*mu/9)*(1 - mu^2/2)*0.01/((1 + 3*mu^2/2)*(1 + mu^2/2)) within
   1e-12.
9. Degree outputs: coning_angle_deg 3.1197551944873334,
   longitudinal_flapping_deg -4.5596641287897972, lateral_flapping_deg
   -1.1941646677463478 and the trim degree outputs
   (longitudinal_cyclic_pitch_deg -3.836545588541195,
   lateral_cyclic_pitch_deg 0.75360440877510981) within 1e-9 relative,
   each _deg equal to the _rad value times 180.0/math.pi within 1e-12;
   flap_response_summary returns exactly the six documented keys and no
   others, each matching its standalone function within 1e-12, and the same
   key and component discipline holds for the trim and swashplate dicts.
10. Coning decoupling: coning_angle(0.3, 0.06, 0.14, 6.0, theta1s) is
    unchanged by any finite theta1c (it takes none) and equals
    (gamma/2)*(theta0*(1 + mu^2)/4 - lam/3 + mu*theta1s/3) within 1e-12 at
    theta1s = -0.04 (0.042450000000000009) and theta1s = 0.0
    (0.054450000000000012).
11. Independent Fourier self-consistency: at the worked point with
    theta1c = 0.02, theta1s = -0.04 the closed-form equilibrium nulls the
    steady, cos and sin projections of (gamma/2)*M - (beta'' + beta) by
    direct quadrature (at least 1024 by 128 points, stdlib only) with
    absolute residuals below 1e-5 each (the anchor's 4096 by 512 run gives
    -1.316e-07, -1.110e-08 and 2.295e-08).
12. ValueErrors: mu = -0.1, mu = 1.0, mu = 1.5, lam = 0.0, lam = -0.02,
    theta0 = 0.0, theta0 = -0.1, gamma = 0.0, gamma = -3.0, theta1s = nan,
    theta1c = inf and a1s_target = nan all raise ValueError from the named
    functions (twelve anchor cases); mu = 0.0 and the negative cyclic and
    negative a1s_target values used above are valid inputs.
13. Determinism: two identical flap_response_summary and trim_cyclic calls
    return identical bits; no RNG; no imports beyond math; module constants
    DEG = 180.0/math.pi and MU_MAX = 1.0 fixed as above. No exact-float
    equality on computed sums; use assertAlmostEqual/math.isclose
    everywhere. Contract test file named test_rotorcraft_cyclic_pitch_trim.py
    (underscores), unittest, offline in under 20 seconds.
14. Run the deterministic contract test offline (no network); it exits 0.
    Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3; the anchor was additionally
    verified identical under the default python3 3.12.9).

## Corpus fragment (2 verbatim queries for
eval/hit1-wave47-rotorcraft-cyclic-pitch-trim.yaml)

Query 1 (copy verbatim from the probe receipt gate (e)):
  "check the main-rotor trim control at cruise: solve for the
  longitudinal-cyclic-pitch and the lateral-cyclic-pitch required to hold
  the tip-path plane at the level-disk attitude at an advance ratio of 0.3
  with uniform inflow"
  intent: "flight-mechanics; rotorcraft cyclic-pitch trim: the
  longitudinal-cyclic-pitch and the lateral-cyclic-pitch required to hold
  the tip-path plane at the level-disk attitude at an advance ratio of 0.3
  with uniform inflow, the trim inversion of the steady first-harmonic
  flap equilibrium with the cyclic control channel"
  expected_skill: "flight-mechanics/performance/rotorcraft-cyclic-pitch-trim"
Query 2 (copy verbatim from the probe receipt gate (e)):
  "compute the swashplate-tilt cyclic inputs to trim the rotor disk to a
  target longitudinal and lateral flapping state at a given advance ratio
  and inflow ratio, and report the cyclic-flap-response gains of the
  centrally hinged blade"
  intent: "flight-mechanics; rotorcraft cyclic-pitch trim: the
  swashplate-tilt cyclic inputs that trim the rotor disk to a target
  longitudinal and lateral flapping state at a given advance ratio and
  inflow ratio, and the cyclic-flap-response gains of the centrally hinged
  blade"
  expected_skill: "flight-mechanics/performance/rotorcraft-cyclic-pitch-trim"
Task ids: w47-rotorcraft-cyclic-pitch-trim-1 and -2. Prep grep and probe
evidence (real greps at prep for this spec): cyclic pitch, swashplate,
longitudinal cyclic, lateral cyclic, control plane and control-plane
appear in NO existing eval/hit1-corpus.yaml task and in NO skills/ file (0
hits, exit 1); the only "cyclic" corpus task is
w24r-strain-life-fatigue-2 (stress-cycle fatigue tokens, no rotorcraft
content); the wave-46 tasks (w46-rotorcraft-forward-flight-flapping-1/-2)
carry forward-flight-flapping, tip-path-plane-tilt and
longitudinal/lateral-flapping-angle tokens only and continue to route to
the wave-46 leaf, so the queries above are collision-free and deliberately
carry the longitudinal-cyclic-pitch, lateral-cyclic-pitch, swashplate-tilt,
cyclic-flap-response and tip-path-plane-control hyphenated tokens of the
gate (f) tag list, never the bare words cyclic, pitch, rotorcraft or
swashplate as standalone tags. Build-time notes (wave-46 precedent): add
one fence line to rotorcraft-forward-flight-flapping ("collective-only
equilibrium; cyclic pitch, swashplate-tilt and control-plane content belong
to the cyclic-trim sibling"), fence the broad rotorcraft-blade-flapping-
dynamics router guidance row, add one router row in skills/flight-mechanics/
SKILL.md, and add the 2 corpus tasks at merge. Flight-mechanics 48 -> 49
leaves after landing.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the cyclic-pitch trim of a
helicopter main rotor blade in forward flight under uniform inflow:" and
include the outputs in the Claim order (the coning angle and the
longitudinal and lateral flapping angles of the cyclic-forced equilibrium,
the affine cyclic-flap-response gains, the trim cyclic pitch and the
equivalent swashplate tilt that hold the target tip-path-plane attitude),
then close with the Trigger list. First tag: rotorcraft-cyclic-pitch-trim.
Metadata tags EXACTLY as the probe receipt gate (f) lists them, nothing
else: longitudinal-cyclic-pitch, lateral-cyclic-pitch, swashplate-tilt,
cyclic-flap-response, trim-cyclic, control-plane-tilt, disk-attitude-trim.
NEVER the bare single words cyclic, pitch, rotorcraft, rotor control or
swashplate as tags (the receipt gate (f) prunes them: the flap siblings and
the family router own the generic rotorcraft and blade-dynamics surface),
NEVER the wave-46 sibling tags forward-flight-flapping, tip-path-plane-
tilt, first-harmonic-flap-response, longitudinal-flapping-angle,
lateral-flapping-angle, advance-ratio-flapping and flap-equilibrium-tilt
(they route the w46 corpus tasks; this leaf's prose may describe the
longitudinal and lateral flapping outputs but never as tags), NEVER the
hover sibling tokens lock-number, hover-coning, coning-angle,
flap-frequency-ratio, hinge-offset, rotor-blade-flapping
(rotorcraft-blade-flapping-dynamics), NEVER glauert-inflow,
induced-power, parasite-power, profile-power, best-endurance-speed,
best-range-speed, equivalent-flat-plate-area
(rotorcraft-forward-flight-performance), NEVER lead-lag, lag-frequency,
regressing-lag-mode, ground-resonance-clearance, coincidence-rotor-speed
(rotorcraft-lead-lag-dynamics), and never autorotation, axial-descent,
vortex-ring, hover-power, momentum-theory, figure-of-merit or
range-endurance (the other rotorcraft performance leaves). Do NOT claim
hover coning, lag dynamics, nonuniform or dynamic inflow, blade structural
dynamics, blade twist, hinge offset, pitch-flap coupling, control-phase
rigging geometry, or feathering-axis kinematics beyond the 1/rev cyclic
model in the description or tags; the blade Lock number gamma and the
inflow ratio enter as inputs, named in prose, never as the lock-number or
hover-coning tags. Recommended wording, 50-150 words, <=1000 chars, action
verb present, no em dash (verified at spec time at 997 chars, 140 words):

"Use when you must compute the cyclic-pitch trim of a helicopter main rotor
blade in forward flight under uniform inflow: the steady first-harmonic
(1/rev) flapping equilibrium of the idealized centrally hinged blade with
the control channel added, longitudinal cyclic theta1s and lateral cyclic
theta1c about the collective, in the standard rotor convention, and the
trim inversion for the cyclic pitch and equivalent swashplate tilt that
hold the tip-path plane at a target longitudinal and lateral attitude,
level or prescribed. Produces the coning angle and the longitudinal and
lateral flapping angles of the cyclic-forced equilibrium, the affine
cyclic-flap-response gains, and the trim cyclic and swashplate tilt for the
target attitude; the zero-cyclic limit reproduces the collective-only
forward-flight flapping sibling exactly. Trigger: rotorcraft cyclic pitch
trim, longitudinal cyclic pitch, lateral cyclic pitch, swashplate tilt,
trim cyclic, cyclic flap response, disk attitude trim."

The sibling triggers "lock number", "hover coning", "coning angle", "flap
frequency ratio", "hinge offset", "glauert", "parasite power", "best
endurance speed", "best range speed", "lead lag", "ground resonance",
"forward flight flapping" and "tip path plane tilt" must not appear as
description tokens. ZERO em dashes in every file; no sensitivity-level
marking vocabulary in prose (the compliance posture of every leaf in this
repo is standards-reference, never restricted-content). Standards
reference-only: far-29 is the FAA transport-category rotorcraft
airworthiness standard (ecfr.gov); the cyclic-trim relations above are
standard engineering methodology (Johnson, Helicopter Theory ch. 4 and
Leishman, Principles of Helicopter Aerodynamics ch. 4, paraphrased, never
reproduced), summary-only per standards-map.yaml. Model-decision notes for
the builder: the receipt prescribes the wave-46 harmonic balance extended
with the cyclic control channel; the closed forms above are the exact
solution of that balance (all coefficients certified by the anchor's
4096 by 512 point full-moment Fourier self-consistency check at the worked
point, residuals order 1e-7), they reproduce the wave-46 leaf closed forms
bit-identically at zero cyclic, and they are the forms the contract test
asserts, so implement them literally rather than re-deriving from a variant
of the velocity model. The cyclic sign convention is pinned by the verified
standard rotor convention: theta1c (cos(psi) harmonic) is the lateral
cyclic pitch and theta1s (sin(psi) harmonic) the longitudinal cyclic pitch,
with psi measured from the downwind blade position as in the wave-46 leaf;
at hover this gives a1s = -theta1s and b1s = theta1c, so lateral cyclic
controls the lateral disk orientation and longitudinal cyclic the
longitudinal orientation. The swashplate tilt report uses the ideal
zero-control-phase swashplate idealization with unit pitch gearing pinned
in this spec; do not introduce control-phase or delta-3 rigging geometry.
Repo paths in this spec are repo-relative; the repo root is the local
AeroSkills checkout (~/AeroSkills).

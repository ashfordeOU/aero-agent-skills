# Wave-44 leaf spec: restrained-warping (structures, fem pack)

- Path: skills/structures/fem/restrained-warping/
- Pack: fem (22 leaves present at prep: beam-column-analysis,
  beam-frame-analysis, beam-vibration, buckling-analysis, calculix-linear,
  calculix-nonlinear, contact-analysis, crippling-analysis,
  curved-beam-analysis, cylindrical-shell-buckling, diagonal-tension-field-
  webs, hertzian-contact-stress, lug-joint-analysis, metallic-fastener-
  joints, modal-analysis, plastic-collapse-analysis, plate-buckling,
  pressure-bulkhead, shear-center-analysis, shrink-fit-analysis,
  torsion-shear-flow, truss-analysis; restrained-warping is a wave-44
  addition of the family, wave-43 reserve candidate re-verified GO).
  Claim fences (quoted from the sibling frontmatter at prep; none owns
  warping restraint, a bimoment or a non-uniform torsion response):
  - torsion-shear-flow (this pack) is the FREE-warping complement: its
    description opens "Use when you must compute the torsion shear flow
    of a closed or open structural section: the polar second moment J
    for solid and tube shafts, the Saint-Venant torsion constant for
    thin open rectangles and built-up open sections, the Bredt-Batho
    closed-section shear flow q = T/(2 A_m), the closed-section twist
    rate, the shear stress and torsional stress margin, and the
    multi-cell shear-flow distribution of a two-cell section under an
    applied torque". Its whole response is uniform-torsion machinery:
    the open-section twist rate is T/(G*J) with J = b*t**3/3 per thin
    rectangle, the closed-section twist rate comes from the Bredt
    circulation, and its worked example never evaluates a derivative of
    the twist. A body grep of its SKILL.md for warping, restraint and
    bimoment gives 0 hits (real run, exit 1): no warping constant, no
    bimoment, no theta'' warping-stress term anywhere in that leaf. Its
    tags torsion-shear-flow, bredt-batho, saint-venant-torsion,
    angle-of-twist, multi-cell-section, closed-section-shear-flow and
    torsional-stress-margin are NOT reusable here, and its trigger
    "Saint-Venant torsion" must not appear in this leaf's description.
  - shear-center-analysis (this pack) is the TRANSVERSE-shear
    complement: its description opens "Use when you must locate the
    shear center of a thin-walled open section under transverse shear:
    walk the contour from the free edge accumulating the first moment
    Q, build the V*Q/I shear-flow distribution, integrate the
    wall-shear resultant and its moment, and report the shear-center
    offset ...". Its load is a transverse force V applied through the
    shear center, its flow is the bending shear q = V*Q/I, and torsion
    never enters: no torque, no twist, no bimoment. Its tags
    shear-center-analysis, shear-center-location, transverse-shear-flow
    and thin-walled-open-section are NOT reusable here.
  - No leaf anywhere in skills/ claims torsional-flexural or
    warping-torsion buckling of columns: beam-column-analysis and
    buckling-analysis stay elastic compression and bending instability,
    and neither file contains the words torsion or warping (real grep).
  - Whole-tree greps at prep (real runs): "warping", "bimoment",
    "warping constant", "non-uniform torsion" and "restrained" over the
    skills/ SKILL.md bodies give structural hits ONLY at this leaf's
    future home; the nonzero matches elsewhere are all noise, quoted
    for the record: frequency prewarping of the bilinear transform in
    digital-filter-design, digital-control-design and the
    gnc-autonomy family index; restrained thermal expansion in
    thermal-stress-analysis and thermal-buckling; the plate-buckling
    adjective "heavily restrained edges" (an edge boundary condition,
    not warping restraint); and the cylindrical-shell-buckling
    cross-reference to thermal-buckling. In eval/hit1-corpus.yaml the
    distinctive tokens restrained-warping, non-uniform-torsion,
    bimoment, warping-constant and torsional-flexure each match 0
    tasks; the only "warping" corpus words sit inside
    frequency-prewarping (2 tasks: the wave-1 digital filter design and
    a digital control design task) and the only "restrained" corpus
    words belong to the wave-26 thermal-buckling restrained-temperature
    tasks. GENUINE STRUCTURES gap (fresh probe): no leaf computes the
    restrained (non-uniform) torsion response of an open thin-walled
    section, the warping constant, the bimoment or the warping normal
    stress; torsion-shear-flow is free-warping by claim and
    shear-center-analysis is transverse V*Q/I by claim.
- Standards id: far-25, cs-25 (reference-only, both present in
  standards-map.yaml, gated false, matching the fem siblings; the FAR
  25.301 / CS 25.301 applied-load and FAR 25.303 / CS 25.303 1.5
  ultimate-factor requirements set the load context of the torque
  cases, summary paraphrase only, never standard text). Ledger
  Standard: far-25, cs-25.
- Family: structures

## Claim

Analyze the restrained (non-uniform) torsion of a thin-walled open
doubly symmetric I-section: compute the Saint-Venant torsion constant
J = (2*b*t_f**3 + (d - 2*t_f)*t_w**3)/3 of the open section, the
warping constant (sectorial second moment) Cw = I_y*h**2/4 of the
doubly symmetric I-section with h = d - t_f the flange mid-line spacing
and I_y = 2*(b**3)*t_f/12 the flange-pair second moment about the web
plane (the web lies on the sectorial zero line, so its own t_w**3 minor
term contributes nothing and Cw equals the direct sectorial integral
t_f*h**2*b**3/24), the sectorial coordinate omega = h*b/4 at the flange
tip, and the decay parameter k = sqrt(G*J/(E*Cw)) of the non-uniform
torsion equation E*Cw*theta'''' - G*J*theta'' = 0 (the characteristic
1/k over which warping restraint decays along the span); solve the
hyperbolic closed-form solution of that ODE for the two classical
boundary-value cases: the fixed-end cantilever of length L with a point
torque T at the free tip (root built in, twist and warping prevented,
theta(0) = 0 and theta'(0) = 0; tip free to warp with the applied
torque, theta''(L) = 0 and G*J*theta'(L) - E*Cw*theta'''(L) = T),
giving theta(z) = (T/(G*J*k))*(k*z - sinh(k*z) + tanh(u)*(cosh(k*z) -
1)) with u = k*L, and the fork-supported beam with a point torque T at
midspan (both ends twist-fixed and free to warp, theta = theta'' = 0 at
each fork, torque applied through a rigid collar so the midspan plane
is a symmetry plane, theta'(L/2) = 0), giving theta(x) = (T/(2*G*J))*
(x - sinh(k*x)/(k*cosh(v))) on the half-beam x in [0, L/2] with
v = k*L/2 and the full span mirrored by symmetry; report the twist
theta(z), the twist rate theta'(z), the bimoment B(z) = -E*Cw*theta''
(z), the warping normal stress sigma_w = B*omega/Cw at the flange tip,
and the torque partition T = T_sv + T_w along the span with the
Saint-Venant shear torque T_sv = G*J*theta'(z) and the warping torque
T_w = -E*Cw*theta'''(z), showing the classical load path: at a built-in
root or a torque collar the full torque is carried by warping
(T_sv = 0, T_w = T), while far from the restraint the Saint-Venant
share dominates, with the closed-form extremes T_sv(L) = T*(1 -
1/cosh(u)) and T_w(L) = T/cosh(u) at the free tip of the cantilever,
and the twist-ratio identity theta(L)/(T*L/(G*J)) = 1 - tanh(u)/u for
the cantilever and theta(L/2)/(T*L/(4*G*J)) = 1 - tanh(v)/v for the
fork beam quantifying the torsional stiffening the restraint produces
against the free Saint-Venant baseline. Produces the section constants
(J, Cw, omega at the flange tip, sectorial modulus Cw/omega, k), the
twist and twist-rate profiles, the bimoment distribution with its root
or midspan peak, the flange-tip warping normal stress sigma_w, the
T_sv/T_w torque-split profile and the restraint twist ratios that gate
restrained-torsion checks of open-section spars, booms and stiffeners
in the FAR 25.301/25.303 load context. Does NOT do: uniform (free)
Saint-Venant torsion as a result, the free twist rate T/(G*J) of a
section, the Bredt-Batho closed-cell shear flow q = T/(2*A_m), the
closed-section twist rate, the multi-cell shear-flow solve or the
torsional stress margin (torsion-shear-flow, free-warping by claim);
shear-center location or the transverse V*Q/I shear-flow distribution
of open sections under a transverse shear force (shear-center-analysis,
which reports a shear-center offset in millimeters and never applies a
torque); elastic column buckling or torsional-flexural instability
under axial load (buckling-analysis, beam-column-analysis, which are
instability eigenvalues, not torque response). Scope: thin-walled open
doubly symmetric I-section with the shear center at the centroid,
principal sectorial coordinates with the web as the zero line, uniform
section and span, linear elastic isotropic material, small twist,
single point torque per case, no distributed torque, no axial load
interaction, no closed cells and no channel, Z, angle or hat sections
(their shear center sits off the web line and their sectorial
coordinates need the shear-center-offset integration; a stated
extension, not this contract). SI units (metres, newtons, pascals).
Deterministic, pure stdlib.

## Model (implement exactly)

Pure stdlib, math only. All functions take plain SI floats; the
I-section travels as the positional dims (d, b, t_f, t_w) in that
order with d the overall depth, b the flange breadth, t_f the flange
thickness and t_w the web thickness. No module constants beyond math.

Defining relations (pin these exactly; every function below derives
from them):
- Open-section Saint-Venant constant: J = (2*b*t_f**3 + h_w*t_w**3)/3
  with h_w = d - 2*t_f the web depth, the sum b_i*t_i**3/3 over the two
  flanges and the web.
- Warping constant: h = d - t_f, I_y = 2*(b**3)*t_f/12 (flange pair
  about the web plane), Cw = I_y*h**2/4. The identity
  Cw = t_f*h**2*b**3/24 from the direct sectorial integral over the
  flanges of omega**2 dA holds to roundoff (anchor residual
  1.32348898008e-23 m^6); the web contributes nothing because its
  sectorial coordinate is zero. The AISC-style full-section minor
  inertia would add the web's own t_w**3*h_w/12 term, below 0.1% here
  and outside the thin-walled sectorial model.
- Sectorial coordinate: omega(s) = integral of rho ds from the web
  mid-line, rho = h/2 the lever arm of the flange mid-line about the
  shear center at the centroid; omega_max at the flange tip =
  (h/2)*(b/2) = h*b/4, linear along each flange, zero on the web. The
  sectorial modulus W_w = Cw/omega_max = 1.0875e-05 m^4 for the anchor
  section.
- Non-uniform torsion ODE: E*Cw*theta'''' - G*J*theta'' = 0 (homogeneous
  torque-free span), decay parameter k = sqrt(G*J/(E*Cw)) (1/m),
  dimensionless u = k*L and v = k*L/2. Bimoment B(z) = -E*Cw*theta''(z)
  in N m^2; warping normal stress sigma_w = B*omega/Cw, at the flange
  tip B*omega_tip/Cw (equivalently E*omega_tip*theta'' in magnitude).
  Torque partition: T_sv(z) = G*J*theta'(z) and T_w(z) = -E*Cw*theta'''
  (z), the z-derivative of the bimoment, with T_sv + T_w equal to the
  torque carried at every station.
- Fixed-end cantilever (root z = 0 built in, torque T at the free tip
  z = L): theta(z) = (T/(G*J*k))*(k*z - sinh(k*z) + tanh(u)*(cosh(k*z)
  - 1)). The four boundary conditions hold identically: theta(0) = 0,
  theta'(0) = 0 (root prevents twist and warping), theta''(L) = 0 (tip
  warps freely), G*J*theta'(L) - E*Cw*theta'''(L) = T (applied tip
  torque). Closed-form consequences: theta(L) = (T*L/(G*J))*(1 -
  tanh(u)/u), |B(0)| = T*tanh(u)/k, T_sv(L) = T*(1 - 1/cosh(u)),
  T_w(L) = T/cosh(u), T_sv(0) = 0 and T_w(0) = T: the restraint sheds
  the full torque as warping at the built-in root and the torque
  returns to pure Saint-Venant shear at the free tip. Warping
  interpretation: the bimoment is the flange counter-bending couple
  B = M_f*h and sigma_w at the flange tip is the flange bending stress
  M_f*(b/2)/I_fl with I_fl = b**3*t_f/12 per flange, which equals
  B*omega_tip/Cw by construction.
- Fork-supported central torque (fork ends z = 0 and z = L hold theta
  and theta'' at zero; torque T applied at midspan through a rigid
  collar): half-beam x in [0, L/2], theta(x) = (T/(2*G*J))*(x -
  sinh(k*x)/(k*cosh(v))), full span theta(z) = theta(min(z, L - z)).
  Closed-form consequences: theta(L/2) = (T*L/(4*G*J))*(1 - tanh(v)/v),
  B(L/2) = (T/(2*k))*tanh(v), B(0) = 0 (free warping at the fork),
  theta'(L/2) = 0 (symmetry plane, so the collar torque enters each
  half purely as warping torque: T_sv(L/2) = 0, T_w(L/2) = T/2),
  T_sv(0) = (T/2)*(1 - 1/cosh(v)) and T_w(0) = (T/2)/cosh(v) at the
  fork face.
- Free Saint-Venant baselines for the twist ratios only (the leaf
  NEVER returns a free-torsion result as its deliverable): the
  cantilever free twist T*L/(G*J) and the fork free midspan twist
  T*L/(4*G*J); the ratios 1 - tanh(u)/u and 1 - tanh(v)/v quantify the
  stiffening of the restraint.

Functions:
- i_section_saint_venant_j(d, b, t_f, t_w) -> float: J in m^4 by the
  open-section sum above. ValueError: any dim <= 0; d <= 2*t_f.
- i_section_warping_constant(d, b, t_f, t_w) -> float: Cw in m^6 by
  I_y*h**2/4 with h = d - t_f. Identical ValueError set.
- i_section_sectorial_max(d, b, t_f) -> float: omega_tip = (d - t_f)*
  b/4 in m^2. ValueError: any dim <= 0; d <= 2*t_f (arity 3).
- torsion_decay_parameter(e, cw, g, j) -> float: sqrt(g*j/(e*cw)) in
  1/m. ValueError: e, cw, g or j <= 0.
- warping_stress(bimoment, omega_tip, cw) -> float: bimoment*omega_tip/
  cw in Pa, signed (flange-tip stress at the positive-omega tip).
  ValueError: omega_tip or cw <= 0.
- fixed_end_twist(z, torque, length, g, j, e, cw) -> float: theta(z)
  in rad by the hyperbolic closed form. ValueError: length <= 0 or any
  modulus/constant <= 0.
- fixed_end_twist_rate(z, torque, length, g, j, e, cw) -> float:
  theta'(z) in rad/m.
- fixed_end_bimoment(z, torque, length, g, j, e, cw) -> float:
  B(z) = -E*Cw*theta''(z) in N m^2, signed.
- fork_twist(z, torque, length, g, j, e, cw) -> float: theta(z) in rad
  on the full span by the half-beam mirror.
- fork_bimoment(z, torque, length, g, j, e, cw) -> float: B(z) in
  N m^2, signed, symmetric about midspan.
- torque_components(z, torque, length, g, j, e, cw) -> dict with keys
  "T_sv" and "T_w" (N m) for the torque-carried convention of the
  caller's case: fixed-end carries the full torque, fork each half
  carries torque/2.
- fixed_end_response(torque, length, g, j, e, cw) -> dict with keys
  "twist_tip" (rad), "twist_rate_tip" (rad/m), "free_twist"
  (torque*length/(g*j), baseline only), "twist_ratio" (twist_tip/
  free_twist), "bimoment_root" (signed N m^2), "bimoment_tip" (N m^2,
  zero to roundoff), "saint_venant_torque_tip", "warping_torque_tip",
  "saint_venant_torque_root", "warping_torque_root" (N m).
- fork_response(torque, length, g, j, e, cw) -> dict with keys
  "twist_mid" (rad), "free_twist" (torque*length/(4*g*j), baseline
  only), "twist_ratio", "bimoment_mid" (N m^2), "bimoment_fork"
  (N m^2, zero to roundoff), "saint_venant_torque_fork",
  "warping_torque_fork", "saint_venant_torque_mid",
  "warping_torque_mid" (N m, per half at the collar).
  ValueErrors as above plus torque == 0 raises in the response
  functions (the twist ratios are undefined at zero torque).

Identities to test (closed form, deterministic):
- Section constants of the anchor I-beam (d = 0.3, b = 0.15,
  t_f = 0.01, t_w = 0.006): J = 1.2016e-07 m^4, I_y = 5.625e-06 m^4,
  Cw = 1.18265625e-07 m^6, omega_tip = 0.010875 m^2, W_w =
  1.0875e-05 m^4; |Cw - t_f*h**2*b**3/24| = 1.32348898008e-23 m^6.
- k**2 = G*J/(E*Cw) exactly by construction; the ODE residual
  |E*Cw*theta'''' - G*J*theta''| over 501 stations is at machine
  precision (anchor: 1.137e-13 absolute, 3.806e-16 relative to the
  largest term).
- Torque partition: T_sv(z) + T_w(z) = T at every one of 501 stations
  for the cantilever (anchor max residual 1.137e-13 N m) and T/2 per
  half-beam for the fork case (anchor residuals at the fork face and
  the midspan face both 5.0e+02 N m exactly against T/2 = 500).
- Twist ratios: 1 - tanh(u)/u = 0.49185453792 for the cantilever at
  u = 1.87803988331 and 1 - tanh(v)/v = 0.217512206405 for the fork
  beam at v = 0.939019941654 (anchor values, real outputs).
- Boundary conditions: |theta(0)| = 0.0, |theta'(0)| = 0.0,
  |theta''(L)| = 4.284e-17 1/m^2 and |G*J*theta'(L) -
  E*Cw*theta'''(L) - T| = 0.0 for the cantilever; fork theta(0) = 0,
  B(0) = 0 and theta'(L/2) = 0 exactly (anchor).
- Determinism: two identical runs produce identical bits (anchor sha256
  ed1e3ddfb7d48ef1aa047bd61cb768e2ecb9e700153926bd874964f1b0db0222 for
  both runs); no imports beyond math; no RNG.

## Worked example

I-beam d = 0.3 m, b = 0.15 m, t_f = 0.01 m, t_w = 0.006 m (a
spar-like open section), aluminium E = 70 GPa, G = 27 GPa, span
L = 3 m. All values below are REAL outputs of the prep anchor
/tmp/w44spec/anchor_warp.py (stdlib math, exit 0).

- Section constants:
  - h = d - t_f = 0.29 m (flange mid-line spacing), h_w = d - 2*t_f =
    0.28 m.
  - J = (2*b*t_f**3 + h_w*t_w**3)/3 = 1.2016e-07 m^4; G*J = 3244.32
    N m^2.
  - I_y = 2*(b**3)*t_f/12 = 5.625e-06 m^4; Cw = I_y*h**2/4 =
    1.18265625e-07 m^6; E*Cw = 8278.59375 N m^4. The direct sectorial
    integral t_f*h**2*b**3/24 gives 1.18265625e-07 m^6, residual
    1.32348898008e-23 m^6: the closed form is exact for the
    thin-walled model.
  - omega_tip = h*b/4 = 0.010875 m^2 at the flange tip; sectorial
    modulus W_w = Cw/omega_tip = 1.0875e-05 m^4.
  - k = sqrt(G*J/(E*Cw)) = 0.626013294436 1/m; the warping decay
    length 1/k = 1.59741016507 m is more than half the span, so the
    restraint reaches the whole beam (u = k*L = 1.87803988331, a
    strongly restrained regime, not a local end effect).
- Fixed-end cantilever, torque T = 500 N m at the free tip:
  - Restrained tip twist theta(L) = 0.227407224589 rad against the
    free Saint-Venant baseline T*L/(G*J) = 0.462346500962 rad: the
    built-in root cuts the twist to 49.2% of the free value
    (twist ratio 1 - tanh(u)/u = 0.49185453792). This is the
    torsional stiffening of warping restraint.
  - Twist rate peaks at the tip: theta'(L) = 0.108066620404 rad/m
    (theta'(0) = 0 at the built-in root, where warping is blocked);
    Saint-Venant surface shear there tau = G*t*theta' = 29177987.509
    Pa on the flange (t = t_f) and 17506792.5054 Pa on the web
    (t = t_w), the open-section linear-across-thickness shear.
  - Bimoment at the root B(0) = -762.21819312 N m^2 (signed; the
    magnitude equals T*tanh(u)/k = 762.21819312), and the tip
    bimoment B(L) = 3.54696309006e-13 N m^2, zero to roundoff: the
    tip warps freely.
  - Warping normal stress at the flange tip at the root sigma_w =
    B(0)*omega_tip/Cw = -70089029.2524 Pa (-70.09 MPa, compression at
    the positive-omega tip; the two tips of each flange pair carry
    equal and opposite sigma_w). The same number follows from
    sigma_w = E*omega_tip*|theta''(0)|, the flange-bending picture:
    the bimoment is the flange couple B = M_f*h and the tip stress is
    the flange bending stress.
  - Torque split along the span (T = 500 N m carried everywhere):
    at the root T_sv = 0 and T_w = 500 N m (all warping torque: the
    root blocks warping, so the torque arrives as differential flange
    bending); at the tip T_sv(L) = T*(1 - 1/cosh(u)) = 350.602697909
    N m (70.1%) and T_w(L) = T/cosh(u) = 149.397302091 N m (29.9%).
    Span table (real anchor rows; theta rad, theta' rad/m, B N m^2,
    sigma_w Pa, T_sv N m, T_w N m):
    z = 0.000:  theta = 0.000000e+00,  rate = 0.000000e+00,
      B = -7.622182e+02, sigma_w = -7.008903e+07, T_sv = 0.000000e+00,
      T_w = 5.000000e+02
    z = 0.750:  theta = 2.208046e-02,  rate = 5.431743e-02,
      B = -4.588543e+02, sigma_w = -4.219350e+07, T_sv = 1.762231e+02,
      T_w = 3.237769e+02
    z = 1.500:  theta = 7.591534e-02,  rate = 8.622829e-02,
      B = -2.585118e+02, sigma_w = -2.377120e+07, T_sv = 2.797522e+02,
      T_w = 2.202478e+02
    z = 2.250:  theta = 1.476402e-01,  rate = 1.028972e-01,
      B = -1.162102e+02, sigma_w = -1.068600e+07, T_sv = 3.338314e+02,
      T_w = 1.661686e+02
    z = 3.000:  theta = 2.274072e-01,  rate = 1.080666e-01,
      B = 3.546963e-13, sigma_w = 3.261575e-08, T_sv = 3.506027e+02,
      T_w = 1.493973e+02
    The Saint-Venant share climbs monotonically from 0% at the root
    to 70.1% at the tip while the bimoment magnitude decays
    hyperbolically from the root peak; the warping torque is the
    z-derivative of the bimoment.
- Fork-supported beam, torque T = 1000 N m at midspan through a rigid
  collar (both forks hold theta = 0 and let the section warp):
  - Restrained midspan twist theta(L/2) = 0.0502830037738 rad against
    the free baseline T*L/(4*G*J) = 0.231173250481 rad: the collar
    restraint cuts the midspan twist to 21.8% of the free value
    (twist ratio 1 - tanh(v)/v = 0.217512206405), far stronger than
    the cantilever case because the collar blocks warping at the very
    section of maximum twist.
  - The bimoment vanishes at the forks (B(0) = 0 N m^2, warping
    free) and peaks at the collar: B(L/2) = (T/(2*k))*tanh(v) =
    586.865845196 N m^2, with sigma_w = 53964675.4204 Pa (53.96 MPa)
    at the flange tip there.
  - Torque split (each half carries T/2 = 500 N m): at the fork face
    T_sv = (T/2)*(1 - 1/cosh(v)) = 160.842723176 N m (32.2%) and
    T_w = (T/2)/cosh(v) = 339.157276824 N m (67.8%); at the collar
    T_sv = 0 and T_w = 500 N m per half: the applied torque enters
    the beam entirely as warping torque at the midspan collar.
    Span table (real anchor rows):
    z = 0.000:  theta = 0.000000e+00,  B = 0.000000e+00,
      sigma_w = 0.000000e+00,  T_sv = 1.608427e+02, T_w = 3.391573e+02
    z = 0.750:  theta = 3.427006e-02,  B = 2.638170e+02,
      sigma_w = 2.425903e+07,  T_sv = 1.227691e+02, T_w = 3.772309e+02
    z = 1.500:  theta = 5.028300e-02,  B = 5.868658e+02,
      sigma_w = 5.396468e+07,  T_sv = 0.000000e+00, T_w = 5.000000e+02
    z = 2.250:  theta = 3.427006e-02,  B = 2.638170e+02,
      sigma_w = 2.425903e+07,  T_sv = 1.227691e+02, T_w = 3.772309e+02
    z = 3.000:  theta = 0.000000e+00,  B = 0.000000e+00,
      sigma_w = 0.000000e+00,  T_sv = 1.608427e+02, T_w = 3.391573e+02
    The profile is symmetric about midspan: theta and B mirror, the
    Saint-Venant torque changes sign sense across the collar as each
    half twists toward its fork.
- Residual and identity checks (real anchor runs):
  - Cantilever ODE residual max |E*Cw*theta'''' - G*J*theta''| over
    501 stations = 1.137e-13 (3.806e-16 relative to the largest
    term); torque partition residual max |T_sv + T_w - T| =
    1.137e-13 N m.
  - Cantilever boundary residuals: |theta(0)| = 0.0 rad, |theta'(0)| =
    0.0 rad/m, |theta''(L)| = 4.284e-17 1/m^2, |G*J*theta'(L) -
    E*Cw*theta'''(L) - T| = 0.0 N m.
  - Fork case: torque at the fork section G*J*theta'(0) -
    E*Cw*theta'''(0) = 5.000000e+02 N m against T/2 = 500, torque at
    the midspan face of the half-beam 5.000000e+02 N m, symmetry
    |theta'(L/2)| = 0.0 rad/m and |B(0)| = 0.0 N m^2; the mirror
    check |theta(L/2) - theta(L/2 + dz)| = 1.274e-06 rad over one
    dz = 0.006 m step equals theta''(L/2)*dz**2/2, the second-order
    remainder of the symmetry.
  - Determinism: sha256 of the canonical dump is
    ed1e3ddfb7d48ef1aa047bd61cb768e2ecb9e700153926bd874964f1b0db0222
    on both runs, identical.
Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w44spec/anchor_warp.py
(stdlib math, exit 0).

## Validation list (contract test must include)

- i_section_saint_venant_j(0.3, 0.15, 0.01, 0.006) = 1.2016e-07 within
  1e-9 relative; equals (2*b*t_f**3 + (d - 2*t_f)*t_w**3)/3 by
  construction; the per-rectangle sum identity (1/3)*sum(b_i*t_i**3)
  over flange, flange, web reproduces it.
- i_section_warping_constant(0.3, 0.15, 0.01, 0.006) = 1.18265625e-07
  within 1e-9 relative; |Cw - t_f*h**2*b**3/24| no greater than 1e-20
  (anchor 1.32348898008e-23); i_section_sectorial_max(0.3, 0.15,
  0.01) = 0.010875 within 1e-9 relative and Cw/omega_tip =
  1.0875e-05 m^4.
- torsion_decay_parameter(70e9, 1.18265625e-07, 27e9, 1.2016e-07) =
  0.626013294436 within 1e-6 relative; k**2*E*Cw = G*J within 1e-9
  relative.
- warping_stress(-762.21819312020125, 0.010875, 1.18265625e-07) =
  -70089029.2524 within 1e-6 relative; warping_stress(B, omega, Cw)
  is linear in B (doubling B doubles the stress).
- fixed_end_response(500.0, 3.0, 27e9, 1.2016e-07, 70e9,
  1.18265625e-07): twist_tip 0.227407224589 within 1e-6 relative;
  twist_rate_tip 0.108066620404 within 1e-6 relative; free_twist
  0.462346500962 within 1e-6 relative; twist_ratio 0.49185453792
  within 1e-6 relative and equal to 1 - tanh(u)/u with u = k*L;
  bimoment_root -762.21819312 within 1e-6 relative and equal to
  -T*tanh(u)/k; bimoment_tip magnitude below 1e-9 (anchor 3.5e-13);
  saint_venant_torque_tip 350.602697909 within 1e-6 relative equal to
  T*(1 - 1/cosh(u)); warping_torque_tip 149.397302091 within 1e-6
  equal to T/cosh(u); saint_venant_torque_root 0.0;
  warping_torque_root 500.0; tip components sum to 500.0 within 1e-6
  N m.
- fixed_end_twist along the span reproduces the five anchor table rows
  of the worked example within 1e-5 relative (theta, rate, B and
  sigma_w = B*omega_tip/Cw), e.g. fixed_end_twist(1.5, 500.0, 3.0,
  27e9, 1.2016e-07, 70e9, 1.18265625e-07) = 7.591534e-02 and
  fixed_end_bimoment(0.0, ...) = -7.622182e+02; torque_components sums
  to the carried torque at every sampled station within 1e-9 relative.
- fork_response(1000.0, 3.0, 27e9, 1.2016e-07, 70e9,
  1.18265625e-07): twist_mid 0.0502830037738 within 1e-6 relative;
  free_twist 0.231173250481; twist_ratio 0.217512206405 within 1e-6
  equal to 1 - tanh(v)/v; bimoment_mid 586.865845196 within 1e-6
  equal to (T/(2*k))*tanh(v); bimoment_fork 0.0;
  saint_venant_torque_fork 160.842723176; warping_torque_fork
  339.157276824 (sum 500.0 = T/2 within 1e-6 N m);
  saint_venant_torque_mid 0.0; warping_torque_mid 500.0.
- fork_twist symmetry: fork_twist(z) == fork_twist(L - z) within 1e-9
  relative; fork_bimoment(z) == fork_bimoment(L - z); the five anchor
  table rows match within 1e-5 relative.
- Boundary conditions: for the cantilever, |fixed_end_twist(0, ...)|
  and |fixed_end_twist_rate(0, ...)| below 1e-9 and
  |fixed_end_bimoment(L, ...)| below 1e-6 (anchor 4.3e-17 rad/m and
  3.5e-13 N m^2 scales); for the fork, |fork_twist(0, ...)| and
  |fork_bimoment(0, ...)| below 1e-9.
- ODE residual: sampling 501 stations, max |E*Cw*theta'''' - G*J*theta''|
  below 1e-9 absolute for both cases (anchor 1.137e-13 and 0.0), with
  the fourth derivative evaluated from the closed form.
- Section stress identity: sigma_w at the root equals
  E*omega_tip*|theta''(0)| within 1e-6 relative, and the tip warping
  stress magnitude is |sigma_w| = |B|*omega_tip/Cw (anchor
  -70089029.2524 Pa at the root, 53964675.4204 Pa at the fork
  midspan).
- ValueErrors across the module: unknown arity (i_section_warping_
  constant called with 2 dims); b <= 0; t_f = 0; t_w <= 0; d <= 2*t_f
  (0.25 m depth against 0.26 m of flange pair); e = 0; g <= 0;
  cw = 0; j <= 0; length = 0; torque = 0 in the response functions;
  omega_tip <= 0 and cw <= 0 in warping_stress (11 anchor cases, each
  raises ValueError).
- Determinism: two identical runs return identical bits; no imports
  beyond math; no RNG. Contract test file named test_restrained_
  warping.py (underscores), unittest, offline in under 20 seconds.

## Corpus fragment (eval/hit1-wave44-restrained-warping.yaml)

Query 1 (copy verbatim):
  "compute the restrained torsion response of a thin-walled open
  I-beam built in at one end under a tip torque: the warping constant
  Cw = I_y*h^2/4 of the doubly symmetric I-section, the bimoment
  B = -E*Cw*theta'' with the hyperbolic closed-form twist of the
  non-uniform torsion equation, the warping normal stress at the
  flange tip and the Saint-Venant versus warping torque split along
  the span"
  intent: "structures; restrained (non-uniform) torsion of a
  thin-walled open I-section: warping constant, decay parameter of the
  non-uniform torsion ODE, hyperbolic twist solution of the built-in
  cantilever under a tip torque, bimoment and flange-tip warping
  normal stress, and the T_sv/T_w torque split along the span"
  expected_skill: "structures/fem/restrained-warping"
Query 2 (copy verbatim):
  "find the twist, bimoment and warping normal stress of an I-beam
  with fork supports (twist fixed, warping free at the ends) carrying
  a point torque at midspan, and report how the warping restraint
  stiffens the beam against the free Saint-Venant twist"
  intent: "structures; non-uniform torsion of a fork-supported beam
  under a midspan torque: half-beam hyperbolic solution, midspan
  bimoment peak, warping normal stress and the restraint twist ratio
  against the free Saint-Venant baseline"
  expected_skill: "structures/fem/restrained-warping"
Task ids: w44-restrained-warping-1 and -2. Prep grep and probe: the
distinctive tokens restrained-warping, non-uniform-torsion, bimoment,
warping-constant and torsional-flexure each match 0 existing
eval/hit1-corpus.yaml tasks (real greps); the only "warping" matches
in the corpus sit inside the frequency-prewarping words of the wave-1
Butterworth filter task and a digital-control task (numerics and
gnc-autonomy, filter design and z-domain emulation), and the only
"restrained" matches belong to the wave-26 thermal-buckling
restrained-temperature tasks, so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the restrained
(non-uniform) torsion response of a thin-walled open I-beam section:"
and include the outputs in the Claim. First tag: restrained-warping.
Additional tags ONLY: non-uniform-torsion, bimoment, warping-constant,
warping-normal-stress, torsional-flexure. NEVER single generic words
(warping, torsion, twist, torque, stress, section, beam, I-beam,
flange, web, stiffness, analysis) and NEVER the free-torsion or
transverse-shear sibling tokens: torsion-shear-flow, bredt-batho,
saint-venant-torsion, angle-of-twist, multi-cell-section,
closed-section-shear-flow, torsional-stress-margin (torsion-shear-flow,
which owns free Saint-Venant and Bredt-Batho torsion and must not be
steered to by this leaf's description), shear-center-analysis,
shear-center-location, transverse-shear-flow, thin-walled-open-section
(shear-center-analysis, which owns the V*Q/I transverse shear flow),
nor prewarping, frequency-prewarping, tustin-bilinear-emulation
(digital-filter-design, digital-control-design, gnc-autonomy),
restrained-thermal-expansion, critical-temperature-rise,
thermal-buckling (thermal-stress-analysis, thermal-buckling),
buckling-load, euler-buckling (buckling-analysis) or portal-frame,
member-end-actions (beam-frame-analysis). 50-150 words, <=1000 chars,
no em dash, no content-policy sweep term, action verb present.
Recommended wording (outputs in Claim order): "Use when you must
compute the restrained (non-uniform) torsion response of a thin-walled
open I-beam section: the warping constant Cw = I_y*h^2/4 of the
doubly symmetric I-section, the sectorial coordinate at the flange
tip, the decay parameter k = sqrt(G*J/(E*Cw)) of the non-uniform
torsion equation E*Cw*theta'''' - G*J*theta'' = 0, the hyperbolic
closed-form twist and twist rate, the bimoment B = -E*Cw*theta'' and
the warping normal stress sigma_w = B*omega/Cw at the flange tip for a
built-in cantilever under a tip torque and a fork-supported beam under
a midspan torque, and the shear-torque versus warping-torque split
along the span. Produces the section constants, the twist and
twist-rate profiles, the bimoment with its root or midspan peak, the
flange-tip warping stress and the torque-partition table that gate
restrained-torsion checks of open-section spars and stiffeners.
Trigger: restrained warping, non-uniform torsion, warping constant,
bimoment, torsional flexure, warping normal stress." The sibling
triggers "Saint-Venant torsion", "Bredt-Batho", "angle of twist",
"shear flow", "shear center", "transverse shear" and "prewarping"
must not appear.

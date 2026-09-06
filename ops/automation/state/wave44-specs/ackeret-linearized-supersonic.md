# Wave-44 leaf spec: ackeret-linearized-supersonic (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/ackeret-linearized-supersonic/
- Pack: high-speed (18 leaves present at prep: aerodynamic-heating,
  bow-shock-standoff, compressible-couette-flow, fanno-flow,
  flat-plate-skin-friction-heating, hypersonic-flow,
  isentropic-flow-relations, normal-shock, oblique-shock, prandtl-meyer,
  rayleigh-flow, regular-shock-reflection, shock-expansion-airfoil,
  shock-tube, supercritical-airfoil, swept-wing-aerodynamics,
  transonic-similarity, wave-drag-area-rule; ackeret-linearized-supersonic
  and hypersonic-piston-theory are the two wave-44 high-speed additions).
  Claim fences (quoted from the sibling frontmatter at prep; none owns the
  linearized thin-section coefficient producer):
  - shock-expansion-airfoil (this pack) is the exact-march sibling: its
    description reads "Use when you must compute the supersonic
    shock-expansion solution for a diamond (double-wedge) airfoil section:
    patch oblique-shock and Prandtl-Meyer relations over the four planar
    surfaces at a freestream Mach number and angle of attack, then integrate
    the panel pressures into the section lift, wave drag, and leading-edge
    moment coefficients". Its Pitfalls fence the march to the DIAMOND
    geometry: "the panel march is only defined for the diamond geometry, not
    for cambered or rounded sections", and its linear-theory handover is
    quoted: "use the linear value as a 10% cross-check, not as the exact
    answer". Its Verification pins the same flat-plate anchor this leaf
    produces: "Flat-plate limit: eps = 0.1 deg, M = 2, alpha = 3 deg gives
    cl = 0.1210, within 5% of the linear supersonic value 0.1209", and its
    Worked example quotes "cl = 4*alpha/sqrt(M^2 - 1) = 0.121 (the exact
    value sits 1.5% above it)". The regime the sibling self-fences out
    (curved and rounded thin sections, camber, the linearized pressure law
    itself) is exactly this leaf's claim; the exact diamond march stays with
    the sibling.
  - isentropic-flow-relations (this pack) is the area-Mach owner: its
    description reads "recover the Mach number that produces a given area
    ratio from the area-Mach relation on the subsonic low branch or the
    supersonic high branch, and compute the choked mass flow a passage
    passes at its sonic throat from total pressure, total temperature and
    throat area". It is a 1-D streamtube/duct relation set with no surface
    pressure law and no section coefficients; its supersonic high branch is
    a duct Mach from an area ratio, not a surface pressure coefficient.
  - hypersonic-piston-theory (this pack, same-wave sibling; its SKILL.md is
    in flight at prep, so the fence is quoted from the wave-44 leaf plan,
    entry 6: "Lighthill piston-theory surface pressure p/p_inf = (1 +
    ((gamma-1)/2)*v/a_inf)^(2gamma/(gamma-1)) with the linearized limit,
    shock vs expansion side split, unsteady/small-perturbation hypersonic
    surfaces"). It is a M >> 1 surface PRESSURE LAW for unsteady hypersonic
    surfaces, not a steady section coefficient set; this leaf lives at
    moderate supersonic Mach on thin sections and outputs cl, cd_wave and
    cm_le.
  - supercritical-airfoil (this pack) is the subsonic/transonic
    supercritical section owner; transonic-similarity (this pack) owns the
    near-Mach-1 similarity regime the ackeret formulas diverge away from
    (beta -> 0 as M -> 1); wave-drag-area-rule (this pack) is the
    three-dimensional zero-lift volume wave drag of slender bodies by the
    supersonic area rule, no section pressure coefficients; swept-wing-
    aerodynamics (this pack) adds 3-D sweep effects; thin-airfoil-section-
    theory (aerodynamics/airfoil, subsonic incompressible) owns the Glauert
    camber-line A0/A1/A2 sine series of the M ~ 0 regime; flutter-speed-
    prediction (aerodynamics/aeroelasticity) owns the unsteady oscillatory
    Theodorsen C(k) subsonic thin-airfoil content, no steady supersonic
    section coefficients.
  Whole-tree greps at prep (real runs for this spec): "ackeret" = 0 hits in
  skills/ and 0 corpus tasks; "biconvex" = 0 and 0; "linearized supersonic"
  = 0 and 0; "linear-supersonic" = 0 and 0 (grep exit 1 each). Corpus
  phrase neighbors: "thin airfoil" appears in exactly 2 corpus intents, both
  subsonic Glauert tasks (zero-lift angle and cl from the A0/A1/A2 Fourier
  coefficients of a cambered line), and the supersonic-airfoil queries in
  the corpus are the tasks w24r-shock-expansion-airfoil-1/-2, which route on
  "diamond airfoil", "shock-expansion method" and "double-wedge section"
  tokens, never on ackeret or biconvex. GENUINE AERO gap (fresh probe): no
  leaf produces the linearized (ackeret) supersonic thin-section
  coefficients; shock-expansion-airfoil self-fences curved/rounded sections
  out of its exact march and uses linear theory only as a ~10% validation
  anchor (quoted above), and no other high-speed leaf integrates a surface
  pressure LAW into section coefficients.
- Standards id: naca-tr-824 (reference-only, present in standards-map.yaml,
  matching every high-speed sibling). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Produce the linearized supersonic thin-airfoil section coefficients of
ackeret theory (Liepmann & Roshko ch. 10, Anderson sec 9) for a thin
section at supersonic Mach: evaluate the ackeret parameter
beta = sqrt(M^2 - 1), the ackeret surface pressure coefficient
Cp = +-2*theta/beta on a surface deflected by theta from the freestream
(positive theta compresses, sign positive on the windward side), the
section lift coefficient cl = 4*alpha/beta of the thin closed section at
angle of attack alpha (radians; lift is independent of thickness and camber
in the linear theory), the supersonic lift-curve slope 4/beta, the leading
edge moment coefficient cm_le (nose-up positive), and the wave drag
coefficient cd_wave of the flat plate, of the thin biconvex circular-arc
section of thickness ratio tau and of a cambered thin plate of camber ratio
h/c, each by the linearized pressure integral over the surface slopes
cd = alpha*cl + (2/beta) integral [phi_u^2 + phi_l^2] dx over the chord,
with the closed forms cd = 4 alpha^2/beta for the flat plate, cd = (4
alpha^2 + (16/3) tau^2)/beta for the biconvex section and cd = (4 alpha^2 +
(64/3) (h/c)^2)/beta for the circular-arc cambered plate. Produces the
ackeret Cp values, cl, the lift-curve slope, cd_wave and cm_le that gate
thin supersonic airfoil wave-drag estimates, section design cross-checks
and gas-dynamics coursework. Does NOT do: the exact shock-expansion march
over a diamond or double-wedge section with oblique-shock and Prandtl-Meyer
turns (shock-expansion-airfoil, which self-fences curved and rounded
sections out of its march and quotes this leaf's linear values only as a 10%
cross-check); single-turn theta-beta-M, oblique-shock and Prandtl-Meyer
relations (oblique-shock, prandtl-meyer); area-Mach inversion, isentropic
total-to-static ratios or choked mass flow at a sonic throat
(isentropic-flow-relations); the hypersonic piston-theory surface pressure
law at M >> 1 (hypersonic-piston-theory, same wave); transonic similarity
near M = 1 (transonic-similarity), supercritical sections
(supercritical-airfoil), the 3-D volume wave drag of the supersonic area
rule (wave-drag-area-rule), subsonic Glauert thin-airfoil camber theory
(thin-airfoil-section-theory) or unsteady oscillatory flutter content
(flutter-speed-prediction). Scope: thin sections, small surface slopes and
small angles of attack (linear theory, |alpha| and slopes of a few degrees;
theta, tau and h/c small), steady flow, freestream Mach strictly above 1
(the linearized coefficients diverge as M -> 1, so the module raises at
M <= 1), perfect gas. Deterministic, pure stdlib. The section coefficients
are gamma-free; the gamma = 1.4 default appears only in the optional
pressure reconstruction p/p_inf = 1 + (gamma/2) M^2 Cp.

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG. Module constants: GAMMA =
1.4 (air default, honored only by surface_pressure_ratio), SIMPSON_PANELS =
2000 (fixed panel count of the deterministic composite Simpson quadrature;
identical inputs give identical bits). Angle convention, pinned: ALL angles
are in RADIANS (the ackeret formulas are radian identities; alpha = 3 deg =
0.052359877560 rad). Positive alpha means the freestream is inclined up
relative to the chord, so the lower surface is windward and cl is positive.
Surface slopes phi = dy/dx are taken relative to the chord. The freestream
drag direction sits at +alpha to the chord, so the wave drag carries the
alpha*cl term (sin(alpha) -> alpha, cos(alpha) -> 1 at linear order).

Defining relations (pin these exactly; every function below derives from
them), xhat = x/c in [0, 1]:
- Ackeret parameter: beta(M) = sqrt(M^2 - 1), the divisor of every linear
  supersonic coefficient; beta -> 0 at M -> 1 (the coefficients diverge,
  hence the M <= 1 guard) and beta -> M at large M.
- Linearized surface pressure law: cp_u(xhat) = 2 (phi_u(xhat) -
  alpha)/beta and cp_l(xhat) = 2 (alpha - phi_l(xhat))/beta on the upper
  and lower surfaces; equivalently Cp = +-2*theta/beta with theta the local
  flow deflection by the surface, positive for a compression turn. A flat
  plate at positive alpha carries cp_l = +2 alpha/beta (compression,
  windward) and cp_u = -2 alpha/beta (suction).
- Lift integral: cl = (1/c) integral_0^c (cp_l - cp_u) dx = 4 alpha/beta
  for every thin CLOSED section: the thickness and camber terms integrate to
  zero because integral (phi_u + phi_l) dx = 0 around a closed section.
  Lift-curve slope: cl_alpha = 4/beta, the ackeret slope (2.3094 per radian
  at M = 2, falling to 1.4142 per radian at M = 3 and 4.0 at M = sqrt(2)
  where beta = 1).
- Leading-edge moment (nose-up positive): cm_le = -(1/c^2) integral_0^c x
  (cp_l - cp_u) dx = -2 alpha/beta - (2/(beta c^2)) integral (y_u + y_l) dx.
  Flat and symmetric sections (y_u + y_l = 0) sit at cm_le = -2 alpha/beta
  with the center of pressure at mid-chord (x_cp/c = 0.5, the supersonic
  linear-theory position); camber adds the nose-down couple -(4/(beta c^2))
  integral eta dx = -(8/3)(h/c)/beta for the circular-arc plate.
- Wave drag by the linearized pressure resolution: cd = alpha*cl +
  (2/(beta c)) integral_0^c [phi_u^2 + phi_l^2 - alpha (phi_u + phi_l)] dx;
  the alpha (phi_u + phi_l) cross term integrates to zero over a closed
  section, so thickness and camber drags are additive with the flat-plate
  alpha drag.
- Canonical geometry rows (chord c, total thickness tau*c and camber h*c at
  mid-chord):
  - flat plate: y_u = y_l = 0, phi_u = phi_l = 0.
  - biconvex (parabolic-arc, symmetric): y_u = 2 tau c xhat (1 - xhat),
    phi_u = 2 tau (1 - 2 xhat), y_l = -y_u, phi_l = -phi_u; the surface
    slopes run from +2 tau at the leading edge to -2 tau at the trailing
    edge. Closed forms: cl = 4 alpha/beta, cd_wave = (4 alpha^2 + (16/3)
    tau^2)/beta, cm_le = -2 alpha/beta.
  - cambered plate (circular-arc mean line, zero thickness): y_u = y_l =
    eta(xhat) = 4 (h/c) c xhat (1 - xhat), phi_u = phi_l = eta' = 4 (h/c)
    (1 - 2 xhat). Closed forms: cl = 4 alpha/beta, cd_wave = (4 alpha^2 +
    (64/3) (h/c)^2)/beta, cm_le = -2 alpha/beta - (8/3)(h/c)/beta.
- Pressure reconstruction (optional output): p/p_inf = 1 + (gamma/2) M^2
  Cp on the surface (the only gamma-dependent relation).

Functions (implement with exactly these signatures):
- ackeret_parameter(mach) -> float: beta = sqrt(mach^2 - 1). ValueError if
  mach <= 1.0 or not finite.
- cp_linear(theta_rad, mach) -> float: Cp = 2*theta/beta by the linear law,
  theta signed positive for a compression deflection. ValueError if mach <=
  1.0 or not finite.
- lift_coefficient(alpha_rad, mach) -> float: cl = 4*alpha/beta.
  ValueError as cp_linear.
- lift_curve_slope(mach) -> float: cl_alpha = 4/beta per radian.
  ValueError as cp_linear.
- flat_plate(alpha_rad, mach) -> dict with keys "cl", "cd_wave", "cm_le",
  "x_cp_over_c": cl = 4 alpha/beta, cd_wave = 4 alpha^2/beta, cm_le =
  -2 alpha/beta, x_cp_over_c = 0.5. ValueError as cp_linear.
- biconvex_section(alpha_rad, thickness_ratio, mach) -> dict with keys
  "cl", "cd_wave", "cm_le": cl = 4 alpha/beta, cd_wave = (4 alpha^2 +
  (16/3) tau^2)/beta, cm_le = -2 alpha/beta. ValueError if mach <= 1.0,
  not finite, or thickness_ratio <= 0.0.
- cambered_plate(alpha_rad, camber_ratio, mach) -> dict with keys "cl",
  "cd_wave", "cm_le": cl = 4 alpha/beta, cd_wave = (4 alpha^2 + (64/3)
  (h/c)^2)/beta, cm_le = -2 alpha/beta - (8/3)(h/c)/beta. ValueError if
  mach <= 1.0, not finite, or camber_ratio <= 0.0.
- section_coefficients(alpha_rad, mach, slope_upper, slope_lower, chord =
  1.0, panels = SIMPSON_PANELS) -> dict with keys "cl", "cd_wave",
  "cm_le": the general thin section of slope callables phi_u(x) and
  phi_l(x) on x in [0, chord], integrated by composite Simpson over the
  `panels` even intervals with the relations above; closed-form agreement
  with the three canonical families is an identity (anchor residuals below
  1e-12). ValueError if mach <= 1.0, not finite, chord <= 0.0, panels < 2
  or panels odd, or a slope callable returns a non-finite value.
- surface_pressure_ratio(cp, mach, gamma = GAMMA) -> float: p/p_inf = 1 +
  (gamma/2) mach^2 Cp. ValueError if mach <= 1.0 or gamma <= 1.0.

Identities to test (closed form, deterministic; all values REAL anchor
outputs of /tmp/w44spec/anchor_ackeret.py, stdlib math, exit 0):
- ackeret_parameter table: beta(1.5) = 1.118033988750, beta(2.0) =
  1.732050807569, beta(3.0) = 2.828427124746, beta(sqrt(2)) =
  1.000000000000.
- cp_linear table at M = 2: cp(+0.05) = 0.057735026919, cp(-0.05) =
  -0.057735026919, cp(2 deg) = 0.040306652539, cp(-2 deg) =
  -0.040306652539; the flat-plate lower-surface value at alpha = 3 deg is
  cp_l = 0.060459978808 (windward compression) with p/p_inf =
  1.169287940662 at gamma 1.4.
- Lift: cl(alpha = 3 deg = 0.052359877560 rad, M = 2) = 0.120919957616,
  the value the shock-expansion sibling quotes as its linear cross-check
  (0.121 in its worked example, 0.1209 in its flat-plate limit); cl is
  identical for the flat plate, the biconvex tau = 0.06 section and the
  cambered h/c = 0.02 plate at the same alpha and M to below 1e-12
  (thickness and camber independence). lift_curve_slope: 4/beta = 2.3094
  per radian at M = 2, 2.309401076759; 1.414213562373 per radian at M = 3;
  4.000000000000 at M = sqrt(2).
- Flat plate at alpha = 3 deg, M = 2: cl = 0.120919957616, cd_wave =
  0.006331354175, cm_le = -0.060459978808, x_cp_over_c = 0.500000000000.
- Biconvex tau = 0.06 at M = 2: zero-lift cd_wave(alpha = 0) =
  0.011085125168 and cd_wave(alpha = 3 deg) = 0.017416479344 = 0.006331354175
  + 0.011085125168 (drag additive), cm_le = -0.060459978808; at M = 3,
  alpha = 0: cd_wave = 0.006788225099 (the M^-2 fall of the wave drag).
- Cambered plate h/c = 0.02 at M = 2: cd_wave(0) = 0.004926722297,
  cd_wave(3 deg) = 0.011258076472, cm_le = -0.091251993165 = -0.060459978808
  - 0.030792014357 (the camber couple (8/3)(h/c)/beta = 0.030792014357).
- Linearized pressure integral vs closed forms: section_coefficients
  residuals for the three families at the worked point are all below 4.1e-15
  (REAL anchor residuals: flat cl 4.080e-15, cd 2.142e-16, cm 0.0; biconvex
  cd 2.116e-16; cambered cd 1.735e-18), so the engine and the closed forms
  are one theory.
- Zero-lift and symmetry: cl(0) = 0.000000000000 and cm_le(0) =
  -0.000000000000 for the symmetric biconvex at M = 2 (engine anchor),
  while cd_wave(0) stays positive (0.011085125168), the classic zero-lift
  wave drag.
- Sibling cross-validation: the exact-march diamond of eps = 5 deg (10 deg
  included angle, thickness ratio tau = tan(5 deg) = 0.087488663526) at
  M = 2 has the linear zero-lift cd_wave = 4 tau^2/beta = 0.017676770709,
  matching the shock-expansion-airfoil worked-example cd_wave = 0.0177, and
  cl(exact)/cl(linear) = 1.014720832024 at alpha = 3 deg, matching the
  sibling's quoted "1.5% above" handover.
- ValueErrors across the module: ackeret_parameter(1.0) and (-2.0);
  cp_linear(0.1, 1.0) and (0.05, 0.9); lift_coefficient(0.05, 1.0);
  lift_curve_slope(0.9); flat_plate(0.05, 1.0); biconvex_section(0.05,
  0.0, 2.0) and (0.05, -0.1, 2.0); cambered_plate(0.05, 0.0, 2.0);
  section_coefficients with chord 0.0 and with panels 3; surface_pressure_
  ratio(0.1, 1.0) and (0.1, 2.0, gamma = 1.0).
- Determinism: two identical engine runs return identical bits (anchor
  True); no imports beyond math; no RNG; the section coefficients carry no
  gamma dependence (only surface_pressure_ratio honors gamma, default 1.4).

## Worked example

Representative point: M = 2.0, alpha = 3 deg = 0.052359877560 rad, with
the biconvex tau = 0.06 (6% thick) and the cambered plate h/c = 0.02
(2% circular-arc camber), gamma = 1.4 where used. All values below are REAL
outputs of the prep anchor /tmp/w44spec/anchor_ackeret.py (stdlib math,
deterministic Simpson over 2000 panels, exit 0).

- Ackeret parameter and pressure law: beta(2.0) = 1.732050807569. A surface
  deflection of theta = +0.05 rad (2.865 deg, compression) carries Cp =
  0.057735026919, the mirror deflection Cp = -0.057735026919; at the
  worked example's 2 deg local angles Cp = +-0.040306652539. The flat
  plate's windward lower surface at alpha = 3 deg: cp_l = 2 alpha/beta =
  0.060459978808, so p/p_inf = 1 + 0.5 gamma M^2 cp = 1.169287940662 on the
  lower surface and its mirror 0.830712059338 on the suction upper surface.
- Lift and slope: cl = 4 alpha/beta = 0.120919957616 for the flat plate,
  the biconvex and the cambered plate alike (thickness and camber drop out
  of the lift integral); the supersonic lift-curve slope is 4/beta =
  2.309401076759 per radian at M = 2. The exact-march sibling computes
  cl = 0.1227 for its eps = 5 deg diamond at this point, and its own quoted
  linear cross-check is 0.121: the linear value sits 1.47% below the exact
  (cl ratio 1.014720832024), inside the sibling's quoted 10% band.
- Wave drag by the linearized pressure integral: cd = alpha*cl + (2/beta)
  integral (phi_u^2 + phi_l^2) dx over the chord. Flat plate: cd_wave =
  4 alpha^2/beta = 0.006331354175. Biconvex tau = 0.06: zero-lift part
  (16/3) tau^2/beta = 0.011085125168, total cd_wave = 0.017416479344 at
  alpha = 3 deg (the additive thickness drag, 2.75 times the flat plate's
  alpha drag). Cambered plate h/c = 0.02: zero-lift part (64/3)(h/c)^2/beta
  = 0.004926722297, total cd_wave = 0.011258076472. Cross-check on the
  exact sibling: its symmetric diamond (eps = 5 deg, thickness ratio
  tan(5 deg) = 0.087488663526) at M = 2, alpha = 0 carries cd_wave = 0.0177
  by the march, and the linear zero-lift form 4 tau^2/beta gives
  0.017676770709, agreement inside 0.2%.
- Moments: cm_le = -2 alpha/beta = -0.060459978808 (nose-up positive) for
  the flat plate and the symmetric biconvex, with the center of pressure at
  mid-chord, x_cp_over_c = 0.500000000000 (the supersonic linear-theory
  position, versus quarter-chord subsonically). The cambered plate adds the
  nose-down couple (8/3)(h/c)/beta = 0.030792014357, giving cm_le =
  -0.091251993165: camber produces no lift in the linear theory but it does
  pitch the section nose-down.
- Read-off: at M = 2 every ackeret coefficient scales with 1/beta =
  0.577350269190; the lift of a 3 deg thin section is cl ~ 0.121 per radian
  slope 2.309, the zero-lift biconvex wave drag 0.0111 at 6% thickness
  grows quadratically with tau, and the linear-theory answers sit a few
  percent from the exact-march values the sibling reports, exactly the
  cross-check role the sibling's Pitfalls assign.
Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w44spec/anchor_ackeret.py (stdlib math,
deterministic Simpson, exit 0).

## Validation list (contract test must include)

- ackeret_parameter: (1.5) = 1.118033988750 within 1e-6, (2.0) =
  1.732050807569 within 1e-6, (3.0) = 2.828427124746 within 1e-6,
  (sqrt(2)) = 1.000000000000 within 1e-12.
- cp_linear at M = 2: (+0.05) = 0.057735026919 within 1e-8, (-0.05) =
  -0.057735026919 within 1e-8, (2 deg) = 0.040306652539 within 1e-8;
  antisymmetry cp(-theta) = -cp(theta) exactly.
- lift_coefficient(0.052359877560, 2.0) = 0.120919957616 within 1e-6;
  lift_curve_slope: (2.0) = 2.309401076759 within 1e-6, (3.0) =
  1.414213562373 within 1e-6, (sqrt(2)) = 4.000000000000 within 1e-12.
- flat_plate(0.052359877560, 2.0): cl = 0.120919957616, cd_wave =
  0.006331354175, cm_le = -0.060459978808, x_cp_over_c = 0.5, all within
  1e-6; cd_wave = alpha*cl within 1e-12 at linear order.
- biconvex_section(0.052359877560, 0.06, 2.0): cd_wave = 0.017416479344
  within 1e-6 and equals flat cd_wave + (16/3) tau^2/beta = 0.006331354175
  + 0.011085125168 within 1e-12; biconvex_section(0.0, 0.06, 2.0): cl = 0.0
  within 1e-12, cm_le = 0.0 within 1e-12, cd_wave = 0.011085125168 within
  1e-6; biconvex_section(0.0, 0.06, 3.0): cd_wave = 0.006788225099 within
  1e-6 (wave drag falls with Mach).
- cambered_plate(0.052359877560, 0.02, 2.0): cd_wave = 0.011258076472
  within 1e-6, cm_le = -0.091251993165 within 1e-6, and cm_le =
  flat cm_le - 0.030792014357 within 1e-12; cl identical to the flat plate
  within 1e-12 (camber makes no lift in the linear theory).
- Shape independence of cl: flat_plate, biconvex_section and
  cambered_plate cl values at the worked point agree within 1e-12.
- section_coefficients engine at the worked point reproduces every closed
  form within 1e-9 (REAL anchor residuals below 4.1e-15 for all three
  families); engine cl(alpha = 0) for the biconvex is 0.000000000000 within
  1e-12.
- Surface pressure reconstruction: surface_pressure_ratio(0.060459978808,
  2.0) = 1.169287940662 within 1e-9 (gamma 1.4).
- ValueErrors (the 12 anchor cases listed under Identities): mach 1.0, 0.9
  and -2.0 on the mach-bearing functions; thickness_ratio 0.0 and -0.1;
  camber_ratio 0.0; chord 0.0; panels 3 (odd); gamma 1.0.
- Determinism: two identical runs return identical bits; no imports beyond
  math; no RNG; gamma defaults to 1.4 and is honored by
  surface_pressure_ratio only. Contract test file named
  test_ackeret_linearized_supersonic.py (underscores), unittest, offline in
  under 20 seconds.

## Corpus fragment (2 verbatim queries for eval/hit1-wave44-ackeret-
linearized-supersonic.yaml)

Query 1 (copy verbatim):
  "analyze the ackeret linearized-supersonic flow over a thin airfoil
  section at a supersonic mach number: from the freestream mach compute the
  ackeret parameter sqrt(M^2 - 1), the ackeret surface pressure coefficient
  Cp = +-2*theta/sqrt(M^2 - 1) for a surface deflection theta, the section
  lift cl = 4*alpha/sqrt(M^2 - 1) and the supersonic lift curve slope"
  intent: "aerodynamics; ackeret linearized supersonic thin-airfoil section
  coefficients: Cp law, cl and the supersonic lift-curve slope"
  expected_skill: "aerodynamics/high-speed/ackeret-linearized-supersonic"
Query 2 (copy verbatim):
  "compute the ackeret wave drag of the thin biconvex circular-arc section
  and of a cambered thin plate in linear supersonic flow from the
  linearized pressure integral over the surface slopes, with the section
  leading edge moment coefficient cm_le, at mach 2"
  intent: "aerodynamics; ackeret wave-drag and moment coefficients of
  biconvex and cambered thin sections by the linearized pressure integral"
  expected_skill: "aerodynamics/high-speed/ackeret-linearized-supersonic"
Task ids: w44-ackeret-linearized-supersonic-1 and -2. Prep grep and probe:
"ackeret", "biconvex", "linearized supersonic" and "linear-supersonic"
appear in NO existing eval/hit1-corpus.yaml task and in NO skills/ file
(0 hits each, real greps, exit 1); the corpus "supersonic airfoil" queries
are the two shock-expansion tasks w24r-shock-expansion-airfoil-1/-2, which
route on diamond-airfoil, double-wedge and shock-expansion tokens, the two
corpus "thin airfoil" intents are the subsonic Glauert camber-line tasks,
and the ackeret/biconvex tokens above are collision-free. The queries
deliberately carry the ackeret, biconvex and linear-supersonic hyphenated
tokens because the shock-expansion sibling's generic supersonic-airfoil and
wave-drag-coefficient tags are a live steal risk for bare-worded queries.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the section coefficients
of a thin airfoil at supersonic speed by ackeret linearized supersonic
theory:" and include the outputs in the Claim. First tag:
ackeret-linearized-supersonic. Additional tags ONLY: ackeret-theory,
linear-supersonic-thin-airfoil, supersonic-lift-curve-slope,
biconvex-section, cambered-plate-supersonic. NEVER single generic words
(supersonic, mach, airfoil, lift, drag, pressure, section, flow) and NEVER
supersonic-airfoil, diamond-airfoil, double-wedge, shock-expansion,
shock-expansion-airfoil, surface-pressure-integration, wave-drag-
coefficient (shock-expansion-airfoil tags), area-Mach, area-ratio,
mach-from-area-ratio, total-to-static-ratio, choked-mass-flow
(isentropic-flow-relations), thin-airfoil-section-theory or its Glauert
camber-line tokens (subsonic), hypersonic-piston-theory, piston-theory
(hypersonic-piston-theory, the same-wave sibling), supercritical-airfoil,
transonic-similarity, wave-drag-area-rule, swept-wing-aerodynamics,
flutter-speed-prediction, and never the tokens diamond-panel-march,
shock-expansion-exact or sharp-leading-edge-panel. 50-150 words, <=1000
chars, no em dash, action verb present. Recommended wording (outputs in
Claim order): "Use when you must compute the section coefficients of a thin
airfoil at supersonic speed by ackeret linearized supersonic theory:
evaluate the ackeret parameter sqrt(M^2 - 1) and the surface pressure
coefficient Cp = 2*theta/sqrt(M^2 - 1) on a surface deflected by theta,
the section lift cl = 4*alpha/sqrt(M^2 - 1) of the thin closed section and
the supersonic lift curve slope 4/sqrt(M^2 - 1), and the wave drag
coefficient of the flat plate, the thin biconvex circular-arc section and
a cambered thin plate from the linearized pressure integral over the
surface slopes, with the section leading edge moment coefficient cm_le.
Produces the ackeret Cp, cl, cd_wave and cm_le values that gate thin
supersonic airfoil wave drag estimates, section design cross-checks and
gas dynamics coursework. Trigger: ackeret theory, linearized supersonic
flow, linear supersonic thin airfoil, biconvex wave drag, supersonic lift
curve slope." The sibling triggers "shock-expansion", "diamond airfoil",
"surface pressure table", "area ratio", "sonic throat" and "piston theory"
must not appear. ZERO em dashes in every file; never the word "classified"
in prose. Standards reference-only: naca-tr-824 named and paraphrased as
the frame, never reproduced.

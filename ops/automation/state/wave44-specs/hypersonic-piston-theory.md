# Wave-44 leaf spec: hypersonic-piston-theory (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/hypersonic-piston-theory/
- Pack: high-speed (18 leaves present at prep: aerodynamic-heating,
  bow-shock-standoff, compressible-couette-flow, fanno-flow,
  flat-plate-skin-friction-heating, hypersonic-flow, isentropic-flow-relations,
  normal-shock, oblique-shock, prandtl-meyer, rayleigh-flow,
  regular-shock-reflection, shock-expansion-airfoil, shock-tube,
  supercritical-airfoil, swept-wing-aerodynamics, transonic-similarity,
  wave-drag-area-rule; hypersonic-piston-theory and ackeret-linearized-supersonic
  are the two wave-44 additions to this pack per the wave-44 leaf plan, entries 5
  and 6). Claim fences (quoted from the sibling frontmatter at prep; none owns the
  unsteady small-perturbation hypersonic surface-pressure law):
  - hypersonic-flow (this pack) is the steady blunt-body leaf: its body reads
    "the flow is fast enough (Mach well above 5) that the bow shock sits close to
    the body, so the surface pressure is set by the impact of freestream particles
    rather than by isentropic turning", and its tag set covers steady stagnation
    estimates, blunt-body and sphere drag coefficients, cone axial force and the
    vacuum limit on shadowed surfaces. Its pitfall clause fences the regime
    handover: "for M below ~5 the supersonic shock-expansion and oblique-shock
    leaves own the estimate." Nothing in its claim is unsteady: no piston
    velocity, no local compression-expansion law from a moving surface, no
    instantaneous pressure on a deforming or oscillating surface. The new leaf is
    the unsteady complement: same hypersonic surface-pressure physics, built from
    the local piston velocity rather than from steady impact integrals.
  - flutter-speed-prediction (aerodynamics/aeroelasticity) is the oscillatory
    thin-airfoil flutter leaf: its description reads "run the V-g method across
    the reduced frequency range, locate the flutter speed where the artificial
    structural damping g crosses zero", built on a complex lift-deficiency
    function C(k) of a thin airfoil oscillating in subsonic incompressible flow.
    That C(k) is a reduced-frequency circulation lag; it carries no hypersonic
    Mach content and no surface-pressure compression-expansion law. The new leaf
    is the hypersonic large-Mach counterpart: piston-theory pressure from the
    local normal velocity ratio, with no C(k), no circulation lag and no
    reduced-frequency machinery.
  - ackeret-linearized-supersonic (this pack, same-wave plan entry 5; its SKILL.md
    is in flight at prep, so the fence is quoted from the wave-44 leaf plan:
    "Cp = +-2*theta/sqrt(M^2-1), cl = 4*alpha/sqrt(M^2-1), supersonic lift-curve
    slope 4/sqrt(M^2-1), wave drag for flat-plate/biconvex/cambered thin
    sections"). Ackeret is the LINEARIZED supersonic law of the M^2 - 1
    denominator; the linearized piston limit Cp = 2 sin(theta)/M is its
    hypersonic asymptote, but the new leaf claims the nonlinear piston law
    (exact at M*sin(theta) of order 1), which Ackeret theory never reaches.
  - shock-expansion-airfoil, oblique-shock, prandtl-meyer and normal-shock (this
    pack) are the steady shock and expansion turning methods; piston theory here
    evaluates a local compression or expansion state from a piston velocity
    ratio with no shock-polar construction, no turning-angle iteration and no
    steady wave system.
  - added-mass-coefficients-potential-flow (aerodynamics/aeroelasticity,
    same-wave plan entry 7) owns the kinetic-energy apparent-mass catalog of
    potential flow; it is incompressible and irrotational with no compressible
    pressure law, the inverse regime of this leaf.
- Whole-tree greps at prep: "piston-theory|hypersonic-piston|
  small-perturbation-hypersonic|lighthill" (case-insensitive) = 0 hits in skills/
  (SKILL.md bodies and scripts, real grep) and each token counts 0 in
  eval/hit1-corpus.yaml. The bare word "piston" in skills/ appears only in
  manufacturing-quality/ndt/ultrasonic-inspection (circular piston transducer
  near-field length N = D^2/(4 lambda)) and in vehicle-design/sizing
  hydraulic-actuator-sizing and hydraulic-system-sizing (actuator piston area and
  flow), both non-aerodynamic meanings; the two corpus "piston" hits (lines 4338
  and 4674) are the hydraulic pump flow task and the hydraulic-actuator sizing
  task, hydraulic actuator noise only. GENUINE AERO gap (fresh probe): no leaf
  computes the Lighthill piston-theory surface pressure, its linearized limit, or
  a surface-pressure coefficient from a local piston velocity for unsteady or
  small-perturbation hypersonic surfaces; hypersonic-flow is steady blunt-body
  impact theory by claim, and flutter-speed-prediction is subsonic oscillatory
  thin-airfoil C(k) work.
- Standards id: naca-tr-824 (reference-only, present in standards-map.yaml,
  matching every high-speed sibling). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Solve the Lighthill piston-theory surface-pressure problem of a
small-perturbation hypersonic surface: evaluate the piston-theory pressure ratio
p/p_inf = (1 + ((gamma - 1)/2) * (v/a_inf))^(2 gamma/(gamma - 1)) from the local
piston velocity ratio v/a_inf (the Lighthill 1953 piston analogy in the
Ashley-Zartarian hypersonic small-perturbation class), where a positive ratio is
a compression (shock-side) motion and a negative ratio an expansion, with the
law collapsing to vacuum p/p_inf = 0 at the expansion cutoff
v/a_inf = -2/(gamma - 1); compute the linearized limit p/p_inf = 1 +
gamma * v/a_inf valid for small piston velocity ratios; form the piston velocity
ratio of a steady surface inclined theta to the freestream as the freestream
normal component v/a_inf = M * sin(theta) and evaluate the local
surface-pressure coefficient Cp = 2/(gamma M^2) * (p/p_inf - 1) on the
compression side and on the expansion side separately, with the linearized
hypersonic limit Cp = 2 * sin(theta)/M; and extend the law to an unsteady
surface whose normal wall motion adds to the geometric piston velocity, giving
the instantaneous pressure ratio and pressure coefficient of the moving surface
at any phase of its motion. Produces the piston-theory pressure ratios, the
linearized limits, the per-side pressure coefficients and the unsteady
instantaneous pressures that gate hypersonic panel pressure estimates, stability
and control derivative work and oscillating-surface load checks. Does NOT do:
steady blunt-body stagnation estimates, impact-law drag integrals over a sphere,
cone or flat plate, and the vacuum limit on shadowed surfaces (hypersonic-flow);
the C(k) lift-deficiency flutter aerodynamics of a thin airfoil in subsonic
incompressible flow (flutter-speed-prediction); linearized supersonic
section coefficients with the M^2 - 1 denominator (ackeret-linearized-supersonic,
same wave); steady shock-polar, oblique-shock and Prandtl-Meyer turning of
complete configurations (oblique-shock, prandtl-meyer, shock-expansion-airfoil);
incompressible apparent-mass coefficients (added-mass-coefficients-potential-
flow, same wave). Scope: perfect-gas small-perturbation hypersonic surfaces at
Mach above 1 (the hypersonic usage sits at Mach well above 5, but the closed
form is a pure gas-dynamic law with only a Mach-exceeds-1 guard), inclination
theta in degrees over [0, 90), piston velocity ratios above the expansion cutoff
-2/(gamma - 1), gamma = 1.4 air by default and a parameter elsewhere, the wall
motion amplitude a pure ratio of a_inf. Deterministic, pure stdlib.

## Model (implement exactly)

Pure stdlib, math only. Module constants: GAMMA = 1.4 (air default; gamma is a
parameter of every function). Sign convention, pinned: the piston velocity ratio
v/a_inf is positive when the surface motion compresses the gas (shock side) and
negative when it lets the gas expand; on a steady inclined surface the
compression side carries v/a_inf = +M*sin(theta) and the expansion side
v/a_inf = -M*sin(theta). The exponent 2 gamma/(gamma - 1) is 7 at gamma = 1.4;
the expansion cutoff -2/(gamma - 1) is -5 at gamma = 1.4, where the base
(1 + ((gamma - 1)/2) * v/a_inf) reaches exactly zero and the pressure ratio is
exactly 0.0. The linearized limit 1 + gamma * v/a_inf is the first-order
expansion of the piston law; because Cp = 2/(gamma M^2) * (p/p_inf - 1), the
linearized pressure ratio maps to the Mach-independent hypersonic coefficient
Cp = 2 * sin(theta)/M in which gamma cancels.

Defining relations (pin these exactly; every function below derives from them):
- Piston law: p/p_inf = (1 + ((gamma - 1)/2) * (v/a_inf))^(2 gamma/(gamma -
  1)). Equal to 1.0 at v/a_inf = 0, strictly increasing in v/a_inf, above 1 on
  the compression side, between 1 and 0 on the expansion side down to the
  cutoff. At v/a_inf = 0.5 the law gives p/p_inf = 1.5^7 at gamma 1.4 (see
  anchor row 1.948717100000).
- Linearized limit: p_lin/p_inf = 1 + gamma * (v/a_inf); first-order in the
  piston velocity ratio, the regime of small M*sin(theta).
- Piston velocity ratio of a steady surface: v/a_inf = M * sin(theta), the
  freestream normal component U*sin(theta) divided by a_inf = U/M.
- Surface-pressure coefficient: Cp = 2/(gamma M^2) * (p/p_inf - 1), evaluated
  per side with the side's own pressure ratio; the linearized coefficient
  Cp_lin = 2 * sin(theta)/M follows from the linearized ratio and is exactly
  gamma-independent.
- Unsteady composition: the instantaneous piston velocity ratio of a moving
  surface is the steady geometric term M*sin(theta) plus the wall normal
  velocity ratio w/a_inf, added for inward (compression) wall motion and
  subtracted for retreat; the instantaneous pressure follows from the composed
  ratio through the same closed form, no time integration, no RNG.

Functions:
- piston_pressure_ratio(v_a, gamma = GAMMA) -> float: p/p_inf by the pinned
  closed form. Returns 0.0 when the base is exactly 0 (the cutoff). ValueError
  if gamma <= 1 or the base is negative (piston velocity ratio below the
  cutoff -2/(gamma - 1); the flow is fully expanded and the law has no real
  value).
- linear_pressure_ratio(v_a, gamma = GAMMA) -> float: 1 + gamma * v_a.
  ValueError if gamma <= 1.
- piston_velocity_ratio(mach, theta_deg) -> float: M * sin(theta). ValueError
  if mach <= 1 or theta outside [0, 90) degrees.
- surface_pressure_ratio(mach, theta_deg, side, gamma = GAMMA) -> float: the
  piston pressure ratio on the "compression" side (v/a_inf = +M*sin(theta)) or
  the "expansion" side (v/a_inf = -M*sin(theta)). ValueError as
  piston_velocity_ratio plus gamma <= 1 and a side other than the two names.
- surface_pressure_coefficient(mach, theta_deg, side, gamma = GAMMA) -> float:
  Cp by the pinned relation from the side's pressure ratio. Same ValueError set
  as surface_pressure_ratio.
- linear_cp(mach, theta_deg) -> float: 2 * sin(theta)/M, the linearized
  hypersonic limit. ValueError as piston_velocity_ratio.
- unsteady_piston_ratio(mach, theta_deg, wall_v_a, direction) -> float: the
  geometric term plus direction * abs(wall_v_a), direction +1 for wall motion
  into the gas, -1 for retreat. ValueError as piston_velocity_ratio plus a
  direction other than +1 or -1.
- unsteady_pressure_ratio(mach, theta_deg, wall_v_a, direction, gamma = GAMMA)
  -> float: piston_pressure_ratio of the composed unsteady ratio. ValueError set
  of unsteady_piston_ratio plus gamma <= 1 and the cutoff guard.

Identities to test (closed form, deterministic):
- p/p_inf(0) = 1.000000000000 and Cp(0) = 0.000000000000 at any Mach (an
  aligned surface, theta = 0, sees no compression).
- Cutoff: piston_pressure_ratio(-5.0) = 0.000000000000 at gamma 1.4, and
  piston_pressure_ratio(-5.5) raises (below the cutoff).
- Linearized accuracy: at v/a_inf = +-0.02 the linearized ratio sits within a
  relative error of about 3.4e-4 of the exact law (anchor 0.000343265810 and
  0.000328927745); at v/a_inf = 0.5 the residual between the exact and the
  linearized ratio is 0.248717100000, the law clearly nonlinear.
- Cp linearization identity: the Cp built from the linearized pressure ratio
  equals linear_cp = 2 * sin(theta)/M to float zero (anchor residual
  0.000000000000 at M = 6, theta = 5 deg, both 0.029051914249).
- Compression-expansion split: at M = 6, theta = 5 deg the compression side
  p/p_inf = 2.006315343379 exceeds the expansion side 0.461491957246; at M = 8,
  theta = 10 deg, 5.563247915155 versus 0.102434506727. The law is not
  reciprocal: the product p_c * p_e = 0.569868555988 at M = 8, theta = 10 deg
  (the exponent 7 is not antisymmetric under a sign flip).
- Unsteady composition: with a wall velocity ratio amplitude 0.10 at M = 6,
  theta = 5 deg the instantaneous piston ratios are 0.622934456486 (inward) and
  0.422934456486 (retreat) around the steady 0.522934456486, and the pressure
  swing about the steady state is 0.253904031159 of the steady p/p_inf.
- gamma honored: piston_pressure_ratio(0.5, gamma = 1.3) =
  1.871572650534 and surface_pressure_ratio(8.0, 10.0, "compression", gamma =
  1.3) = 5.157316326010; gamma = 1.0 raises everywhere.
- ValueErrors across the module: mach at and below 1; theta negative and at or
  above 90; gamma at and below 1; piston velocity ratio below -2/(gamma - 1)
  (-5.5 at gamma 1.4); side and direction values outside the two allowed names.
- Determinism; no imports beyond math; two identical runs return identical bits
  (anchor True); no RNG anywhere.

## Worked example

Two steady surfaces and one unsteady surface, gamma = 1.4. All values below are
REAL outputs of the prep anchor /tmp/w44spec/anchor_piston.py (stdlib math,
closed forms only, deterministic, exit 0).

- Piston law across the sides (the raw law): at v/a_inf = +0.5 (compression)
  p/p_inf = 1.948717100000 and at -0.5 (expansion) 0.478296900000; at +1.5 the
  ratio 6.274851700000 versus the linearized 3.100000000000, a residual
  3.174851700000, so the exponent 7 law runs far above its tangent once the
  piston ratio is not small. At v/a_inf = -5.0 the base vanishes and the law
  returns exactly 0.000000000000 (vacuum); below the cutoff it raises.
- Linearized limit validity: at v/a_inf = +-0.02 the exact ratios are
  1.028338248982 and 0.972333768939 against linearized 1.028000000000 and
  0.972000000000, relative errors 0.000328927745 and 0.000343265810, so the
  linearized limit is the small-M*sin(theta) regime; at v/a_inf = 0.5 the exact
  1.948717100000 already sits 14.6 percent above the linearized 1.700000000000
  and the exact law is required.
- Steady surface A, M = 6, theta = 5 deg (M*sin(theta) = 0.522934456486,
  moderate): compression side p/p_inf = 2.006315343379 with Cp =
  0.039933148547; expansion side p/p_inf = 0.461491957246 with Cp =
  -0.021369366776; the linearized coefficient Cp = 2*sin(theta)/M =
  0.029051914249 equals the Cp rebuilt from the linearized pressure ratio to
  float zero (residual 0.000000000000). The exact compression Cp is 37 percent
  above the linearized value, so at M*sin(theta) = 0.52 the linearized limit
  underestimates the load.
- Steady surface B, M = 8, theta = 10 deg (M*sin(theta) = 1.389185421335, order
  1): compression side p/p_inf = 5.563247915155 with Cp = 0.101858212392;
  expansion side p/p_inf = 0.102434506727 with Cp = -0.020034944046, a
  compression-to-expansion pressure ratio near 54.3; the linearized Cp =
  0.043412044417 is less than half the exact compression coefficient, and the
  product p_c * p_e = 0.569868555988 shows the exponent-7 law is far from
  reciprocal at this loading.
- Unsteady surface, M = 6, theta = 5 deg, wall normal velocity ratio amplitude
  0.10 (an oscillating panel whose normal speed peaks at one tenth of the local
  sound speed): geometric steady piston ratio 0.522934456486; at the inward
  peak 0.622934456486 and at the retreat peak 0.422934456486. Pressures:
  steady p/p_inf = 2.006315343379, inward peak 2.274841372010, retreat peak
  1.765429818550; the pressure coefficients follow as 0.039933148547 (steady),
  0.050588943334 (inward) and 0.030374199149 (retreat). The motion swings the
  surface pressure by 0.253904031159 of the steady p/p_inf, a quarter-wave load
  cycle about the steady compression state, which is the unsteady content the
  steady blunt-body leaf cannot produce.
- Read-off: an aligned surface (theta = 0) carries p/p_inf = 1.000000000000 and
  Cp = 0.000000000000 at any Mach; the compression side always exceeds the
  freestream pressure and the expansion side falls below it down to vacuum at
  the cutoff, and the wall-motion term adds to or subtracts from the geometric
  compression at the phase of the motion.
Run your module and take the real outputs as assert targets; the anchors above
are real prep outputs of /tmp/w44spec/anchor_piston.py (stdlib math, closed
forms, exit 0).

## Validation list (contract test must include)

- Piston law table at gamma 1.4 within 1e-5: v/a -1.5 -> 0.082354300000, -0.8
  -> 0.295090346557, -0.5 -> 0.478296900000, -0.2 -> 0.751447478108, -0.05 ->
  0.932065347907, 0.0 -> 1.000000000000 (within 1e-12), 0.05 ->
  1.072135352107, 0.2 -> 1.315931779236, 0.5 -> 1.948717100000, 0.8 ->
  2.826219734467, 1.5 -> 6.274851700000; strictly increasing in v/a across a
  sample sweep of both sides (anchor True).
- Cutoff: piston_pressure_ratio(-5.0) = 0.000000000000 within 1e-12 (exactly 0);
  piston_pressure_ratio(-5.5) raises ValueError; piston_pressure_ratio(0.0) =
  1.000000000000 within 1e-12.
- Linearized limit: linear_pressure_ratio matches 1 + gamma * v/a at every
  sample; relative error of the linearized against the exact law at v/a =
  +-0.02 is 0.000328927745 and 0.000343265810 within 1e-5; at v/a = 0.5 the
  exact-versus-linear residual is 0.248717100000 within 1e-5.
- Linearized Cp identity: at M = 6, theta = 5 deg the Cp rebuilt from
  linear_pressure_ratio(piston_velocity_ratio) equals linear_cp =
  0.029051914249 within 1e-9 (anchor residual 0.000000000000); linear_cp is
  gamma-independent by construction.
- Steady surface A (M = 6, theta = 5 deg): piston_velocity_ratio =
  0.522934456486 within 1e-9; compression p/p_inf = 2.006315343379 and Cp =
  0.039933148547 within 1e-5; expansion p/p_inf = 0.461491957246 and Cp =
  -0.021369366776 within 1e-5; exact compression Cp exceeds linear_cp
  0.029051914249.
- Steady surface B (M = 8, theta = 10 deg): piston_velocity_ratio =
  1.389185421335 within 1e-9; compression p/p_inf = 5.563247915155 and Cp =
  0.101858212392 within 1e-5; expansion p/p_inf = 0.102434506727 and Cp =
  -0.020034944046 within 1e-5; linear_cp = 0.043412044417 within 1e-5; product
  p_c * p_e = 0.569868555988 within 1e-5 (not 1).
- Unsteady surface (M = 6, theta = 5 deg, wall_v_a = 0.10): piston ratios
  0.622934456486 (inward), 0.422934456486 (retreat) within 1e-9 around the
  steady 0.522934456486; pressures 2.274841372010 and 1.765429818550 within
  1e-5 around 2.006315343379; pressure coefficients 0.050588943334 and
  0.030374199149 within 1e-5 around 0.039933148547; swing 0.253904031159 of the
  steady ratio within 1e-5.
- Aligned surface: surface_pressure_ratio(8.0, 0.0, "compression") =
  1.000000000000 and Cp = 0.000000000000 within 1e-12.
- Gamma honored: piston_pressure_ratio(0.5, gamma = 1.3) = 1.871572650534
  within 1e-5; surface_pressure_ratio(8.0, 10.0, "compression", gamma = 1.3) =
  5.157316326010 within 1e-5; the exponent and cutoff follow gamma.
- ValueErrors (anchor cases): piston_pressure_ratio at v/a -5.5 and gamma 1.0;
  linear_pressure_ratio at gamma 1.0; surface_pressure_ratio at mach 1.0;
  surface_pressure_coefficient at theta 95 degrees (and at theta 90); a side
  name other than the two allowed; unsteady direction 0 (and -2); each raises
  ValueError.
- Determinism: two identical runs return identical bits (anchor True); no
  imports beyond math; no RNG. Contract test file named
  test_hypersonic_piston_theory.py (underscores), unittest, offline in under 20
  seconds.

## Corpus fragment (eval/hit1-wave44-hypersonic-piston-theory.yaml)

Query 1 (copy verbatim):
  "estimate the surface pressure on the compression and the expansion side of a
  small-perturbation hypersonic surface by Lighthill piston theory: from the
  freestream Mach and the local inclination compute the piston-theory pressure
  ratio p/p_inf and the surface-pressure coefficient with the linearized limit"
  intent: "aerodynamics; Lighthill piston-theory surface pressure:
  piston-theory pressure ratio and per-side surface-pressure coefficient of an
  inclined small-perturbation hypersonic surface with the linearized limit"
  expected_skill: "aerodynamics/high-speed/hypersonic-piston-theory"
Query 2 (copy verbatim):
  "find the instantaneous surface-pressure coefficient of an unsteady
  hypersonic surface whose oscillatory normal motion adds to the geometric
  piston velocity, with the small-perturbation hypersonic-piston analogy at
  hypersonic Mach"
  intent: "aerodynamics; unsteady hypersonic piston theory: piston velocity as
  the geometric term plus the wall normal motion, instantaneous
  surface-pressure ratio and pressure coefficient of a moving surface"
  expected_skill: "aerodynamics/high-speed/hypersonic-piston-theory"
Task ids: w44-hypersonic-piston-theory-1 and -2. Prep grep and probe:
"piston-theory", "hypersonic-piston", "small-perturbation-hypersonic" and
"lighthill" appear in NO existing eval/hit1-corpus.yaml task and in NO skills/
file (0 hits each, real greps); the only corpus "piston" hits are the two
hydraulic actuator tasks (lines 4338 and 4674), so the queries above are
collision-free. The steady hypersonic-flow corpus tasks route on stagnation
coefficients and blunt-body and sphere drag integrals, the flutter tasks on
C(k) flutter speeds, and the supersonic linear-theory tasks on the M^2 - 1
section coefficients, none of which these queries carry.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the surface pressure on a
small-perturbation hypersonic surface by Lighthill piston theory:" and include
the outputs in the Claim. First tag: hypersonic-piston-theory. Additional tags
ONLY: lighthill-piston-analogy, small-perturbation-hypersonic,
piston-theory-pressure-ratio, unsteady-hypersonic-surface-pressure. NEVER single
generic words (piston, pressure, surface, mach, hypersonic, unsteady,
expansion, compression, shock) and NEVER hypersonic-flow (the steady blunt-body
sibling, whose steady stagnation, blunt-body and sphere drag integral, cone
axial force and vacuum-limit tokens stay with it), NEVER a C(k) lift-deficiency
or reduced-frequency token (flutter-speed-prediction), NEVER ackeret,
linearized-supersonic (ackeret-linearized-supersonic), shock-expansion,
prandtl-meyer, oblique-shock (the steady turning leaves) or apparent-mass
(added-mass-coefficients-potential-flow). 50-150 words, <=1000 chars, no em
dash, action verb present. Recommended wording (outputs in Claim order):
"Use when you must estimate the surface pressure on a small-perturbation
hypersonic surface by Lighthill piston theory: evaluate the piston-theory
pressure ratio
p/p_inf = (1 + ((gamma - 1)/2) v/a_inf)^(2 gamma/(gamma - 1)) from the local
piston velocity ratio, apply the linearized limit p/p_inf = 1 + gamma v/a_inf
for a small piston velocity, split the compression side from the expansion side
of the inclined surface, compute the local surface-pressure coefficient from
the freestream Mach and inclination on either side, and extend the same law to
an unsteady surface whose normal motion adds to the geometric piston velocity.
Produces the piston-theory surface-pressure ratios, the linearized limits and
the per-side and instantaneous pressure coefficients that gate hypersonic panel
pressure, stability derivative and oscillating-surface load estimates. Trigger:
piston theory, hypersonic piston analogy, small perturbation hypersonic surface
pressure, Lighthill." The sibling triggers "stagnation pressure coefficient",
"blunt body drag", "sphere drag", "cone axial force", "vacuum limit", "flutter",
"lift deficiency" and "shock expansion" must not appear.

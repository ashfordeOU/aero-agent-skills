# Wave-45 leaf spec: inelastic-column-buckling (structures, fem pack)

- Path: skills/structures/fem/inelastic-column-buckling/
- Pack: fem (24 leaves present at prep: beam-column-analysis,
  beam-frame-analysis, beam-vibration, buckling-analysis, calculix-linear,
  calculix-nonlinear, contact-analysis, crippling-analysis,
  curved-beam-analysis, cylindrical-shell-buckling, diagonal-tension-field-
  webs, hertzian-contact-stress, lug-joint-analysis, metallic-fastener-
  joints, modal-analysis, plastic-collapse-analysis, plate-buckling,
  pressure-bulkhead, restrained-warping, shear-center-analysis,
  shrink-fit-analysis, statically-indeterminate, torsion-shear-flow,
  truss-analysis; inelastic-column-buckling is a wave-45 addition of the
  family, the task-10 probe GO candidate 1). Claim fences (quoted from the
  sibling frontmatter and bodies at prep; no sibling computes an inelastic
  column allowable anchored on the solid-section yield):
  - buckling-analysis (this pack) is the ELASTIC Euler column owner and
    the direct sibling of the same member: its description opens "Use when
    a column, strut, spar cap, landing-gear leg or actuator rod must be
    sized or margin-checked against elastic instability in a stdlib-only
    environment without FEA software. Calculate the Euler critical
    buckling load of slender compression members: apply
    Pcr = pi^2*E*I/(K*L)^2 for pinned-pinned, fixed-fixed, fixed-pinned
    and cantilever end conditions, resolve the effective length factor K
    from the support type, compute the slenderness ratio from the radius
    of gyration, and run the buckling stress check against the
    yield-based transition slenderness". Its Domain quick reference
    states "If lambda > lambda_1 the column is slender and Euler governs;
    if lambda < lambda_1 the material yields first and Euler overpredicts
    the capacity (Johnson or test-data range)" (lines 68-70) with
    lambda_1 = pi * sqrt(E / sigma_y) the yield crossing, and its workflow
    step 7 hands the inelastic side off: "Classify the column: compute
    lambda_1 = pi * sqrt(E / sigma_y) ... If lambda > lambda_1, Euler
    governs and Pcr is the capacity; if not, Euler is unconservative, so
    fall back to a Johnson parabola or test data" (lines 119-122). The
    leaf's deliverable is the classification flag only: the elastic Euler
    LOAD of a slender member and the euler_governs verdict at its own
    yield-crossing lambda_1; the inelastic fallback computation is handed
    off, never implemented. Its tags euler-buckling,
    critical-buckling-load, slenderness-ratio, effective-length-factor,
    end-conditions, buckling-stress, radius-of-gyration, cantilever-
    column, pinned-pinned and fixed-fixed are NOT reusable here, and its
    trigger phrases "Euler critical buckling load", "slenderness ratio",
    "end conditions", "radius of gyration" and "yield-based transition"
    must not appear in this leaf's description.
  - crippling-analysis (this pack) is the formed-stiffener owner and the
    in-repo precedent for the Johnson arm equation family, re-anchored on
    the LOCAL crippling stress: its description states it computes "the
    Johnson-Euler interaction that anchors the stiffener column curve on
    the local crippling stress", with F_col = F_cc * (1 - F_cc *
    lambda**2 / (4 * pi**2 * E)) (line 63) and "lambda_t = pi *
    sqrt(2 * E / F_cc)" (its own crippling-stress transition), never on
    yield. Its Related leaves fence the seam both ways: "structures/fem/
    buckling-analysis: the GLOBAL column Euler load of the same member
    with the end-condition effective length factor and the yield-based
    transition; this leaf takes lambda = K*L/r as an input and anchors its
    Johnson curve on the local crippling stress, never on the solid-
    section yield" (lines 196-200). Its Pitfalls: "Anchoring the Johnson
    curve on sigma_y: the stiffener short-column curve anchors on the
    LOCAL crippling allowable F_cc (the lambda-tending-to-0 limit), so
    using sigma_y in the parabola overstates short stiffeners whose
    section cripples before it yields" (lines 241-244), and its scope
    note "extruded, machined or fiber-reinforced sections, elevated
    temperature, fastener bearing or pull-through of the attachments, and
    corner radii (flat widths only) are out of scope for this closed
    form" (lines 250-253): extruded and machined whole sections are
    exactly the population this leaf serves. Its tags crippling-analysis,
    shape-constant-method, element-crippling, local-crippling-stress,
    inter-rivet-buckling, stringer-crippling,
    stiffener-compression-allowable, formed-compression-shapes and
    johnson-euler-interaction are NOT reusable here, and the trigger
    words crippling, inter-rivet and stringer must not appear in this
    leaf's description.
  - No leaf anywhere in skills/ computes a Johnson arm anchored on the
    material yield F_cy of a whole solid or extruded column. Whole-tree
    greps at prep (real runs for this spec): "johnson|inelastic|
    column[- ]strength" over the skills/ SKILL.md bodies gives structural
    hits ONLY at buckling-analysis (its two hand-off lines 70 and 122),
    crippling-analysis (its own F_cc-anchored content), the
    structures/SKILL.md family index line 202 which routes Johnson-Euler
    questions to crippling-analysis, and two rotorcraft leaves whose
    "Johnson" words are the helicopter-rotor theory author (W. Johnson,
    with Leishman), flight-mechanics noise with zero column content. The
    token "inelastic" alone gives ZERO hits in any skills/ SKILL.md body;
    the tangent-modulus stress-strain curve of materials/ramberg-osgood
    is the only yield-adjacent content in the tree and it defines
    material response, not a column curve.
  - Corpus scan (real runs over eval/hit1-corpus.yaml): the distinctive
    tokens johnson-parabola, inelastic-column, column-strength,
    intermediate-slenderness, stubby-column, euler-johnson-tangent and
    yield-anchored-johnson each match 0 existing tasks, so the two new
    tasks written at build (w45-inelastic-column-buckling-1 and -2) steal
    nothing and nothing routes here by accident. The existing buckling
    tasks bka1/bka2 carry euler critical buckling load, effective length
    factor, slenderness ratio, Pcr, cantilever column, elastic
    instability and radius of gyration tokens with no johnson, parabola,
    inelastic or intermediate-slenderness content, and the crippling
    tasks carry the crippling token family, so the new queries below are
    collision-free in both directions.
  GENUINE STRUCTURES gap (fresh probe): buckling-analysis ends its
  elastic Euler arm at the yield-transition classification flag and
  hands the inelastic computation off in its own workflow text;
  crippling-analysis anchors its Johnson arm on the local crippling
  stress of formed sheet stiffeners and states it is never on the
  solid-section yield, with extruded and machined sections out of scope;
  the yield-anchored Euler-Johnson tangent column strength curve of the
  whole solid, round, tube and extruded column sits between the two and
  is owned by nobody.
- Standards id: far-25, cs-25 (reference-only, both present in
  standards-map.yaml at lines 16 and 27, gated false, matching the fem
  siblings buckling-analysis, crippling-analysis and plate-buckling; the
  FAR 25.301 / CS 25.301 applied-load and FAR 25.303 / CS 25.303 1.5
  ultimate-factor requirements set the load context of the column
  compression cases, summary paraphrase only, never standard text).
  Ledger Standard: far-25, cs-25.
- Family: structures

## Claim

Compute the inelastic column strength of a whole solid, round, tube or
extruded compression member in the intermediate slenderness band: the
effective slenderness lambda = K*L/r from the effective length factor K,
the physical length L and the radius of gyration r of the section, the
Euler-Johnson tangent transition lambda_t = sqrt(2*pi^2*E/F_cy) at which
the yield-anchored Johnson parabola is tangent to the Euler arm, the
Johnson parabola arm F_col = F_cy*(1 - F_cy*lambda^2/(4*pi^2*E)) of the
column strength curve for lambda at or below lambda_t, the Euler arm
F_col = pi^2*E/lambda^2 above lambda_t, the regime classification
(johnson below the tangent transition, euler above it), the column
capacity P_col = F_col*A of the section area A, and the margin of safety
MS = P_col/P_applied - 1 against the applied axial compression with the
pass verdict, where both arms of the curve return exactly F_cy/2 at
lambda_t (tangency by construction, verified to float roundoff: the
parabola is the quadratic interpolation between the yield anchor F_cy at
lambda = 0 and the Euler hyperbola tangent point at F_cy/2, the standard
Johnson form of the published Euler-Johnson tangent column strength
curve, the same equation family crippling-analysis already implements
re-anchored from the local crippling stress on the solid-section yield).
Produces the inelastic column allowable stress F_col, the transition
slenderness lambda_t, the regime, the column capacity P_col, the margin
and the verdict that gate the stubby and intermediate column checks of
actuator rods, tube compression members and extruded struts in the FAR
25.301 / FAR 25.303 load context (standards referenced, not reproduced).
Does NOT do: the elastic Euler critical load Pcr = pi^2*E*I/(K*L)^2 of a
slender member as a deliverable, the resolution of K from the end-
condition support table (pinned-pinned, fixed-fixed, fixed-pinned,
cantilever), the radius-of-gyration-from-section-properties workflow or
the yield-crossing classification at lambda_1 = pi*sqrt(E/sigma_y) with
the euler_governs flag (buckling-analysis owns the elastic Euler arm and
its end-condition machinery; this leaf takes K as a number and reports
the Euler arm only as the upper arm of the yield-anchored column
strength curve, the crippling-analysis precedent); the local crippling
of formed sheet stiffeners, the element crippling power law with the
shape constants, the area-weighted section crippling allowable, inter-
rivet buckling, or any Johnson curve anchored on the local crippling
stress F_cc (crippling-analysis, formed compression shapes only); the
elastic-plastic stress-strain curve, secant or tangent modulus of the
material itself (ramberg-osgood, materials pack); flat-plate or shell
instability of the walls of a thin section (plate-buckling,
cylindrical-shell-buckling); or axial-plus-bending interaction
(beam-column-analysis). Scope: whole solid sections, round or extruded
tubes and extruded or machined members whose local wall stability does
not govern (thin formed sheet belongs to crippling-analysis); linear
elastic isotropic material characterized by E and F_cy as plain floats
(the worked examples use the in-repo registry values shared with
crippling-analysis: 2024-T3 E = 72.4 GPa and F_cy = 290 MPa, 7075-T6
E = 71.7 GPa and F_cy = 462 MPa); ideally straight, concentrically
loaded column with no initial-imperfection or eccentricity knockdown and
no residual-stress correction beyond the yield anchor; compression only;
uniform section and length; SI units (metres, newtons, pascals).
Deterministic, pure stdlib.

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG. Module constants:
E_2024_T3 = 72.4e9 and F_CY_2024_T3 = 290.0e6, E_7075_T6 = 71.7e9 and
F_CY_7075_T6 = 462.0e6 (Pa, the in-repo material registry values shared
with the crippling-analysis sibling, used by the worked examples only;
all functions take E and F_cy as plain float arguments). All functions
take plain SI floats. No imports beyond math.

Defining relations (pin these exactly; every function below derives from
them):
- Effective slenderness: lambda = K*L/r with K the effective length
  factor (a plain number, given; the end-condition K table belongs to
  buckling-analysis), L the physical length in m, r the radius of
  gyration in m.
- Euler-Johnson tangent transition: lambda_t = sqrt(2*pi^2*E/F_cy). At
  lambda_t both arms of the curve return F_cy/2 and the parabola is
  tangent to the Euler hyperbola (equal closed-form slopes), the
  "tangent" of the Euler-Johnson tangent column strength curve.
- Johnson parabola arm (lambda <= lambda_t):
  F_col = F_cy*(1 - F_cy*lambda^2/(4*pi^2*E)), the quadratic between the
  yield anchor F_col = F_cy at lambda = 0 and the tangent point
  F_col = F_cy/2 at lambda_t. Re-arranged, the drop from the yield
  anchor is exactly quadratic in lambda:
  F_cy - F_col = F_cy^2*lambda^2/(4*pi^2*E), so the drop at lambda_t/2
  is exactly one quarter of the drop at lambda_t.
- Euler arm (lambda > lambda_t): F_col = pi^2*E/lambda^2, the elastic
  hyperbola of the same curve, coincident with the buckling-analysis
  Euler stress in the slender band and reported only as this curve's
  upper arm.
- Column capacity and margin: P_col = F_col*A with A the gross section
  area in m^2; MS = P_col/P_applied - 1 against the applied axial
  compression P_applied in N, pass when MS >= 0.
- Regime classification: "johnson" at or below lambda_t, "euler" above
  (the crippling-analysis convention at its own transition); at the
  exact float equality the arms agree to roundoff, so the tie
  classification is inert. The yield-crossing transition of the
  buckling-analysis sibling, lambda_1 = pi*sqrt(E/F_cy), equals
  lambda_t/sqrt(2): the tangent transition of this leaf sits sqrt(2)
  higher, so the Johnson arm also covers the intermediate band where the
  ideal Euler stress is still below yield but real column allowables
  follow the parabola (per the published column-strength-curve
  treatments, Bruhn column analysis chapter, Niu column allowable
  curves, Timoshenko and Gere inelastic columns, Roark columns chapter;
  public engineering science, paraphrase only, no reproduced tables).

Functions (implement with exactly these signatures; pure math only):
- effective_slenderness(k_factor, length, radius_gyration) -> float:
  lambda = k_factor*length/radius_gyration, dimensionless. ValueError:
  any argument <= 0.
- johnson_transition_slenderness(e, f_cy) -> float:
  sqrt(2*pi**2*e/f_cy), dimensionless. ValueError: e <= 0 or f_cy <= 0.
- johnson_parabola_stress(e, f_cy, lam) -> float: the Johnson arm
  f_cy*(1 - f_cy*lam**2/(4*pi**2*e)) in Pa. ValueError: e, f_cy or
  lam <= 0.
- euler_arm_stress(e, lam) -> float: pi**2*e/lam**2 in Pa. ValueError:
  e <= 0 or lam <= 0.
- column_regime(e, f_cy, lam) -> str: "johnson" when lam <= lambda_t,
  "euler" otherwise. ValueErrors as johnson_transition_slenderness plus
  lam <= 0.
- column_strength_allowable(e, f_cy, lam) -> float: the Johnson arm at
  or below lambda_t, the Euler arm above (the F_col of the column
  strength curve). ValueErrors of the two arms.
- column_capacity(e, f_cy, lam, area) -> float: P_col =
  column_strength_allowable(e, f_cy, lam)*area in N. ValueError: area
  <= 0, plus the curve ValueErrors.
- margin_of_safety(allowable, applied) -> float:
  allowable/applied - 1, pass when >= 0. ValueError: allowable <= 0 or
  applied <= 0.
- column_check(e, f_cy, lam, area, applied_load) -> dict with keys
  "lambda_t" (float), "regime" ("johnson" or "euler"), "F_col" (Pa),
  "P_col" (N), "margin" (float) and "verdict" ("pass" when margin >= 0,
  else "fail"). ValueErrors of all component functions.

Identities to test (closed form, deterministic; all values REAL anchor
outputs of /tmp/w45spec/anchor_inelastic_column_buckling.py, stdlib
math, exit 0, byte-identical under /usr/bin/python3 3.9.6 and
~/.pyenv/versions/3.13.12/bin/python3):
- Transition values: johnson_transition_slenderness(71.7e9, 462.0e6) =
  55.348194774118063 (7075-T6) and johnson_transition_slenderness(72.4e9,
  290.0e6) = 70.199683594869498 (2024-T3). The cross-form identity
  lambda_t = sqrt(2)*pi*sqrt(E/F_cy) holds to 1e-9 relative (anchor
  pass, both materials), and lambda_t = sqrt(2)*lambda_1 pins the fence
  against the buckling-analysis yield crossing.
- Both arms return F_cy/2 at lambda_t: for 7075-T6 the relative
  residuals of the Johnson arm, the Euler arm and their cross difference
  at lambda_t are 2.5802876526143126e-16, 1.2901438263071563e-16 and
  1.2901438263071563e-16 respectively; for 2024-T3 all three residuals
  are 0.0 (real anchor outputs; assert below 1e-12 relative).
- Tangency: the closed-form slopes of the two arms at lambda_t agree to
  2.2314728682835765e-16 relative (7075-T6) and 0.0 (2024-T3), real
  anchor outputs (Johnson slope -F_cy^2*lam/(2*pi^2*E) equals the Euler
  slope -2*pi^2*E/lam^3 at lam = lambda_t).
- Quadratic-decay quarter-drop identity: drop(lam) = F_cy -
  F_col(lam), and 4*drop(lam_t/2) equals drop(lam_t) = F_cy/2 to
  2.580287652614312e-16 relative (7075-T6) and 0.0 (2024-T3).
- Yield anchor: the parabola at lam = lambda_t*1e-6 sits within
  5.000597470766538e-13 (7075-T6) and 5.000624163397427e-13 (2024-T3)
  relative of F_cy, so F_col -> F_cy as lambda -> 0.
- Regime flip and continuity: column_regime is "johnson" at
  lam = lambda_t*(1 - 1e-12) and "euler" at lam = lambda_t*(1 + 1e-12),
  and F_col at the upper point is within 2.000238988306615e-12
  (7075-T6) and 2.0000441321011246e-12 (2024-T3) relative of F_cy/2
  (real anchor outputs).
- Euler arm ordering: the Euler arm lies strictly above the Johnson arm
  for every lambda below lambda_t (checked at lam_t/2, anchor True for
  both materials) and the arms touch at lambda_t, so Euler overpredicts
  the column allowable everywhere in the Johnson band, exactly the
  overprediction the parabola corrects.
- Determinism: two identical full runs return identical bits; the
  canonical dump sha256 is
  1f3904e5de54c994b725577b30d02c298b726db9a7a2394172f74c6c2c8e1183 on
  both in-process passes and across two separate
  shell runs; no imports beyond math; no RNG.

## Worked example

All values below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_inelastic_column_buckling.py (stdlib math,
deterministic, exit 0, byte-identical under /usr/bin/python3 3.9.6 and
~/.pyenv/versions/3.13.12/bin/python3).

Actuator rod (corpus query 1): 7075-T6 solid round rod, diameter
d = 0.04 m, E = 71.7 GPa, F_cy = 462 MPa, effective length factor
K = 1.0 (given as a number; the end-condition K table is the
buckling-analysis sibling's job), length L = 0.55 m, applied axial
compression P_applied = 200 kN.

- Section: A = pi*d^2/4 = 1.2566370614359172e-03 m^2, r = d/4 = 0.01 m
  (the solid-round identity r = d/4).
- Effective slenderness lambda = K*L/r = 55 (float round trip exact at
  the printed digits).
- Tangent transition lambda_t = sqrt(2*pi^2*E/F_cy) =
  55.348194774118063, so lambda = 55 sits just below the transition and
  the regime is johnson: the Euler-Johnson tangent column strength curve
  still follows the parabola at this intermediate slenderness.
- Johnson parabola stress F_col = 233897293.82113209 Pa (233.897 MPa),
  the inelastic column allowable. The Euler arm of the curve at the same
  lambda is 233934094.39937419 Pa (233.934 MPa), only 1.573e-4 above
  the parabola (the curve is near its tangency point: lambda_t - lambda
  = 0.348, and F_cy/2 = 231000000 Pa = 231 MPa is 1.255e-2 below the
  allowable), so Euler overpredicts the column strength even at this
  slenderness, and the parabola interpolates between the yield anchor
  462 MPa at lambda = 0 and the Euler arm at the transition.
- Column capacity P_col = F_col*A = 293924.00798520073 N (293.9 kN).
- Margin MS = P_col/P_applied - 1 = 0.46962003992600376, verdict pass
  against the 200 kN applied axial load.
- Regime and tangency bookkeeping: lambda_t = 55.348194774118063 for
  this material, and both arms return F_cy/2 = 231 MPa there (residuals
  2.58e-16 and 1.29e-16 relative, real anchor outputs).

Extruded tube compression member (corpus query 2): 2024-T3 extruded
round tube, outer diameter d_o = 0.05 m, inner diameter d_i = 0.04 m
(5 mm wall), E = 72.4 GPa, F_cy = 290 MPa, K = 1.0, applied axial
compression P_applied = 120 kN.

- Section: A = pi*(d_o^2 - d_i^2)/4 = 7.0685834705770374e-04 m^2,
  I = pi*(d_o^4 - d_i^4)/64 = 1.8113245143353656e-07 m^4,
  r = sqrt(I/A) = 0.016007810593582122 m. The round-tube identity
  r = sqrt((d_o^2 + d_i^2)/16) = sqrt(2.5625e-04) reproduces r exactly.
- The member length L = 40*r = 0.6403124237432849 m pins the effective
  slenderness lambda = K*L/r = 40 (round trip exact at the printed
  digits).
- Tangent transition lambda_t = sqrt(2*pi^2*E/F_cy) =
  70.199683594869498, so lambda = 40 is deep in the Johnson band
  (40 < 0.57*lambda_t) and the regime is johnson.
- Johnson parabola stress F_col = 242922035.66673699 Pa (242.922 MPa,
  0.83766 of F_cy): the stubby-column allowable. The Euler arm at the
  same lambda is 446599599.14929342 Pa (446.6 MPa), 1.8384482820734314
  times F_col and above F_cy itself (1.54x the yield stress), the
  overprediction of the ideal elastic formula in the intermediate band
  that the parabola corrects.
- Column capacity P_col = F_col*A = 171711.46859528226 N (171.7 kN).
- Margin MS = P_col/P_applied - 1 = 0.43092890496068548, verdict pass
  against the 120 kN applied axial load.

Column strength curve sweeps (real anchor rows; F_col in Pa, regime in
parentheses; the Euler arm column equals the elastic Euler stress of the
same slenderness):
- 7075-T6, lambda_t = 55.348194774118063: lambda 10 ->
  454459414.671773 (johnson, Euler arm 7076506355.58107), 20 ->
  431837658.687092 (johnson, 1769126588.89527), 40 ->
  341350634.748367 (johnson, 442281647.223817), 55 ->
  233897293.821132 (johnson, 233934094.399374), 60 -> 196569620.988363
  (euler, equals its Euler arm), 80 -> 110570411.805954 (euler), 100 ->
  70765063.5558107 (euler). The parabola falls from the 462 MPa yield
  anchor toward the F_cy/2 = 231 MPa tangency at lambda_t and the Euler
  arm takes over above it; the sweep value at lambda 100 equals the
  Euler stress of the slender column exactly, the elastic band shared
  with the buckling-analysis sibling.
- 2024-T3, lambda_t = 70.199683594869498: lambda 10 ->
  287057627.229171 (johnson), 20 -> 278230508.916684 (johnson), 30 ->
  263518645.06254 (johnson), 40 -> 242922035.666737 (johnson), 55 ->
  200993223.682425 (johnson, Euler arm 236217969.797973), 70 ->
  145823734.229382 (johnson, just below the transition; the Euler arm
  145828440.538545 is 3.2e-05 above it, the near-tangency), 90 ->
  88217204.7702308 (euler), 120 -> 49622177.6832548 (euler). At the
  transition both arms of the 2024-T3 curve return F_cy/2 = 145 MPa to
  0.0 relative residual on this anchor.

Read-off: the 7075-T6 rod at lambda 55 runs a 0.470 margin against its
200 kN applied load with the allowable only 1.25 percent above the
F_cy/2 tangency value, while the 2024-T3 tube at lambda 40 runs a 0.431
margin against 120 kN with the allowable at 0.838 of yield and the Euler
arm 1.84 times too high; the curve family interpolates the yield anchor
at lambda = 0, the parabola through the intermediate band, and the Euler
hyperbola in the slender band, tangent at F_cy/2.
Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w45spec/anchor_inelastic_column_
buckling.py (stdlib math, exit 0).

## Validation list (contract test must include)

1. Worked-example 1 (7075-T6 rod): effective_slenderness(1.0, 0.55,
   0.01) = 55 within 1e-12 relative; johnson_transition_slenderness(
   71.7e9, 462.0e6) = 55.348194774118063 within 1e-9 relative;
   johnson_parabola_stress(71.7e9, 462.0e6, 55.0) =
   233897293.82113209 within 1e-6 relative; euler_arm_stress(71.7e9,
   55.0) = 233934094.39937419 within 1e-6 relative;
   column_regime(71.7e9, 462.0e6, 55.0) = "johnson";
   column_strength_allowable(71.7e9, 462.0e6, 55.0) equals the Johnson
   arm within 1e-9 relative; column_capacity(71.7e9, 462.0e6, 55.0,
   1.2566370614359172e-03) = 293924.00798520073 within 1e-6 relative;
   column_check margin 0.46962003992600376 within 1e-6 relative;
   verdict "pass".
2. Worked-example 2 (2024-T3 tube): r = sqrt(1.8113245143353656e-07 /
   7.0685834705770374e-04) = 0.016007810593582122 within 1e-9 relative
   and equals sqrt(2.5625e-04) within 1e-12 relative (the round-tube
   identity); effective_slenderness(1.0, 0.6403124237432849,
   0.016007810593582122) = 40 within 1e-12 relative;
   johnson_transition_slenderness(72.4e9, 290.0e6) =
   70.199683594869498 within 1e-9 relative; johnson_parabola_stress(
   72.4e9, 290.0e6, 40.0) = 242922035.66673699 within 1e-6 relative;
   euler_arm_stress(72.4e9, 40.0) = 446599599.14929342 within 1e-6
   relative and the overprediction ratio 1.8384482820734314 within 1e-9
   relative; column_capacity(72.4e9, 290.0e6, 40.0,
   7.0685834705770374e-04) = 171711.46859528226 within 1e-6 relative;
   column_check margin 0.43092890496068548 within 1e-6 relative;
   verdict "pass".
3. Curve sweep anchors: column_strength_allowable and column_regime at
   the 7075-T6 rows (10, 20, 40, 55, 60, 80, 100) and the 2024-T3 rows
   (10, 20, 30, 40, 55, 70, 90, 120) of the Worked example reproduce
   the listed F_col values within 1e-6 relative and the listed regimes;
   in the euler regime column_strength_allowable equals
   euler_arm_stress to 1e-12 relative; the curve is strictly monotone
   decreasing over a dense grid of lambda from 1 to 200 for both
   materials; euler_arm_stress(e, lam) > johnson_parabola_stress(e,
   f_cy, lam) at lam = lambda_t/2 for both materials (anchor True).
4. Tangency at lambda_t for both materials: the Johnson arm, the Euler
   arm and their cross difference at lambda_t each sit within 1e-12
   relative of F_cy/2 (anchor 2.58e-16, 1.29e-16 and 1.29e-16 for
   7075-T6, 0.0 for 2024-T3); the closed-form slopes
   -f_cy**2*lam/(2*pi**2*e) and -2*pi**2*e/lam**3 agree at lambda_t
   within 1e-9 relative (anchor 2.23e-16 and 0.0).
5. Quadratic-decay quarter-drop identity: |4*(F_cy -
   johnson_parabola_stress(e, f_cy, lam_t/2)) - (F_cy -
   johnson_parabola_stress(e, f_cy, lam_t))| no greater than 1e-9*F_cy
   for both materials (anchor residuals 2.58e-16 and 0.0 relative), and
   drop(lam_t) = F_cy/2 within 1e-12 relative.
6. Yield anchor: johnson_parabola_stress(e, f_cy, lam_t*1e-6) within
   1e-9 relative of F_cy (anchor 5.0e-13 for both materials).
7. Regime flip and continuity: column_regime(e, f_cy, lam_t*(1 - 1e-12))
   is "johnson" and column_regime(e, f_cy, lam_t*(1 + 1e-12)) is
   "euler" for both materials; |column_strength_allowable(e, f_cy,
   lam_t*(1 + 1e-12)) - F_cy/2| within 1e-9 relative of F_cy/2 (anchor
   2.0e-12), so the curve is continuous across the transition to float
   roundoff.
8. Cross-form transition identity: johnson_transition_slenderness(e,
   f_cy) equals sqrt(2)*pi*sqrt(e/f_cy) within 1e-9 relative for both
   materials, and equals sqrt(2) times the buckling-analysis yield
   crossing pi*sqrt(e/f_cy) (lambda_t = sqrt(2)*lambda_1, the fence
   relation between the tangent transition here and the elastic yield
   crossing of the sibling).
9. Capacity and margin linearity: column_capacity is linear in area
   (doubling area doubles P_col within 1e-9 relative);
   column_capacity/A equals column_strength_allowable within 1e-9
   relative; margin_of_safety(P_col, P_applied/2) = 2*MS + 1 within
   1e-9 relative (anchor pass); margin_of_safety reproduces
   P_col/P_applied - 1 exactly; column_check agrees with the component
   functions key by key within 1e-12 relative.
10. ValueErrors across the module: effective_slenderness(0.0, 0.55,
    0.01), (1.0, 0.0, 0.01), (1.0, 0.55, 0.0) raise;
    johnson_transition_slenderness(0.0, 462.0e6), (71.7e9, 0.0) raise;
    johnson_parabola_stress(0.0, 462.0e6, 55.0), (71.7e9, 0.0, 55.0),
    (71.7e9, 462.0e6, 0.0) raise; euler_arm_stress(0.0, 55.0),
    (71.7e9, 0.0) raise; column_regime and column_strength_allowable
    with lam = 0.0 raise; column_capacity(71.7e9, 462.0e6, 55.0, 0.0)
    raises; margin_of_safety(0.0, 200.0e3) and margin_of_safety(
    293924.00798520073, 0.0) raise; column_check with applied_load =
    0.0 raises through the margin function (13 anchor cases, each
    raises ValueError).
11. Determinism: two identical full runs return identical bits (anchor
    canonical dump sha256
    1f3904e5de54c994b725577b30d02c298b726db9a7a2394172f74c6c2c8e1183
    on both in-process passes and across two
    separate shell runs); no imports beyond math; no RNG. Test passes
    under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.
    Contract test file named test_inelastic_column_buckling.py
    (underscores), unittest, offline in under 20 seconds.

## Corpus fragment (2 verbatim queries for
eval/hit1-wave45-inelastic-column-buckling.yaml)

Query 1 (copy verbatim):
  "run the inelastic-column-buckling check of the 7075-T6 solid round
  actuator rod with the johnson-parabola column-strength-curve: at the
  intermediate-slenderness of 55 below the euler-johnson-tangent
  transition the allowable falls between the yield anchor and the euler
  arm, so compute the parabola stress and the margin against the applied
  axial load"
  intent: "structures; inelastic column buckling of the 7075-T6 solid
  round rod at intermediate slenderness 55 below the euler-johnson
  tangent transition: yield-anchored johnson-parabola stress of the
  column strength curve and the margin against the applied axial load"
  expected_skill: "structures/fem/inelastic-column-buckling"
Query 2 (copy verbatim):
  "determine the stubby-column-allowable of the 2024-T3 extruded tube
  compression member in the johnson-parabola range: the
  inelastic-column-buckling stress at effective slenderness 40 where the
  euler stress overpredicts, tangent to the euler arm at the
  column-strength-curve transition"
  intent: "structures; inelastic column buckling of the 2024-T3 extruded
  tube member at effective slenderness 40 in the johnson-parabola range:
  stubby-column-allowable of the yield-anchored column strength curve
  where the euler stress overpredicts, tangent to the euler arm at the
  transition"
  expected_skill: "structures/fem/inelastic-column-buckling"
Task ids: w45-inelastic-column-buckling-1 and -2. Prep grep and probe:
the distinctive tokens johnson-parabola, inelastic-column,
column-strength, intermediate-slenderness, stubby-column,
euler-johnson-tangent and yield-anchored-johnson each match 0 existing
eval/hit1-corpus.yaml tasks (real greps, count 0 each) and the corpus
johnson words are absent entirely, so the two new tasks steal nothing;
the existing buckling tasks bka1/bka2 carry euler critical buckling
load, effective length factor, slenderness ratio, Pcr, cantilever
column, elastic instability and radius of gyration tokens with no
johnson, parabola, inelastic or intermediate-slenderness overlap, the
crippling tasks carry the local-crippling and johnson-euler-interaction
token family, and the skills/ tree johnson hits outside the two fem
fences are the rotorcraft-blade-flapping-dynamics and
rotorcraft-lead-lag-dynamics helicopter-rotor author references, so the
queries above are collision-free in both directions (no theft from bka
or crippling tasks, no accidental routing away from them).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the inelastic column
strength of a solid round, tube or extruded compression member in the
intermediate slenderness band:" and include the outputs in the Claim.
First tag: inelastic-column-buckling. Additional tags ONLY the receipt's
gate (f) list, verbatim: inelastic-column-buckling, johnson-parabola,
column-strength-curve, intermediate-slenderness, euler-johnson-tangent,
yield-anchored-johnson, stubby-column-allowable. NEVER the bare single
words johnson, parabola, euler, column, buckling, slenderness, yield,
allowable, margin, rod, tube, strut, load or stress alone, and NEVER the
sibling tokens euler-buckling, critical-buckling-load,
slenderness-ratio, effective-length-factor, end-conditions,
buckling-stress, radius-of-gyration, cantilever-column, pinned-pinned,
fixed-fixed (buckling-analysis, which owns the elastic Euler load, the
end-condition K table and the yield-crossing classification, so its
triggers "Euler critical buckling load", "slenderness ratio", "end
conditions", "radius of gyration" and "yield-based transition" must not
appear), crippling-analysis, shape-constant-method,
element-crippling, local-crippling-stress, inter-rivet-buckling,
stringer-crippling, stiffener-compression-allowable,
formed-compression-shapes, johnson-euler-interaction (crippling-
analysis, whose trigger words crippling, inter-rivet, stringer,
stiffener and formed must not appear), and ramberg-osgood,
stress-strain-curve, secant-modulus, tangent-modulus, elastic-plastic
(materials/ramberg-osgood, the stress-strain curve leaf). 50-150 words,
<=1000 chars, no em dash, no content-policy sweep term, action verb
present. Recommended wording (outputs in Claim order): "Use when you
must compute the inelastic column strength of a solid round, tube or
extruded compression member in the intermediate slenderness band: the
effective slenderness lambda = K*L/r of the member, the
euler-johnson-tangent transition lambda_t = sqrt(2*pi^2*E/F_cy) where
the yield-anchored Johnson parabola meets the Euler arm at F_cy/2, the
johnson-parabola stress F_col = F_cy*(1 - F_cy*lambda^2/(4*pi^2*E))
below the transition and the Euler arm stress above it, the column
capacity P_col = F_col*A and the margin of safety against the applied
axial load, with the johnson or euler regime verdict. Produces the
inelastic column allowable stress and load, the
stubby-column-allowable and the pass-fail margin that gate compression
checks of 7075-T6 and 2024-T3 actuator rods, tube members and extruded
struts. Trigger: inelastic column buckling, Johnson parabola, column
strength curve, intermediate slenderness, stubby column allowable." The
sibling triggers "euler buckling", "critical buckling load", "end
conditions", "radius of gyration", "slenderness ratio", "crippling",
"inter-rivet", "stringer", "tangent modulus" and "stress-strain curve"
must not appear. ZERO em dashes in every file; no content-policy sweep
terms. Standards reference-only: far-25 and cs-25 named
as the certification compression context (the FAR 25 and CS 25
structural rules frame the context; the Euler-Johnson relations are
standard engineering methodology, summary-only), never reproduced
verbatim.

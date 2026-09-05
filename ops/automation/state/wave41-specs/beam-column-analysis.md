# Wave-41 leaf spec: beam-column-analysis (structures, fem pack)

- Path: skills/structures/fem/beam-column-analysis/
- Pack: fem. Closest siblings: buckling-analysis (Euler axial-only
  compression member: its frontmatter claim is "Use when a column,
  strut, spar cap, landing-gear leg or actuator rod must be sized or
  margin-checked against elastic instability in a stdlib-only
  environment without FEA software. Calculate the Euler critical
  buckling load of slender compression members: apply Pcr =
  pi^2*E*I/(K*L)^2 for pinned-pinned, fixed-fixed, fixed-pinned and
  cantilever end conditions, resolve the effective length factor K from
  the support type, compute the slenderness ratio from the radius of
  gyration, and run the buckling stress check against the yield-based
  transition slenderness"; its margin is the pure-axial MS = Pcr / P -
  1, and its own Pitfalls hand the gap away verbatim: "Euler assumes a
  perfectly straight, concentrically loaded column; initial
  imperfection and load eccentricity reduce the real capacity below
  Pcr". No moment, eccentricity or bending input exists in any
  buckling-analysis function), beam-frame-analysis (first-order linear
  rigid-jointed frame: "members carry axial force, shear and bending
  moment together" in a stiffness-matrix solve whose body contains zero
  second-order, P-delta, moment-amplification, eccentricity or
  instability terms, verified by whole-tree grep at prep),
  plate-buckling (flat-panel compression and shear buckling with a
  compression-shear interaction check; the "interaction" there is
  panel-level stress interaction, not a member-level axial-plus-bending
  ratio), truss-analysis (pin-jointed axial bars). Whole-tree greps at
  prep: "moment amplification", "secant formula", "beam-column",
  "combined axial", "load eccentricity" and "interaction ratio" = 0
  hits in skills/structures/, and no crippling leaf exists anywhere in
  the tree (stringer-crippling history: local-section crippling is NOT
  reopened; this leaf owns the GLOBAL member-level combined-loading
  case). GENUINE STRUCT gap (fresh probe): buckling-analysis margin
  checks P against Pcr only, and beam-frame-analysis is first-order
  linear, so a compression member that must also carry bending has no
  margin-check owner anywhere in the tree.
- Standards ids: far-25, cs-25 (reference-only; structures fem pack
  convention, matching buckling-analysis). Ledger Standard: far-25.
- Family: structures

## Claim

Margin-check a slender compression member that also carries bending
(lateral load, end moment or load eccentricity): compute the Euler load
P_E = pi^2 E I / (K L)^2 of the member, the moment amplification factor
delta = c_m / (1 - P/P_E) that grows the primary moment as the axial
load approaches the Euler load, the amplified bending moment and stress
contribution, the secant-formula peak compressive stress of an
eccentrically loaded column sigma_max = (P/A) (1 + (e c / r^2) sec((K L
/ (2 r)) sqrt(P / (E A)))), and the axial-plus-bending interaction
ratio P/P_cr + M_applied / (M_capacity (1 - P/P_E)) with its margin of
safety 1/ratio - 1 and pass verdict. Produces P_E, the amplification
factor, the amplified moment, the peak combined stress, the interaction
ratio, the margin and the verdict that gate the global combined-loading
margin check. Does NOT do: the pure-axial Euler critical load with the
effective-length-factor table and the slender-versus-stubby transition
classification (buckling-analysis owns Pcr of the concentrically loaded
column; this leaf takes P_E only as the amplification denominator and
interaction input); first-order linear frame solves with element
stiffness matrices (beam-frame-analysis); flat-panel compression and
shear buckling with the plate buckling coefficient and the panel
compression-shear interaction (plate-buckling); local crippling of the
compression flange or stringer section, which is a local-section
phenomenon outside this global member check. Deterministic closed form
only; inelastic Johnson-range behavior of stubby columns stays with
buckling-analysis.

## Model (implement exactly)

Functions (pure stdlib, math only; SI: E in Pa, I in m^4, A in m^2, L
and e in m, forces in N, moments in N m, stresses in Pa):
- euler_load(e_mod, i, l, k = 1.0) -> float pi^2 * e_mod * i / (k *
  l)**2, the Euler load P_E of the member (the classic ideal-column
  critical load, same physics as the buckling-analysis anchor);
  ValueError if e_mod <= 0, i <= 0, l <= 0 or k <= 0.
- moment_amplification(p, p_euler, c_m = 1.0) -> float c_m / (1.0 - p /
  p_euler), the amplification of the primary bending moment by the
  axial compression, the standard second-order factor 1/(1 - P/P_E)
  (name and paraphrase only; with c_m = 1.0 the worst-case constant
  moment). The factor is 1.0 at zero axial load and grows without bound
  as P approaches P_E from below. ValueError if p < 0, p_euler <= 0,
  c_m <= 0 or p >= p_euler.
- secant_stress(p, area, ecc, c, r, l, e_mod, k = 1.0) -> float (p /
  area) * (1.0 + (ecc * c / r**2) / cos((k * l / (2.0 * r)) * sqrt(p /
  (e_mod * area)))), the secant-formula peak compressive stress of an
  eccentrically loaded column with load eccentricity ecc, extreme-fiber
  distance c and radius of gyration r = sqrt(I/A) (the classical
  secant formula for an initially straight pin-ended column loaded with
  eccentricity e; name and paraphrase only, standard methodology). The
  secant argument equals pi/2 exactly at P = P_E (verify: with I = A
  r^2 the argument is (K L / 2) sqrt(P / (E I)), which reaches pi/2 at
  the Euler load), so the stress diverges precisely where the member
  buckles; reject p >= p_euler through the argument guard arg >= pi/2
  raising ValueError. Additional ValueErrors when p <= 0, area <= 0,
  ecc < 0, c <= 0, r <= 0, l <= 0, e_mod <= 0 or k <= 0. At ecc = 0 the
  function returns p / area exactly (pure axial stress), the
  consistency limit.
- interaction_check(p, p_cr, m_applied, m_capacity, p_euler) -> dict
  {"ratio", "margin", "pass"}: the AISC-style axial-plus-bending
  interaction (paraphrase, the standard amplification of the primary
  moment by 1/(1 - P/P_E)): ratio = p / p_cr + m_applied /
  (m_capacity * (1.0 - p / p_euler)); margin = 1.0 / ratio - 1.0; pass
  = ratio <= 1.0 (inclusive). The first term is the axial utilization
  against the Euler load, the second the amplified bending utilization
  against the section moment capacity. With m_applied = 0 the ratio
  degenerates to p / p_cr and the margin to p_cr / p - 1, the
  buckling-analysis margin-of-safety identity. ValueError if p < 0,
  p_cr <= 0, m_applied < 0, m_capacity <= 0, p_euler <= 0 or p >=
  p_euler; dict keys exactly ratio, margin, pass.

Module constants: none beyond math (pi from math.pi).

Identity to test: delta = 1.0 at P = 0 and monotone increasing in P up
to the P_E pole; secant_stress returns p / area at ecc = 0 and is
monotone increasing in ecc; the secant argument reaches pi/2 at P =
P_E, so both moment_amplification and secant_stress diverge at the same
load; the interaction ratio degenerates to the pure-axial margin p_cr /
p - 1 when m_applied = 0; pass is inclusive at ratio = 1.0.

## Worked example

The steel member used by the buckling-analysis worked anchor (E = 200
GPa, I = 1e-6 m^4, A = 1e-3 m^2, L = 3.0 m, pinned-pinned K = 1.0),
now carrying combined loading: solid circular section with r =
sqrt(I/A) = 0.031623 m, extreme fiber c = 2 r = 0.063246 m, effective
slenderness K L / r = 94.8683 (slender against the 88.9 transition
slenderness of the 250 MPa steel). Limit axial load P = 100 kN with a
primary end moment M = 1 kN m from a load eccentricity e = M / P = 10
mm at the loaded end. All values below are REAL outputs of the prep
anchor script /tmp/w41spec/anchor_beam_column.py (stdlib math,
deterministic).

- P_E = euler_load(200e9, 1e-6, 3.0) = 219324.542 N = 219.325 kN, so
  P / P_E = 0.455945. The same member at K = 0.5 gives 877.298 kN and
  at K = 2.0 gives 54.831 kN, the K-squared scaling of the axial
  sibling.
- delta = moment_amplification(100e3, 219324.542) = 1.838051, so the
  amplified primary moment is 1.838 kN m. The amplification is the
  whole story: the unamplified bending utilization M / M_cap is
  0.252982 but the amplified utilization M / (M_cap (1 - P/P_E)) is
  0.464994.
- sigma_max = secant_stress(100e3, 1e-3, 0.010, 0.063246, 0.031623,
  3.0, 200e9, 1.0) = 2.295230e8 Pa = 229.5230 MPa, 0.9181 of the 250
  MPa yield strength; the secant argument is 1.060660 rad, comfortably
  below the pi/2 = 1.570796 rad pole at P_E.
- M_capacity = sigma_y * I / c = 250e6 * 1e-6 / 0.063246 = 3952.847 N
  m (yield moment of the section, 3.953 kN m).
- interaction_check(100e3, 219324.542, 1000.0, 3952.847, 219324.542):
  axial term 0.455945, amplified moment term 0.464994, ratio =
  0.920939, margin = +0.085848 (8.58%), verdict PASS. The Euler-only
  margin of safety on this member is 1.19 (the buckling-analysis
  anchor); adding the 1 kN m primary bending moment drops the combined
  margin to +0.086, about a 93% reduction, and ignoring the moment
  amplification would overstate the margin to 1/0.708927 - 1 = +0.411.
- Overload case P = 130 kN, M = 1.2 kN m (e = 9.23 mm): delta =
  2.455424, ratio = 1.3381, margin = -0.2527, verdict FAIL; the secant
  peak stress is 344.61 MPa, above the 250 MPa yield. The member
  passes neither check at this load.

## Verification (deterministic checks)

- Edge identities: moment_amplification(0.0, p_euler) = 1.0 exactly;
  secant_stress(..., ecc = 0.0, ...) = 1.0e8 Pa = P / A exactly;
  euler_load pin-to-fixed-fixed ratio 4.0 exactly (K enters squared).
- Divergence consistency: the secant argument at P = P_E computes to
  1.570796 rad = pi/2, and moment_amplification raises ValueError at p
  >= p_euler, as does secant_stress once the argument reaches pi/2
  (assert with p = p_euler + 1.0 N, strictly above the pole; floating
  point at the exact pole is not asserted).
- Monotonicity: delta rises 1.295291 at P = 50 kN, 1.838051 at P = 100
  kN, 3.163736 at P = 150 kN; secant_stress rises with ecc at fixed P.
- Pure-axial degeneration: interaction_check(100e3, 219324.542, 0.0,
  3952.847, 219324.542) gives ratio 0.455945 and margin +1.193245, the
  buckling-analysis MS = Pcr / P - 1 = 1.19 anchor reproduced.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds, computed by running the prep
anchor script /tmp/w41spec/anchor_beam_column.py (prep-verified by
stdlib math).

## Validation list (contract test must include)

- euler_load(200e9, 1e-6, 3.0) = 219324.542 within 1e-3 N; K = 0.5
  gives 877298.169 N and K = 2.0 gives 54831.136 N within 1e-3; K
  ratio 4.0; ValueErrors at zero and negative e_mod, i, l, k.
- moment_amplification(100e3, 219324.542) = 1.838051 within 1e-6;
  (50e3, ...) = 1.295291 and (150e3, ...) = 3.163736 within 1e-6;
  (0.0, ...) = 1.0 exactly; monotone increasing in p; ValueError at p
  = p_euler and p > p_euler, at negative p, p_euler 0 and c_m 0.
- secant_stress worked case (100e3, 1e-3, 0.010, 0.063246, 0.031623,
  3.0, 200e9, 1.0) = 2.295230e8 Pa within 1e2 Pa; ecc = 0 case returns
  1.0e8 exactly; monotone increasing in ecc; ValueError at p 0, area 0,
  negative ecc, c 0, r 0, l 0, E 0, K 0 and at p = p_euler + 1.0 (the
  pi/2 argument guard).
- interaction_check pass case: ratio 0.920939 within 1e-6, margin
  +0.085848 within 1e-6, pass True; overload case (130e3, 219324.542,
  1200.0, 3952.847, 219324.542): ratio 1.3381 within 1e-4, margin
  -0.2527 within 1e-4, pass False; m_applied = 0 case ratio 0.455945
  and margin +1.193245 within 1e-6 (buckling-analysis identity);
  inclusive boundary: a crafted load giving ratio 1.0 exactly reports
  pass True; ValueErrors at p = p_euler, negative p, p_cr 0, negative
  m_applied, m_capacity 0, p_euler 0.
- Determinism; dict keys exactly ratio, margin, pass; fixed pass
  verdict strings never used (bool only).

## Corpus fragment (eval/hit1-wave41-beam-column-analysis.yaml)

Query 1 (copy verbatim):
  "margin-check the longeron under combined axial compression and bending: the axial load sits at 45.6 percent of the euler load, so amplify the primary end moment by the moment-amplification factor 1 over (1 minus P over P_E) and run the axial-plus-bending interaction-ratio check for the margin of safety"
  intent: "structures; compression member that also carries bending, moment-amplification factor, axial-bending interaction ratio, margin of safety"
  expected_skill: "structures/fem/beam-column-analysis"
Query 2 (copy verbatim):
  "compute the peak compressive stress of the eccentrically loaded column by the secant formula from the load eccentricity, the radius of gyration and the axial stress P over A, and compare the peak stress against the yield strength for the global combined-loading case"
  intent: "structures; eccentrically loaded column secant-formula peak stress, load eccentricity, axial and bending combined"
  expected_skill: "structures/fem/beam-column-analysis"
Task ids: w41-beam-column-analysis-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must margin-check a compression
member that also carries bending:" and include the outputs in the
Claim. First tag: beam-column-analysis. Additional tags ONLY:
moment-amplification-factor, secant-formula, load-eccentricity,
axial-bending-interaction-ratio. NEVER single generic words (bending,
buckling, column, strut, moment, stress, margin, interaction alone).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): effective-length-factor,
transition-slenderness, buckling-stress, slender-stubby (buckling-
analysis owns the concentric-column classification; this leaf's
interaction ratio degenerates to it only at zero moment);
buckling-coefficient, skin-panel, spar-web, compression-shear-
interaction, effective-width (plate-buckling); rigid-jointed-frame,
portal-frame, stiffness-matrix, nodal-displacement,
euler-bernoulli-beam-element (beam-frame-analysis); pin-jointed-bar,
member-end-action (truss-analysis); stringer-spacing, frame-pitch,
effective-skin-width (fuselage-skin-stringer-panel sizing tasks);
resonance-amplification, quality-factor (random-vibration-analysis).
The word "interaction" inside this leaf means the member-level
axial-plus-bending ratio, never the plate-level compression-shear
interaction of plate-buckling.

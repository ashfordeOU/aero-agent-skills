# Wave-47 leaf spec: unidirectional-lamina-micromechanics (structures, composites pack)

- Path: skills/structures/composites/unidirectional-lamina-micromechanics/
- Pack: structures/composites (12 leaves present at this HEAD:
  adhesive-bonded-joints, cmh17-allowables, composite-bolted-joints,
  composite-repair, delamination-growth, failure-criteria,
  laminate-first-ply-failure, laminate-hygrothermal-response,
  laminate-plate-buckling, laminate-stiffness, peel-stress-bonded-joints,
  sandwich-panels; adjacent fence on the property-value side:
  structures/materials/material-selection). Wave-47 probe receipt task-5
  rank-1 GO; 0 owners verified whole-tree at prep and re-verified at spec
  time.
- Claim fences (quoted from the sibling frontmatter and bodies at this
  HEAD; the nearest owner, laminate-stiffness, treats the four lamina
  engineering constants as GIVEN inputs, and no leaf anywhere derives
  them from the fiber and matrix constituents, the implicit hand-off
  this leaf closes):
  - laminate-stiffness workflow step 1, body line: "1. Collect ply
    engineering constants E1, E2, nu12, G12." The constants are INPUTS
    to the whole classical lamination theory stack.
  - laminate-stiffness domain quick reference, body line: "A ply has
    orthotropic stiffness in material axes: Q11, Q12, Q22, Q66 from the
    engineering constants." Derivation of those engineering constants
    from fiber and matrix properties is neither produced nor fenced
    there, it is simply absent.
  - laminate-stiffness frontmatter description (line 3): "build the ply
    stiffness from the material constants, rotate it to the ply angle,
    and assemble the A matrix for a symmetric laminate". The leaf
    produces ply stiffness, rotated stiffness and the A matrix; it never
    predicts the material constants themselves.
  - cmh17-allowables frontmatter description: "...derive laminate-level
    allowables from lamina allowables..." and its body line: "it is also
    distinct from structures/composites/laminate-stiffness, which
    computes the elastic stiffness matrix rather than strength design
    values." Its input boundary is coupon test data, not constituent
    properties.
  - material-selection (structures/materials) body line: "Representative
    band values (verify against MMPDS, AMS, or CMH-17 before design
    use; MMPDS design-value tables are never reproduced". Property
    VALUES there are given reference bands with no prediction machinery.
  - laminate-hygrothermal-response frontmatter description:
    "equilibrium moisture content from relative humidity with a linear
    isotherm, stiffness-weighted laminate CTE and CME assembled by
    classical lamination theory from ply-level properties". The
    moisture and CTE vein is owned; this leaf stops at density.
  - Whole-tree greps at prep (probe receipt gate (a), fresh at HEAD and
    re-run at spec time): halpin, micromechanic, rule of mixture, fiber
    volume fraction, constituent properties, voigt bound, reuss bound
    return ZERO files across every skills/ SKILL.md and ZERO of 1286
    eval/hit1-corpus.yaml task blocks; the wave-41..47 recon dirs return
    zero (NEVER adjudicated). No corpus task routes on constituent-level
    prediction: the 85 lamina-token corpus tasks are CLT tasks that
    start from given constants (laminate-stiffness tasks "rotate the
    lamina stiffness matrix...", "compute the laminate in-plane A
    matrix..."). GENUINE composites gap (probe receipt task-5, verified
    zero-owner, GO rank 1).
- Standards id: cmh-17 (CMH-17, Composite Materials Handbook; the
  constituent and lamina property data conventions the micromechanics
  prediction feeds, reference-only and never reproduced; grep 'id:
  cmh-17' at standards-map.yaml line 281, re-verified at spec time).
  Ledger Standard: cmh-17.
- Family: structures

## Claim

Predict the engineering constants of a unidirectional lamina from the
fiber and matrix CONSTITUENT properties and the fiber volume fraction,
the producer side of the lamina-constant chain that every composites
consumer leaf takes as given input. The fiber is transversely isotropic
with five engineering constants as inputs: axial modulus E_f, major
Poisson ratio nu_f, transverse modulus E_fT and longitudinal shear
modulus G_f; the matrix is isotropic with modulus E_m and Poisson ratio
nu_m (its shear modulus is derived, G_m = E_m / (2 (1 + nu_m))); V_f is
the fiber volume fraction. Outputs: the longitudinal modulus
E1 = V_f E_f + (1 - V_f) E_m and the major Poisson ratio
nu12 = V_f nu_f + (1 - V_f) nu_m by the rule of mixtures (Voigt), both
EXACT composite-cylinder-assemblage values; the transverse modulus E2 by
the Halpin-Tsai closed form with the circular-fiber shape factor
xi_E2 = 2 against the fiber TRANSVERSE modulus ratio E_fT / E_m; the
in-plane shear modulus G12 by the Halpin-Tsai closed form with the
circular-fiber shape factor xi_G12 = 1 against G_f / G_m (which is
exactly the composite-cylinder-assemblage longitudinal shear solution);
the density by the rule of mixtures when fiber and matrix densities are
given. Produces, for verification, the closed-form Voigt/Reuss bound
band and the Hashin-Shtrikman (composite cylinder) bound band on E2 and
G12, and the nested-band statement that the predictions fall inside the
envelope: the Hashin-Shtrikman G12 band is the anti-plane (2D
conduction) closed form whose lower endpoint the xi = 1 Halpin-Tsai
value attains exactly; the Hashin-Shtrikman E2 band follows the in-plane
Hashin (1965) closed-form bounds on the plane-strain bulk modulus k* and
the transverse shear modulus m*, converted through the exact
transverse-isotropy identity E2 = 4 k m E1 / (E1 (k + m) + 4 k m
nu12^2) with the exact E1 and nu12. Aerospace composites sit near
V_f = 0.6, where the xi = 2 estimator tracks inside the band. Does NOT
do: the ply stiffness Q11/Q12/Q22/Q66 from the engineering constants,
the rotation to Q-bar and the laminate A matrix of a symmetric laminate
(structures/composites/laminate-stiffness, whose workflow step 1
collects E1, E2, nu12, G12 as inputs, the exact outputs this leaf
produces); Tsai-Wu, Tsai-Hill and max-stress failure indices and the
Xt/Xc/Yt/Yc/S lamina allowables (structures/composites/failure-criteria,
and laminate-first-ply-failure for the laminate-level loads); A-basis
and B-basis statistics, coupon pooling and knockdown factors from coupon
test data (structures/composites/cmh17-allowables); moisture content,
CTE, CME and hygrothermal strain (structures/composites/
laminate-hygrothermal-response; this leaf never predicts a coefficient
of thermal expansion or any hygrothermal quantity); elastic buckling of
orthotropic and laminated plates (structures/composites/
laminate-plate-buckling); bearing, bypass, net-tension and shear-out of
bolted composite joints, adhesive and peel joints, sandwich panels,
delamination growth and composite repair (the remaining composites pack
leaves); material property VALUES, selection bands and design-value
tables (structures/materials/material-selection and mmpsd-allowables;
constituent properties are inputs, never looked up or reproduced, and no
test-data fitting happens anywhere). Constituent properties and V_f are
inputs, never estimated; the model is closed-form arithmetic in SI units
on the unidirectional lamina in its material axes (1 = fiber
direction); off-axis properties, transverse shear G23, strength,
failure, voids, statistical scatter and hygrothermal response are out of
scope.

## Model (implement exactly)

Pure stdlib (math only), closed form, deterministic, no RNG, no tables
beyond the two fixed published Halpin-Tsai circular-fiber shape factors.
Module constants: XI_E2 = 2.0 (transverse modulus shape factor) and
XI_G12 = 1.0 (longitudinal shear shape factor), the standard circular-
fiber values of Halpin and Tsai (AFML-TR-67-423, 1969). All moduli in
Pa, density in kg/m^3, matching the laminate-stiffness SI convention
(its contract test works E1 = 135.0e9 etc.).

Defining relations (pin these exactly; every function derives from
them):
- V_m = 1 - V_f.
- E1 = V_f E_f + V_m E_m (rule of mixtures, exact for the composite
  cylinder assemblage; the fiber axial modulus E_f belongs in the
  longitudinal arm).
- nu12 = V_f nu_f + V_m nu_m (rule of mixtures, exact for the
  composite cylinder assemblage; nu_f is the fiber major Poisson
  ratio).
- Halpin-Tsai shared form: eta = (Mr - 1) / (Mr + xi) with Mr the
  constituent property ratio; P / P_m = (1 + xi eta V_f) / (1 - eta
  V_f) where P is the predicted property and P_m the matrix property.
- E2 = E_m (1 + xi_E2 eta_E V_f) / (1 - eta_E V_f) with
  eta_E = (E_fT / E_m - 1) / (E_fT / E_m + xi_E2) and xi_E2 = 2.0.
  The reinforcement property of the TRANSVERSE arm is the fiber
  transverse modulus E_fT, never the axial 230 GPa-class modulus (a
  carbon fiber is transversely isotropic; using E_f in this arm
  overpredicts E2 by roughly a factor of two and is the classic bug
  class here).
- G12 = G_m (1 + xi_G12 eta_G V_f) / (1 - eta_G V_f) with
  eta_G = (G_f / G_m - 1) / (G_f / G_m + xi_G12) and xi_G12 = 1.0,
  which equals exactly the composite-cylinder-assemblage longitudinal
  shear solution.
- G_m = E_m / (2 (1 + nu_m)), the isotropic matrix shear modulus.
- rho_c = V_f rho_f + V_m rho_m (rule of mixtures, when both
  densities are given).
- Voigt/Reuss band on E2: E2_Reuss = 1 / (V_f / E_fT + V_m / E_m)
  (inverse rule of mixtures, iso-stress lower bound) and E2_Voigt =
  V_f E_fT + V_m E_m (iso-strain upper bound); the same two forms with
  G_f and G_m give the G12 band. Every transverse-band quantity uses
  the fiber TRANSVERSE modulus E_fT, never E_f.
- Hashin-Shtrikman G12 band (anti-plane problem, the 2D conduction
  analog of Hashin and Shtrikman with circular cylinders; the lower
  endpoint is attained by the fiber-in-matrix composite cylinder
  arrangement and equals the xi_G12 = 1 Halpin-Tsai value exactly, the
  upper endpoint by the inverted matrix-in-fiber arrangement):
  G12_lo = G_m + V_f / (1 / (G_f - G_m) + V_m / (2 G_m)),
  G12_hi = G_f + V_m / (1 / (G_m - G_f) + V_f / (2 G_f)).
- Hashin-Shtrikman E2 band (in-plane problem, Hashin 1965 closed-form
  bounds on the plane-strain bulk modulus k* and the transverse shear
  modulus m*, documented idealization: the fiber cross-section enters
  through the transverse modulus E_fT as the isotropic-equivalent pair
  g_fx = E_fT / (2 (1 + nu_f)) and k_fx = g_fx / (1 - 2 nu_f) with the
  given fiber Poisson ratio; fiber transverse shear and transverse
  Poisson are not datasheet constants, and this is the minimal
  idealization that keeps the band closed-form in the receipt's input
  set):
  k_lo = k_m + V_f / (1 / (k_fx - k_m) + V_m / (k_m + g_m)),
  k_hi = k_fx + V_m / (1 / (k_m - k_fx) + V_f / (k_fx + g_fx)),
  m_lo = g_m + V_f / (1 / (g_fx - g_m) + V_m (k_m + 2 g_m) / (2 g_m
  (k_m + g_m))),
  m_hi = g_fx + V_m / (1 / (g_m - g_fx) + V_f (k_fx + 2 g_fx) / (2 g_fx
  (k_fx + g_fx))),
  with g_m = G_m and k_m = g_m / (1 - 2 nu_m) for the isotropic matrix,
  then the exact transverse-isotropy conversion E2 = 4 k m E1 / (E1
  (k + m) + 4 k m nu12^2), monotone increasing in k and in m, evaluated
  at the exact CCA E1 and nu12 of the composite: the (k_lo, m_lo) pair
  gives the E2 lower bound and the (k_hi, m_hi) pair the upper bound.
  Valid when the fiber is the stiffer phase in the cross-section
  (always true for aerospace polymer-matrix composites), enforced by
  ValueError.
- Band-verification scope (documented): the xi_E2 = 2 estimator sits
  inside the E2 Hashin-Shtrikman band over the engineering volume-
  fraction range V_f in [0.3, 0.9] for the worked constituents; below
  roughly V_f = 0.25 the fixed semi-empirical estimator dips slightly
  under the variational lower bound, the known reason Wall (1997)
  formulated bounds on the Halpin-Tsai fitting parameter. The E2 band
  degenerates to E_m exactly at V_f = 0 and closes to a point at
  V_f = 1 whose value (20.758123 GPa for the worked constituents) sits
  a documented 3.8 percent above E_fT because of the cross-section
  idealization; the Halpin-Tsai E2 pure-fiber limit itself is exactly
  E_fT. The G12 identity is exact at both endpoints.

Functions (every public function validates its inputs identically;
ValueError, never assert):
- shear_modulus_isotropic(e, nu) -> float: G = e / (2 (1 + nu)).
  ValueErrors: e not a positive number ("modulus must be a positive
  number, got ..."), nu not in [0, 0.5) ("poisson ratio must be in
  [0, 0.5), got ...").
- e1_longitudinal(e_f, e_m, v_f) -> float: the E1 rule of mixtures.
  ValueErrors: e_f or e_m not positive, v_f outside [0, 1], any boolean
  argument.
- nu12_major(nu_f, nu_m, v_f) -> float: the nu12 rule of mixtures.
  ValueErrors: nu outside [0, 0.5), v_f outside [0, 1], booleans.
- e2_halpin_tsai(e_ft, e_m, v_f, xi=XI_E2) -> float: the E2 closed
  form against E_fT / E_m. ValueErrors as above plus a non-positive
  xi.
- g12_halpin_tsai(g_f, g_m, v_f, xi=XI_G12) -> float: the G12 closed
  form against G_f / G_m.
- e2_reuss_lower(e_ft, e_m, v_f) -> float: E2_Reuss, the inverse
  rule of mixtures lower bound.
- e2_voigt_upper(e_ft, e_m, v_f) -> float: E2_Voigt, the rule of
  mixtures upper bound.
- g12_reuss_lower(g_f, g_m, v_f) -> float and
  g12_voigt_upper(g_f, g_m, v_f) -> float: the shear band endpoints.
- rho_composite(rho_f, rho_m, v_f) -> float: the density rule of
  mixtures.
- g12_hashin_shtrikman_bounds(g_f, g_m, v_f) -> (float, float): the
  (lower, upper) G12 band of the anti-plane closed forms. ValueError
  "the fiber must be the stiffer shear phase, got G_f ... with G_m
  ..." when G_f is at most G_m.
- e2_hashin_shtrikman_bounds(e_f, nu_f, e_ft, e_m, nu_m, v_f) ->
  (float, float): the (lower, upper) E2 band through the k* and m*
  bounds and the E1/nu12 conversion above. ValueErrors of every input,
  plus "the fiber must be the stiffer cross-section phase, got k_f ...
  with k_m ..." when k_fx is at most k_m or g_fx at most g_m.
- unidirectional_lamina_constants(e_f, nu_f, e_ft, g_f, e_m, nu_m,
  v_f, rho_f=None, rho_m=None) -> dict: the one-shot report. Keys:
  "e1", "nu12", "e2", "g12" (Pa), "e2_reuss", "e2_voigt",
  "e2_hs_low", "e2_hs_up", "g12_reuss", "g12_voigt", "g12_hs_low",
  "g12_hs_up" (Pa), and "rho" (kg/m^3) when both densities are given.
  Same ValueErrors; a missing density pair simply omits "rho".

Identities to test (closed form, checkable without the builder
module):
- G12 Halpin-Tsai with xi_G12 = 1 equals the Hashin-Shtrikman G12
  lower bound exactly (algebraic identity: both reduce to
  G_m (G_f (1 + V_f) + G_m (1 - V_f)) / (G_f (1 - V_f) + G_m (1 + V_f)),
  the composite-cylinder-assemblage longitudinal shear solution). Real
  anchor: 4.402037 GPa on both sides.
- Pure-matrix degeneracy V_f = 0: E1 = E_m, nu12 = nu_m,
  E2_halpin_tsai = E_m, G12 = G_m, rho = rho_m, and both E2 bounds
  converge to E_m (the band closes to the point 3.500000 GPa).
- Pure-fiber degeneracy V_f = 1: E1 = E_f, nu12 = nu_f,
  E2_halpin_tsai = E_fT exactly (3.5 (1 + 2 eta) / (1 - eta) = E_fT),
  G12_halpin_tsai = G_f exactly, rho = rho_f.
- Isotropic-fiber collapse: for an isotropic fiber (E-glass), E_fT =
  E_f and G_f = E_f / (2 (1 + nu_f)) reduce every transverse relation
  to the classic single-fiber-modulus Halpin-Tsai and inverse-rule-of-
  mixtures forms; the corpus E-glass query is served by the same
  module with no code change.
- Nested bands at the worked volume fraction: E2_Reuss < E2_HS_lo <
  E2_HT < E2_HS_hi < E2_Voigt and G12_Reuss < G12_HT = G12_HS_lo <
  G12_HS_hi < G12_Voigt; the Reuss bound always sits at or below the
  Hashin-Shtrikman lower bound and the Voigt bound at or above the
  Hashin-Shtrikman upper bound (the Hashin-Shtrikman band is the
  tighter one).
- E2 prediction inside the Hashin-Shtrikman band for V_f in [0.3, 0.9]
  at the worked constituents (real anchor sweep, PASS), with the
  documented below-0.25 and pure-fiber-limit caveats above.
- Determinism: identical outputs run to run, identical under both
  interpreters; no randomness; no imports beyond math.

## Worked example

T300 carbon / epoxy 5208-class unidirectional ply at V_f = 0.60.
Constituent inputs: E_f = 230.0 GPa (fiber axial modulus), nu_f = 0.20
(fiber major Poisson ratio), E_fT = 20.0 GPa (fiber transverse
modulus), G_f = 27.0 GPa (fiber longitudinal shear modulus), E_m = 3.5
GPa (epoxy), nu_m = 0.35, V_f = 0.60, rho_f = 1760.0 kg/m^3, rho_m =
1230.0 kg/m^3. The matrix shear modulus is derived:
G_m = 3.5 / (2 (1 + 0.35)) = 1.296296296 GPa.

All values below are REAL outputs of the prep anchor
/tmp/w47spec/anchor_unidirectional_lamina_micromechanics.py (pure
stdlib, math only, closed form, exit 0, no RNG), run once and quoted
as printed, then re-verified identical under /usr/bin/python3 3.9.6 and
the 3.13.12 interpreter:

- Rule of mixtures (exact composite-cylinder-assemblage values):
  E1 = 139.400000 GPa = 0.60 * 230 + 0.40 * 3.5 and
  nu12 = 0.260000 = 0.60 * 0.20 + 0.40 * 0.35.
- Halpin-Tsai E2 (xi = 2, fiber transverse modulus ratio):
  eta = (20 / 3.5 - 1) / (20 / 3.5 + 2) = 11 / 18 = 0.611111, and
  E2 = 3.5 * (1 + 2 * 0.611111 * 0.60) / (1 - 0.611111 * 0.60) =
  9.578947 GPa (full precision 9578947368.421053 Pa).
- Halpin-Tsai G12 (xi = 1, equal to the composite-cylinder-assemblage
  longitudinal shear solution): G12 = 4.402037 GPa (full precision
  4402037250.138515 Pa).
- Density by rule of mixtures: rho = 1548.000000 kg/m^3 = 0.60 * 1760
  + 0.40 * 1230.
- E2 verification band (GPa, module output): Reuss lower 6.930693 <
  Hashin-Shtrikman lower 8.821709 < E2 9.578947 < Hashin-Shtrikman
  upper 10.939799 < Voigt upper 13.400000. The Halpin-Tsai prediction
  sits inside the Hashin-Shtrikman band with 0.76 GPa to the lower and
  1.36 GPa to the upper endpoint, and both bands bracket it.
- G12 verification band (GPa, module output): Reuss lower 3.023033 <
  G12 4.402037 = Hashin-Shtrikman lower 4.402037 < Hashin-Shtrikman
  upper 12.608295 < Voigt upper 16.718519. The prediction attains the
  Hashin-Shtrikman lower endpoint exactly (the xi = 1 identity).
- Magnitude gates from the probe receipt: E1 in [135, 145] GPa (139.4
  passes), E2 in [8, 12] GPa (9.579 passes), G12 in [4, 6] GPa
  (4.402 passes), matching the textbook T300/5208-class values
  (Daniel and Ishai worked example: E1 near 139 GPa, E2 near 9 to 10
  GPa inside the Hashin bounds).
- Bounds degeneracies (module output): at V_f = 0 the E2 band closes
  to (3499999999.9999995, 3500000000.0) Pa, exactly E_m; at V_f = 1 it
  closes to (20758122743.682312, 20758122743.682316) Pa, the
  documented 20.758123 GPa cross-section-idealization point, 3.8
  percent above E_fT, while the Halpin-Tsai E2 limit at V_f = 1 is
  exactly 20.0 GPa.
- Real ValueError messages (module output, quoted as raised): a zero
  fiber modulus raises "fiber modulus E_f must be a positive number,
  got 0.0"; V_f = 1.5 raises "fiber volume fraction must be in [0, 1],
  got 1.5"; nu_m = 0.5 raises "matrix Poisson ratio nu_m must be in
  [0, 0.5), got 0.5"; a zero fiber transverse modulus raises "fiber
  transverse modulus E_fT must be a positive number, got 0.0"; a zero
  matrix shear modulus raises "matrix shear modulus G_m must be a
  positive number, got 0.0"; a boolean volume fraction raises "fiber
  volume fraction must be in [0, 1], got True"; a soft fiber shear
  raises "the fiber must be the stiffer shear phase, got G_f
  1296296296.2962961 with G_m 27000000000.0"; a soft fiber
  cross-section raises "the fiber must be the stiffer cross-section
  phase, got k_f 2430555555.555556 with k_m 4320987654.320987".
- The anchor's internal asserts (magnitude gates, nested bands, the
  G12 identity, the V_f = 0 and 1 limits, the E2-in-band sweep over
  V_f in [0.3, 0.9], determinism, every ValueError) all pass and the
  anchor exits 0.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w47spec/anchor_unidirectional_lamina_micromechanics.py (stdlib
math, closed form, exit 0, no randomness, identical under both
interpreters).

## Validation list (contract test must include)

1. Worked example asserts within 1e-6 relative: e1_longitudinal(230e9,
   3.5e9, 0.6) = 139.4e9; nu12_major(0.2, 0.35, 0.6) = 0.26;
   e2_halpin_tsai(20e9, 3.5e9, 0.6) = 9578947368.421053 within 1e-6
   relative; g12_halpin_tsai(27e9, 1.2962962962962963e9, 0.6) =
   4402037250.138515 within 1e-6 relative; rho_composite(1760.0,
   1230.0, 0.6) = 1548.0 within 1e-9; the magnitude gates E1 in
   [135e9, 145e9], E2 in [8e9, 12e9], G12 in [4e9, 6e9] hold.
2. Nested-band asserts at V_f = 0.6 within 1e-6 relative:
   e2_reuss_lower = 6930693069.30693, e2_hs_low = 8821708541.607254,
   e2 = 9578947368.421053, e2_hs_up = 10939798623.57372,
   e2_voigt_upper = 13.4e9, ordered strictly increasing; and
   g12_reuss_lower = 3023032629.5585403, g12 = g12_hs_low =
   4402037250.138515, g12_hs_up = 12608294930.875574,
   g12_voigt_upper = 16718518518.518518, ordered with the equality.
3. G12 identity: g12_halpin_tsai(g_f, g_m, v_f) with the default
   xi = XI_G12 equals g12_hashin_shtrikman_bounds(g_f, g_m, v_f)[0]
   within 1e-9 relative at the worked inputs and at V_f in {0.3, 0.5,
   0.7}; both equal the closed form G_m (G_f (1 + V_f) + G_m (1 - V_f))
   / (G_f (1 - V_f) + G_m (1 + V_f)).
4. V_f = 0 degeneracy: E1 = E_m, nu12 = nu_m, E2 = E_m, G12 = G_m,
   rho = rho_m exactly within 1e-9; the E2 Hashin-Shtrikman band
   degenerates (lower equals upper within 1e-9 and equals E_m).
5. V_f = 1 degeneracy: E1 = E_f, nu12 = nu_f, e2_halpin_tsai =
   E_fT within 1e-9, g12_halpin_tsai = G_f within 1e-9, rho = rho_f;
   the E2 band closes to a point (lower equals upper within 1e-9).
6. E2-in-band sweep: for V_f in {0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9}
   at the worked constituents, e2_hashin_shtrikman_bounds()[0] <=
   e2_halpin_tsai() <= e2_hashin_shtrikman_bounds()[1]; the sweep
   deliberately starts at 0.3, the documented lower edge of the
   band-verification range (the xi = 2 estimator dips under the
   variational lower bound below roughly V_f = 0.25, per Wall 1997).
7. Isotropic-fiber collapse: with e_ft = e_f and
   g_f = e_f / (2 (1 + nu_f)) (an E-glass-style fiber), every
   transverse output of the module equals the classic single-fiber-
   modulus forms on the same inputs; e2_halpin_tsai with e_ft = e_f
   equals the textbook Halpin-Tsai E2 written with E_f.
8. Matrix shear derivation: shear_modulus_isotropic(3.5e9, 0.35) =
   1296296296.2962961 within 1e-9; the one-shot dict
   unidirectional_lamina_constants reports "rho" only when both
   densities are passed and omits it when either is None.
9. ValueErrors raise from the named public function with the real
   message prefixes quoted in the Worked example: zero or boolean
   moduli and densities ("... must be a positive number, got ..."), nu
   at or above 0.5 or negative ("... must be in [0, 0.5), got ..."), V_f
   outside [0, 1] ("fiber volume fraction must be in [0, 1], got ..."),
   G_f at most G_m ("the fiber must be the stiffer shear phase, got
   ..."), k_fx or g_fx at most the matrix value ("the fiber must be the
   stiffer cross-section phase, got ..."), and a non-positive xi.
10. Determinism: two consecutive one-shot calls return identical
    dicts; no randomness anywhere; no imports beyond math; module
    constants XI_E2 = 2.0 and XI_G12 = 1.0 fixed as above.
11. No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere. Test passes under BOTH
    interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).
12. Run the deterministic contract test offline (no network); it
    exits 0. All worked-example numbers above were verified identical
    under both interpreters before spec time.

## Corpus fragment (eval/hit1-wave47-unidirectional-lamina-micromechanics.yaml)

Query 1 (copy verbatim):
  "predict the unidirectional-lamina stiffness properties of the
  T300/5208 ply at 0.60 fiber-volume-fraction by the rule-of-mixtures
  longitudinal modulus and Poisson ratio and the halpin-tsai transverse
  and in-plane shear moduli from the fiber and matrix constituent
  properties, then verify the transverse modulus against the
  hashin-shtrikman bounds"
  intent: "structures/composites; unidirectional-lamina-micromechanics:
  the E1 longitudinal modulus and nu12 major Poisson ratio by the
  rule-of-mixtures from the fiber axial modulus and the matrix modulus,
  the E2 transverse modulus by the halpin-tsai closed form with the
  fiber transverse modulus and the xi equal to 2 shape factor, the G12
  in-plane shear modulus by the halpin-tsai closed form with the fiber
  shear modulus and the xi equal to 1 shape factor, at the 0.60
  fiber-volume-fraction of the T300/5208 ply, with the transverse
  modulus verified against the hashin-shtrikman band"
  expected_skill: "structures/composites/unidirectional-lamina-micromechanics"
Query 2 (copy verbatim):
  "compute the E1, E2 and G12 lamina engineering constants of an
  E-glass-epoxy unidirectional ply from the fiber and matrix moduli,
  the fiber-volume-fraction and the standard halpin-tsai shape factors,
  and report the voigt-reuss bound band the transverse modulus must
  fall inside for the laminate-stiffness chain"
  intent: "structures/composites; unidirectional-lamina-micromechanics:
  the E1, E2 and G12 lamina engineering constants of the isotropic-
  fiber E-glass-epoxy ply (the isotropic-fiber collapse, e_ft = e_f and
  g_f derived from the fiber modulus and Poisson ratio), with the
  voigt-reuss bound band reported as the envelope, producing the
  engineering constants the laminate-stiffness chain consumes"
  expected_skill: "structures/composites/unidirectional-lamina-micromechanics"
Task ids: w47-unidirectional-lamina-micromechanics-1 and -2. Prep grep
(run at spec time by the probe, re-run fresh): each of the tokens
halpin, micromechanic, rule-of-mixtures, fiber-volume-fraction,
constituent-property, voigt-bound, reuss-bound, hashin-shtrikman
returns ZERO matches in every skills/ SKILL.md and in
eval/hit1-corpus.yaml (grep exit 1; re-run grep -icE
"halpin|micromechanic|fiber-volume-fraction|rule.of.mixture" over the
1286-block corpus returns 0), so the queries are collision-free; the 85
existing lamina-token corpus tasks are CLT tasks starting from given
constants and carry laminate-a-matrix, ply-stiffness and rotation
language, none of which overlap the constituent-prediction surface.
Add one routing bullet to laminate-stiffness at build time pointing
fiber-volume-fraction and "lamina constants from fiber and matrix"
questions at the new leaf (wave-45 routing-line precedent).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must predict the engineering
constants of a unidirectional composite lamina from the fiber and
matrix constituent properties and the fiber volume fraction:" and
include the outputs in the Claim order (the longitudinal modulus E1 and
the major Poisson ratio nu12 by the rule of mixtures, the transverse
modulus E2 by the Halpin-Tsai closed form with the xi equal to 2 shape
factor, the in-plane shear modulus G12 by the Halpin-Tsai closed form
with the xi equal to 1 shape factor, the density by rule of mixtures,
and the Voigt-Reuss and Hashin-Shtrikman bound bands as the
verification envelope), then close with the Trigger list. Refer to the
fiber transverse modulus E_fT and the fiber shear modulus G_f as
constituent properties of the transversely isotropic fiber throughout;
never claim the ply stiffness, the rotated stiffness, the laminate A
matrix or any failure or hygrothermal output, and never present
property values as design data (cmh-17 is reference-only context).
First tag: unidirectional-lamina-micromechanics. Metadata tags EXACTLY
as the probe receipt gate (f) lists them, nothing else:
rule-of-mixtures, halpin-tsai-equations, fiber-volume-fraction,
constituent-property-prediction, voigt-reuss-bounds,
hashin-shtrikman-bounds. 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term, action verb present. Recommended wording
(149 words, 963 chars, verified at spec time):

"Use when you must predict the engineering constants of a unidirectional
composite lamina from the fiber and matrix constituent properties and
the fiber volume fraction: compute the longitudinal modulus E1 and the
major Poisson ratio nu12 by the rule of mixtures, the transverse
modulus E2 by the Halpin-Tsai closed form with the xi equal to 2 shape
factor on the fiber transverse modulus, the in-plane shear modulus G12
by the Halpin-Tsai closed form with the xi equal to 1 shape factor on
the fiber shear modulus, and the density by the rule of mixtures.
Produces the lamina engineering constants in the material axes and the
Voigt-Reuss and Hashin-Shtrikman bound bands on E2 and G12 as the
verification envelope predictions fall inside. Constituent properties
are inputs; no property tables are reproduced. Trigger: unidirectional
lamina micromechanics, fiber volume fraction, rule of mixtures, halpin
tsai transverse and shear moduli, hashin shtrikman bounds."

FORBIDDEN TOKENS (belong to siblings): ply-stiffness, ply-stiffness-
matrix, q11, q12, q22, q66, qbar, rotated-ply-stiffness, laminate-a-
matrix, laminate-stiffness-matrix, abd-matrix, classical-lamination-
theory and any claim that computes the ply or laminate stiffness from
the constants (laminate-stiffness owns the stiffness assembly; here E1,
E2, nu12 and G12 are OUTPUTS produced from constituents, never inputs
collected); tsai-wu, tsai-hill, max-stress, failure-index, first-ply-
failure, ply-allowables, strength-allowables and any failure verdict
(failure-criteria, laminate-first-ply-failure); a-basis, b-basis,
tolerance-k-factor, coupon-pooling, knockdown-factor, laminate-
allowables and any coupon-test-data statistics (cmh17-allowables);
moisture-content, cte, cme, hygrothermal-strain, cure-cooldown and any
coefficient of thermal expansion or hygrothermal quantity
(laminate-hygrothermal-response, which owns that vein); buckling,
critical-load, plate-buckling (laminate-plate-buckling); bearing,
bypass, net-tension, shear-out, bolt, fastener (composite-bolted-
joints); peel-stress, adhesive-bond (peel-stress-bonded-joints,
adhesive-bonded-joints); core-shear, face-wrinkling, sandwich
(sandwich-panels); delamination-growth and composite-repair content;
material-selection, mmpsd, property-tables, design-values and any
representative property band or design-value table
(structures/materials/material-selection and mmpsd-allowables); and the
bare single words lamina, laminate, stiffness, modulus, fiber, matrix,
composite, bound, volume, fraction, density, strength, moisture as
standalone metadata tags (use only the hyphenated compounds listed
above). CMH-17 is referenced for constituent and lamina property data
conventions only, never reproduced verbatim.

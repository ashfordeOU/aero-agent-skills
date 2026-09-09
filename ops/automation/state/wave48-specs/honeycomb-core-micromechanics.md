# Wave-48 leaf spec: honeycomb-core-micromechanics (structures, composites pack)

- Path: skills/structures/composites/honeycomb-core-micromechanics/
- Pack: structures/composites (13 leaves present at this HEAD:
  adhesive-bonded-joints, cmh17-allowables, composite-bolted-joints,
  composite-repair, delamination-growth, failure-criteria,
  laminate-first-ply-failure, laminate-hygrothermal-response,
  laminate-plate-buckling, laminate-stiffness, peel-stress-bonded-joints,
  sandwich-panels, unidirectional-lamina-micromechanics; the panel-level
  owner sandwich-panels sits in-pack and collects the core modulus and
  core shear modulus as GIVEN workflow inputs, the exact outputs this
  leaf produces; adjacent fence on the property-value side:
  structures/materials/material-selection). Wave-48 probe receipt task-5
  rank-1 GO; 0 owners verified whole-tree at prep (greps below re-run at
  spec time).
- Claim fences (quoted from the sibling frontmatter and bodies at spec
  time, re-verified at HEAD a29a1608; the nearest owner,
  sandwich-panels, treats the core modulus Ec and the core shear modulus
  Gc as COLLECTED INPUTS and compares Gc/rho bands only for core
  SELECTION, never predicting either property from the cell geometry,
  the implicit hand-off this leaf closes):
  - sandwich-panels frontmatter description (line 3): "Use when the
    task is sandwich panel sizing or analysis, honeycomb or foam core
    selection, face sheet stress or core shear failure checks, face
    wrinkling, or sandwich bending stiffness and deflection. Design and
    analyze aerospace sandwich panels: compute the equivalent bending
    stiffness from the face modulus, face thickness, and core
    thickness, the face sheet stresses from a bending moment, the core
    shear stress from a shear load..." The core properties are given
    panel inputs; the leaf analyzes the panel, it never derives the
    core material.
  - sandwich-panels workflow step 1 (lines 62-65): "1. Collect the
    configuration: face modulus Ef and poisson ratio nu, face thickness
    t, core thickness c, core modulus Ec, core shear modulus Gc, and
    the loads (moment M, shear V, or distributed load q over span L)."
    Ec and Gc are COLLECTED INPUTS at step 1; derivation of either
    from the cell geometry is neither produced nor fenced there, it is
    simply absent.
  - sandwich-panels domain quick reference (lines 56-58): "Core
    selection: honeycomb wins on specific shear stiffness (Gc/rho,
    typically 3-10x foam); foam wins on impact tolerance, moisture
    immunity, and cost on contoured parts." Gc/rho is compared as a
    given band for core SELECTION, never predicted from geometry.
  - sandwich-panels workflow step 7 (lines 77-79): "7. Select the core
    type with select_core: weight-critical flat panels favor honeycomb,
    impact- or moisture-critical or contoured parts favor foam." A
    selection verdict on collected inputs, not a property prediction.
  - laminate-hygrothermal-response Related leaves (line 185):
    "structures/composites/sandwich-panels: honeycomb core selection"
    a routing line only, the sole other honeycomb mention in the tree;
    no leaf anywhere predicts core properties from cell geometry.
  - Producer-pattern precedent in-pack: unidirectional-lamina-
    micromechanics Related leaves (lines 154-157): "consumes E1, E2,
    nu12 and G12 as workflow step 1 inputs to build the ply stiffness,
    rotate it and assemble the laminate A matrix; this leaf produces
    those four constants, it never assembles stiffness matrices." The
    honeycomb core leaf holds the same relationship to
    sandwich-panels' step 1 Ec/Gc inputs.
  - Whole-tree greps at prep (probe receipt gate (a), fresh at HEAD and
    re-run at spec time): gibson, cell-wall, relative-density,
    hexagonal-cell return ZERO files across every skills/ SKILL.md and
    ZERO of 1306 eval/hit1-corpus.yaml task blocks; honeycomb returns
    exactly two files (sandwich-panels and the
    laminate-hygrothermal-response routing line above) and 2 corpus
    blocks, both sandwich-panels core-SELECTION tasks on given
    properties; the wave-41..47 recon dirs, leaf plans and specs return
    zero (NEVER adjudicated; the only wave-48 files mentioning the
    candidate are its own receipt, its leaf plan and one incidental
    MMOD spec in another family). GENUINE composites producer gap
    (probe receipt task-5, verified zero-owner, GO rank 1).
- Standards id: cmh-17 (CMH-17, Composite Materials Handbook; the vol. 6
  core convention that brackets the magnitudes this prediction produces,
  reference-only and never reproduced; grep 'id: cmh-17' at
  standards-map.yaml line 281, re-verified at spec time). Ledger
  Standard: cmh-17.
- Family: structures

## Claim

Predict the equivalent mechanical properties of an aerospace hexagonal
honeycomb core from the cell geometry (wall thickness t, inclined wall
edge length l, vertical double-wall height h, cell angle theta) and the
foil material (E_s, G_s or E_s with nu_s, rho_s), the producer side of
the core-property chain that the sandwich panel leaf takes as given
input. The cell has double-thickness vertical walls, the standard
honeycomb construction convention. Outputs: the relative density of the
hexagonal cell rho*/rho_s = (t/l)(h/l+2)/(2 cos(theta)(h/l+sin(theta))),
which reduces to (2/sqrt(3))(t/l) for the regular hexagon h/l = 1,
theta = 30 deg; the core density rho* = rho_s (rho*/rho_s); the
stabilized out-of-plane compressive modulus E3 = E_s (rho*/rho_s); the
out-of-plane shear closed forms G13/G_s = (t/l) cos(theta)/(h/l +
sin(theta)) and G23/G_s = (t/l)(h/l + sin(theta))/((h/l)^2 cos(theta)
(2 h/l + 1)), which coincide at the regular hexagon with the published
reduction G13 = G23 = G_s (rho*/rho_s)/2; and the in-plane
cell-wall-bending moduli E1*, E2* and G12* that scale with (t/l)^3, the
wall-bending stiffness of the cell. The foil is the isotropic aluminum
alloy sheet of the core, so G_s = E_s/(2(1 + nu_s)) when only E_s and
nu_s are given. Magnitude gate (probe receipt gate (d), reproduced by
the anchor run): a regular-hex 5056 core with t/l = 0.02 gives
rho*/rho_s = 0.0231, E3 ~ 1.66 GPa and core density ~ 61 kg/m^3,
order-of-magnitude inside the published mid-density 1/8-inch 5056 core
band. Does NOT do: the panel-level sandwich analysis on the given core,
the equivalent bending stiffness D from the face and core thicknesses,
the face sheet stresses from a bending moment, the core shear stress
and margin from a shear load, the face wrinkling stress, and the
bending plus core shear deflection terms
(structures/composites/sandwich-panels, whose workflow step 1 collects
"core modulus Ec, core shear modulus Gc" as inputs, the exact outputs
this leaf produces from geometry); the Gc/rho specific-shear band
comparison and the honeycomb-versus-foam selection verdict
(sandwich-panels select_core, the core SELECTION slice, which takes
Gc and rho as given); empirical core property bands and datasheet
values for any specific commercial core, Hexcel and CMH-17 included
(cell-geometry arithmetic only; published bands are reference context,
never reproduced tables); material property VALUES, selection bands and
design-value tables (structures/materials/material-selection and
mmpsd-allowables); foam core, nomex core, metallic faces, inserts and
the remaining sandwich content the wave-45/46 declines carried; and the
constituent-to-lamina constants of the fiber composite siblings
(structures/composites/unidirectional-lamina-micromechanics owns that
seam; a honeycomb core is a foil cellular structure, not a fiber
composite). Cell geometry and foil properties are inputs, never
estimated or looked up; the model is closed-form arithmetic in SI units
on the perfect hexagonal cell; core defects, node bond quality, foil
wrinkles, moisture, fatigue and statistical scatter are out of scope.

## Model (implement exactly)

Pure stdlib (math only), closed form, deterministic, no RNG, no tables.
All moduli in Pa, density in kg/m^3, length ratios dimensionless, the
cell angle in degrees (converted to radians inside every function with
math.radians). Geometry conventions (Gibson and Ashby, Cellular Solids:
Structure and Properties, 2nd ed., CUP 1997, ch. 4 "Honeycomb
materials"): axis 1 is the ribbon direction of the vertical double
walls, axis 2 the transverse direction in the core plane, axis 3 the
out-of-plane core thickness direction; h is the vertical double-wall
length, l the inclined wall length, t the foil wall thickness, theta
the angle of the inclined walls to the 1 axis; the double-thickness
vertical walls are already embedded in the published closed forms (the
(h/l + 2) term of the relative density numerator). The foil is the
isotropic aluminum alloy sheet (5056, 7075 and similar), E_s its
modulus, nu_s its Poisson ratio, rho_s its density.

Defining relations (pin these exactly; every function derives from
them):
- rho*/rho_s = (t/l)(h/l + 2)/(2 cos(theta)(h/l + sin(theta))), the
  relative density of the hexagonal cell with double-thickness vertical
  walls. Regular hexagon h/l = 1, theta = 30 deg: rho*/rho_s =
  (2/sqrt(3))(t/l).
- rho* = rho_s (rho*/rho_s), the core density.
- E3 = E_s (rho*/rho_s), the stabilized out-of-plane compressive
  modulus (the stabilized core, the in-service condition; the
  unstabilized crush strength is not a modulus and is out of scope).
- G13/G_s = (t/l) cos(theta)/(h/l + sin(theta)), the out-of-plane shear
  modulus in the ribbon plane.
- G23/G_s = (t/l)(h/l + sin(theta))/((h/l)^2 cos(theta)(2 h/l + 1)),
  the out-of-plane shear modulus in the transverse plane.
- Regular-hexagon shear reduction: at h/l = 1, theta = 30 deg both
  closed forms coincide and G13 = G23 = G_s (rho*/rho_s)/2, exactly
  the published reduction (each equals G_s t/l / sqrt(3)).
- In-plane cell-wall-bending moduli (the cell walls bend as
  beams, the (t/l)^3 stiffness scaling):
  E1*/E_s = (t/l)^3 cos(theta)/((h/l + sin(theta)) sin^2(theta)),
  E2*/E_s = (t/l)^3 (h/l + sin(theta))/cos^3(theta),
  G12*/E_s = (t/l)^3 (h/l + sin(theta))/((h/l)^2 (1 + 2 h/l)
  cos(theta)). Regular hexagon: E1* = E2* and G12* = E1*/4 (the in-
  plane Poisson ratio of the regular hexagonal cell is exactly 1).
- G_s = E_s/(2(1 + nu_s)), the isotropic foil shear modulus, derived
  when only E_s and nu_s are given (aluminum foil is isotropic).

Functions (every public function validates its inputs identically;
ValueError, never assert; booleans are rejected by every numeric
check):
- shear_modulus_isotropic(e_s, nu_s) -> float: G_s = E_s/(2(1 + nu_s)).
  ValueErrors: e_s not a positive number ("foil modulus E_s must be a
  positive number, got ..."), nu_s not in [0, 0.5) ("foil Poisson ratio
  nu_s must be in [0, 0.5), got ...").
- relative_density(t_l, h_l, theta_deg) -> float: the closed form
  above, dimensionless. ValueErrors: t_l not in (0, 1) ("wall
  thickness to edge-length ratio t/l must be in (0, 1), got ..."), h_l
  not a positive number ("cell aspect ratio h/l must be a positive
  number, got ..."), theta_deg not in (0, 90) ("cell angle theta must
  be in (0, 90) degrees, got ...").
- core_density(rho_s, t_l, h_l, theta_deg) -> float: rho_s times
  relative_density, kg/m^3. ValueError: rho_s not positive ("foil
  density rho_s must be a positive number, got ...").
- compressive_modulus_e3(e_s, t_l, h_l, theta_deg) -> float: the
  stabilized modulus E3 = E_s (rho*/rho_s), Pa.
- shear_modulus_g13(g_s, t_l, h_l, theta_deg) -> float and
  shear_modulus_g23(g_s, t_l, h_l, theta_deg) -> float: the two
  out-of-plane shear closed forms, Pa. ValueError: g_s not positive
  ("foil shear modulus G_s must be a positive number, got ...").
- inplane_modulus_e1(e_s, t_l, h_l, theta_deg) -> float,
  inplane_modulus_e2(e_s, t_l, h_l, theta_deg) -> float and
  inplane_shear_modulus_g12(e_s, t_l, h_l, theta_deg) -> float: the
  three in-plane cell-wall-bending moduli, Pa.
- honeycomb_core_properties(e_s, nu_s, rho_s, t_l, h_l, theta_deg,
  g_s=None) -> dict: the one-shot report. Keys: "relative_density"
  (dimensionless), "core_density" (kg/m^3), "e3", "g13", "g23" (Pa,
  out-of-plane), "e1", "e2", "g12" (Pa, in-plane cell-wall-bending),
  and the ratios "e3_over_es", "g13_over_gs", "g23_over_gs"
  (dimensionless). When g_s is None the foil shear modulus is derived
  by shear_modulus_isotropic(e_s, nu_s); an explicit g_s is validated
  and used as given. Same ValueErrors.

Identities to test (closed form, checkable without the builder
module):
- Regular-hexagon reduction identity: relative_density(t_l, 1.0, 30.0)
  equals (2/sqrt(3)) t_l exactly within 1e-12 relative, and at h/l = 1,
  theta = 30 deg both out-of-plane shear closed forms equal
  G_s (rho*/rho_s)/2 = G_s t_l / sqrt(3). Real anchor (t_l = 0.02,
  5056 foil): relative_density 0.023094010767585 on both sides and
  G13 = G23 = 312550521.666564 Pa on all three sides.
- G13/G23 ordering sanity at h/l = 1: the ratio of the two closed forms
  equals the algebraic identity (h/l)^2 cos^2(theta)(2 h/l + 1)/
  (h/l + sin(theta))^2 within 1e-12 relative at any geometry, equals
  exactly 1 at h/l = 1 with theta = 30 deg (real anchor ratio
  1.000000000), sits below 1 for h/l below 1 and above 1 for h/l above
  1 at theta = 30 deg (real anchor sweep: 0.375000000 at h/l = 0.5,
  0.738461538 at 0.8, 1.270588235 at 1.2, 1.687500000 at 1.5,
  2.400000000 at 2.0), so the ordering never flips spuriously through
  the regular-hexagon point.
- In-plane isotropy degeneracy: at h/l = 1, theta = 30 deg the in-plane
  cell-wall-bending moduli give E1* = E2* (real anchor 1330215.0202129
  Pa both sides) and G12* = E1*/4 (real anchor 332553.755053225 Pa),
  the in-plane Poisson ratio of the regular hexagonal cell being
  exactly 1.
- E3 linear scaling: E3 is exactly linear in the foil modulus at fixed
  geometry (doubling E_s doubles E3 within 1e-12 relative), the
  signature of a stabilized compressive modulus proportional to the
  relative density.
- Determinism: identical outputs run to run, identical under both
  interpreters; no randomness; no imports beyond math.

## Worked example

Realistic aerospace aluminum foil honeycomb cores, all values below are
REAL outputs of the prep anchor /tmp/w48spec/anchor_honeycomb_core.py
(pure stdlib, math only, closed form, exit 0, no RNG), run once and
quoted as printed, then re-verified identical under /usr/bin/python3
3.9.6 and the 3.13.12 interpreter (numeric stdout byte-identical; only
the version header line differs).

Case A (main worked example, the probe receipt gate (d) magnitude
case): regular-hex 1/8-inch-class 5056 aluminum foil core, h/l = 1,
theta = 30 deg, t/l = 0.02, E_s = 72.0 GPa, nu_s = 0.33, rho_s = 2640.0
kg/m^3. The foil shear modulus is derived:
G_s = 72.0/(2(1 + 0.33)) = 27067669172.9323 Pa.

- Relative density: rho*/rho_s = 0.023094010767585 = (2/sqrt(3))
  (0.02) = 0.023094010767585 (regular-hexagon reduction, agreement to
  the 3e-16 relative level). The probe receipt magnitude gate quotes
  0.0231.
- Core density: rho* = 60.9681884264245 kg/m^3 (60.968188 kg/m^3;
  receipt gate quotes ~61 kg/m^3).
- Stabilized compressive modulus: E3 = 1662768775.26612 Pa = 1.662769
  GPa (receipt gate quotes ~1.66 GPa, inside the published mid-density
  1/8-inch 5056 band).
- Out-of-plane shear moduli: G13 = G23 = 312550521.666564 Pa =
  312.550522 MPa, equal at the regular hexagon and equal to
  G_s (rho*/rho_s)/2 (real anchor relative errors 3.81e-16 and 0).
- In-plane cell-wall-bending moduli (MPa scale, the (t/l)^3 bending
  stiffness): E1* = E2* = 1330215.0202129 Pa = 1.330215 MPa and
  G12* = 332553.755053225 Pa = 0.332554 MPa = E1*/4.

Case B (corpus query 1 geometry): the 3.2 mm cell, 0.038 mm foil
regular-hex 5056 core. The regular-hex cell size s (distance across
flats) = sqrt(3) l, so l = 3.2/sqrt(3) = 1.847521 mm and
t/l = 0.038/1.847521 = 0.020568103; the sqrt(3) cancels in the
reduction, giving exactly rho*/rho_s = (2/sqrt(3)) t/l = 2 (0.038)/3.2
= 0.02375. Anchor outputs: E3 = 1710000000 Pa = 1.710000 GPa, core
density = 62.700000 kg/m^3, G13 = G23 = 321.428571 MPa.

Case C (corpus query 2 geometry): 7075 foil (E_s = 71.7 GPa,
nu_s = 0.33, rho_s = 2810.0 kg/m^3), elongated cell h/l = 1.5,
theta = 30 deg, t/l = 0.02, the geometry that separates the two
out-of-plane shear directions. Anchor outputs: rho*/rho_s =
0.0202072594216369, core density = 56.782399 kg/m^3, E3 =
1448860500.53137 Pa = 1.448861 GPa, G13 = 233436170.869715 Pa =
233.436171 MPa and G23 = 138332545.700572 Pa = 138.332546 MPa, with
G13/G23 = 1.687500000 exactly the closed-form ratio.

Identities with real numbers (anchor output): regular-hexagon
reduction relative error 3e-16; G13 = G23 = G_s (rho*/rho_s)/2 with
relative errors 3.81e-16 (G13) and 0 (G23); E1* = E2* relative error
5.25e-16; G12* = E1*/4 relative error 3.5e-16; the G13/G23 ratio equals
the closed form at every h/l in the sweep with equality exactly 1 at
h/l = 1.

Real ValueError messages (module output, quoted as raised): t_l = 0.0
raises "wall thickness to edge-length ratio t/l must be in (0, 1), got
0.0"; t_l = 1.0 raises the same with "got 1.0"; h_l = 0.0 raises "cell
aspect ratio h/l must be a positive number, got 0.0"; theta = 0.0 and
90.0 deg raise "cell angle theta must be in (0, 90) degrees, got 0.0"
and "... got 90.0"; theta = -30.0 deg raises the same with "got
-30.0"; E_s = 0.0 raises "foil modulus E_s must be a positive number,
got 0.0"; nu_s = 0.5 raises "foil Poisson ratio nu_s must be in [0,
0.5), got 0.5"; rho_s = 0.0 raises "foil density rho_s must be a
positive number, got 0.0"; an explicit G_s = 0.0 raises "foil shear
modulus G_s must be a positive number, got 0.0"; t_l = True raises
"wall thickness to edge-length ratio t/l must be in (0, 1), got True";
E_s = True raises "foil modulus E_s must be a positive number, got
True".

The anchor's internal asserts (magnitude gates rho*/rho_s ~ 0.0231,
E3 ~ 1.66 GPa, core density ~ 61 kg/m^3, E3 linear scaling under a
doubled foil modulus, the regular-hexagon reductions, the G13/G23
ordering sweep with the closed-form ratio at six h/l values, the
in-plane isotropy degeneracy, determinism, every ValueError) all pass
and the anchor exits 0.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w48spec/anchor_honeycomb_core.py (stdlib math, closed form, exit
0, no randomness, identical under both interpreters).

## Validation list (contract test must include)

1. Worked example asserts within 1e-6 relative: relative_density(0.02,
   1.0, 30.0) = 0.023094010767585; core_density(2640.0, 0.02, 1.0,
   30.0) = 60.9681884264245; compressive_modulus_e3(72.0e9, 0.02, 1.0,
   30.0) = 1662768775.26612; shear_modulus_g13(g_s, 0.02, 1.0, 30.0) =
   shear_modulus_g23(g_s, 0.02, 1.0, 30.0) = 312550521.666564 with
   g_s = shear_modulus_isotropic(72.0e9, 0.33) = 27067669172.9323;
   inplane_modulus_e1 = inplane_modulus_e2 = 1330215.0202129;
   inplane_shear_modulus_g12 = 332553.755053225; the magnitude gates
   rho*/rho_s in [0.02, 0.026], E3 in [1.5e9, 1.8e9], core density in
   [55.0, 68.0], G13/G23 in [0.25e9, 0.40e9] hold.
2. Regular-hexagon reduction identity within 1e-9 relative:
   relative_density(t_l, 1.0, 30.0) equals (2/sqrt(3)) t_l and both
   out-of-plane shear moduli equal g_s (rho*/rho_s)/2 at t_l in {0.01,
   0.02, 0.05} with the worked foil.
3. G13/G23 ordering sanity at h/l = 1: shear_modulus_g13 divided by
   shear_modulus_g23 equals the closed form (h/l)^2 cos^2(theta)(2
   h/l + 1)/(h/l + sin(theta))^2 within 1e-12 relative at h/l in
   {0.5, 0.8, 1.0, 1.2, 1.5, 2.0} with theta = 30 deg, equals 1 within
   1e-9 exactly at h/l = 1 (real values 0.375000000, 0.738461538,
   1.000000000, 1.270588235, 1.687500000, 2.400000000), sits below 1
   for h/l below 1 and above 1 for h/l above 1 (g13 > g23 at h/l = 2.0,
   g13 < g23 at h/l = 0.5).
4. In-plane isotropy degeneracy within 1e-9 relative at h/l = 1,
   theta = 30 deg: inplane_modulus_e1 equals inplane_modulus_e2 and
   inplane_shear_modulus_g12 equals e1/4 (real values 1330215.0202129
   and 332553.755053225 at the worked inputs).
5. Case B corpus core: t_l = 0.038/(3.2/sqrt(3)) = 0.020568103;
   relative_density equals 0.02375 within 1e-9 (the sqrt(3) cancels:
   rho*/rho_s = 2 (0.038)/3.2), e3 = 1710000000 within 1e-9,
   core_density = 62.7 within 1e-9, g13 = g23 within 1e-9 relative.
6. Case C ordering and magnitude: with the 7075 foil inputs and
   h_l = 1.5, theta = 30 deg, g13/g23 = 1.6875 within 1e-9 relative,
   g13 strictly above g23, e3 = 1448860500.53137 within 1e-6 relative.
7. E3 linear scaling: compressive_modulus_e3(2 E_s, t_l, h_l,
   theta_deg) equals twice compressive_modulus_e3(E_s, t_l, h_l,
   theta_deg) within 1e-12 relative at the worked geometry.
8. Foil shear derivation: shear_modulus_isotropic(72.0e9, 0.33) =
   27067669172.9323 within 1e-9; the one-shot dict
   honeycomb_core_properties with g_s = None equals the dict built
   with the explicit g_s = shear_modulus_isotropic(...) within 1e-12
   relative on every key, and reports all eleven keys.
9. ValueErrors raise from the named public function with the real
   message prefixes quoted in the Worked example: t/l at 0.0, 1.0 or a
   boolean ("wall thickness to edge-length ratio t/l must be in (0, 1),
   got ..."), h/l at 0.0 or below ("cell aspect ratio h/l must be a
   positive number, got ..."), theta at 0.0, 90.0 or negative ("cell
   angle theta must be in (0, 90) degrees, got ..."), E_s at 0.0 or a
   boolean ("foil modulus E_s must be a positive number, got ..."),
   nu_s at or above 0.5 ("foil Poisson ratio nu_s must be in [0, 0.5),
   got ..."), rho_s at 0.0 ("foil density rho_s must be a positive
   number, got ..."), and an explicit g_s at 0.0 ("foil shear modulus
   G_s must be a positive number, got ...").
10. Determinism: two consecutive one-shot calls return identical
    dicts; no randomness anywhere; no imports beyond math.
11. No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere. Test passes under BOTH
    interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).
12. Run the deterministic contract test offline (no network); it
    exits 0. All worked-example numbers above were verified identical
    under both interpreters before spec time (numeric stdout
    byte-identical, version header line apart).

## Corpus fragment (eval/hit1-wave48-honeycomb-core-micromechanics.yaml)

Query 1 (copy verbatim):
  "predict the equivalent-core-properties of the 3.2 mm cell 5056
  aluminum honeycomb core with 0.038 mm foil thickness for the sandwich
  panel: the relative-density, the out-of-plane stabilized compressive
  modulus and the out-of-plane shear moduli from the gibson-ashby
  hexagonal-cell closed forms with the double-thickness vertical cell
  walls and the foil modulus and density inputs for the core-shear
  margin"
  expected_skill: "structures/composites/honeycomb-core-micromechanics"
Query 2 (copy verbatim):
  "compute the honeycomb-core shear modulus G13 and G23 and the core
  density of the 1-8 inch cell 7075 foil core from the cell geometry,
  the cell-wall thickness to edge-length ratio and the foil shear
  modulus by the hexagonal-cell closed forms, the
  equivalent-core-properties the sandwich-panels workflow collects as
  given inputs"
  expected_skill: "structures/composites/honeycomb-core-micromechanics"
Task ids: w48-honeycomb-core-micromechanics-1 and -2. The two query
texts are the wave-48 probe receipt task-5 gate (e) queries verbatim,
sim-verified by replicating the scripts/router_eval.py token router
EXACTLY over the real index plus the hypothetical candidate (receipt
method note): query 1 HIT1 37.5 with runner-up sandwich-panels 29.5
(margin 8.0), query 2 HIT1 28.5 with runner-up sandwich-panels 17.5
(margin 11.0), zero theft over all 1306 corpus tasks (the 2 existing
honeycomb corpus tasks stay owned by sandwich-panels). Prep grep (run
at spec time by the probe, re-run fresh): each of the tokens gibson,
cell-wall, relative-density, hexagonal-cell, double-thickness-cell-
walls, equivalent-core-properties returns ZERO matches in every
skills/ SKILL.md and in eval/hit1-corpus.yaml (grep exit 1; re-run
grep -icE "gibson|cell-wall|relative-density|foil-thickness|cell-size"
over the 1306-block corpus returns 0), so the queries are
collision-free; the 2 existing honeycomb corpus tasks are
sandwich-panels core-SELECTION tasks carrying core-shear margin, face-
wrinkling and honeycomb-versus-foam selection language on given
properties, none of which overlaps the cell-geometry prediction
surface. Add one routing bullet to sandwich-panels at build time
reading that cell-geometry and core-property-prediction questions
belong to the honeycomb-core-micromechanics sibling (wave-45 routing-
line precedent, as noted in the probe receipt gate (f)).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must predict the equivalent
mechanical properties of a hexagonal honeycomb core from the cell
geometry and the foil material:" and include the outputs in the Claim
order (the relative density of the hexagonal cell with the double-
thickness vertical walls, the core density from the foil density, the
stabilized out-of-plane compressive modulus E3 from the foil modulus,
the out-of-plane shear moduli G13 and G23 from the foil shear modulus,
and the in-plane cell-wall-bending moduli E1, E2 and G12), then close
with the Trigger list. Refer to the core properties as the equivalent
core properties predicted from geometry, never as the bare single
words honeycomb, core, shear, modulus, density, foam, sandwich, foil,
cell, geometry or prediction; never claim the panel-level sandwich
bending stiffness, face stresses, core shear stresses, face wrinkling,
deflection or any core SELECTION verdict, and never present core
property values as design data or reproduce Hexcel or CMH-17 core
bands (cmh-17 is reference-only context). First tag:
honeycomb-core-micromechanics. Metadata tags EXACTLY as the probe
receipt gate (f) lists them, nothing else:
hexagonal-honeycomb-cell, gibson-ashby-closed-forms,
equivalent-core-properties, out-of-plane-shear-modulus,
stabilized-compressive-modulus, relative-density,
double-thickness-cell-walls, core-density-prediction. 50-150 words,
<=1000 chars, no em dash, no content-policy sweep term, action verb
present. Recommended wording (146 words, 995 chars, verified at spec
time):

"Use when you must predict the equivalent mechanical properties of a
hexagonal honeycomb core from the cell geometry and the foil material:
compute the relative density of the hexagonal cell with double-thickness
vertical walls, the core density from the foil density, the stabilized
out-of-plane compressive modulus E3 from the foil modulus, the
out-of-plane shear moduli G13 and G23 from the foil shear modulus, and
the in-plane cell-wall-bending moduli E1, E2 and G12 by the Gibson and
Ashby hexagonal-cell closed forms. Produces the equivalent core
properties the sandwich panel workflow collects as given inputs; the
foil shear modulus derives from the foil modulus and Poisson ratio of
the isotropic foil. Cell geometry and foil properties are inputs; no
core property tables are reproduced. Trigger: honeycomb core
micromechanics, hexagonal honeycomb cell, gibson ashby closed forms,
equivalent core properties, out of plane shear modulus, stabilized
compressive modulus, relative density."

FORBIDDEN TOKENS (belong to siblings): core-shear, core-shear-stress,
core-shear-margin, face-stress, face-sheet-stress, face-wrinkling,
wrinkling-stress, sandwich-bending-stiffness, sandwich-deflection,
bending-plus-shear-deflection, select-core, core-selection,
honeycomb-versus-foam, foam-core, honeycomb-core-selection and any
claim that computes a panel stress, a panel stiffness or a panel
deflection from the given core properties, or that selects a core type
against another (sandwich-panels owns the panel-level analysis on
collected inputs and the core SELECTION band comparison; the wave-47
micromechanics spec fenced the bare core-shear, face-wrinkling and
sandwich analysis vocabulary to sandwich-panels, and this leaf extends
that fence to every panel-level and selection token above); hexcel,
datasheet, property-table and any representative core property band or
design value reproduced as data (published bands are reference context
only, never tables); core-crush, crush-strength, stabilized-crush-
strength, plate-shear, bare-compressive and the empirical strength
properties of a specific core grade (out of scope, coupon data
content); and the bare single words honeycomb, core, shear, modulus,
density, foam, sandwich, foil, cell, geometry, prediction as
standalone metadata tags (use only the hyphenated compounds listed
above). CMH-17 is referenced for core property conventions only, never
reproduced verbatim.

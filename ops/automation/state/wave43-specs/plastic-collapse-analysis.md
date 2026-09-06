# Wave-43 leaf spec: plastic-collapse-analysis (structures, fem pack)

- Path: skills/structures/fem/plastic-collapse-analysis/
- Pack: fem (18 leaves present at prep: beam-column-analysis,
  beam-frame-analysis, beam-vibration, buckling-analysis, calculix-linear,
  calculix-nonlinear, contact-analysis, curved-beam-analysis,
  cylindrical-shell-buckling, diagonal-tension-field-webs,
  lug-joint-analysis, modal-analysis, plate-buckling, pressure-bulkhead,
  shear-center-analysis, shrink-fit-analysis, torsion-shear-flow,
  truss-analysis; crippling-analysis, hertzian-contact-stress,
  metallic-fastener-joints and plastic-collapse-analysis are the four
  wave-43 additions of the family). Claim fences (quoted from the sibling
  frontmatter at prep; none owns plastic collapse load analysis of beams
  and frames):
  - beam-frame-analysis (this pack) is the ELASTIC complement: its
    description reads "Use when you must solve a two-dimensional
    rigid-jointed frame with the Euler Bernoulli beam element: build the
    local beam element stiffness from the axial and bending
    contributions, rotate it into the global frame with the member
    orientation, assemble the global stiffness matrix, apply the fixed
    support conditions, solve for the nodal displacements and rotations
    with a compact elimination solver, and recover the support reactions
    and the member end actions. Produces the nodal displacement and
    rotation vector, the support reactions, the member end bending
    moments and shears, and equilibrium checks for a hand-calc or
    stdlib-only frame analysis. Units are SI." That leaf stops at the
    elastic end actions: no yield stress enters, no hinge can form, and
    no collapse load or mechanism exists there. Its tags include
    portal-frame and its triggers include "portal frame"; this leaf
    reaches the same rigid-jointed frames only through the plastic
    collapse load and MUST NOT reuse the portal-frame tag.
  - ramberg-osgood (structures/materials) owns the material stress-strain
    curve only: "build the elastic-plastic stress-strain response of a
    metallic material with the Ramberg-Osgood three-parameter model:
    compute the total strain at a given stress with strain = stress/E +
    0.002*(stress/sigma_0.2)^n, invert the implicit equation by
    bisection for the stress at a required total strain, and derive the
    plastic strain, secant modulus, and tangent modulus along the
    curve". Its plasticity stays at the material point: no section
    plastic modulus, no member bending, no hinge, no structural
    collapse.
  - multiaxial-yield-criteria (structures/materials) owns pointwise yield
    checks of a stress state: "compute the multiaxial yield margin of an
    isotropic metal part: evaluate the von Mises equivalent stress ...,
    compute the Tresca equivalent stress as the maximum principal stress
    difference ..., compute the yield margin yield/equivalent - 1 ...".
    It judges whether one stress state yields, never a mechanism; a
    plastic hinge and a collapse load are out of its scope.
  - strain-life-fatigue (structures/fatigue) owns cyclic behavior: its
    description opens "determine the strain-life (low-cycle fatigue)
    endurance of an aerospace structure: Coffin-Manson total strain
    amplitude from reversals to failure ...". Its plastic strain
    amplitudes are per-cycle fatigue damage quantities, not collapse
    mechanisms.
  - buckling-analysis (this pack) owns elastic instability: "Calculate
    the Euler critical buckling load of slender compression members ...".
    It is elastic stability of a member under compression with no yield
    surface, no moment redistribution and no collapse mechanism.
  - cylindrical-shell-buckling (this pack) uses the word "collapse" only
    for the elastic ovalization (Brazier) collapse of a curved shell
    cross section under bending, an elastic stability phenomenon of a
    different geometry and mechanism.
  Whole-tree greps at prep (real runs, all exit 0): "plastic hinge",
  "plastic collapse", "collapse mechanism", "collapse load", "limit
  analysis" and "plastic-collapse" each give 0 hits in skills/ SKILL.md
  bodies; the only "hinge" hits in the whole tree are control-surface
  hinge moments (propulsion, vehicle-design) and the boundary-condition
  adjective "hinged" in buckling-analysis, none structural-plastic; in
  eval/hit1-corpus.yaml the distinctive tokens plastic-collapse-analysis,
  plastic-hinge, collapse-mechanism and limit-analysis-beam each match 0
  tasks, and the corpus-collisions.py batch-D run (ops/automation/state/
  wave43-recon/corpus-collisions.py, real run) reports 'plastic hinge' 0,
  'plastic collapse' 0, 'shape factor' 0, 'collapse load' 0 and 'fully
  plastic' 0; the only "collapse" word in the corpus is the wave-33
  cylindrical-shell-buckling task ("the bending critical moment and the
  ovalization collapse moment of a thin-walled cylinder"), the elastic
  shell meaning. GENUINE STRUCTURES gap (fresh probe): no leaf computes
  the fully plastic moment, the shape factor, plastic hinge mechanisms or
  the plastic collapse loads of indeterminate beams and frames;
  beam-frame-analysis is elastic by claim and ramberg-osgood stops at the
  stress-strain curve.
- Standards id: far-25, cs-25 (reference-only, both present in
  standards-map.yaml, matching the fem siblings; FAR 25.303 / CS 25.303
  require the structure to withstand 1.5 times the limit loads without
  failure, the ultimate-factor context of the margin below). Ledger
  Standard: far-25, cs-25.
- Family: structures

## Claim

Analyze the plastic collapse (limit state) of beams and simple frames in
rigid-perfectly-plastic bending: compute the fully plastic moment Mp =
sigma_y*Zp of the section from the plastic section modulus Zp, the first
moment of area about the equal-area axis (plastic neutral axis), with the
closed forms Zp = b*h**2/4 for a rectangle of breadth b and depth h, Zp =
d**3/6 for a solid circle of diameter d, and Zp = b*t_f*(d - t_f) +
t_w*(d - 2*t_f)**2/4 for a doubly symmetric I-beam of overall depth d,
flange breadth b, flange thickness t_f and web thickness t_w with the
plastic neutral axis in the web; compute the elastic section modulus Z of
the same section (b*h**2/6, pi*d**3/32, and Z = 2*I/d from I =
(b*d**3 - (b - t_w)*(d - 2*t_f)**3)/12) so the shape factor nu = Zp/Z
gives the reserve between first yield and full plasticity, nu = 1.5
exactly for the rectangle, nu = 16/(3*pi) = 1.69765272631 for the
circle and
 the two-closed-form value for the I-beam (about 1.10 to 1.25 for rolled
shapes, the material pushed into the flanges leaving the least reserve);
form the plastic hinges of the collapse mechanism, r + 1 hinges for a
beam or frame of r-fold static indeterminacy, and apply the kinematic
theorem (virtual work, external work equals the sum of Mp*theta over the
hinge rotations) and the static theorem (the collapse-state equilibrium
moment diagram satisfies |M| <= Mp with equality only at the hinge
stations) to get the plastic collapse loads of the single-span catalog
under one central point load: Wc = 4*Mp/L for the simply supported beam
(one hinge at midspan), Wc = 6*Mp/L for the propped cantilever (hinges at
the fixed end and under the load), Wc = 8*Mp/L for the fixed-fixed beam
(hinges at both supports and midspan), and the sway mechanisms of a
simple rectangular frame under a lateral load at the top: Hc = 2*Mp/h
with pinned bases (hinges at the two top corners) and Hc = 4*Mp/h with
fixed bases (hinges at all four corners); express the result as the
plastic collapse load factor lambda = collapse load / applied (limit)
load and the ultimate margin lambda/1.5 in the FAR 25.303 context, where
the structure must support 1.5 times the limit load, issuing the
adequate/inadequate verdict from collapse load versus 1.5 times the limit
load. Produces the plastic and elastic section moduli, the shape factor,
the fully plastic moment, the first-yield moment My = Mp/nu, the plastic
collapse loads with their hinge counts and stations, the elastic
first-yield loads for context (W_y = 4*My/L simply supported, W_y =
16*My/(3*L) propped with the 3*W*L/16 hogging fixed-end moment, W_y =
8*My/L fixed-fixed), the collapse-to-yield ratios (nu, 9*nu/8 and nu),
the collapse load factors and the ultimate-margin verdicts that gate
metallic beam and frame strength checks and FAR 25.303 ultimate checks.
Does NOT do: elastic stiffness-method frames, nodal displacements,
rotations, elastic member end actions, support reactions or the tag
portal-frame (beam-frame-analysis, which is elastic by claim); the
Ramberg-Osgood material stress-strain curve, plastic strain or secant
modulus at a stress state (ramberg-osgood); von Mises or Tresca pointwise
yield margins of a stress state with no hinge or mechanism
(multiaxial-yield-criteria); cyclic strain-life fatigue amplitudes,
Coffin-Manson or Neuber local strain (strain-life-fatigue, cyclic
behavior); Euler elastic buckling of compression members
(buckling-analysis); crippling or inter-rivet buckling of formed shapes
(crippling-analysis, same wave); elastic shell ovalization collapse and
buckling knockdowns of curved shells (cylindrical-shell-buckling). Scope:
rigid-perfectly-plastic bending, doubly symmetric sections with the
plastic neutral axis in the web for the I-beam, small-deflection
mechanisms, one central point load per span case and one top lateral load
per frame case, constant Mp along each member, no axial-moment (P-delta)
interaction, no distributed-load collapse, no combined mechanisms beyond
the sway mechanism, no strain hardening and no unloading. SI units
(metres, newtons, pascals). Deterministic, pure stdlib.

## Model (implement exactly)

Pure stdlib, math only. All functions take plain SI floats; section
dimensions travel as the positional dims of the section (rectangle (b,
h); circle (d); I-beam (d, b, t_f, t_w), in that order). No module
constants beyond math.

Defining relations (pin these exactly; every function below derives from
them):
- Fully plastic moment: Mp = sigma_y*Zp with Zp the first moment of area
  about the equal-area axis: Zp = sum over one side of the axis of
  A_i*|y_i|, doubled (equivalently (A/2)*(ybar_t - ybar_c) with ybar
  measured from the plastic neutral axis). Closed forms: rectangle Zp =
  b*h**2/4; circle Zp = d**3/6 (= 4*r**3/3); I-beam (doubly symmetric,
  PNA in the web, d > 2*t_f) Zp = b*t_f*(d - t_f) + t_w*(d - 2*t_f)**2/4,
  the flanges at full stress at lever arms about the mid-depth plus the
  two half-webs.
- Elastic section modulus: rectangle Z = b*h**2/6; circle Z = pi*d**3/32;
  I-beam I = (b*d**3 - (b - t_w)*(d - 2*t_f)**3)/12 and Z = 2*I/d. The
  shape factor nu = Zp/Z is exactly 3/2 for the rectangle, exactly
  16/(3*pi) for the circle, and the quotient of the two I-beam closed
  forms otherwise. My = sigma_y*Z = Mp/nu is the first-yield moment, the
  moment at which the extreme fibre reaches sigma_y; the shape factor is
  the section reserve between first yield and the fully plastic state.
- Hinge count rule: a collapse mechanism needs r + 1 plastic hinges for
  r-fold static indeterminacy: 1 (simply supported, r = 0), 2 (propped
  cantilever, r = 1), 3 (fixed-fixed beam, r = 2), 2 (pinned-base frame
  sway, r = 1), 4 (fixed-base frame sway, r = 3). Hinge formation order
  follows the elastic moment peaks: fixed-fixed central load yields the
  two supports first (elastic end moments W*L/8), then the midspan hinge
  completes the mechanism at collapse.
- Kinematic theorem per case (virtual work W*delta = sum Mp*theta_i with
  delta = theta*L/2 under the central load): simply-supported-central,
  1 hinge: Wc = 4*Mp/L; propped-cantilever-central, hinges at the fixed
  end (theta) and under the load (2*theta): Wc = 6*Mp/L;
  fixed-fixed-central, hinges at both supports (theta each) and midspan
  (2*theta): Wc = 8*Mp/L. Frame sway under a top lateral load H, columns
  of height h rotating by theta about the bases, delta = theta*h:
  pinned bases, hinges at the two top corners: Hc = 2*Mp/h; fixed bases,
  hinges at all four corners: Hc = 4*Mp/h.
- Static theorem cross-check (implemented in the anchor, contract test
  may reproduce): at the collapse load the equilibrium moment diagram of
  the mechanism state has |M| <= Mp everywhere and |M| = Mp exactly at
  the hinge stations: fixed-fixed central collapse state, reactions
  Wc/2 at each support, M(x) = -Mp + (Wc/2)*x from x = 0 to L/2 reaching
  +Mp under the load and mirroring to -Mp at x = L; propped collapse
  state, reactions R_A = 4*Mp/L at the fixed end and R_B = 2*Mp/L at the
  pin.
- Elastic first-yield context loads (elastic moment peaks, for the
  collapse-to-yield ratios only): simply supported W_y = 4*My/L (peak
  W*L/4 at midspan), propped cantilever W_y = 16*My/(3*L) (peak 3*W*L/16
  hogging at the fixed end), fixed-fixed W_y = 8*My/L (peaks W*L/8 at
  both ends). Ratios Wc/Wy = nu, 9*nu/8 and nu; the fixed-fixed and
  simply supported beams both collapse at nu times their first-yield
  load while the propped cantilever, with its single hogging peak,
  reaches 1.125*nu.
- FAR 25.303 context: ultimate load = 1.5 times the limit load; the
  plastic collapse load factor lambda = collapse load / limit load must
  reach 1.5, so the ultimate margin lambda/1.5 clears 1 exactly when the
  collapse load clears the 1.5-factor ultimate load.

Functions:
- plastic_section_modulus(shape, *dims) -> float: Zp in m^3 by the
  closed forms above; shapes "rectangle", "circle", "i-beam".
  ValueErrors: unknown shape; wrong dims arity; any dim <= 0; i-beam
  with d <= 2*t_f (plastic neutral axis outside the web) or t_w >= b
  (web not thinner than the flange).
- elastic_section_modulus(shape, *dims) -> float: Z in m^3 by the
  closed forms above. Identical ValueError set.
- shape_factor(shape, *dims) -> float: Zp/Z; 1.5 for the rectangle,
  16/(3*pi) for the circle, the closed-form quotient for the I-beam.
  Identical ValueError set.
- fully_plastic_moment(sigma_y, zp) -> float: sigma_y*zp in N m.
  ValueError if sigma_y <= 0 or zp <= 0. First-yield moment My is not a
  separate function: My = Mp/nu with the shape factor (module
  convention), so callers pass fully_plastic_moment(sigma_y, zp) and
  divide by shape_factor(shape, *dims).
- collapse_load_beam(config, span, mp) -> dict with keys "case",
  "collapse_load" (N), "plastic_hinges", "hinge_locations" (station
  texts) and "mechanism": configs "simply-supported-central" (4*mp/span,
  1 hinge at midspan), "propped-cantilever-central" (6*mp/span, hinges
  at the fixed end x = 0 and under the load x = L/2),
  "fixed-fixed-central" (8*mp/span, hinges at x = 0, L/2, L). ValueError
  if span <= 0, mp <= 0, or an unknown config name.
- portal_sway_collapse_load(height, mp, base = "pinned") -> dict with
  keys "case", "collapse_load" (N), "plastic_hinges" and
  "hinge_locations": base "pinned" gives 2*mp/height with 2 top-corner
  hinges, base "fixed" gives 4*mp/height with 4 corner hinges.
  ValueError if height <= 0, mp <= 0, or an unknown base name.
- collapse_load_factor(limit_load, collapse_load) -> float: collapse
  load divided by the applied (limit) load. ValueError if either
  argument <= 0.
- ultimate_margin(limit_load, collapse_load, ultimate_factor = 1.5) ->
  dict with keys "collapse_load_factor", "ultimate_load_required"
  (ultimate_factor*limit_load), "ultimate_margin" (factor divided by
  ultimate_factor) and "verdict" ("adequate" when collapse_load >=
  ultimate_load_required, else "inadequate"). ValueError if
  ultimate_factor <= 0 (plus the load guard).

Identities to test (closed form, deterministic):
- Shape-factor closed values: rectangle nu = 1.5 exactly (anchor
  residual 0.0); circle nu = 16/(3*pi) (anchor residual
  2.22044604925e-16); nu = Mp/My identity for every section (anchor
  residual 2.22044604925e-16).
- Ordering: nu_circle = 1.69765272631 > nu_rect = 1.5 > nu_I-beam =
  1.12325660721 for the anchor I-beam: flanged sections leave the least
  reserve between first yield and full plasticity.
- Collapse loads at Mp = 31250 N m, L = 3 m: simply supported
  41666.6666667 N (1 hinge), propped 62500 N (2 hinges), fixed-fixed
  83333.3333333 N (3 hinges), each equal to the closed forms 4*Mp/L,
  6*Mp/L, 8*Mp/L.
- Collapse-to-yield ratios: Wc/Wy = 1.5 (simply supported and
  fixed-fixed, = nu) and 1.6875 (propped, = 9*nu/8) at nu = 1.5.
- Static theorem: sampling the collapse-state moment diagram at
  2001 stations gives max |M| = Mp = 31250 N m and overshoot above Mp
  of exactly 0.0 for all three beam cases; the diagram touches Mp only
  at the hinge stations.
- Portal sway: pinned bases Hc = 2*Mp/h = 151744 N (2 hinges) and fixed
  bases Hc = 4*Mp/h = 303488 N (4 hinges) at Mp = 303488 N m, h = 4 m,
  the fixed-base sway exactly double the pinned-base sway.
- Margin logic: verdict adequate exactly when the collapse load clears
  1.5 times the limit load (anchor: 83333.333 N collapse clears the
  60000 N required at a 40000 N limit and fails the 90000 N required at
  a 60000 N limit); pinned-base portal margin 1.68604444444 at a 60000 N
  limit, and the limit load that fails at ultimate is Hc/1.5 =
  101162.666667 N.
- ValueErrors across the module: unknown shape "triangle"; rectangle
  dims with b <= 0; circle d = 0; i-beam d <= 2*t_f (0.2 <= 0.24) and
  wrong arity; sigma_y <= 0; unknown beam case "cantilever-central";
  span = 0; mp <= 0; unknown frame base "propped"; height = 0; limit
  load <= 0; ultimate_factor = 0 (13 anchor cases, each raises).
- Determinism; no imports beyond math; no RNG.

## Worked example

sigma_y = 250 MPa throughout; rectangle 50 x 100 mm (b = 0.05 m, h =
0.1 m), circle d = 0.1 m, I-beam 400 x 200 x 12 x 8 mm (d = 0.4 m, b =
0.2 m, t_f = 0.012 m, t_w = 0.008 m). All values below are REAL outputs
of the prep anchor /tmp/w43spec/anchor_plcol.py (stdlib math, exit 0).

- Section reserves at sigma_y = 250 MPa:
  - Rectangle 50 x 100: Zp = b*h**2/4 = 0.000125 m^3 (125 cm^3), Z =
    b*h**2/6 = 8.33333333333e-05 m^3, nu = 1.5 exactly, Mp =
    sigma_y*Zp = 31250 N m, My = Mp/nu = 20833.3333333 N m.
  - Circle d = 100: Zp = d**3/6 = 0.000166666666667 m^3 (166.7 cm^3),
    Z = pi*d**3/32 = 9.81747704247e-05 m^3, nu = 16/(3*pi) =
    1.69765272631, Mp = 41666.6666667 N m, My = 24543.6926062 N m.
  - I-beam 400 x 200 x 12 x 8: Zp = b*t_f*(d - t_f) + t_w*(d - 2*t_f)**
    2/4 = 0.001213952 m^3, Z = 2*I/d with I = (b*d**3 - (b - t_w)*(d -
    2*t_f)**3)/12 = 0.00108074325333 m^3, nu = 1.12325660721, Mp =
    303488 N m, My = 270185.813333 N m. The shape-factor ladder
    1.6977 (circle) > 1.5 (rectangle) > 1.1233 (I-beam) is the reserve
    ordering: the I-beam puts its material in the flanges, far from the
    neutral axis, so first yield and full plasticity nearly coincide.
  - Identity residuals: |nu - 1.5| = 0.0 for the rectangle, |nu -
    16/(3*pi)| = 2.22044604925e-16 for the circle, |nu - Mp/My| =
    2.22044604925e-16 for every section.
- Single-span beams, rectangle Mp = 31250 N m, L = 3 m, one central
  point load:
  - Collapse loads by the kinematic theorem: simply supported Wc =
    4*Mp/L = 41666.6666667 N (1 hinge at midspan), propped cantilever
    Wc = 6*Mp/L = 62500 N (2 hinges: fixed end and under the load),
    fixed-fixed Wc = 8*Mp/L = 83333.3333333 N (3 hinges: both supports
    and midspan). Each mechanism has r + 1 hinges for its r-fold
    indeterminacy, and the virtual-work identity Wc = (sum of Mp*theta)/
    delta is the whole analysis: the fixed-fixed beam dissipates four
    theta of hinge rotation at one theta*L/2 of deflection, the propped
    cantilever three.
  - Elastic first-yield context (elastic moment peaks: W*L/4 midspan,
    3*W*L/16 hogging at the fixed end, W*L/8 at both ends): W_y =
    27777.7777778 N, 37037.037037 N and 55555.5555556 N. The
    collapse-to-first-yield reserves Wc/Wy = 1.5 (= nu), 1.6875
    (= 9*nu/8) and 1.5 (= nu): the propped cantilever gains the extra
    12.5% because only its fixed-end peak reaches yield before the
    mechanism.
  - Static theorem check at collapse: sampling the collapse-state
    equilibrium moment diagram at 2001 stations, max |M| = 31250 N m =
    Mp with overshoot above Mp exactly 0.0 for all three cases; the
    moment diagram touches Mp only at the hinge stations, e.g. the
    fixed-fixed collapse state runs linearly from -Mp at x = 0 through
    +Mp under the load to -Mp at x = L with reactions Wc/2 = 41666.6667
    N at each support.
- Portal frame, I-beam columns with Mp = 303488 N m, column height h =
  4 m, horizontal load at the top:
  - Sway mechanisms: pinned bases Hc = 2*Mp/h = 151744 N (2 hinges at
    the top corners), fixed bases Hc = 4*Mp/h = 303488 N (4 hinges at
    all corners), exactly double: fixing the feet doubles the hinge
    dissipation.
  - At an applied limit load of 60 kN: pinned bases collapse load
    factor lambda = 2.52906666667, ultimate load required 1.5*60000 =
    90000 N, ultimate margin lambda/1.5 = 1.68604444444, verdict
    adequate (151.7 kN collapse clears 90 kN); fixed bases lambda =
    5.05813333333, margin 3.37208888889, adequate. The pinned-base
    limit load that would fail at ultimate is Hc/1.5 = 101162.666667 N,
    so any limit load above 101.2 kN fails the FAR 25.303 check before
    the plastic mechanism forms.
- Load factor and ultimate margin, fixed-fixed beam (Mp = 31250 N m,
  L = 3 m, Wc = 83333.3333333 N):
  - Applied limit 40 kN: lambda = 2.08333333333, required 60000 N,
    margin 1.38888888889, adequate (83.3 kN collapse clears 1.5*40 kN).
  - Applied limit 60 kN: lambda = 1.38888888889, required 90000 N,
    margin 0.925925925926, inadequate (83.3 kN collapse fails the 90 kN
    ultimate requirement): the plastic mechanism forms below the FAR
    25.303 ultimate load.
- ValueErrors (13 anchor cases, each raises ValueError): unknown shape
  "triangle"; rectangle b <= 0; circle d = 0; I-beam d <= 2*t_f (0.2
  m depth against 0.24 m of flange pair) and a 3-arg I-beam call;
  sigma_y <= 0; beam case "cantilever-central"; span = 0; mp <= 0;
  frame base "propped"; height = 0; limit load <= 0; ultimate_factor = 0.
Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w43spec/anchor_plcol.py (stdlib
math, exit 0).

## Validation list (contract test must include)

- plastic_section_modulus: rectangle (0.05, 0.1) = 0.000125 within 1e-9
  relative; circle (0.1) = 0.000166666666667 within 1e-9; i-beam (0.4,
  0.2, 0.012, 0.008) = 0.001213952 within 1e-9 relative; the rectangle
  closed form equals b*h**2/4 and the circle equals d**3/6 by
  construction.
- elastic_section_modulus: rectangle = 8.33333333333e-05, circle =
  9.81747704247e-05, i-beam = 0.00108074325333, each within 1e-6
  relative.
- shape_factor: rectangle 1.5 within 1e-12, circle 1.69765272631 within
  1e-6, i-beam 1.12325660721 within 1e-6; ordering 1.6977 > 1.5 >
  1.1233; nu = Mp/My within 1e-9 relative (anchor residual
  2.22044604925e-16).
- fully_plastic_moment(250e6, 0.000125) = 31250 within 1e-9 relative;
  with the section Zp values: rectangle 31250, circle 41666.6666667,
  i-beam 303488 N m.
- collapse_load_beam at span 3.0, mp 31250: simply-supported-central
  collapse_load = 41666.6666667 within 0.01 N with plastic_hinges 1;
  propped-cantilever-central = 62500 within 0.01 N with plastic_hinges
  2; fixed-fixed-central = 83333.3333333 within 0.01 N with
  plastic_hinges 3; hinge_locations include x = 0, x = L/2 and x = L as
  the case dictates; each dict case key echoes the config.
- Elastic first-yield context: W_y = 4*My/L = 27777.7777778,
  16*My/(3*L) = 37037.037037, 8*My/L = 55555.5555556 with My =
  20833.3333333, L = 3, each within 0.01 N; Wc/Wy ratios 1.5, 1.6875
  and 1.5 within 1e-9.
- Static theorem: max |M| over the 2001-station sampled collapse-state
  diagram equals Mp = 31250 within 1e-6 relative with overshoot above
  Mp no greater than 1e-9 relative (anchor 0.0) for all three beam
  cases; the diagram equals Mp at the hinge stations.
- portal_sway_collapse_load(4.0, 303488, "pinned") = 151744 within 0.01
  N with plastic_hinges 2; (4.0, 303488, "fixed") = 303488 within 0.01
  N with plastic_hinges 4, the fixed-base sway double the pinned-base
  value.
- ultimate_margin at a 60000 N limit on the pinned-base portal:
  collapse_load_factor = 2.52906666667 within 1e-6, ultimate_margin =
  1.68604444444 within 1e-6, verdict "adequate"; fixed-base:
  5.05813333333 and 3.37208888889; fixed-fixed beam at a 40000 N limit:
  2.08333333333, margin 1.38888888889, adequate, and at a 60000 N
  limit: 1.38888888889, margin 0.925925925926, verdict "inadequate";
  ultimate_load_required = 1.5*limit_load in every case; verdict flips
  exactly where collapse_load crosses 1.5*limit_load.
- ValueErrors: the 13 anchor cases of the worked example each raise
  ValueError (unknown shape, dims arity, nonpositive dims, i-beam d <=
  2*t_f, sigma_y <= 0, unknown beam case, span 0, mp <= 0, unknown
  frame base, height 0, limit load <= 0, ultimate_factor 0).
- Determinism: two identical runs return identical bits; no imports
  beyond math; no RNG. Contract test file named test_plastic_collapse_
  analysis.py (underscores), unittest, offline in under 20 seconds.

## Corpus fragment (eval/hit1-wave43-plastic-collapse-analysis.yaml)

Query 1 (copy verbatim):
  "analyze the plastic collapse of a fixed-fixed beam and a propped
  cantilever under a central point load: compute the fully plastic
  moment Mp = sigma_y*Zp from the plastic section modulus Zp and the
  shape factor nu = Zp/Z of the section, form the plastic hinge
  mechanism and find the plastic collapse load by the kinematic theorem"
  intent: "structures; plastic collapse (limit) analysis of statically
  indeterminate beams: plastic section modulus and shape factor closed
  forms, fully plastic moment, plastic hinge mechanisms and collapse
  loads by the kinematic (virtual work) theorem"
  expected_skill: "structures/fem/plastic-collapse-analysis"
Query 2 (copy verbatim):
  "find the plastic collapse load of a simple frame under a lateral
  load by the sway mechanism with pinned and fixed bases, then report
  the collapse load factor against the applied load and the ultimate
  margin in the 1.5 ultimate-factor context of FAR 25.303"
  intent: "structures; rectangular frame sway plastic collapse loads
  under lateral load, collapse load factor versus the applied limit load
  and the FAR 25.303 1.5 ultimate-factor margin with the adequate or
  inadequate verdict"
  expected_skill: "structures/fem/plastic-collapse-analysis"
Task ids: w43-plastic-collapse-analysis-1 and -2. Prep grep and probe:
the distinctive tokens plastic-collapse-analysis, plastic-hinge,
collapse-mechanism and limit-analysis-beam each match 0 existing
eval/hit1-corpus.yaml tasks (real greps), and the corpus-collisions.py
batch-D run reports 'plastic hinge' 0, 'plastic collapse' 0, 'shape
factor' 0, 'collapse load' 0 and 'fully plastic' 0 (real run; the lone
batch-D nonzero, 'net section' 1, belongs to the metallic-fastener-joints
probe token, a different same-wave leaf). The only "collapse" word in
the corpus is the cylindrical-shell-buckling ovalization-collapse task
(elastic Brazier collapse of a curved shell section, judged against
bifurcation), so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must find the plastic collapse
(limit) load of a beam or a simple frame:" and include the outputs in
the Claim. First tag: plastic-collapse-analysis. Additional tags ONLY:
plastic-hinge, collapse-mechanism, limit-analysis-beam,
fully-plastic-moment, shape-factor, collapse-load-factor. NEVER single
generic words (plastic, collapse, hinge, moment, load, beam, frame,
yield, stress, section, modulus, bending, strength, structure, portal,
analysis) and NEVER elastic stiffness-method or portal-frame tokens
(beam-frame-analysis, which owns the tag portal-frame and the trigger
"portal frame": this leaf reaches the same rigid-jointed frames only as
plastic collapse loads), von-mises, tresca, yield-margin,
equivalent-stress, principal-stress (multiaxial-yield-criteria),
ramberg-osgood, stress-strain-curve, plastic-strain, secant-modulus,
offset-yield-strength (ramberg-osgood), strain-life, coffins-manson,
neuber, low-cycle-fatigue (strain-life-fatigue), euler-buckling,
buckling-load (buckling-analysis), ovalization-collapse, knockdown
(cylindrical-shell-buckling), crippling, inter-rivet-buckling
(crippling-analysis, same wave), net-section, bolt-group
(metallic-fastener-joints, same wave) or hertzian
(hertzian-contact-stress, same wave). 50-150 words, <=1000 chars, no em
dash, no content-policy sweep term (the banned word from the builder
kit), action verb present. Recommended wording (outputs in Claim order):
"Use when you must find the plastic collapse (limit) load of a beam or a
simple frame: compute the fully plastic moment Mp = sigma_y*Zp from the
plastic section modulus Zp (rectangle b*h^2/4, circle d^3/6, I-beam with
the plastic neutral axis in the web), the shape factor nu = Zp/Z, and
the plastic hinge mechanisms of statically indeterminate beams and
rectangular frames, applying the kinematic (virtual work) and static
(equilibrium plus yield) theorems to give the plastic collapse load, the
collapse load factor against the applied load and the ultimate margin in
the 1.5 ultimate-factor context of FAR 25.303. Produces the plastic
section moduli and shape factors, fully plastic moments, plastic
collapse loads with hinge mechanisms, and the load factor and ultimate
margin verdicts that gate metallic beam and frame strength checks.
Trigger: plastic collapse, plastic hinge, collapse mechanism, fully
plastic moment, shape factor." The sibling triggers "portal frame",
"nodal displacement", "member end actions", "von Mises margin", "Tresca",
"stress-strain curve", "strain-life", "Coffin-Manson" and "Euler
buckling" must not appear.

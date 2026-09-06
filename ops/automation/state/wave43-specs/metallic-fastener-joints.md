# Wave-43 leaf spec: metallic-fastener-joints (structures, fem pack)

- Path: skills/structures/fem/metallic-fastener-joints/
- Pack: fem (present siblings at prep: beam-column-analysis,
  beam-frame-analysis, beam-vibration, buckling-analysis, calculix-linear,
  calculix-nonlinear, contact-analysis, curved-beam-analysis,
  cylindrical-shell-buckling, diagonal-tension-field-webs, lug-joint-analysis,
  modal-analysis, plate-buckling, pressure-bulkhead, shear-center-analysis,
  shrink-fit-analysis, torsion-shear-flow, truss-analysis; wave-43 planned
  additions crippling-analysis, hertzian-contact-stress and
  plastic-collapse-analysis are in flight per the wave-43 leaf plan, entries
  13, 14 and 16, and their fences are quoted from that plan below).
- Claim fences (quoted from the sibling frontmatter/body at prep; none owns
  per-fastener metallic joint margins or bolt-group mechanics):
  - structures/composites/composite-bolted-joints is LAMINATE-only: its
    description reads "Use when you must analyze a bolted joint in a
    composite laminate under bearing and bypass loading: compute the bolt
    bearing stress from the applied load, bolt diameter, and laminate
    thickness, the net-tension stress across the net section, the shear-out
    stress at the edge distance, and the joint margin against each
    allowable ... Trigger: bolted joint, bearing stress, bypass loading,
    net-tension, shear-out, bolt diameter, edge distance, fastener, joint
    margin, composite laminate joint." Its body states that the joint
    margin is M = allowable / applied - 1 for a fiber-reinforced panel
    with a BYPASS load share carried around the hole through the laminate;
    composite failure modes (bearing/bypass interaction, laminate
    allowables) are not the metallic sheet modes below, and no fastener
    shank shear or bolt-group quantity appears there.
  - structures/fem/lug-joint-analysis is the SINGLE-PIN metallic lug: its
    description reads "Use when you must analyze a metallic pin-loaded lug
    fitting under an axial load: compute the hole bearing stress, the net
    section tension stress across the lug width, the tearout shear stress
    on the two planes from the hole tangent to the round outer contour ..."
    Its body adds "this leaf is the metallic lug with e/D proportioning,
    head geometry and tearout planes from the hole contour, with no
    load-sharing split concept." One pin, round-end proportioning w = 2e,
    tearout planes running to the outer contour; there is no equal-share
    split, no multi-fastener row, no fastener shank shear and no bolt group.
  - structures/fem/diagonal-tension-field-webs handles web rivet shear
    flows as DISTRIBUTED load paths, not fastener joint margins: its
    description reads "... the flange and end post axial loads pulled in by
    the field, the rivet shear flows on the flange and end post
    attachments, and the margin against buckling"; its worked example
    quotes rivet flows in N/m (48000 N/m at 45 degrees) along a continuous
    attachment, a load-per-unit-length quantity with no fastener area, no
    bearing stress, no edge-distance shear-out and no per-fastener margin.
  - manufacturing-quality/assembly/fastener-installation-quality and
    manufacturing-quality/assembly/solid-rivet-installation-quality
    (manufacturing-quality family) are process quality, not stress: their
    corpus tasks route on grip selection, thread protrusion, torque clamp
    load, collar engagement and countersink flushness, with no stress
    allowables or margins.
  - cross-cutting/tolerancing/fastener-position-tolerance-calc (cross-
    cutting) sizes positional tolerances of holes; it computes no stress.
  - wave-43 same-pack siblings in flight (wave-43 leaf plan): entry 13
    crippling-analysis treats inter-rivet buckling as a column-stability
    length between rivets of a compression shape, not fastener load;
    entry 14 hertzian-contact-stress is the curved-body contact patch
    (p0, subsurface tau_max) of spheres/cylinders/rollers, not pin bearing
    of a hole; entry 16 plastic-collapse-analysis is fully plastic bending
    Mp = sigma_y*Zp of beams and frames, with no fastener mechanics.
  Whole-tree greps at prep: the distinctive tokens metallic-fastener-joints,
  bolt-group-analysis, eccentric-bolt-group and fastener-shear-margin each
  match 0 tasks in eval/hit1-corpus.yaml and 0 files under skills/; the
  only "eccentric" content in structures/ is "eccentrically loaded column"
  in beam-column-analysis (secant-formula column stress, no bolt group).
  GENUINE structures gap (probe #5, GO): no leaf computes metallic
  multi-fastener joint margins or eccentric bolt-group loads.
- Standards ids: mmpsd, far-25 AND cs-25 (all reference-only; all present
  in standards-map.yaml, ids at lines 160, 16 and 27; mmpsd gated true so
  design values are named parameters, never reproduced). Ledger Standard:
  mmpsd, far-25.
- Family: structures

## Claim

Analyze a metallic multi-fastener joint (bolt or rivet pattern) under its
applied load: split the load into the per-fastener share of a symmetric
pattern (P/n for n identical fasteners), check each fastener in shear
(single shear on one plane, double shear on two, using the fastener shear
area pi*D^2/4 and the fastener shear allowable), check the sheet in bearing
P/(D*t) against the material bearing allowable, in net-section tension
across the fastener row P/((w - holes*D)*t) against the tension allowable,
and in shear-out (tear-out) at the sheet edge P/(2*e*t) on the two shear
planes against the sheet shear allowable; and resolve an eccentric bolt
group by the polar moment method for a load applied off the pattern
centroid, adding the equal direct share to the torque-driven secondary
share M*r_i/J (M the applied torque about the group centroid, J = sum of
r_i^2) on each fastener to find the max-loaded fastener. Produces the
per-fastener load share, the fastener single and double shear stresses, the
sheet bearing, net-section and shear-out stresses, the per-mode margins of
safety against the allowables with the governing mode and pass verdict, and
for the eccentric group the centroid, polar moment, applied torque,
per-fastener direct and secondary resultants and the max-loaded fastener
load. The allowables are module parameters in the MMPDS style (BOLT_F_SU,
the fastener shear ultimate F_su of the bolt material; SHEET_F_BRU, the
sheet bearing ultimate F_bru; SHEET_F_TU, the sheet tension ultimate F_tu;
SHEET_F_SU, the sheet shear ultimate F_su; the defaults are representative
values for a steel MS-class bolt in 2024-T3 sheet and are stated as module
constants, never as reproduced design-value tables), and every margin uses
the standard 1.5 ultimate factor context MoS = allowable/(applied*factor)
- 1 with factor = 1.5 applied to LIMIT stresses (FAR 25.303 style), a
module parameter whose factor = 1.0 recovers the plain allowable/applied
- 1 form.
Does NOT do: composite laminate bolted joints with bearing/bypass load
splits and laminate allowables (composite-bolted-joints); single-pin lug
fittings with round-end proportioning and contour tearout (lug-joint-
analysis); distributed web rivet shear flows in N/m or buckling margins of
post-buckled webs (diagonal-tension-field-webs); fastener installation
process quality, grip, torque or hole prep (fastener-installation-quality,
solid-rivet-installation-quality); hole positional tolerancing (fastener-
position-tolerance-calc); secant-formula or stability checks of columns
(beam-column-analysis, crippling-analysis); Hertz contact patches of curved
bodies (hertzian-contact-stress); plastic collapse of beams and frames
(plastic-collapse-analysis). Elastic equal sharing only: load redistribution
from fastener flexibility, joint slip, secondary bending of the lap,
fatigue, and mixed fastener types are out of scope. SI units throughout
(N, mm, MPa).

## Model (implement exactly)

Pure stdlib, math only, closed form. Units: loads in N, geometry in mm
(sheet thickness t, joint width w, edge distance e, fastener diameter D all
in mm), stresses in MPa = N/mm^2, bolt-group moments in N*mm, polar moment
in mm^2.

Module constants (module parameters, MMPDS-style names, representative
defaults):
- BOLT_F_SU = 655.0: fastener shear ultimate (MPa), representative steel
  MS-class bolt (e.g. 1/4-in and 3/8-in MS bolts).
- SHEET_F_TU = 427.0: 2024-T3 sheet tension ultimate (MPa).
- SHEET_F_SU = 255.0: 2024-T3 sheet shear ultimate (MPa).
- SHEET_F_BRU = 620.0: 2024-T3 sheet bearing ultimate (MPa), valid for the
  edge distance e/D >= 2 used in the worked example.
- ULTIMATE_FACTOR = 1.5: design ultimate factor on limit stresses
  (FAR 25.303 style).

Defining relations (pin these exactly; every function below derives from
them):
- Per-fastener share of a symmetric pattern: P_f = P/n.
- Fastener shear area: A = pi*D^2/4; shear stress on one fastener over
  `planes` shear planes: tau = P_f/(planes*A); planes = 1 single shear,
  planes = 2 double shear.
- Sheet bearing stress under one fastener: sigma_b = P_f/(D*t).
- Net-section tension at a row of `holes` fasteners across the width:
  sigma_nt = P/((w - holes*D)*t); the net width w - holes*D must be
  positive.
- Sheet shear-out at the edge: tau_so = P_f/(2*e*t), two shear planes each
  of length e (edge distance from the hole center to the free edge along
  the load direction) and thickness t.
- Margin of safety: MoS = allowable/(factor*applied_limit) - 1 with the
  default factor 1.5; design ultimate stress = factor*applied_limit, and a
  margin of zero means the factored applied stress equals the allowable.
- Eccentric group polar method: bolt group centroid (x_c, y_c), polar
  moment J = sum_i((x_i - x_c)^2 + (y_i - y_c)^2); applied force
  (fx, fy) at (ax, ay) gives torque about the centroid
  M = (ax - x_c)*fy - (ay - y_c)*fx; direct share (fx, fy)/n on every
  bolt; secondary share on bolt i, at (dx_i, dy_i) = (x_i - x_c,
  y_i - y_c), is F_sec,i = (M/J)*(-dy_i, dx_i), magnitude |M|*r_i/J
  perpendicular to the radius, so the secondary forces sum to zero and
  their moments sum exactly to M; the bolt load is the vector sum of
  direct and secondary, and the max-loaded fastener is the largest such
  magnitude.

Functions:
- fastener_area(D) -> float: pi*D^2/4. ValueError if D <= 0.
- fastener_shear_stress(P_f, D, planes=1) -> float: P_f/(planes*A).
  ValueError if P_f < 0, D <= 0, or planes not in (1, 2).
- bearing_stress(P_f, D, t) -> float: P_f/(D*t). ValueError if P_f < 0,
  D <= 0 or t <= 0.
- net_section_stress(P, w, holes, D, t) -> float: P/((w - holes*D)*t).
  ValueError if P < 0, w <= 0, D <= 0, t <= 0, holes not a positive
  integer, or the net width w - holes*D <= 0 (net section destroyed).
- shear_out_stress(P_f, e, t) -> float: P_f/(2*e*t). ValueError if P_f < 0,
  e <= 0 or t <= 0.
- margin_of_safety(allowable, applied_limit, factor=ULTIMATE_FACTOR) ->
  float: allowable/(factor*applied_limit) - 1. ValueError if allowable
  <= 0, applied_limit <= 0, or factor <= 0.
- splice_joint_analysis(P, n, D, t, w, e, f_su_fastener, f_bru, f_tu,
  f_su_sheet, planes=1, factor=ULTIMATE_FACTOR) -> dict: the one-shot
  symmetric n-fastener single-row shear splice report. Returns
  per_fastener_load_N = P/n, the four limit stresses fastener_shear_MPa
  (planes shear planes), bearing_MPa, net_section_MPa (full row load P
  over the net width), shear_out_MPa, the margins dict keyed
  fastener_shear, bearing, net_section, shear_out (fastener shear vs
  f_su_fastener, bearing vs f_bru, net section vs f_tu, shear-out vs
  f_su_sheet), governing (lowest margin key), min_margin and passes
  (min_margin >= 0). ValueError if P < 0, n not a positive integer, any
  dimension <= 0 (via the helpers), or any allowable <= 0.
- bolt_group_properties(bolts) -> (x_c, y_c, J): bolts is a list of (x, y)
  tuples in mm; returns the centroid and polar moment. ValueError if the
  list is empty.
- eccentric_bolt_group_loads(fx, fy, ax, ay, bolts) -> dict: polar-moment
  resolution described above. Returns centroid, polar_moment_mm2,
  torque_Nmm, direct_per_fastener_N, fasteners (list of dicts per bolt in
  input order with x, y, r_mm, direct_N, secondary_N, total_N,
  magnitude_N), max_magnitude_N, max_indices (all bolts within 1e-9 of the
  maximum; a symmetric group ties by mirror symmetry) and max_fastener.
  ValueError if bolts empty, the applied force is (0, 0), or J <= 0 (all
  bolts coincident).

Identities to test (closed form, exact):
- Double shear halves the single-shear stress exactly:
  2*fastener_shear_stress(P, D, 2) == fastener_shear_stress(P, D, 1)
  (anchor residual 0.0e+00).
- Bearing to shear-out stress ratio equals 2e/D exactly; at the worked
  edge distance e = 2D the ratio is exactly 4 (anchor 4.000000).
- Margin algebra: margin_of_safety(F, F/1.5) == 0 exactly (anchor
  0.000000e+00); margin_of_safety(F, F) == -1/3 (anchor -0.333333333);
  margin_of_safety(2*F, F, factor=1.0) == 1 exactly (the plain sibling
  form).
- Equal share: n*fastener share == P exactly (anchor residual 0.0e+00);
  with the force line through the group centroid (M = 0) every bolt
  carries exactly P/n (anchor 6750.000000000 N at 27000 N over 4).
- Eccentric equilibrium: the per-bolt total forces sum to the applied
  force and the moments sum exactly to the applied torque about the
  centroid (anchor sums 27000.000000 N, 0.0e+00 N and -2700000.000000
  N*mm).
- Polar moment of the 4-bolt square at (+/-25, +/-25) mm: J = n*r^2 =
  4*(25^2 + 25^2) = 5000 mm^2 (anchor 5000.000000 mm^2).
- Governing mode is the lowest margin and passes iff min margin >= 0; the
  2x limit overload flips the governing bearing margin negative.
- ValueErrors across the module: D <= 0; planes outside (1, 2); negative
  fastener or section loads; t <= 0; e <= 0; holes < 1; net width
  w - holes*D <= 0; n < 1; allowable <= 0; applied limit <= 0; factor
  <= 0; empty bolt group; zero applied force; coincident bolts (J = 0).
- Determinism; no imports beyond math; no RNG; identical floats run to run
  (anchor bit-identical True).

## Worked example

Example A: a representative aircraft single-lap shear splice with four
1/4-in MS bolts (D = 6.35 mm) in a symmetric row across a 2024-T3 sheet of
thickness t = 2.5 mm, width w = 90 mm, edge distance e = 12.7 mm (e/D = 2),
carrying a limit load P = 20000 N through the row. Example B: an eccentric
bracket bolt group of four bolts at (+/-25, +/-25) mm (a 50 mm square)
carrying a 27000 N force in +x applied at (0, +100) mm, 100 mm off the
pattern centroid. All values below are REAL outputs of the prep anchor
/tmp/w43spec/anchor_fastj.py (stdlib math only, closed form, exit 0).

Example A (splice, P = 20000 N limit, n = 4):
- Per-fastener share P/4 = 5000.0000 N exactly; fastener area
  pi*D^2/4 = 31.669217 mm^2.
- Fastener shear (1/4-in MS bolt, F_su = 655 MPa): single shear
  tau = 157.882019 MPa, MoS = 655/(1.5*157.882019) - 1 = +1.765778;
  double shear tau = 78.941010 MPa, MoS = +4.531557 (exactly half the
  single-shear stress).
- Sheet bearing (F_bru = 620 MPa): sigma = 5000/(6.35*2.5) =
  314.960630 MPa, MoS = +0.312333, the GOVERNING mode.
- Net-section tension (F_tu = 427 MPa): net width w - 4D = 64.6000 mm,
  sigma = 20000/(64.6*2.5) = 123.839009 MPa, MoS = +1.298683.
- Sheet shear-out (F_su = 255 MPa): tau = 5000/(2*12.7*2.5) =
  78.740157 MPa, MoS = +1.159000; bearing/shear-out = 314.960630/
  78.740157 = 4.000000 = 2e/D exactly.
- splice_joint_analysis verdict: margins {fastener_shear: 1.765778,
  bearing: 0.312333, net_section: 1.298683, shear_out: 1.159000},
  governing bearing, min margin +0.312333, passes True.
- The same splice at 2.0x limit (P = 40000 N): bearing margin -0.343833,
  governing stays bearing, passes False (fastener shear +0.382889, net
  section +0.149342, shear-out +0.0795); the joint is bearing-critical.
- Convention check: MoS(F, F/1.5) = 0.000000e+00 (factored applied stress
  equal to the allowable is exactly zero margin); MoS(F, F) =
  -0.333333333; factor = 1.0 gives the sibling form exactly.

Example B (eccentric group, P = 27000 N in +x at (0, +100) mm):
- bolt_group_properties: centroid (0.000000, 0.000000), J =
  5000.000000 mm^2; per-bolt radius r = 35.355339 mm.
- Torque about the centroid M = (ax-xc)*fy - (ay-yc)*fx = 0*0 - 100*27000
  = -2700000.000000 N*mm (clockwise); direct share per fastener
  (6750.00, 0.00) N.
- Per-bolt loads (direct + secondary; the anchor prints the secondary
  components, magnitude sqrt(2)*13500.00 = 19091.883 N = |M|*r/J):
  - bolt 0 at (25, 25): total (20250.00, -13500.00) N, magnitude
    24337.4711 N.
  - bolt 1 at (-25, 25): total (20250.00, 13500.00) N, magnitude
    24337.4711 N.
  - bolt 2 at (-25, -25): total (-6750.00, 13500.00) N, magnitude
    15093.4588 N.
  - bolt 3 at (25, -25): total (-6750.00, -13500.00) N, magnitude
    15093.4588 N.
  max-loaded fastener magnitude = 24337.471109 N on indices [0, 1]: the
  two top bolts tie by mirror symmetry about the load plane.
- Equilibrium: sum of bolt loads = (27000.000000, 0.000000e+00) N and
  sum(r x F) = -2700000.000000 N*mm, exactly the applied force and torque.
- Bracket fasteners sized as 3/8-in MS bolts (D = 9.525 mm, shear area
  pi*D^2/4 = 71.257 mm^2): max bolt shear stress = 341.551030 MPa,
  MoS = 655/(1.5*341.551030) - 1 = +0.278481 (passes); the same group
  with 1/4-in bolts gives 768.489817 MPa and MoS -0.431786 (fails): the
  bracket needs the 3/8-in bolts.
- Force line through the centroid (M = 0): every bolt magnitude =
  6750.000000000 N, the equal share P/4 exactly.
Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w43spec/anchor_fastj.py (stdlib math,
closed form, exit 0).

## Validation list (contract test must include)

- fastener_area(6.35) = 31.669217 mm^2 within 1e-3.
- fastener_shear_stress(5000, 6.35, 1) = 157.882019 MPa within 1e-3;
  planes=2 gives 78.941010 within 1e-3, and 2*tau_double equals tau_single
  within 1e-9 relative.
- bearing_stress(5000, 6.35, 2.5) = 314.960630 MPa within 1e-3;
  net_section_stress(20000, 90, 4, 6.35, 2.5) = 123.839009 MPa within
  1e-3 (net width 64.6 mm); shear_out_stress(5000, 12.7, 2.5) =
  78.740157 MPa within 1e-3.
- Identity: bearing_stress(P, D, t) / shear_out_stress(P, 2*D, t) = 4.0
  within 1e-9 (the 2e/D relation at e = 2D).
- Margin convention: margin_of_safety(427, 427/1.5) = 0 within 1e-12;
  margin_of_safety(427, 427) = -1/3 within 1e-9;
  margin_of_safety(200, 100, factor=1.0) = 1.0 within 1e-12 (sibling
  form).
- splice_joint_analysis(20000, 4, 6.35, 2.5, 90, 12.7, 655, 620, 427,
  255): margins {fastener_shear 1.765778, bearing 0.312333, net_section
  1.298683, shear_out 1.159000} each within 1e-3, governing bearing,
  passes True; same call at P = 40000 gives bearing margin -0.343833
  within 1e-3 and passes False.
- bolt_group_properties([(25,25), (-25,25), (-25,-25), (25,-25)]) returns
  centroid (0, 0) and J = 5000 within 1e-9.
- eccentric_bolt_group_loads(27000, 0, 0, 100, square_bolts): torque
  -2700000 N*mm within 1, max magnitude 24337.471109 N within 0.01,
  max_indices [0, 1], the four bolt magnitudes within 0.01 of the anchor
  values, and the equilibrium sums (27000, 0) N and -2700000 N*mm within
  1e-6 relative.
- Zero-torque case: eccentric_bolt_group_loads(27000, 0, 0, 0, bolts)
  gives every bolt exactly 6750 N (within 1e-9).
- Governing/pass consistency: governing key has the min margin; passes
  True at 20000 N and False at 40000 N.
- ValueErrors: fastener_area(0); fastener_shear_stress(1000, 6.35, 3);
  fastener_shear_stress(-1, 6.35); bearing_stress(1000, 6.35, 0);
  net_section_stress(10000, 25.4, 4, 6.35, 2.5) (net width zero);
  net_section_stress(10000, 90, 0, 6.35, 2.5); shear_out_stress(1000, 0,
  2.5); margin_of_safety(0, 100); margin_of_safety(400, 0);
  margin_of_safety(400, 100, 0); splice_joint_analysis with n = 0;
  bolt_group_properties([]); eccentric_bolt_group_loads(0, 0, 0, 100,
  bolts); eccentric_bolt_group_loads(1000, 0, 0, 100, coincident_bolts).
- Determinism: two runs of the eccentric case are bit-identical; no
  imports beyond math; no RNG.

## Corpus fragment (eval/hit1-wave43-metallic-fastener-joints.yaml)

Query 1 (copy verbatim):
  "analyze the metallic-fastener-joints single-lap shear splice: split the
  limit load into the per-fastener share of the four 1/4-inch MS bolts in
  the 2024-T3 sheet and compute the fastener shear margin in single and
  double shear, the bearing margin, the net-section tension margin and the
  shear-out margin under the 1.5 ultimate factor"
  intent: "structures; metallic multi-fastener joint analysis: per-fastener
  load share with fastener shear, bearing, net-section and shear-out
  margins of safety against MMPDS-style allowables"
  expected_skill: "structures/fem/metallic-fastener-joints"
Query 2 (copy verbatim):
  "run the bolt-group-analysis of the eccentric-bolt-group bracket by the
  polar moment method: the torque about the group centroid, the per-bolt
  direct and secondary resultants, and the fastener-shear-margin of the
  max-loaded fastener"
  intent: "structures; eccentric bolt group polar moment method: applied
  torque about the group centroid, per-bolt direct plus secondary loads,
  max-loaded fastener and its shear margin"
  expected_skill: "structures/fem/metallic-fastener-joints"
Task ids: w43-metallic-fastener-joints-1 and -2. Prep grep: the tokens
metallic-fastener-joints, bolt-group-analysis, eccentric-bolt-group and
fastener-shear-margin each match 0 tasks in eval/hit1-corpus.yaml; the
fastener-adjacent corpus tasks route elsewhere (composite-bolted-joints-w8
on laminate bearing/bypass, widespread-fatigue-damage on MSD screening of
cracked fastener holes, lug-joint-analysis on the single-pin lug,
fastener-installation-quality and solid-rivet-installation-quality on
installation process quality, fastener-position-tolerance-calc on hole
tolerance, adhesive-bonded-joints and peel-stress-bonded-joints on bonded
joints), so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must analyze a metallic multi-fastener
joint:" and include the outputs in the Claim. First tag:
metallic-fastener-joints. Additional tags ONLY: bolt-group-analysis,
eccentric-bolt-group, fastener-shear-margin, fastener-load-share. NEVER
single generic words as tags (bolt, rivet, fastener, joint, bearing,
shear, tension, margin, splice, bracket, analysis) and NEVER the
sibling-owned compound or laminate tag tokens: bolted-joints, joint-margin,
bypass, bypass-loading, laminate (composite-bolted-joints); lug, tearout,
pin-loaded (lug-joint-analysis); diagonal-tension, tension-field,
web-rivet (diagonal-tension-field-webs); grip, torque, clamp-load,
collar, countersink (fastener-installation-quality,
solid-rivet-installation-quality); positional-tolerance (fastener-
position-tolerance-calc). 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term (the banned word from the builder kit), action
verb present. Recommended wording (outputs and verdict in Claim order):
"Use when you must analyze a metallic multi-fastener joint: split the
applied load into the per-fastener share of a symmetric bolt or rivet
pattern, compute the fastener shear stress in single or double shear, the
sheet bearing stress P/(D*t), the net-section tension across the fastener
row and the sheet shear-out at the edge distance, and the eccentric bolt
group loads by the polar moment method for a load applied off the pattern
centroid. Produces the per-fastener loads, the shear, bearing, net-section
and shear-out stresses, the eccentric group torque with the per-bolt
direct and secondary resultants, the max-loaded fastener, and the margin
of safety of each mode against the MMPDS-style allowables F_su, F_bru and
F_tu stated as module parameters, in the MoS = allowable/(applied*factor)
- 1 convention with the 1.5 ultimate factor. Trigger: metallic fastener
joints, bolt group analysis, eccentric bolt group, fastener shear margin,
single lap splice."

FORBIDDEN TOKENS (belong to siblings): laminate, composite, bypass,
bypass-loading, bypass-ratio, fiber-reinforced, bearing-and-bypass,
composite-laminate-joint (composite-bolted-joints); lug, lug-tearout,
pin-loaded-lug, round-end-lug, lug-edge-distance (lug-joint-analysis);
diagonal-tension, tension-field, post-buckled, tension-field-angle,
web-rivet-shear-flow, shear-web-reserve (diagonal-tension-field-webs);
grip-length, thread-protrusion, clamp-load, torque-clamp,
collar-engagement, countersink-flushness, installation-quality
(fastener-installation-quality, solid-rivet-installation-quality);
positional-tolerance, hole-pattern-tolerance (fastener-position-tolerance-
calc); eccentric-load-column, secant-formula, crippling, inter-rivet-
buckling, contact-patch, hertzian, plastic-collapse, Mp, shape-factor
(beam-column-analysis, crippling-analysis, hertzian-contact-stress,
plastic-collapse-analysis); fatigue, spectrum, life (damage-tolerance and
fatigue leaves). Bearing, net-section and shear-out stresses of a METALLIC
sheet are this claim's own modes (the composite sibling fence is the
laminate and the bypass split, not the mode names), so those single words
stay usable in prose but never as tags.

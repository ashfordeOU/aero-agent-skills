# Wave-43 leaf spec: crippling-analysis (structures, fem pack)

- Path: skills/structures/fem/crippling-analysis/
- Pack: fem (present siblings beam-column-analysis, beam-frame-analysis,
  beam-vibration, buckling-analysis, calculix-linear, calculix-nonlinear,
  contact-analysis, curved-beam-analysis, cylindrical-shell-buckling,
  diagonal-tension-field-webs, lug-joint-analysis, modal-analysis,
  plate-buckling, pressure-bulkhead, shear-center-analysis, shrink-fit-
  analysis, torsion-shear-flow, truss-analysis).
- Claim fences (quoted from the sibling frontmatter/body at prep, none owns
  the LOCAL crippling of a formed stiffener cross-section):
  - buckling-analysis owns the GLOBAL column and its yield-anchored
    Johnson fallback: its description reads "Use when a column, strut,
    spar cap, landing-gear leg or actuator rod must be sized or
    margin-checked against elastic instability in a stdlib-only
    environment without FEA software. Calculate the Euler critical
    buckling load of slender compression members: apply Pcr =
    pi^2*E*I/(K*L)^2 for pinned-pinned, fixed-fixed, fixed-pinned and
    cantilever end conditions, resolve the effective length factor K from
    the support type, compute the slenderness ratio from the radius of
    gyration, and run the buckling stress check against the yield-based
    transition slenderness", and its workflow step 7 reads "Compute the
    transition slenderness lambda_1 = pi * sqrt(E / sigma_y) ... If
    lambda > lambda_1, Euler governs and Pcr is the capacity; if not,
    Euler is unconservative, so fall back to a Johnson parabola or test
    data". The plateau of its Johnson fallback is the MATERIAL yield
    sigma_y and its member is a solid section with given I and A; it
    never computes a local crippling stress and never sees a formed
    thin-wall cross-section, so a stiffener whose short-column strength
    is set by local crippling has no allowable owner there.
  - plate-buckling owns single flat panels and hands the shell closure
    away verbatim: its Pitfalls read "Routing panel sizing here:
    fuselage-skin-stringer and wing-box-sizing (vehicle-design family)
    close the overall stiffened shell or wing box (skin thickness from
    hoop stress, stringer area, spar cap area); plate-buckling only
    checks the elastic stability of one flat panel with known
    dimensions." Its k-coefficient machinery needs an aspect ratio and
    edge-condition inputs; the inter-rivet allowable of a stiffener flat
    between fasteners is a fixed-k fastener-pitch limit inside a
    stiffener compression check, not a panel margin.
  - beam-column-analysis (wave-41, same pack) disclaims the local
    phenomenon verbatim in its Claim: "local crippling of the
    compression flange or stringer section, which is a local-section
    phenomenon outside this global member check", and its header notes
    "no crippling leaf exists anywhere in the tree (stringer-crippling
    history: local-section crippling is NOT reopened; this leaf owns the
    GLOBAL member-level combined-loading case)".
  - fuselage-skin-stringer and wing-box-sizing (vehicle-design family)
    size the panel AREA: fuselage-skin-stringer sizes "the stringer area
    from the compression strip load with the effective skin width" and
    the frame pitch from a column-buckling length; wing-box-sizing sizes
    spar cap area and web thickness from the box couple. Both CONSUME an
    allowable stress; neither computes the local crippling allowable of
    the stringer section.
  - Decline history: stringer-crippling was probed and declined at
    wave-38 on model-fidelity grounds, recorded in wave38-state.md as
    "stringer-crippling candidate DECLINED on model-fidelity
    (Gerard/NACA-TN-3781 crippling charts are correlation-based, not a
    clean closed form - whirl-flutter precedent)" and held closed through
    wave-42. The wave-43 probe receipt (leaf plan item 13, STRUCT 53,
    probe receipt #1) re-opens it because the shape-constant method is an
    algebraic closed form with module-declared constants, no chart
    reading: "local crippling + inter-rivet buckling of formed
    compression shapes, shape-constant method, Johnson-Euler interaction;
    buckling-analysis is global Euler only, plate-buckling hands off
    stiffened shells".
  Whole-tree greps at prep: "crippling" = 0 hits under skills/**/SKILL.md
  (all 26 tree hits live in ops/automation state files) and 0 hits in
  eval/hit1-corpus.yaml; "inter rivet buckling", "shape constant",
  "inter-rivet-buckling", "local-crippling-stress", "stringer-crippling"
  and "crippling-analysis" likewise 0 hits in eval/hit1-corpus.yaml
  (corpus-collisions.py batch-D run, quoted below). GENUINE STRUCT gap
  (fresh probe, GO 13): no leaf computes the local crippling allowable of
  a formed compression section or the inter-rivet allowable of its
  fastener-attached flats.
- Citation note (probe correction): the probe receipt shorthand
  "Gerard/Needham NACA-TN-3789" is factually off; NACA-TN-3789 is a
  swept-wing wind-tunnel report (Edwards, Dickson, Sutton and Demele),
  not a crippling source, so this spec anchors the method family on the
  public-domain NACA crippling literature instead: Gerard and Becker,
  Handbook of Structural Stability Part IV "Failure of Plates and
  Composite Elements" (NACA-TN-3784) and Part V "Compressive Strength of
  Flat Stiffened Panels" (NACA-TN-3785), the Gerard shape-constant
  correlation family for crippling of compression elements, and Semonian
  and Peterson (NACA-TN-3431) for inter-rivet buckling of riveted
  sheet-stringer connections. All paraphrased by name only, never
  reproduced.
- Standards ids: far-25 and cs-25 (both reference-only, present in
  standards-map.yaml; fem-pack sibling convention matching
  buckling-analysis and plate-buckling). Ledger Standard: far-25, cs-25.
- Family: structures

## Claim

Compute the LOCAL crippling and inter-rivet allowables of a formed
compression stiffener and convert them into the stiffener compression
allowable: for each flat element of the cross-section (outstanding
one-edge-free legs and flanges, no-edge-free webs between corners),
compute the element crippling stress from the shape-constant power-law
correlation F_cc,i = min(F_cy, C_s * sqrt(F_cy * E) * (t/b)**0.75) with
the per-class shape constants C_oef = 0.31 and C_sef = 0.55 stated
explicitly as module constants (Gerard/Needham style, material folded
through sqrt(F_cy*E)); average the element crippling loads over the
section area to get the crippling allowable of the whole formed shape
(angle, channel, Z, hat stringer, bulb angle); compute the inter-rivet
buckling stress of the fastener-attached flat between rivets sigma_ir =
4 * pi**2 * E / (12 * (1 - nu**2)) * (t_attach/s)**2 (rivet lines as
simple supports, long-plate coefficient 4), capped at the compressive
yield; then run the Johnson-Euler interaction that anchors the stiffener
column curve on the LOCAL crippling allowable, F_col = F_cc * (1 - F_cc
* lambda**2 / (4 * pi**2 * E)) on the Johnson arm below the tangent
slenderness lambda_t = pi * sqrt(2*E/F_cc) and the Euler arm pi**2*E /
lambda**2 above it, with both arms meeting at F_cc/2 at lambda_t by
construction. Produces the crippling allowable, the inter-rivet
allowable, the column interaction allowable, the stiffener compression
allowable (the minimum of the interaction and inter-rivet allowables)
and the margin of safety against the applied compression stress, in SI
units, that gate the stiffener compression sizing of the local
cross-section. Does NOT do: the global column Euler load with the
effective-length-factor end-condition table, the radius of gyration from
full section properties, or the yield-based transition classification of
a whole column (buckling-analysis; this leaf takes the effective
slenderness lambda = K*L/r as an input and anchors its Johnson curve on
the crippling stress, never on sigma_y); the flat-panel buckling
coefficient k versus aspect ratio, the panel compression-shear
interaction, or the effective width of stiffened skin (plate-buckling);
the axial-plus-bending global member with moment amplification and the
secant formula (beam-column-analysis); the hoop-stress skin thickness,
stringer area from the strip load, effective skin width, stringer
spacing or frame pitch of the skin-stringer panel (fuselage-skin-stringer
and wing-box-sizing close the overall stiffened shell or wing box); the
riveted skin-strip inter-rivet panel check between fastener rows, which
is a flat-panel check with known dimensions (plate-buckling). Does NOT
size the whole stiffened panel or shell. Formed-sheet crippling only,
with corner radii ignored (flat widths); the correlation constants are
calibrated on the aluminum sheet crippling test family, so the method is
stated for 2024-T3 and 7075-T6 only; extruded, machined or
fiber-reinforced sections, elevated temperature, and fastener bearing or
pull-through of the attachments are out of scope.

## Model (implement exactly)

Pure stdlib, math only, closed form. Module constants (pin these exactly;
they ARE the correlation and must appear as module-level names):

    CRIPPLING_EXPONENT = 0.75      # exponent n in the t/b power law
    C_OEF = 0.31                   # one-edge-free flat element (outstanding leg/flange)
    C_SEF = 0.55                   # no-edge-free flat element (web between corners)
    K_INTER_RIVET = 4.0            # long-plate coefficient, rivet lines simple supports
    MATERIALS = {
        "2024-T3": {"E": 72.4e9, "fcy": 290.0e6, "nu": 0.33},
        "7075-T6": {"E": 71.7e9, "fcy": 462.0e6, "nu": 0.33},
    }

Defining relations (pin these exactly; every function below derives from
them; all SI: b, t, pitch in m, stresses in Pa, slenderness lambda =
K*L/r dimensionless):
- Element crippling stress, edge-support class s:
  F_cc,i = min(F_cy, C_s * sqrt(F_cy * E) * (t/b)**CRIPPLING_EXPONENT).
  One-edge-free elements (the legs of an angle, the outstanding flanges
  of a channel or Z, the legs of a hat, the plain leg and the stem of a
  bulb angle) use C_OEF; interior elements supported on both long edges
  (the web of a channel or Z between its flanges, the crown of a hat
  between its legs) use C_SEF. The yield cap applies because the power
  law would exceed F_cy at small b/t (for 2024-T3 one-edge-free elements
  the raw curve crosses F_cy near b/t = 8.3).
- Section crippling allowable: the crippling loads of the elements are
  averaged over the section area, F_cc = sum(F_cc,i * A_i) / sum(A_i)
  with A_i = b_i * t_i per flat element; a bulb element (cls "bulb",
  solid cylinder of diameter d) carries at F_cy with area pi*d**2/4 and
  does not cripple locally (the classic bulb treatment: the bulb
  stabilizes the adjacent stem, which is conservatively kept as a
  one-edge-free flat of width bs). Corner radii are ignored; b is the
  flat width.
- Inter-rivet buckling of the fastener-attached flat of thickness
  t_attach between rivets at pitch s:
  sigma_ir = K_INTER_RIVET * pi**2 * E / (12 * (1 - nu**2)) * (t_attach/s)**2,
  the long-plate value with the rivet lines as simple supports (for
  aluminum this reads about 3.69 * E * (t_attach/s)**2 at nu = 0.33).
  Inter-rivet allowable F_ir = min(sigma_ir, F_cy): above yield the flat
  yields before it can buckle between the fasteners.
- Johnson-Euler interaction on the crippling allowable: the crippling
  stress is the lambda-tending-to-0 limit of the stiffener column curve,
  so the parabola is anchored at F_cc (not at sigma_y):
  lambda_t = pi * sqrt(2*E/F_cc); for lambda <= lambda_t,
  F_col = F_cc * (1 - F_cc * lambda**2 / (4 * pi**2 * E)) (Johnson arm);
  for lambda > lambda_t, F_col = pi**2 * E / lambda**2 (Euler arm).
  At lambda_t both arms equal F_cc/2 exactly (tangency by construction,
  the module's built-in cross-check).
- Stiffener compression allowable and margin:
  F_comp = min(F_col, F_ir); MS = F_comp / sigma_applied - 1; verdict
  pass when MS >= 0.

Functions (pure stdlib; SI as above; every non-physical input raises
ValueError):
- material(name) -> dict: resolve "2024-T3" or "7075-T6" (case and
  whitespace insensitive) to its constants dict. ValueError on unknown.
- element_crippling_stress(b, t, edge_class, mat) -> float: the capped
  power law above; edge_class must be "oef" or "sef". ValueError if
  b <= 0, t <= 0 or unknown edge_class.
- section_crippling_stress(elements, mat) -> dict: area-weighted section
  crippling allowable; elements is a list of dicts, each either
  {"label": str, "b": float, "t": float, "cls": "oef"|"sef"} or
  {"label": str, "d": float, "cls": "bulb"}. Returns {"fcc", "area_total",
  "elements"} where the per-element rows carry area and fcc.
  ValueError on an empty list or an unknown element key.
- inter_rivet_allowable(t_attach, pitch, mat) -> dict: returns
  {"stress_raw", "allowable"} with allowable = min(raw, fcy).
  ValueError if t_attach <= 0 or pitch <= 0.
- column_interaction_allowable(fcc, lam, mat) -> dict: returns
  {"allowable", "lam_t", "regime"} with regime "johnson" or "euler".
  ValueError if fcc <= 0 or lam <= 0.
- compression_margin(f_allowable, sigma_applied) -> float: MS =
  f_allowable / sigma_applied - 1. ValueError if sigma_applied <= 0.
- formed_shape_elements(shape, **dims) -> list: expand a formed shape
  into its flat element list. Shapes and required dims (all positive):
  "angle": b1, b2, t (two one-edge-free legs); "channel": bw, bf, t and
  "z": bw, bf, t (no-edge-free web plus two one-edge-free flanges);
  "hat": bc, bl, t (no-edge-free crown plus two one-edge-free legs);
  "bulb-angle": b1, bs, d, t (one-edge-free plain leg, one-edge-free
  stem to the bulb, solid bulb of diameter d). ValueError on unknown
  shape, missing or non-positive dims.
- stiffener_compression_check(elements, mat, t_attach, pitch, lam,
  sigma_applied) -> dict: the umbrella check returning the four claim
  outputs: {"fcc_section", "area_total", "sigma_ir_raw",
  "f_ir_allowable", "f_col_allowable", "lam_t", "column_regime",
  "f_compression_allowable", "margin", "verdict"} with
  f_compression_allowable = min(f_col_allowable, f_ir_allowable).
  ValueError set inherited from every callee.

Identities to test (closed form, exact):
- Tangency: at lam = lam_t the Johnson arm and the Euler arm both return
  fcc/2 (real anchor values 121.180120 MPa from both arms, relative
  difference 2.46e-16).
- Inter-rivet scaling: sigma_ir is quadratic in t_attach/pitch; doubling
  t_attach at fixed pitch quadruples the stress (real anchor ratio
  4.000000000000, relative difference 0).
- Crippling power law: at fixed t, quadrupling b multiplies the raw
  element stress by (1/4)**0.75 = 0.353553390593 (real anchor ratio
  0.353553390593, relative difference 0).
- Yield cap: element crippling never exceeds fcy; a stubby one-edge-free
  2024-T3 element at b/t = 5 returns exactly fcy (290.0 MPa).
- Class ranking: at equal b/t the no-edge-free element allowance sits at
  or above the one-edge-free allowance, and both sit at or below fcy.
- Section average: the area-weighted section allowable lies strictly
  between the smallest and largest element allowance of a mixed section.
- Margins: compression_margin(f_compression_allowable, sigma_applied)
  reproduces the margin field of stiffener_compression_check exactly.
- Determinism; no imports beyond math; only the two material registry
  entries, 2024-T3 and 7075-T6.

## Worked example

2024-T3 (E = 72.4 GPa, F_cy = 290 MPa, nu = 0.33, sqrt(F_cy*E) =
4.58214e9 Pa). All values below are REAL outputs of the prep anchor
/tmp/w43spec/anchor_cripp.py (stdlib math, closed form, exit 0).

- Z-stringer 2024-T3, t = 1.6 mm, outstanding flanges b_f = 19 mm, web
  b_w = 32 mm, rivet pitch s = 25 mm on the attached flange, effective
  slenderness lambda = 40 (typical frame pitch K*L = 0.5 m over the
  weak-axis radius of gyration of about 12.5 mm), applied compression
  stress 150 MPa:
  - element crippling: web (no-edge-free, b/t = 20) F_cc = 266.4762 MPa;
    each flange (one-edge-free, b/t = 11.9) F_cc = 222.0520 MPa.
  - section crippling allowable F_cc = (32*266.4762 + 2*19*222.0520)/70
    = 242.3602 MPa (0.8357 of F_cy), area 1.12e-4 m^2.
  - inter-rivet: sigma_ir raw = 1094.84 MPa, allowable = 290.00 MPa
    (yield-capped; the 1.6 mm flange at 25 mm pitch cannot buckle
    between the fasteners before yielding).
  - column interaction: lambda_t = 76.790, regime johnson, F_col =
    209.4793 MPa at lambda = 40 (13.6 percent below the crippling
    allowable).
  - compression allowable = min(209.4793, 290.00) = 209.4793 MPa;
    MS = 209.4793/150 - 1 = 0.396529, pass.
- Angle stringer 2024-T3, legs 25 mm x 25 mm, t = 1.6 mm, pitch 25 mm,
  lambda = 50, applied 120 MPa:
  - each leg (one-edge-free, b/t = 15.6) F_cc = 180.7444 MPa; section
    F_cc = 180.7444 MPa (0.6233 of F_cy).
  - inter-rivet allowable 290.00 MPa (raw 1094.84 MPa); lambda_t =
    88.920; F_col = 152.1704 MPa at lambda = 50.
  - compression allowable = 152.1704 MPa; MS = 0.268087, pass.
- Hat stringer 2024-T3 (thin gauge), crown 25 mm, legs 12 mm, t = 0.7 mm,
  pitch 25 mm, lambda = 60, applied 100 MPa:
  - crown (no-edge-free, b/t = 35.7) F_cc = 172.5041 MPa; each leg
    (one-edge-free, b/t = 17.1) F_cc = 168.6039 MPa; section F_cc =
    170.5938 MPa (0.5883 of F_cy).
  - inter-rivet: sigma_ir raw = 209.56 MPa, allowable = 209.56 MPa, the
    genuine sub-yield inter-rivet regime (thin attachment gauge relative
    to pitch).
  - lambda_t = 91.528; F_col = 133.9390 MPa at lambda = 60.
  - compression allowable = min(133.9390, 209.56) = 133.9390 MPa;
    MS = 0.339390, pass. Inter-rivet does not bind here but sits below
    yield and would bind a shorter, stiffer column once F_col rose above
    209.56 MPa.
- Formed shape family sweep, 2024-T3, t = 1.6 mm (channel and Z share
  web 32 mm and flanges 19 mm; bulb-angle plain leg 25 mm, stem 19 mm,
  bulb diameter 5 mm): section crippling allowable angle 25x25 =
  180.7444 MPa, channel 32x19 = 242.3602 MPa, Z 32x19 = 242.3602 MPa
  (identical element classes), bulb-angle = 218.5184 MPa (0.7535 of
  F_cy, lifted by the solid bulb carrying at yield); hat 25/12 at
  t = 0.7 mm = 170.5938 MPa.
- Material normalization: the same Z geometry in 7075-T6 (E = 71.7 GPa,
  F_cy = 462 MPa) gives section F_cc = 304.4203 MPa but only 0.6589 of
  F_cy versus 0.8357 for 2024-T3: the sqrt(F_cy*E) normalization captures
  the lower normalized crippling of the higher-strength alloy.
- Johnson-Euler interaction curve for the Z (F_cc = 242.3602 MPa,
  lambda_t = 76.790): lambda 20 -> 234.1400 MPa, 40 -> 209.4793 MPa,
  60 -> 168.3781 MPa (johnson arm), 76.790 -> 121.1801 MPa, 100 ->
  71.4559 MPa and 150 -> 31.7582 MPa (euler arm). Both arms at lambda_t
  return 121.180120 MPa = F_cc/2, relative difference 2.46e-16.
- Identity check outputs: inter-rivet doubling of t_attach gives stress
  ratio 4.000000000000 (relative difference 0); crippling quadrupling of
  b gives stress ratio 0.353553390593 = (1/4)**0.75 (relative difference
  0); the stubby one-edge-free element at b/t = 5 returns exactly
  290.0 MPa (cap); the section average lies between its element
  extremes; all twelve ValueError cases raise (non-positive b, t, pitch,
  fcc, lambda, sigma_applied; unknown material, shape, edge_class; empty
  elements list; missing shape dims).
- Read-off: the 2024-T3 Z-stringer at 150 MPa design compression runs a
  0.40 margin driven by the column interaction at lambda 40, not by
  crippling (crippling sits 62 percent above the applied stress and
  inter-rivet is yield-capped); the same stiffener in 7075-T6 would carry
  about 26 percent more crippling load, and lengthening the bay to
  lambda 77 halves the column allowable, the crippling-stress-based
  transition.
Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w43spec/anchor_cripp.py (stdlib
math, closed form, exit 0).

## Validation list (contract test must include)

- Z-stringer anchors within 1e-3 relative: element F_cc web 266.4762 MPa
  and flange 222.0520 MPa; section F_cc 242.3602 MPa; sigma_ir raw
  1094.84 MPa and inter-rivet allowable 290.00 MPa; lam_t 76.790;
  F_col 209.4793 MPa at lambda 40; compression allowable 209.4793 MPa;
  margin 0.396529 (assert with the module values, not the rounded text).
- Angle stringer anchors: section F_cc 180.7444 MPa; F_col 152.1704 MPa
  at lambda 50; margin 0.268087. Hat stringer anchors: section F_cc
  170.5938 MPa; sigma_ir raw and allowable 209.56 MPa; F_col 133.9390
  MPa at lambda 60; margin 0.339390.
- Family sweep: channel and Z share the element classes and give the
  same section F_cc 242.3602 MPa; bulb-angle 218.5184 MPa sits above the
  plain angle 180.7444 MPa; 7075-T6 Z section F_cc 304.4203 MPa with the
  lower normalized ratio 0.6589 versus 0.8357 for 2024-T3.
- Interaction curve: F_col values 234.1400 MPa (lambda 20), 168.3781
  (60), 71.4559 (100, euler), 31.7582 (150, euler); both arms equal
  F_cc/2 = 121.180120 MPa at lam_t within 1e-9 relative (anchor 2.46e-16);
  regime switches at lam_t.
- Identities: doubling t_attach quadruples sigma_ir (relative difference
  below 1e-12, anchor 0); quadrupling b multiplies the raw element stress
  by (1/4)**0.75 within 1e-9 relative (anchor 0); element F_cc never
  exceeds fcy and equals fcy for a stubby one-edge-free element at
  b/t = 5; sef allowance >= oef allowance at equal b/t; the section
  average lies between the element extremes; compression_margin
  reproduces the check margin exactly; ValueErrors on every non-physical
  input enumerated above; determinism; no imports beyond math.
- Cross-check the margin by hand: MS = min(F_col, F_ir)/sigma_applied - 1
  for each worked example.

## Corpus fragment (eval/hit1-wave43-crippling-analysis.yaml)

Query 1 (copy verbatim):
  "compute the local crippling stress of a 2024-T3 Z-stringer by the
  shape-constant method, add the inter-rivet buckling allowable of the
  riveted flange, and report the stiffener column interaction margin
  against the applied compression stress"
  intent: "structures; local crippling-analysis of a formed Z-stringer by
  the shape-constant power law with the inter-rivet buckling allowable
  and the Johnson-Euler stiffener column interaction margin"
  expected_skill: "structures/fem/crippling-analysis"
Query 2 (copy verbatim):
  "crippling-analysis of formed angle, channel, Z and hat stringers:
  element crippling stress from the shape constants, inter-rivet
  buckling stress between fasteners, and the interaction allowable that
  gates stringer-crippling"
  intent: "structures; per-shape element crippling and inter-rivet
  allowables of formed compression stiffeners with the compression
  allowable conversion"
  expected_skill: "structures/fem/crippling-analysis"
Task ids: w43-crippling-analysis-1 and -2. Prep grep (corpus-collisions.py
batch-D run, quoted verbatim): crippling-analysis: 'crippling' -> 0,
'inter rivet buckling' -> 0, 'shape constant' -> 0 in
eval/hit1-corpus.yaml; direct grep of the tokens crippling-analysis,
local-crippling-stress, inter-rivet-buckling and stringer-crippling
returns 0 matches (grep exit 1), and "crippling" has 0 hits under any
skills/**/SKILL.md. The only adjacent batch-D hit, 'net section' -> 1,
belongs to metallic-fastener-joints and is not reused. Collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the local crippling and
inter-rivet allowables of a formed compression stiffener (angle, channel,
Z, hat stringer, bulb angle):" and include the outputs in the Claim.
First tag: crippling-analysis. Additional tags ONLY: shape-constant-
method, element-crippling, local-crippling-stress, inter-rivet-buckling,
stringer-crippling, stiffener-compression-allowable,
formed-compression-shapes, johnson-euler-interaction. NEVER single
generic words (crippling, buckling, column, flange, web, skin, stiffener,
stress, allowable, compression alone) and NEVER the sibling compound
tokens euler-buckling, critical-buckling-load, effective-length-factor,
slenderness-ratio, plate-buckling, effective-width, panel-buckling,
hoop-stress, frame-pitch, spar-cap, shear-flow, moment-amplification.
50-150 words, <=1024 chars (draft below is 130 words, 923 chars,
no em dash, no content-policy sweep term, action verb present).
Recommended wording (outputs and verdict in Claim order): "Use when you
must compute the local crippling and inter-rivet allowables of a formed
compression stiffener (angle, channel, Z, hat stringer, bulb angle):
compute the element crippling stress F_cc = min(F_cy,
C*sqrt(F_cy*E)*(t/b)**0.75) with the shape constants C = 0.31 for
one-edge-free flanges and C = 0.55 for webs between corners, average the
element crippling loads over the section area, compute the inter-rivet
buckling stress of the attached flat from the rivet pitch, and run the
Johnson-Euler interaction that anchors the stiffener column curve on the
local crippling stress. Produces the crippling allowable, the
inter-rivet allowable, the column interaction allowable, the compression
allowable and the margin against the applied stress that gate the local
stiffener compression check. Trigger: stringer crippling, local
crippling stress, inter-rivet buckling, shape constant method, formed
compression shapes."

FORBIDDEN TOKENS (belong to siblings): global column Euler load at
resolved end conditions, effective-length-factor, yield-based transition
slenderness and the sigma_y plateau of a whole solid column
(buckling-analysis); flat-panel k-coefficient versus aspect ratio,
compression-shear panel interaction, effective width of stiffened skin
(plate-buckling); moment amplification, secant formula, eccentric loaded
column of the global member (beam-column-analysis); hoop stress, skin
thickness, stringer spacing, frame pitch, stringer area from the strip
load, effective-skin-width (fuselage-skin-stringer); spar cap area, web
thickness from the box couple (wing-box-sizing). The stiffened-panel and
shell closure belongs to the vehicle-design leaves.

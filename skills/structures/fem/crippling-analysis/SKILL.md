---
name: crippling-analysis
description: "Use when you must compute the local crippling and inter-rivet allowables of a formed compression stiffener (angle, channel, Z, hat stringer, bulb angle): compute the element crippling stress F_cc = min(F_cy, C*sqrt(F_cy*E)*(t/b)**0.75) with the shape constants C = 0.31 for one-edge-free flanges and C = 0.55 for webs between corners, average the element crippling loads over the section area, compute the inter-rivet buckling stress of the attached flat from the rivet pitch, and run the Johnson-Euler interaction that anchors the stiffener column curve on the local crippling stress. Produces the crippling allowable, the inter-rivet allowable, the column interaction allowable, the compression allowable and the margin against the applied stress that gate the local stiffener compression check. Trigger: stringer crippling, local crippling stress, inter-rivet buckling, shape constant method, formed compression shapes."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: fem
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [crippling-analysis, shape-constant-method, element-crippling, local-crippling-stress, inter-rivet-buckling, stringer-crippling, stiffener-compression-allowable, formed-compression-shapes, johnson-euler-interaction]
  version: 0.1.0
  author: AeroSkills
---

# Crippling Analysis of Formed Compression Stiffeners (structures/fem/crippling-analysis)

Use when the LOCAL crippling of a formed thin-wall compression section
gates the stiffener sizing: the element crippling stress of each flat
(one-edge-free outstanding legs and flanges with shape constant C = 0.31,
no-edge-free webs and crowns between corners with C = 0.55) by the
shape-constant power-law correlation of the Gerard crippling family
(NACA-TN-3784, NACA-TN-3785, paraphrased by name only), the area-weighted
section crippling allowable, the inter-rivet buckling allowable of the
fastener-attached flat between rivet lines (Semonian and Peterson,
NACA-TN-3431, paraphrased), and the Johnson-Euler stiffener column
interaction that anchors the short-column curve on the local crippling
stress rather than on yield. Pure Python, stdlib only, closed form, SI
units. This leaf covers the LOCAL cross-section check only: it pairs with
structures/fem/buckling-analysis for the global Euler column of the same
member, with structures/fem/beam-column-analysis for the global
axial-plus-bending member, and with structures/fem/plate-buckling for the
stability of single flat panels with known dimensions.

## Domain quick reference

- Element crippling stress by edge-support class s (one-edge-free "oef"
  with C_OEF = 0.31, no-edge-free "sef" with C_SEF = 0.55):
  F_cc,i = min(F_cy, C_s * sqrt(F_cy * E) * (t / b)**0.75). The yield cap
  binds because the raw power law would exceed F_cy at small b/t (the
  2024-T3 one-edge-free curve crosses yield near b/t = 8.3).
- Section crippling allowable: the element crippling loads are averaged
  over the section area, F_cc = sum(F_cc,i * A_i) / sum(A_i) with A_i =
  b_i * t_i per flat; a bulb element (solid cylinder of diameter d)
  carries at F_cy with area pi * d**2 / 4 and does not cripple locally.
  Corner radii are ignored; b is the flat width.
- Inter-rivet buckling of the attached flat of thickness t_attach between
  rivets at pitch s: sigma_ir = K * pi**2 * E / (12 * (1 - nu**2)) *
  (t_attach / s)**2 with K = 4.0 (rivet lines as simple supports, long
  plate); for aluminum at nu = 0.33 this reads about 3.69 * E *
  (t_attach / s)**2. Inter-rivet allowable F_ir = min(sigma_ir, F_cy).
- Johnson-Euler interaction anchored on the crippling allowable: the
  crippling stress is the lambda-tending-to-0 limit of the stiffener
  column curve, so the parabola anchors at F_cc, never at sigma_y.
  lambda_t = pi * sqrt(2 * E / F_cc); for lambda <= lambda_t,
  F_col = F_cc * (1 - F_cc * lambda**2 / (4 * pi**2 * E)) (Johnson arm);
  for lambda > lambda_t, F_col = pi**2 * E / lambda**2 (Euler arm). At
  lambda_t both arms equal F_cc / 2 exactly (tangency by construction).
- Stiffener compression allowable and margin: F_comp = min(F_col, F_ir);
  MS = F_comp / sigma_applied - 1; the verdict is pass when MS >= 0.
- Units are SI throughout: b, t, d and pitch in m, stresses in Pa,
  slenderness lambda = K * L / r dimensionless. Materials registry holds
  only 2024-T3 (E 72.4 GPa, F_cy 290 MPa, nu 0.33) and 7075-T6 (E 71.7
  GPa, F_cy 462 MPa, nu 0.33); the correlation constants are calibrated on
  the aluminum sheet crippling test family.

## Workflow

1. Resolve the material constants with material(name), case and
   whitespace insensitive, for "2024-T3" or "7075-T6" (step 1 of the
   workflow in the contract test docstrings).
2. Expand the formed shape into its flat element list with
   formed_shape_elements(shape, **dims): "angle" (b1, b2, t), "channel"
   and "z" (bw, bf, t), "hat" (bc, bl, t), "bulb-angle" (b1, bs, d, t).
3. Compute each element crippling stress with
   element_crippling_stress(b, t, edge_class, mat), edge_class "oef" or
   "sef", yield capped.
4. Average the element crippling loads over the section area with
   section_crippling_stress(elements, mat) to get the section crippling
   allowable F_cc and the total flat area.
5. Compute the inter-rivet allowable of the fastener-attached flat with
   inter_rivet_allowable(t_attach, pitch, mat), yield capped.
6. Run the Johnson-Euler interaction with
   column_interaction_allowable(fcc, lam, mat): regime "johnson" at or
   below lambda_t, "euler" above, tangent at F_cc / 2.
7. Combine into the stiffener compression allowable and margin with
   stiffener_compression_check(elements, mat, t_attach, pitch, lam,
   sigma_applied): F_comp = min(F_col, F_ir), MS and the pass verdict;
   cross-check the margin directly with compression_margin(f_allowable,
   sigma_applied).
8. Confirm the deterministic checks with the contract test
   scripts/test_crippling_analysis.py.

## Worked example

2024-T3 (E = 72.4 GPa, F_cy = 290 MPa, nu = 0.33, sqrt(F_cy * E) =
4.58214e9 Pa). All values are REAL outputs of
scripts/crippling_analysis_logic.py.

- Z-stringer t = 1.6 mm, flanges 19 mm, web 32 mm, rivet pitch 25 mm,
  lambda = 40, applied 150 MPa: element crippling web (no-edge-free,
  b/t = 20) 266.4762 MPa and each flange (one-edge-free, b/t = 11.9)
  222.0520 MPa; section F_cc = (32*266.4762 + 2*19*222.0520)/70 =
  242.3602 MPa (0.8357 of F_cy) over the 1.12e-4 m^2 flat area;
  inter-rivet sigma_ir raw 1094.84 MPa capped at 290.00 MPa (the 1.6 mm
  flange at 25 mm pitch cannot buckle between fasteners before yield);
  column interaction lambda_t = 76.790, regime johnson, F_col =
  209.4793 MPa at lambda 40 (13.6 percent below the crippling allowable);
  compression allowable min(209.4793, 290.00) = 209.4793 MPa; MS =
  209.4793/150 - 1 = 0.396529, pass.
- Angle stringer legs 25 x 25 mm, t = 1.6 mm, pitch 25 mm, lambda = 50,
  applied 120 MPa: each leg (one-edge-free, b/t = 15.6) 180.7444 MPa;
  section F_cc = 180.7444 MPa (0.6233 of F_cy); inter-rivet allowable
  290.00 MPa; lambda_t = 88.920; F_col = 152.1704 MPa at lambda 50;
  compression allowable 152.1704 MPa; MS = 0.268087, pass.
- Hat stringer crown 25 mm, legs 12 mm, t = 0.7 mm, pitch 25 mm,
  lambda = 60, applied 100 MPa: crown (no-edge-free, b/t = 35.7)
  172.5041 MPa; each leg (one-edge-free, b/t = 17.1) 168.6039 MPa;
  section F_cc = 170.5938 MPa (0.5883 of F_cy); inter-rivet sigma_ir raw
  and allowable 209.56 MPa, the genuine sub-yield inter-rivet regime of
  the thin attachment gauge; lambda_t = 91.528; F_col = 133.9390 MPa at
  lambda 60; compression allowable min(133.9390, 209.56) = 133.9390 MPa;
  MS = 0.339390, pass.
- Formed shape family sweep, 2024-T3, t = 1.6 mm (channel and Z share web
  32 mm and flanges 19 mm; bulb-angle plain leg 25 mm, stem 19 mm, bulb
  diameter 5 mm): section crippling allowable angle 25x25 180.7444 MPa,
  channel 32x19 242.3602 MPa, Z 32x19 242.3602 MPa (identical element
  classes), bulb-angle 218.5184 MPa (0.7535 of F_cy, lifted by the solid
  bulb carrying at yield); hat 25/12 at t = 0.7 mm 170.5938 MPa.
- Material normalization: the same Z geometry in 7075-T6 (E = 71.7 GPa,
  F_cy = 462 MPa) gives section F_cc = 304.4203 MPa but only 0.6589 of
  F_cy versus 0.8357 for 2024-T3, the lower normalized crippling of the
  higher-strength alloy under the sqrt(F_cy * E) fold.
- Johnson-Euler interaction curve for the Z (F_cc = 242.3602 MPa,
  lambda_t = 76.790): lambda 20 -> 234.1400 MPa, 40 -> 209.4793 MPa,
  60 -> 168.3781 MPa (johnson arm); 100 -> 71.4559 MPa and 150 ->
  31.7582 MPa (euler arm). Both arms at lambda_t return 121.180120 MPa =
  F_cc / 2, relative difference 2.46e-16.
- Identity outputs: doubling t_attach at fixed pitch gives stress ratio
  4.000000000000 (relative difference 0); quadrupling b at fixed t gives
  stress ratio 0.353553390593 = (1/4)**0.75 (relative difference 0); the
  stubby one-edge-free element at b/t = 5 returns exactly 290.0 MPa
  (yield cap); the section average lies strictly between its element
  extremes; every non-physical input raises ValueError.
- Read-off: the 2024-T3 Z-stringer at 150 MPa design compression runs a
  0.40 margin driven by the column interaction at lambda 40, not by
  crippling (crippling sits 62 percent above the applied stress and
  inter-rivet is yield capped); the same stiffener in 7075-T6 would carry
  about 26 percent more crippling load, and lengthening the bay toward
  lambda 77 halves the column allowable at the crippling-stress-based
  transition.

## Verification

- Confirm the Z-stringer worked example: web element 266.4762 MPa,
  flange element 222.0520 MPa, section F_cc 242.3602 MPa (0.8357 of
  F_cy), inter-rivet raw 1094.84 MPa capped at 290.00 MPa, lambda_t
  76.790, F_col 209.4793 MPa at lambda 40, compression allowable
  209.4793 MPa, margin 0.396529, verdict pass.
- Confirm the angle (section F_cc 180.7444 MPa, F_col 152.1704 MPa at
  lambda 50, margin 0.268087) and hat (section F_cc 170.5938 MPa,
  inter-rivet raw and allowable 209.56 MPa, F_col 133.9390 MPa at lambda
  60, margin 0.339390) anchors.
- Confirm the family sweep: channel and Z give the same section F_cc
  242.3602 MPa; bulb-angle 218.5184 MPa sits above the plain angle
  180.7444 MPa; the 7075-T6 Z gives 304.4203 MPa at the lower normalized
  ratio 0.6589.
- Confirm the interaction curve: F_col 234.1400 MPa (lambda 20),
  168.3781 (60), 71.4559 (100, euler), 31.7582 (150, euler), and both
  arms equal F_cc / 2 at lambda_t within 1e-9 relative (2.46e-16 on the
  module).
- Confirm the identities: doubling t_attach quadruples sigma_ir; the
  power law scales as (1/4)**0.75 under a quadrupled width; element
  crippling never exceeds F_cy and equals F_cy at b/t = 5 for a stubby
  one-edge-free 2024-T3 element; sef allowance >= oef allowance at equal
  b/t; the section average lies between the element extremes;
  compression_margin reproduces the check margin exactly.
- Confirm ValueError rejection on every non-physical input: non-positive
  b, t, t_attach, pitch, fcc, lambda, sigma_applied, element d, and shape
  dims; unknown material, shape, edge class, element class; an empty
  elements list; missing shape dims and missing element geometry keys.
- Run the contract test offline under both interpreters:
  python3 scripts/test_crippling_analysis.py and the pyenv 3.13.12
  interpreter used by the pre-push hook (33 tests, deterministic, both
  exit 0).

## Related leaves

- structures/fem/buckling-analysis: the GLOBAL column Euler load of the
  same member with the end-condition effective length factor and the
  yield-based transition; this leaf takes lambda = K*L/r as an input and
  anchors its Johnson curve on the local crippling stress, never on the
  solid-section yield.
- structures/fem/beam-column-analysis: the global axial-plus-bending
  member check with moment amplification, the sibling that disclaims the
  local crippling of the compression flange as outside its global scope.
- structures/fem/plate-buckling: the flat-panel stability check with the
  k-coefficient versus aspect ratio and the edge conditions, the routing
  home for single flat panels with known dimensions and for riveted
  skin-strip panel checks between fastener rows.
- structures/fem/beam-frame-analysis, structures/fem/truss-analysis and
  structures/fem/shrink-fit-analysis: the other member-level and
  joint-level checks in the fem pack.
- vehicle-design leaves fuselage-skin-stringer and wing-box-sizing: the
  overall stiffened shell and wing box closure that CONSUME the local
  stiffener allowable produced here.

## Pitfalls

- Routing the GLOBAL column here: the Euler load at resolved end
  conditions, the radius of gyration from full section properties and
  the yield-based transition classification of a whole solid column
  belong to structures/fem/buckling-analysis; this leaf takes the
  effective slenderness lambda as an input and its Johnson curve is
  anchored on the local crippling stress.
- Routing single flat panels here: the flat-panel k-coefficient versus
  aspect ratio, the panel compression-shear interaction and the
  effective width of stiffened skin belong to structures/fem/
  plate-buckling; plate-buckling in turn hands the stiffened-shell and
  wing-box closure to the vehicle-design leaves.
- Averaging crippling stresses without the area weights: the section
  allowable is the load average sum(F_cc,i * A_i) / sum(A_i), so a wide
  thin web with a low element stress drags the section allowable down
  even when the stiffer flanges cripple higher.
- Forgetting the yield cap: the raw power law crosses F_cy near b/t =
  8.3 for one-edge-free 2024-T3 elements, so stubby flats return exactly
  F_cy; an uncapped reading of the correlation overstates stubby-element
  allowables.
- Treating inter-rivet as a panel check: the rivet-line simple-support
  long-plate value with the fixed coefficient K = 4.0 applies to the
  fastener-attached flat between rivets; the riveted skin-strip check
  between fastener rows is a flat-panel check with known dimensions for
  plate-buckling.
- Anchoring the Johnson curve on sigma_y: the stiffener short-column
  curve anchors on the LOCAL crippling allowable F_cc (the
  lambda-tending-to-0 limit), so using sigma_y in the parabola
  overstates short stiffeners whose section cripples before it yields.
- Reading the inter-rivet allowable above yield: F_ir = min(sigma_ir,
  F_cy), so a thick attached flat at a tight pitch is yield limited and
  the inter-rivet number to report is F_cy, not the raw buckling stress.
- Applying the correlation outside its calibration: the shape constants
  are calibrated on the aluminum sheet crippling test family, so the
  method is stated for 2024-T3 and 7075-T6 only; extruded, machined or
  fiber-reinforced sections, elevated temperature, fastener bearing or
  pull-through of the attachments, and corner radii (flat widths only)
  are out of scope for this closed form.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_crippling_analysis.py

The 33 tests cover the material registry resolution (case and whitespace
insensitive, ValueError on unknowns), the worked-example anchors for the
Z, angle and hat stringers (element, section and interaction allowables
with the margins of safety), the formed-shape family sweep (channel and Z
identical classes, bulb-angle elevation above the plain angle), the
7075-T6 material normalization, the Johnson-Euler interaction curve and
its tangency at lambda_t, the closed-form identities (inter-rivet
quadratic scaling, crippling power-law quartering, yield cap at b/t = 5,
class ranking, section averaging bounds, margin reproduction),
determinism, math-only imports, and ValueError rejection of every
non-physical input. All numeric asserts are tolerance-based and pass
under both python3 and the pyenv 3.13.12 hook interpreter.

## Compliance

- Standards referenced, not reproduced: the crippling method paraphrases
  the public-domain NACA crippling literature by name only (Gerard and
  Becker, Handbook of Structural Stability Part IV, NACA-TN-3784, and
  Part V, NACA-TN-3785; Semonian and Peterson, NACA-TN-3431, for
  inter-rivet buckling). FAR-25 and CS-25 frame the airframe structural
  context (summary references per standards-map.yaml; no standard text is
  reproduced).
- compliance: STANDARDS-REF, gated: false.

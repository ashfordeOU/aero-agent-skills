# Wave-34 leaf spec: lug-joint-analysis (structures, fem pack)

- Path: skills/structures/fem/lug-joint-analysis/
- Pack: fem (stdlib hand-calc joint stress analysis alongside
  beam-frame-analysis, truss-analysis, buckling-analysis; the leaf is
  METALLIC pin-loaded lugs). Closest siblings: composite-bolted-joints
  (single-fastener-row analysis IN A COMPOSITE LAMINATE with a
  bypass-ratio split; no lug proportioning e/D, no head geometry, no
  tearout-plane geometry from the hole contour, no e/D governing-mode
  map), contact-analysis (cites lug-to-bolt bearing only as an FEA
  contact application), strain-life-fatigue (tags notched-lug only as
  a notch Kt example), notch-sensitivity (lug only as a notched
  detail). Alias checks: pin/fitting/bushing/tearout wording return
  only pin-jointed truss/frame and contact-analysis interfaces.
- Standards id: mmpsd (lug ultimate data heritage, reference-only).
  Ledger Standard: mmpsd. Also cite far-25 in the body as fitting
  substantiation context (id exists).
- Family: structures

## Claim

Analyze a metallic pin-loaded lug fitting under an axial pin load:
the bearing stress on the hole, the net-section tension stress across
the lug width, the tearout shear stress on the two planes tangent to
the hole running to the outer contour, the margin per mode against the
material allowables, the governing failure mode (lowest margin), and
the governing-mode capacity map over the edge-distance ratio e/D
(short-lug net-tension / intermediate tearout / long-lug bearing).
Produces the applied stresses, per-mode margins, governing mode and
pass/fail for a round-end lug (w = 2e), the limiting capacity, and the
e/D governing sweep.

Does NOT do: composite-laminate bolted joints with bypass ratio
(composite-bolted-joints owns single-row laminate bearing/bypass/net-
tension/shear-out); FEA contact stress (contact-analysis); fastener
flexibility / multi-fastener elastic load distribution (declined:
scope beyond a compact deterministic stdlib contract); lug fatigue
life (strain-life-fatigue uses a lug only as an example detail).

## Model (implement exactly)

Conventions: round-end lug, hole of diameter D at the center of a
round head of radius e, lug width w = 2e, thickness t, axial pin load
P. Edge distance e must exceed D/2 and w must exceed D (ValueErrors).
Material allowables are INPUTS (F_tu ultimate tension, F_su ultimate
shear, F_bru lug bearing ultimate): flag them as MMPDS chapter 9 data
in the SKILL body; never reproduce standard tables.

Mode stresses:
- bearing: sigma_b = P / (D t).
- net-section tension: sigma_nt = P / ((w - D) t).
- tearout: sigma_te = P / (2 t L_te), L_te = sqrt(e^2 - (D/2)^2)
  (the length of each of the two shear planes from the hole tangent to
  the outer contour).
Margins: m_mode = allowable / applied - 1 (bearing uses F_bru, tension
F_tu, tearout F_su). Governing mode = argmin margin; pass when the min
margin >= 0.

Functions (pure stdlib):
- lug_stresses(load_n, hole_diameter_m, thickness_m, lug_width_m,
  edge_distance_m) -> dict {bearing_pa, net_tension_pa, tearout_pa,
  tearout_plane_length_m, net_section_width_m}. ValueErrors: load < 0,
  any dimension <= 0, edge_distance <= hole_diameter/2, lug_width <=
  hole_diameter.
- lug_margins(stresses, f_tu_pa, f_su_pa, f_bru_pa) -> dict
  {bearing_margin, net_tension_margin, tearout_margin}. ValueErrors on
  non-positive allowables.
- lug_analysis(load_n, hole_diameter_m, thickness_m, lug_width_m,
  edge_distance_m, f_tu_pa, f_su_pa, f_bru_pa) -> dict
  {bearing_stress_pa, net_tension_stress_pa, tearout_stress_pa,
  bearing_margin, net_tension_margin, tearout_margin, governing_mode,
  min_margin, passes (bool), e_over_d, d_over_t,
  tearout_plane_length_m, net_section_width_m}.
- lug_allowable_capacity(hole_diameter_m, thickness_m, edge_distance_m,
  f_tu_pa, f_su_pa, f_bru_pa) -> dict {bearing_capacity_n,
  net_tension_capacity_n, tearout_capacity_n, limiting_mode,
  limiting_capacity_n}: per-mode P_allow = allowable * geometry term
  (bearing F_bru D t; tension F_tu (w - D) t; tearout F_su 2 t L_te);
  the limiting mode has the smallest capacity.
- lug_governing_map(hole_diameter_m, thickness_m, f_tu_pa, f_su_pa,
  f_bru_pa, e_over_d_lo = 0.6, e_over_d_hi = 2.5, steps = 20) -> list
  of dicts {e_over_d, governing_mode, capacity_n} sweeping the e/D
  ratio at fixed D and t with e = ratio * D, w = 2e.

Governing-map identity to test: for typical aluminum allowables the map
shows net-tension governing at low e/D, tearout in the middle band,
and bearing at high e/D (short-lug tension / intermediate tearout /
long-lug bearing behavior). The e/D = 1 case has tearout_plane_length
= sqrt(1 - 0.25) D = 0.8660254 D.

## Worked example

7075-T6 lug: D = 20 mm, t = 12 mm, e = 24 mm (e/D = 1.2, w = 48 mm),
F_tu = 572 MPa, F_su = 331 MPa, F_bru = 1050 MPa, P = 90 kN.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- bearing stress = 90000 / (0.020 * 0.012) = 375.0 MPa; margin =
  1050/375 - 1 = +1.800.
- net-section tension = 90000 / ((0.048 - 0.020) * 0.012) =
  267.857 MPa; margin = 572/267.857 - 1 = +1.135.
- tearout: L_te = sqrt(24^2 - 10^2) = 21.817 mm; sigma_te = 90000 /
  (2 * 0.012 * 0.021817) = 171.881 MPa; margin = 331/171.881 - 1 =
  +0.926.
- governing_mode = tearout; min_margin = +0.926; passes True.
- Same lug at P = 200 kN: tearout stress = 381.958 MPa; margin -0.133;
  passes False.
- Capacity sweep (D = 20, t = 12, 7075 allowables): net-tension
  governs e/D below about 1.03; tearout governs e/D ~1.03-1.74 (e.g.
  168060 N at e/D 1.17); bearing governs above ~1.74 (252000 N,
  constant). All three modes appear as governing across the range.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: load < 0; non-positive dimensions; edge_distance <=
  hole_diameter/2; lug_width <= hole_diameter; non-positive
  allowables.
- Worked case: stresses and margins match the values above to 1e-6
  relative; governing tearout; passes True.
- Higher load: P = 200 kN gives tearout margin -0.133 and passes
  False; the governing mode stays tearout.
- Geometry identity: for e/D = 1, tearout_plane_length =
  sqrt(3)/2 * D = 0.8660254 D to 1e-9; net_section_width = 2e - D.
- Per-mode capacity: lug_allowable_capacity returns the three
  capacities matching the margin identities (capacity = applied load
  that makes the margin 0); limiting mode matches governing from
  lug_analysis at the same geometry.
- Governing map: e/D sweep shows all three modes as governing at least
  once over [0.6, 2.5] for the 7075 allowables; capacity is
  monotonically non-decreasing in e/D; bearing capacity is constant in
  e/D (geometry independent).
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-lug-joint-analysis.yaml)

Query 1 (copy verbatim):
  "compute the bearing, net section tension and tearout stresses and margins of a metallic pin loaded lug from the hole diameter, lug width, edge distance and material allowables"
  intent: "structures; pin loaded lug bearing net tension tearout stresses and margins"
  expected_skill: "structures/fem/lug-joint-analysis"
Query 2 (copy verbatim):
  "determine the governing failure mode and the limiting lug capacity over the edge distance ratio sweep for a round end lug fitting"
  intent: "structures; lug governing mode and capacity over edge distance ratio"
  expected_skill: "structures/fem/lug-joint-analysis"
Task ids: w34-lug-joint-analysis-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must analyze a metallic pin-loaded
lug fitting under an axial load:" and include the outputs in the
Claim. First tag: lug-joint-analysis. Additional tags ONLY:
pin-loaded-lug, lug-bearing-stress, lug-net-section-tension,
lug-tearout-shear, lug-edge-distance-ratio, round-end-lug. NEVER
single generic words (lug, pin, bearing, tension, shear, joint,
fitting). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): bypass ratio, laminate,
composite, fastener row, net-tension as laminate outputs, shear-out
(composite-bolted-joints owns the composite single-row content with
bypass); FEA, contact pressure (contact-analysis); fatigue life, S-N
(strain-life-fatigue); buckling (buckling-analysis / plate-buckling).
The words "lug", "edge distance", "tearout", "round-end lug", "pin
load" are this leaf's own.

Tags: [lug-joint-analysis, pin-loaded-lug, lug-bearing-stress,
lug-net-section-tension, lug-tearout-shear, lug-edge-distance-ratio,
round-end-lug]

Sibling-citation lines for Related leaves:
structures/composites/composite-bolted-joints (the composite single-
row joint sibling; this leaf is the metallic lug with e/D proportioning
and no bypass concept),
structures/fem/contact-analysis (FEA contact boundary),
structures/fem/beam-frame-analysis and truss-analysis (pin-jointed
frame analysis siblings; they do not size lug fittings).

Ledger Standard: mmpsd.

---
name: torsion-shear-flow
description: "Use when you must compute the torsion shear flow of a closed or open structural section: the polar second moment J for solid and tube shafts, the Saint-Venant torsion constant for thin open rectangles and built-up open sections, the Bredt-Batho closed-section shear flow q = T/(2 A_m), the closed-section twist rate, the shear stress and torsional stress margin, and the multi-cell shear-flow distribution of a two-cell section under an applied torque. Produces the shear flow, twist rate, shear stress and margin that gate torsion checks of fuselage, wing-box and shaft sections. Trigger: torsion shear flow, Bredt-Batho, Saint-Venant torsion, angle of twist, closed-section shear flow, multi-cell section, torsional stress margin, shaft torque, fuselage torsion."
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
  tags: [torsion-shear-flow, bredt-batho, saint-venant-torsion, angle-of-twist, multi-cell-section, closed-section-shear-flow, torsional-stress-margin]
  version: 0.1.0
  author: AeroSkills
---

# Torsion Shear Flow (structures/fem/torsion-shear-flow)

Compute the torsional response of shafts, fuselage and wing-box
sections: polar second moment for solid and tube sections, the
Saint-Venant torsion constant for open thin sections, the Bredt-Batho
closed-section shear flow q = T / (2 A_m), the closed-section twist
rate, the shear stress and torsional stress margin, and the multi-cell
shear-flow distribution for a two-cell section under an applied torque.
This leaf implements the standard torsion methodology in pure Python,
stdlib only. It pairs with the bar-truss and frame solution leaves for
overall stiffness checks and with the buckling leaves for the load-carry
limit of the same sections.

## Domain quick reference

- Closed single cell (Bredt-Batho): A_m is the area enclosed by the
  mid-line of the section (rectangular box: (w - t) * (h - t), or the
  documented input A_m directly). Shear flow q = T / (2 * A_m) in N/m.
- Closed twist rate: d(theta)/dx = q / (2 * A_m * G) times the closed
  integral of ds/t, evaluated as
  T / (4 * A_m**2 * G) * sum(side_length_i / thickness_i) in rad/m.
- Closed shear stress: tau = q / t_min in Pa, with the margin
  tau_allow / tau - 1.
- Open thin sections (Saint-Venant): one thin rectangle of width b and
  thickness t has J = b * t**3 / 3; a built-up open section sums
  b_i * t_i**3 / 3 over independent rectangles (conservative open-section
  model, junction stiffening ignored). Twist rate = T / (G * J); surface
  shear stress tau = T * t_max / J uses the FULL thickness of the
  thickest element.
- Two-cell closed section: equal twist-rate compatibility
  (q1*(S1 + S12) - q2*S12) / A1 == (q2*(S2 + S12) - q1*S12) / A2 plus
  torque balance T = 2*A1*q1 + 2*A2*q2, solved by Cramer's rule, where
  S_i is the outer wall length/thickness integral of cell i and S12 that
  of the shared wall.
- Shafts: solid circular shaft J = pi*r**4/2; tube
  J = pi*(ro**4 - ri**4)/2. Shear stress at the surface tau = T*r/J.
- Units are SI throughout: N m torque, m dimensions, Pa modulus, rad/m
  twist. The shear modulus G and the allowable shear stress are always
  inputs; the module hard-codes no material.
- FAR-25 and CS-25 frame the airframe torque-load context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Classify the section: solid or tube shaft, open thin built-up
   section, or closed single-cell or two-cell section. Each class uses a
   different J or shear-flow model; do not mix them.
2. Solid or tube shaft: polar_j_solid(radius) or
   polar_j_tube(radius_outer, radius_inner) for J, then tau = T*r/J by
   hand and torsion_margin(tau, tau_allow).
3. Open thin section: saint_venant_j_rectangle(width, thickness) per
   element, or saint_venant_j_open(elements) over the list of
   (width, thickness) pairs of the built-up section.
4. Closed single cell: fix the mid-line enclosed area A_m, then
   bredt_shear_flow(T, A_m) for q and closed_twist_rate(T, G,
   side_lengths, thicknesses, A_m) for the twist rate (A_m may be
   omitted for a rectangular outline listed as (a, b, a, b)).
5. Closed-section stress and margin: tau = q / t_min, then
   torsion_margin(tau, tau_allow) to gate the section against the
   allowable shear stress.
6. Two-cell section: multi_cell_shear_flow(T, [A1, A2], [S1, S2], S12,
   G) returns the dict {q1, q2, twist_rate} with q in N/m and the twist
   rate in rad/m.
7. Confirm the deterministic checks with the contract test
   scripts/test_torsion_shear_flow.py.

## Worked example

Rectangular box 0.5 m x 0.3 m (mid-line enclosed area A_m = 0.5 * 0.3 =
0.15 m2), uniform wall 0.002 m, G = 27e9 Pa, T = 100 kN m.

- Shear flow: bredt_shear_flow(1e5, 0.15) = 333333 N/m, within 1% of
  the prep bound 333333 N/m.
- Twist rate: closed_twist_rate(1e5, 27e9, [0.5, 0.3, 0.5, 0.3],
  [0.002]*4) = 0.03292 rad/m: sum s/t = 1.6 / 0.002 = 800, and
  1e5 / (4 * 0.0225 * 27e9) * 800 = 0.03292.
- Shear stress: tau = q / t_min = 333333 / 0.002 = 1.667e8 Pa; margin at
  tau_allow 2.0e8: torsion_margin(1.667e8, 2.0e8) = 0.2.
- Solid shaft r = 0.05 m: J = 9.817e-6 m4. Tube ro = 0.05, ri = 0.04:
  J = 5.796e-6 m4. Open rectangle 0.1 m x 0.003 m: J = 9.0e-10 m4.
- Two-cell box (total width 0.6 m, height 0.3 m, divider 0.2 m from the
  left, uniform wall 0.002 m, G = 27e9 Pa, T = 50 kN m): A1 = 0.06 m2,
  A2 = 0.12 m2, S1 = 350, S2 = 550, S12 = 150;
  multi_cell_shear_flow(5e4, [0.06, 0.12], [350, 550], 150, 27e9) =
  q1 = 126263 N/m, q2 = 145202 N/m, twist rate 0.012763 rad/m; torque
  balance 2*A1*q1 + 2*A2*q2 reconstructs 50000 N m and the two cell
  twist computations agree to better than 1e-6.

## Verification

- Confirm polar_j_solid(0.05) = 9.817e-6 m4 and polar_j_tube(0.05,
  0.04) = 5.796e-6 m4; a tube with ri = 0 degenerates to the solid
  shaft value.
- Confirm saint_venant_j_rectangle(0.1, 0.003) = 9.0e-10 m4 and that a
  built-up open section equals the per-rectangle sum.
- Confirm bredt_shear_flow(1e5, 0.15) = 333333 N/m and
  closed_twist_rate at the worked box = 0.03292 rad/m, each within 1%
  of the prep bound.
- Confirm torsion_margin(1.667e8, 2.0e8) = 0.2, that the margin is 0 at
  the allowable and negative above it, and that it decreases as the
  running torque grows.
- Confirm multi_cell_shear_flow reconstructs the applied torque from
  q1 and q2, gives cell twist computations that agree within 1e-6, and
  degenerates to the single-cell q and twist for symmetric cells.
- Confirm every non-positive torque, modulus, dimension, area, wall
  integral and allowable stress, every empty or mismatched list, and
  every reversed tube radius raises ValueError.
- Run the contract test offline: python3
  scripts/test_torsion_shear_flow.py (33 tests, deterministic).

## Related leaves

- structures/fem/truss-analysis: bar truss solution methods for the
  axial load paths of the same airframe; it does not model torsion of
  closed sections.
- structures/fem/beam-frame-analysis: beam and frame bending response
  under applied loads, the companion stiffness check to torsion.
- vehicle-design/structures-integration/wing-box-sizing: sizes the
  wing-box skin and web from the lift-induced load path of the box,
  adjacent to but distinct from the torque shear-flow distribution
  here.
- structures/fem/plate-buckling: panel stability of the same walls
  under combined load, the post-check that can cap the allowable
  shear stress used in the margin.
- structures/fem/cylindrical-shell-buckling: stability of fuselage
  barrel sections that also carry torque shear flow.

## Pitfalls

- Using the polar J of the solid shaft for an open thin section: J =
  pi*r**4/2 belongs to axisymmetric shaft torsion; an open channel or
  slit tube must use the Saint-Venant b*t**3/3 sum, which gives a far
  lower torsional stiffness for the same material volume.
- Building A_m from the gross outer rectangle: the Bredt area is the
  mid-line enclosed area (0.15 m2 for the 0.5 x 0.3 box in the example,
  not 0.5*0.3 inflated by wall thickness twice over), so gross
  dimensions understate q and the twist rate.
- Treating an open section as a closed loop: a slit tube has no
  Bredt-Batho circulation, so q = T / (2 A_m) does not apply; its
  twist comes from the open-section J and is much larger than the
  closed envelope of the same shape.
- Double-counting the shared wall in the two-cell model: S12 enters
  each cell circulation with the opposite sign as (q1 - q2) flow, so
  it cancels when q1 = q2 and must never be added to both S1 and S2 as
  a positive path.
- Reading the margin sign backwards: margin = tau_allow / tau - 1 is
  positive below the allowable, zero at it, and negative past it; a
  negative margin at the worked torque means the wall or the allowable
  must change before the section passes.
- Mixing unit systems: kN m torque against Pa modulus and m dimensions
  silently shifts q and twist by decades; keep N m, m and Pa together
  before quoting a margin.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_torsion_shear_flow.py

The test covers the worked box contract (q = 333333 N/m and twist
0.03292 rad/m within 1% of the prep bounds, tau = 1.667e8 Pa, margin
0.2), the polar J truth table with the ri = 0 degeneracy, the
Saint-Venant J of a rectangle and of a built-up open channel, the
uniform-wall Bredt identity for the closed twist rate, the torque
doubling and area scaling laws, the two-cell solve (q1 = 126263 N/m,
q2 = 145202 N/m, twist 0.012763 rad/m, torque reconstruction to 50000
N m, cell twist compatibility within 1e-6, symmetric-cell degeneracy to
the single-cell result), dict key exactness, run-to-run determinism and
ValueError rejection of every non-physical input listed in the
validation list.

## Compliance

- FAR-25 and CS-25 are referenced, not reproduced: standards-map.yaml
  marks them gated: false and reference-only: true; only the summary
  paraphrase above is used, never standard text.
- compliance: STANDARDS-REF, gated: false.

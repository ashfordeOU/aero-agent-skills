# Wave-38 leaf spec: torsion-shear-flow (structures, fem pack)

- Path: skills/structures/fem/torsion-shear-flow/
- Pack: fem. Closest siblings: truss-analysis (pin-jointed 2D bar models
  only; its body disclaims torsion), wing-box-sizing (vehicle-design:
  sizes the spar web from the BENDING shear flow of the wing box under
  lift - it does not do closed-section torque shear-flow distribution),
  cylindrical-shell-buckling, plate-buckling, beam-frame-analysis,
  contact-analysis. Whole-tree grep: "shear flow" appears only as the
  bending-web context in wing-box-sizing and the aerodynamic loading
  context in wing leaves; "Bredt", "Saint-Venant torsion", "angle of
  twist", "multi-cell shear flow" = ZERO owning hits. ZERO owners of the
  torsion shear-flow function. GENUINE STRUCT gap (fresh probe).
- Standards id: far-25 (reference-only); cs-25 also reference-only
  (sibling plate-buckling convention carries both). Ledger Standard:
  far-25,cs-25.
- Family: structures

## Claim

Compute the torsional response of shafts, fuselage and wing-box sections:
polar second moment for solid and tube sections, Saint-Venant torsion
constant for open thin sections, the Bredt-Batho closed-section shear flow
q = T / (2 A_m), the closed-section twist rate, the shear stress and
torsional stress margin, and the multi-cell shear-flow distribution for a
two-cell section under an applied torque. Produces the shear flow, twist
rate, shear stress and margin that gate torsion checks of closed and open
structural sections. Does NOT do: pin-jointed truss solution (truss-
analysis); spar web sizing from bending shear (vehicle-design wing-box-
sizing); column and plate buckling (buckling-analysis / plate-buckling).

## Model (implement exactly)

Conventions: SI units (N m torque, m dimensions, Pa modulus, rad/m twist).
Module constants: no hard-coded material; G (shear modulus) and allowable
shear stress are inputs.

Closed single cell (Bredt-Batho):
- Enclosed area A_m is the area enclosed by the mid-line of the section
  (rectangular box: (w - t) * (h - t) to mid-line, or the documented
  input A_m directly).
- Shear flow q = T / (2 * A_m) (N/m).
- Twist rate d(theta)/dx = q / (2 * A_m * G) * closed integral ds/t =
  T / (4 * A_m**2 * G) * sum(side_length_i / t_i).
- Shear stress tau = q / t_min.
- Margin = tau_allow / tau - 1.

Open thin sections (Saint-Venant):
- For a thin rectangle of width b and thickness t: J = b * t**3 / 3.
- For a section of several thin rectangles (built up): J = sum(b_i *
  t_i**3)/3 when the rectangles are treated as independent (conservative
  open-section model); the module documents this as the standard
  conservative open-section J.
- Twist rate = T / (G * J); max shear stress at the surface of the
  thickest element tau = T * t_max / J (thin-rectangle torsion formula).
- Shear stress for a slit tube or open channel uses the same J.

Functions (pure stdlib):
- polar_j_solid(radius) -> float: pi * r**4 / 2. ValueError: radius <= 0.
- polar_j_tube(radius_outer, radius_inner) -> float: pi * (ro**4 - ri**4)
  / 2. ValueErrors: ro <= 0, ri < 0, ri >= ro.
- saint_venant_j_rectangle(width, thickness) -> float: width * thickness
  **3 / 3. ValueErrors: width <= 0, thickness <= 0.
- saint_venant_j_open(elements) -> float: sum of width_i * t_i**3 / 3
  where elements is a list of (width, thickness). ValueError: empty list,
  any non-positive entry.
- bredt_shear_flow(T, A_m) -> float: T / (2 * A_m). ValueErrors: T < 0
  (allow 0), A_m <= 0.
- closed_twist_rate(T, G, side_lengths, thicknesses) -> float: T /
  (4 * A_m**2 * G) * sum(s_i / t_i) where A_m is passed in or computed
  from the side geometry (documented input A_m). ValueErrors: G <= 0,
  mismatched lists, non-positive entries.
- multi_cell_shear_flow(T, cell_areas, wall_integrals, shared_integrals)
  -> dict: for a two-cell section, solve the two linear compatibility
  equations for the cell shear flows q1 and q2. Model: each cell i has
  enclosed area A_i, outer-wall length/thickness integral S_i = sum of
  outer segment length / thickness, and the shared wall has integral
  S12 = L12 / t12. Equal twist rate gives
  (q1*(S1+S12) - q2*S12) / A1 == (q2*(S2+S12) - q1*S12) / A2; torque
  balance gives T = 2*A1*q1 + 2*A2*q2. Solve the resulting 2x2 linear
  system by Cramer's rule (stdlib only); return {q1, q2, twist_rate}
  with twist_rate from either cell equation divided by (2 * A_i * G).
  ValueErrors: non-positive areas or integrals, T < 0, mismatched list
  lengths.
- torsion_margin(tau, tau_allow) -> float: tau_allow / tau - 1.
  ValueErrors: tau_allow <= 0.
Identity to test: closed_twist_rate of a box with a uniform wall equals
the Bredt formula; polar_j_tube with inner radius 0 equals polar_j_solid;
doubling T doubles q and the twist rate; margin decreases as T increases.

## Worked example

Verified at prep:
- Solid shaft radius 0.05 m: J = 9.817e-6 m4.
- Tube ro 0.05, ri 0.04: J = 5.796e-6 m4.
- Open rectangle width 0.1 m, thickness 0.003 m: J = 9.0e-10 m4.
- Rectangular box 0.5 m x 0.3 m (mid-line enclosed area A_m = 0.5*0.3 =
  0.15 m2), uniform wall 0.002 m, G = 27e9 Pa, T = 100 kN m:
  q = 333333 N/m; twist rate = 0.03292 rad/m (with side lengths 0.5, 0.3,
  0.5, 0.3 all over t 0.002: sum s/t = 1.6/0.002 = 800; T/(4*0.0225*27e9)
  * 800 = 0.03292).
  tau = q / 0.002 = 1.667e8 Pa; margin at tau_allow 2.0e8 = 0.2.
- Two-cell example (documented model in the spec body): rectangular two-
  cell box, total width 0.6 m, height 0.3 m, divider 0.2 m from the left,
  uniform wall 0.002 m, T = 50 kN m: A1 = 0.06 m2, A2 = 0.12 m2,
  S1 = 350, S2 = 550, S12 = 150 (length/thickness integrals);
  q1 = 126263 N/m, q2 = 145202 N/m; equal twist rate 0.012763 rad/m
  (verified at prep by the 2x2 compatibility + torque balance solve; the
  two twist computations agree to 1e-6).
Run your module and take the real outputs as assert targets; the anchor
values above are prep-verified bounds (closed-form section formulas).

## Validation list (contract test must include)

- polar J truth table (solid, tube, ri = 0 degeneracy).
- saint_venant J of a rectangle and of an open channel (sum of
  rectangles).
- bredt q at the worked example (333333 N/m within 1 percent).
- closed twist rate at the worked example (0.03292 rad/m within 1
  percent).
- Margin formula and sign behavior.
- Two-cell solve: torque balance reconstructs T from q1, q2 (50000 N m);
  the two-cell twist computations agree within 1e-6 (compatibility).
  Symmetric two-cell (equal areas and wall paths) degenerates to the
  single-cell q and twist.
- ValueErrors for all non-physical inputs.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave38-torsion-shear-flow.yaml)

Query 1 (copy verbatim):
  "compute the bredt-batho shear-flow and twist rate of a closed single-cell section under an applied torque"
  intent: "structures; closed section torsion shear flow"
  expected_skill: "structures/fem/torsion-shear-flow"
Query 2 (copy verbatim):
  "solve the saint-venant torsion constant and angle-of-twist for an open thin section and a multi-cell wing box"
  intent: "structures; Saint-Venant open section torsion and multi-cell shear flow"
  expected_skill: "structures/fem/torsion-shear-flow"
Task ids: w38-torsion-shear-flow-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the torsion shear flow of
a closed or open structural section:" and include the outputs in the
Claim. First tag: torsion-shear-flow. Additional tags ONLY: bredt-batho,
saint-venant-torsion, angle-of-twist, multi-cell-section, closed-section-
shear-flow, torsional-stress-margin. NEVER single generic words (torsion,
shear, flow, section, torque, twist). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): pin-jointed, direct stiffness
(truss-analysis); spar web, bending shear, root bending moment (vehicle-
design wing-box-sizing); buckling coefficient, critical stress (plate-
buckling / cylindrical-shell-buckling).

# Wave-40 leaf spec: peel-stress-bonded-joints (structures, composites pack)

- Path: skills/structures/composites/peel-stress-bonded-joints/
- Pack: composites. Closest sibling: adhesive-bonded-joints (its SKILL
  body states verbatim: "peel and adherend bending are out of scope.
  Peel-critical designs need a Goland-Reissner or FE analysis"; its
  logic implements the Volkersen-style lap-shear lag only). Whole-tree
  greps at prep: "goland", "peel stress", "adherend bending" = 0 hits
  in skills/structures/ (only the adhesive-bonded-joints fence
  sentence). GENUINE STRUCT gap (fresh probe, conf 0.7): the sibling
  leaf self-declares the peel function unbuilt.
- Standards id: cmh-17 (reference-only; composites pack convention).
  Ledger Standard: cmh-17.
- Family: structures

## Claim

Compute the peel stress at the overlap end of a single-lap bonded
joint with the classical Goland-Reissner analysis: find the bending
moment factor k from the load, adherend geometry and elastic modulus,
form the edge moment, resolve the peel stress from the adhesive
Winkler-foundation beam model at the overlap end, and return the peel
margin against an allowable peel strength. Produces the bending moment
factor, the edge moment, the peel decay coefficient, the maximum peel
stress and the peel margin that gate the peel-critical joint check.
Does NOT do: the elastic lap-shear lag distribution along the overlap
(adhesive-bonded-joints owns the Volkersen shear analysis); full
finite-element peel modeling; failure of the adherend or adhesive in
shear.

## Model (implement exactly)

Functions (pure stdlib; SI: load per unit width P_pw in N/m,
thickness in m, elastic moduli in Pa, peel stress in Pa; the joint is
a balanced single lap with identical adherends, analyzed per unit
width):
- bending_moment_factor(load_per_unit_width, adherend_thickness,
  adherend_modulus, poisson_ratio, overlap_half_length) -> float
  u^2 = (3 (1 - nu^2) / 2) * P_pw / (E t^3), then
  k = cosh(u c) / (cosh(u c) + 2 sqrt(2) sinh(u c)) (Goland-Reissner
  moment factor); k lies in (0, 1] and approaches the classical floor
  0.261 for very long overlaps; ValueErrors for negative load, non-
  positive thickness, modulus, half-length, or poisson outside
  (-1, 0.5).
- peel_decay_coefficient(adhesive_modulus, adhesive_thickness,
  adherend_modulus, adherend_thickness) -> float
  beta = sqrt(6 E_a / (t_a E t)), the classical exponential peel-decay
  parameter in 1/m; ValueErrors on non-positive inputs.
- peel_stress_at_overlap_end(load_per_unit_width, adherend_thickness,
  adherend_modulus, poisson_ratio, adhesive_modulus,
  adhesive_thickness, moment_factor) -> dict
  {"peel_stress": sigma_peel, "edge_moment": M0, "lambda": lam} with
  D = E t^3 / (12 (1 - nu^2)), M0 = k P_pw t / 2,
  lam^4 = 3 (1 - nu^2) E_a / (E t^3 t_a),
  w0 = M0 / (2 lam^2 D), sigma_peel = (E_a / t_a) w0; ValueErrors as
  bending_moment_factor plus non-positive adhesive modulus/thickness.
- peel_margin(peel_stress, peel_strength_allowable) -> float
  allowable / peel_stress; ValueError if peel_stress <= 0 or
  allowable <= 0.
Module constants: none beyond the formula literals (SQRT2 = sqrt(2)).

Identity to test: k goes to 1 as the load goes to 0 (bending moment
factor tends to the no-bending limit); k is monotone decreasing in
the overlap length and in the load; k stays in (0, 1] for all valid
inputs; doubling the adhesive modulus raises the peel stress by about
sqrt(2); doubling the adhesive thickness lowers the peel stress; the
peel stress is monotone increasing with the load; at the classical
long-joint limit k approaches about 0.261.

## Worked example

Aluminum adherends E = 70 GPa, nu = 0.33, t = 1.6 mm; epoxy adhesive
E_a = 1.5 GPa, t_a = 0.25 mm; overlap 25 mm (half-length c = 12.5
mm); load P = 4000 N over a 25 mm width, P_pw = 1.6e5 N/m:
- Average adherend stress sigma_avg = P_pw / t = 100 MPa.
- bending_moment_factor k = 0.518201.
- edge moment M0 = 66.3298 N m/m.
- lambda = 486.335 1/m.
- peel stress = 3.13768e7 Pa = 31.3768 MPa.
- peel_decay_coefficient beta = 566.947 1/m.
- peel_margin vs a 35 MPa allowable = 1.11547; vs 25 MPa = 0.796767.
Lower-load case P_pw = 8.0e4 N/m (sigma_avg 50 MPa): k = 0.598868,
M0 = 38.3275 N m/m, peel stress = 18.1306 MPa.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds, computed by running the prep
anchor script /tmp/w40spec/anchors_peel.py (prep-verified by stdlib
math).

## Validation list (contract test must include)

- bending_moment_factor(1.6e5, 1.6e-3, 70e9, 0.33, 0.0125) =
  0.518201 within 1e-5.
- bending_moment_factor at P_pw -> 0: k = 0.999924 (no-bending
  limit); at a very long overlap c = 1 m: k = 0.261204.
- k monotone decreasing in c: k(1 mm) = 0.928308 > k(10 mm) =
  0.287155; k monotone decreasing in load: 0.805922 (80 N/mm) >
  0.518201 (160 N/mm) > 0.417725 (400 N/mm).
- peel_decay_coefficient(1.5e9, 0.25e-3, 70e9, 1.6e-3) = 566.947
  within 0.01.
- peel_stress_at_overlap_end(1.6e5, ...) = 31.3768 MPa within 1e-3;
  edge moment 66.3298 within 1e-3; lambda 486.335 within 0.01.
- Peel growth: 80 N/mm -> 18.1306 MPa; 160 N/mm -> 31.3768 MPa;
  400 N/mm -> 63.23 MPa (monotone).
- Stiffness sensitivity: E_a doubled to 3 GPa raises peel to 44.37
  MPa; t_a doubled to 0.5 mm lowers peel to 22.19 MPa.
- peel_margin(31.3768e6, 35e6) = 1.11547 within 1e-3; ValueError at
  zero allowable.
- ValueErrors: negative load, zero adherend thickness, zero overlap
  half-length, poisson 0.6, zero adhesive modulus.
- Determinism; dict keys exactly peel_stress/edge_moment/lambda.

## Corpus fragment (eval/hit1-wave40-peel-stress-bonded-joints.yaml)

Query 1 (copy verbatim):
  "compute the peel-stress-bonded-joints goland-reissner peel stress at the overlap end of the single-lap joint with the bending-moment-factor and the edge moment from the load and the adherend stiffness"
  intent: "structures; Goland-Reissner peel stress and bending moment factor"
  expected_skill: "structures/composites/peel-stress-bonded-joints"
Query 2 (copy verbatim):
  "estimate the adherend-bending peel stress and the peel-margin against the allowable for the peel-critical bonded joint beyond the lap-shear analysis"
  intent: "structures; peel margin for peel-critical bonded joints"
  expected_skill: "structures/composites/peel-stress-bonded-joints"
Task ids: w40-peel-stress-bonded-joints-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the peel stress at
the overlap end of a single-lap bonded joint:" and include the outputs
in the Claim. First tag: peel-stress-bonded-joints. Additional tags
ONLY: goland-reissner, bending-moment-factor, adherend-bending,
peel-margin. NEVER single generic words (peel, stress, joint, bond,
adhesive, lap, shear, overlap). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): volkersen, shear-lag,
lap-shear, adhesive-shear-stress, overlap-shear-distribution
(adhesive-bonded-joints); tsai, maximum-stress, failure-index
(failure-criteria); cmh17-allowables (own leaf).

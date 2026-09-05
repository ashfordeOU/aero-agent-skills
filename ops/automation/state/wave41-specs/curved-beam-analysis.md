# Wave-41 leaf spec: curved-beam-analysis (structures, fem pack)

- Path: skills/structures/fem/curved-beam-analysis/
- Pack: fem (verified present at prep with beam-frame-analysis,
  beam-vibration, buckling-analysis, calculix-linear,
  calculix-nonlinear, contact-analysis, cylindrical-shell-buckling,
  diagonal-tension-field-webs, lug-joint-analysis, modal-analysis,
  plate-buckling, pressure-bulkhead, torsion-shear-flow, truss-analysis).
  Closest siblings are the two straight-beam leaves this one fences
  against: beam-frame-analysis (its frontmatter claim is "solve a
  two-dimensional rigid-jointed frame with the Euler Bernoulli beam
  element: build the local beam element stiffness from the axial and
  bending contributions, rotate it into the global frame with the member
  orientation, assemble the global stiffness matrix, apply the fixed
  support conditions, solve for the nodal displacements and rotations
  with a compact elimination solver, and recover the support reactions
  and the member end actions"; the straight Euler-Bernoulli bending
  block and the cantilever closed forms P L^3/(3 E I) and
  P L^2/(2 E I) carry no curvature radius, no neutral-axis shift and no
  fiber-stress law), beam-vibration (its body states the beam "is
  treated as a distributed-parameter member with bending stiffness EI
  (N m^2) and mass per unit length m (kg/m); every end condition reduces
  to a root of cos x cosh x = -1 or cos x cosh x = 1", straight-member
  frequencies only, no curved stress state), plus lug-joint-analysis
  (pin and lug bearing, no curved-member bending stress). Whole-tree
  greps at prep: "curved beam" and "winkler" = 0 hits in
  skills/structures/fem; the only Winkler token in the structures tree
  is peel-stress-bonded-joints (composites pack), an adhesive
  Winkler-foundation beam model for the bondline of a flat single-lap
  joint, which takes no curvature radius and no fiber stress. GENUINE
  STRUCTURES gap (fresh probe): no leaf applies the Winkler curved-beam
  correction to a curved member; the stress check of a frame corner,
  torque link or clevis arc is unowned.
- Standards id: far-25 (reference-only; exists in standards-map.yaml).
  Ledger Standard: far-25.
- Family: structures

## Claim

Stress-check a curved member (frame segment, torque link, clevis arc)
with the Winkler curved-beam correction: compute the neutral-axis radius
r_n of a rectangular radial section from the closed form
(r_o - r_i) / ln(r_o / r_i), or of a solid-round or circular-tube
section from the closed form (sqrt(r_c^2 - a_i^2) + sqrt(r_c^2 -
a_o^2)) / 2 with a_i = 0 for the solid case, take the eccentricity
e = r_c - r_n by which the neutral axis sits inward of the centroid
toward the center of curvature, resolve the bending stress at the inner
and outer fibers from the Winkler relation sigma = M (r_n - r_fiber) /
(A e r_fiber), add the axial stress P / A when the member also carries
axial load, compare the inner-fiber stress against the equivalent
straight Euler-Bernoulli extreme fiber stress 6 M / (A h) of the same
section to expose the curved-beam amplification, and return the
stress-to-allowable ratio with the pass/fail verdict. Produces the
neutral-axis radius, the eccentricity, the inner and outer fiber
stresses, the combined axial-plus-bending stresses, the curved-beam
amplification over the straight-beam value, and the verdict against the
allowable that gate the curved-member stress check. Does NOT do: rigid
frame solves, member end actions and support reactions of straight
members (beam-frame-analysis); natural frequencies of straight
continuous members (beam-vibration); pin bearing and lug tearout
(lug-joint-analysis); column or plate buckling (buckling-analysis,
plate-buckling). Deterministic closed-form core only; no FEA, no
iteration, no plasticity.

## Model (implement exactly)

Functions (pure stdlib, math only):

- neutral_axis_radius_rect(r_i, r_o) -> float (r_o - r_i) /
  log(r_o / r_i), the exact neutral-axis radius of a curved bar with a
  rectangular radial section spanning inner radius r_i to outer radius
  r_o (standard engineering closed form of A / integral(dA / rho),
  paraphrase of the classic Winkler curved-beam result); the width out
  of plane cancels. ValueError if r_i <= 0 or r_o <= r_i.
- neutral_axis_radius_circular_tube(r_c, a_i, a_o) -> float
  (sqrt(r_c**2 - a_i**2) + sqrt(r_c**2 - a_o**2)) / 2, the exact
  closed form of A / integral(dA / rho) for a circular cross-section
  whose material annulus (inner radius a_i, outer radius a_o) is
  centered at distance r_c from the center of curvature; a_i = 0.0
  reduces it to the solid circular section (r_c + sqrt(r_c**2 -
  a_o**2)) / 2. The closed form follows from the disk integrals
  integral(dA / rho) = 2 pi (r_c - sqrt(r_c**2 - a**2)) and is
  prep-verified by numeric quadrature (see worked example). ValueError
  if r_c <= 0, a_i < 0, a_o <= a_i or a_o >= r_c.
- eccentricity(r_centroid, r_n) -> float r_centroid - r_n: the inward
  shift of the neutral axis from the centroidal axis toward the center
  of curvature, positive for every physical curved beam. ValueError if
  r_centroid <= 0 or r_n <= 0.
- curved_beam_stress(moment, area, e, r_n, r_fiber) -> float moment *
  (r_n - r_fiber) / (area * e * r_fiber), the Winkler curved-beam
  bending stress at the fiber radius r_fiber (paraphrase of the
  standard curved-beam relation; the stress is hyperbolic across the
  depth, not linear as in the straight-beam law). Sign convention
  documented in the docstring and the SKILL body: positive moment opens
  the arc (tends to straighten the member), which puts the inner fiber
  (r_fiber < r_n) in tension, sigma > 0, and the outer fiber in
  compression, sigma < 0; a negative moment reverses both signs.
  ValueErrors if area <= 0, e <= 0, r_n <= 0 or r_fiber <= 0; moment is
  signed and takes any real value (zero gives zero stress).
- straight_beam_stress_rect(moment, area, depth) -> float
  6.0 * moment / (area * depth): the straight Euler-Bernoulli extreme
  fiber stress M c / I of the same rectangular radial section, with
  c = depth / 2 and I = area * depth**2 / 12 (the beam-frame-analysis
  straight-beam world), used only as the comparison baseline for the
  amplification. ValueError if area <= 0 or depth <= 0.
- combined_axial_stress(bending_stress, axial_force, area) -> float
  bending_stress + axial_force / area, tension positive; ValueError if
  area <= 0.
- stress_verdict(sigma, allowable) -> dict {"abs_stress", "ratio",
  "verdict", "margin"}: ratio = abs(sigma) / allowable, verdict "pass"
  when ratio <= 1.0 else "fail", margin = allowable - abs(sigma);
  ValueError if allowable <= 0. Dict keys exactly as documented.

All radii share one length unit and all stresses one stress unit: in
the worked example mm and MPa, with moment in N mm and area in mm^2, so
N mm / mm^3 = N / mm^2 = MPa. No magic numbers; no module constants
needed beyond the closed forms themselves.

Identity to test: for a fixed rectangular section the neutral-axis
radius is independent of the out-of-plane width; r_n always lies
strictly between r_i and r_c (neutral axis inward of the centroid);
curved_beam_stress at the inner fiber has larger magnitude than at the
outer fiber for the same moment; amplification over
straight_beam_stress_rect grows as the depth-to-radius ratio h / r_c
grows; a_i = 0 in neutral_axis_radius_circular_tube reproduces the
solid-section closed form; the closed forms equal numeric quadrature of
A / integral(dA / rho) (1e-9 class for the rectangle, 1e-6 class for
the 2-D tube grid); verdict flips from pass to fail exactly at
ratio = 1.0.

## Worked example

Torque-link / frame-corner style curved member, 7075-T6-like aluminum
alloy (allowable tension set at 500 MPa for the check; paraphrase of a
design allowable, no standard text): rectangular radial section with
inner radius r_i = 60 mm, outer radius r_o = 100 mm, depth
h = r_o - r_i = 40 mm, width b = 40 mm, area A = 1600 mm^2, centroidal
radius r_c = (r_i + r_o) / 2 = 80 mm. The member carries bending moment
M and axial tension P = 25 kN at the checked section of the arc.

Geometry (run the module and take the real outputs as assert targets;
the values below are prep-verified, computed by running the prep anchor
script /tmp/w41spec/anchor_curved_beam.py with stdlib math only):

- neutral_axis_radius_rect(60.0, 100.0) = 78.30461 mm. The neutral
  axis sits inward of the centroid at r_c - r_n = e = 1.69539 mm
  (eccentricity(80.0, 78.30461) = 1.69539 mm), i.e. shifted toward the
  center of curvature by about 4.2 percent of the depth.
- Cross-check: the closed form agrees with a 400000-bin quadrature of
  A / integral(dA / rho) to relative difference 1.69e-13; the tube
  closed form neutral_axis_radius_circular_tube(80.0, 10.0, 20.0) =
  78.41610 mm agrees with a 1401 x 1401 cell-centered quadrature to
  relative difference 1.08e-6 (grid limited), and
  neutral_axis_radius_circular_tube(80.0, 0.0, 20.0) = 78.72983 mm
  (e = 1.27017 mm) for the solid round section.

Load case 1, M = 1200 N m = 1.2e6 N mm (moderate in-service moment):
inner fiber sigma = curved_beam_stress(1.2e6, 1600.0, 1.69539,
78.30461, 60.0) = 134.95848 MPa (tension); outer fiber
curved_beam_stress(1.2e6, 1600.0, 1.69539, 78.30461, 100.0) =
-95.97509 MPa (compression). The straight Euler-Bernoulli baseline of
the same section is straight_beam_stress_rect(1.2e6, 1600.0, 40.0) =
112.5 MPa (M c / I with I = A h^2 / 12 = 213333.33 mm^4, c = 20 mm):
the curved-beam correction amplifies the inner fiber by a factor
1.19963 over the straight-beam reading, while the outer fiber runs at
0.85311 of it, the classic Winkler signature of a curved member.
Adding the axial tension P / A = 15.625 MPa: combined inner =
150.58348 MPa, combined outer = -80.35009 MPa. Against the 500 MPa
allowable: ratio 0.30117, verdict pass, margin 349.41652 MPa.

Load case 2, limit moment M = 4.0 kN m = 4.0e6 N mm with the same P:
inner fiber curved stress 449.86161 MPa, combined inner =
465.48661 MPa, ratio 0.93097, verdict pass, margin 34.51339 MPa.

Load case 3, ultimate moment M = 4.5 kN m = 4.5e6 N mm with the same
P: inner fiber curved stress 506.09432 MPa, combined inner =
521.71932 MPa, ratio 1.04344, verdict fail, margin -21.71932 MPa. The
same member read as straight (6 M / (A h) = 421.875 MPa combined) would
still pass, which is the point of the correction: the curved-beam
inner-fiber stress is the gating number at a frame corner or torque
link arc.

Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds from
/tmp/w41spec/anchor_curved_beam.py.

## Validation list (contract test must include)

- neutral_axis_radius_rect(60.0, 100.0) = 78.30461 within 1e-5;
  independence from width (the closed form has no width input);
  ValueError at r_i 0, r_i negative and r_o == r_i.
- neutral_axis_radius_circular_tube(80.0, 10.0, 20.0) = 78.41610
  within 1e-5; solid case (80.0, 0.0, 20.0) = 78.72983 within 1e-5;
  ValueErrors at r_c 0, a_i negative, a_o == a_i and a_o >= r_c.
- eccentricity(80.0, 78.30461) = 1.69539 within 1e-5; positive for
  physical inputs; ValueErrors at non-positive r_centroid or r_n.
- curved_beam_stress(1.2e6, 1600.0, 1.69539, 78.30461, 60.0) =
  134.95848 within 1e-4; outer fiber (..., 100.0) = -95.97509 within
  1e-4; |inner| > |outer| for the same moment; negative moment flips
  both signs exactly; zero moment gives 0.0; ValueErrors at area 0, e 0,
  r_n 0 and r_fiber 0.
- straight_beam_stress_rect(1.2e6, 1600.0, 40.0) = 112.5 exactly;
  amplification 134.95848 / 112.5 = 1.19963 within 1e-4; outer ratio
  0.85311 within 1e-4; ValueErrors at area 0 and depth 0.
- combined_axial_stress(134.95848, 25000.0, 1600.0) = 150.58348 within
  1e-4; tension positive, compression negative; ValueError at area 0.
- stress_verdict on case 1 inner: ratio 0.30117, verdict pass, margin
  349.41652 within 1e-3; case 3 inner: ratio 1.04344, verdict fail,
  margin -21.71932 within 1e-3; boundary: exactly ratio 1.0 gives pass;
  ValueError at allowable 0 and negative.
- Closed-form identities: r_n between r_i and r_c; amplification grows
  with h / r_c when the section depth grows at fixed r_c; a_i = 0 tube
  call equals the solid-section closed form.
- Determinism; fixed strings "pass" and "fail".

## Corpus fragment (eval/hit1-wave41-curved-beam-analysis.yaml)

Query 1 (copy verbatim):
  "stress-check the curved frame segment as a winkler curved beam: find the neutral-axis radius from the closed form, the neutral-axis eccentricity, and the inner and outer fiber stresses before rating the member against the allowable"
  intent: "structures; curved-beam neutral-axis radius and inner-outer fiber stress with the Winkler correction against an allowable"
  expected_skill: "structures/fem/curved-beam-analysis"
Query 2 (copy verbatim):
  "check the torque-link arc at the clevis for the curved-beam inner-fiber stress amplification over the straight euler-bernoulli reading and return the pass-fail verdict versus the allowable"
  intent: "structures; torque link clevis arc curved-beam inner-fiber amplification and stress verdict"
  expected_skill: "structures/fem/curved-beam-analysis"
Task ids: w41-curved-beam-analysis-1 and -2. Queries steer around the
astrodynamics tasks that already own the bare token "eccentricity"
(orbital eccentricity) by always pairing it with "neutral-axis", and
around the straight-beam leaves by leading with "curved".

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must stress-check a curved member
with the Winkler curved-beam correction:" and include the outputs in
the Claim (neutral-axis radius, eccentricity, inner and outer fiber
stress, curved-beam amplification over the straight-beam value, verdict
against the allowable). First tag: curved-beam-analysis. Additional
tags ONLY: winkler-curved-beam, neutral-axis-radius,
neutral-axis-eccentricity, inner-fiber-stress, curved-beam-
amplification. NEVER single generic words (beam, stress, bending,
moment, frame, eccentricity, vibration, frequency). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): element-stiffness, rigid-jointed-
frame, member-end-actions, support-reactions, rotation-degree-of-freedom,
portal-frame, gaussian-elimination (beam-frame-analysis);
characteristic-equation-roots, pinned-pinned, clamped-clamped, free-free,
rayleigh-quotient, natural-frequency, mode-shape (beam-vibration);
bearing-bypass, lug-tearout, pin-bearing, lug-efficiency
(lug-joint-analysis). Also keep the bare word eccentricity out of the
description: it must appear only inside neutral-axis-eccentricity.

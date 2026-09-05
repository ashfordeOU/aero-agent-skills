---
name: curved-beam-analysis
description: "Use when you must stress-check a curved member with the Winkler curved-beam correction: compute the neutral-axis radius from the closed form A / integral(dA / rho) for a rectangular radial or circular tube section, take the neutral-axis-eccentricity, resolve the Winkler inner and outer fiber stresses, add the axial stress P / A, compare the inner fiber to the straight Euler-Bernoulli reading for the curved-beam amplification, and return the stress-to-allowable ratio with the pass or fail verdict. Produces the neutral-axis radius, neutral-axis-eccentricity, inner and outer fiber stresses, curved-beam amplification over the straight-beam value, and verdict against the allowable. Trigger: winkler curved beam, curved frame segment, torque link arc, clevis arc, curved member stress."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: fem
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [curved-beam-analysis, winkler-curved-beam, neutral-axis-radius, neutral-axis-eccentricity, inner-fiber-stress, curved-beam-amplification]
  version: 0.1.0
  author: AeroSkills
---

# Curved Beam Analysis (structures/fem/curved-beam-analysis)

Use when the task is the stress check of a curved member: a frame
segment, torque link arc or clevis arc whose section bends about the
center of curvature. Where the straight Euler-Bernoulli beam law puts
the extreme fiber stress at M c / I with a linear gradient, a curved
member shifts its neutral axis inward of the centroid and stresses its
fibers hyperbolically, so the inner fiber runs hotter than any
straight-beam reading of the same section. This leaf applies the
Winkler curved-beam correction: it computes the neutral-axis radius of
the radial section from the exact closed form A / integral(dA / rho),
the neutral-axis-eccentricity e = r_c - r_n, the inner and outer fiber
stresses sigma = M (r_n - r_fiber) / (A e r_fiber), the combined
axial-plus-bending stresses, and the curved-beam amplification over
the straight-beam value, then rates the gating fiber stress against
the allowable. It pairs with the straight-member FEM leaves, and it
owns the frame-corner, torque-link and clevis-arc stress check that no
straight-beam or lug leaf covers.

## Domain quick reference

- Neutral-axis radius of a curved bar with a rectangular radial
  section spanning inner radius r_i to outer radius r_o:
  r_n = (r_o - r_i) / ln(r_o / r_i), the exact closed form of
  A / integral(dA / rho); the width out of plane cancels. The neutral
  axis always sits strictly between r_i and the centroidal radius
  r_c = (r_i + r_o) / 2.
- Neutral-axis radius of a circular solid or tube section whose
  material annulus (inner radius a_i, outer radius a_o) is centered at
  distance r_c from the center of curvature:
  r_n = (sqrt(r_c^2 - a_i^2) + sqrt(r_c^2 - a_o^2)) / 2, from the disk
  integrals integral(dA / rho) = 2 pi (r_c - sqrt(r_c^2 - a^2));
  a_i = 0.0 reduces the tube to the solid round section,
  r_n = (r_c + sqrt(r_c^2 - a_o^2)) / 2. Geometry requires a_o < r_c.
- Neutral-axis eccentricity: e = r_c - r_n, the inward shift of the
  neutral axis toward the center of curvature, positive for every
  physical curved beam.
- Winkler curved-beam bending stress at fiber radius r_fiber:
  sigma = M (r_n - r_fiber) / (A e r_fiber), hyperbolic across the
  depth. Sign convention: a positive moment opens the arc, tending to
  straighten the member, so the inner fiber (r_fiber < r_n) is in
  tension, sigma > 0, and the outer fiber is in compression,
  sigma < 0; a negative moment reverses both signs.
- Straight Euler-Bernoulli baseline of the same rectangular section:
  sigma_straight = 6 M / (A h), from M c / I with c = h / 2 and
  I = A h^2 / 12. The curved-beam amplification is the ratio of the
  Winkler inner-fiber stress to this value and grows with the
  depth-to-radius ratio h / r_c.
- Combined fiber stress with axial load: sigma + P / A, tension
  positive.
- Stress verdict: ratio = |sigma| / allowable, pass when ratio <= 1.0,
  margin = allowable - |sigma|.
- FAR-25 (25.301-25.307) sets the certification context for structure
  loads and strength; the allowable used here comes from the design
  allowables of the material, not from reproduced standard text.

## Workflow

1. Gather the curved-member data at the checked section: the inner and
   outer radii of the rectangular radial section (r_i, r_o), or the
   section center radius r_c with the material annulus radii (a_i, a_o)
   for a solid-round or circular-tube section, the section depth h and
   area A, the centroidal radius r_c = (r_i + r_o) / 2, the applied
   bending moment M (positive opens the arc), the axial load P when
   present, and the material allowable.
2. Compute the neutral-axis radius of the section: call
   neutral_axis_radius_rect(r_i, r_o) for the rectangular radial
   section, or neutral_axis_radius_circular_tube(r_c, a_i, a_o) for a
   circular section (pass a_i = 0.0 for the solid round). The closed
   forms are A / integral(dA / rho); the result is independent of the
   out-of-plane width of a rectangle and lies strictly between r_i and
   r_c.
3. Take the neutral-axis eccentricity with
   eccentricity(r_centroid, r_n): e = r_c - r_n, the inward shift of
   the neutral axis toward the center of curvature, positive for every
   physical curved member.
4. Resolve the Winkler fiber stresses with
   curved_beam_stress(moment, area, e, r_n, r_fiber) at the inner
   fiber r_i and the outer fiber r_o of the section, and form the
   straight Euler-Bernoulli baseline of the same section with
   straight_beam_stress_rect(moment, area, depth) to expose the
   curved-beam amplification, the inner-fiber stress divided by the
   straight reading.
5. Add the axial contribution when the member carries axial load with
   combined_axial_stress(bending_stress, axial_force, area),
   tension positive, at each fiber.
6. Rate the gating inner-fiber combined stress against the allowable
   with stress_verdict(sigma, allowable) and read the ratio, verdict
   and margin from the returned dict.

## Worked example

Torque-link / frame-corner style curved member, 7075-T6-like aluminum
alloy with the design allowable tension set at 500 MPa for the check.
Rectangular radial section: r_i = 60 mm, r_o = 100 mm, depth
h = 40 mm, width b = 40 mm, area A = 1600 mm^2, centroidal radius
r_c = 80 mm, axial tension P = 25 kN. Real module outputs:

- neutral_axis_radius_rect(60.0, 100.0) = 78.30461 mm: the neutral
  axis sits inward of the centroid by
  eccentricity(80.0, 78.30461) = 1.69539 mm, about 4.2 percent of the
  depth toward the center of curvature. The closed form agrees with a
  400000-bin quadrature of A / integral(dA / rho) to relative
  difference 1.45e-13.
- Circular sections: neutral_axis_radius_circular_tube(80.0, 10.0,
  20.0) = 78.41610 mm (e = 1.58390 mm), and the solid round
  neutral_axis_radius_circular_tube(80.0, 0.0, 20.0) = 78.72983 mm
  (e = 1.27017 mm).
- Load case 1, M = 1.2e6 N mm (moderate in-service moment):
  inner fiber curved_beam_stress = 134.95848 MPa tension, outer fiber
  = -95.97509 MPa compression. The straight Euler-Bernoulli baseline
  of the same section is straight_beam_stress_rect = 112.5 MPa: the
  curved-beam correction amplifies the inner fiber by 1.19963 and runs
  the outer fiber at 0.85311 of the straight reading, the classic
  Winkler signature. Adding the axial tension P / A = 15.625 MPa:
  combined inner = 150.58348 MPa, combined outer = -80.35009 MPa.
  Against the 500 MPa allowable: ratio 0.30117, verdict pass, margin
  349.41652 MPa.
- Load case 2, limit moment M = 4.0e6 N mm with the same axial load:
  inner fiber = 449.86161 MPa, combined inner = 465.48661 MPa, ratio
  0.93097, verdict pass, margin 34.51339 MPa.
- Load case 3, ultimate moment M = 4.5e6 N mm: inner fiber =
  506.09432 MPa, combined inner = 521.71932 MPa, ratio 1.04344,
  verdict fail, margin -21.71932 MPa. Read as straight
  (6 M / (A h) = 421.875 MPa combined) the same member would still
  pass, which is the point of the correction: the curved-beam
  inner-fiber stress is the gating number at a frame corner or torque
  link arc.

## Pitfalls

- Reading a curved member with the straight law: the straight
  Euler-Bernoulli baseline of the worked example passes load case 3
  while the Winkler inner-fiber stress fails it; always rate the
  curved inner fiber, never 6 M / (A h), for a frame segment or arc.
- Signing the moment backwards: a positive moment opens the arc, so
  the inner fiber goes into tension and the outer fiber into
  compression; a negative moment reverses both. Flipping the sign
  convention swaps which fiber the verdict gates on.
- Taking the neutral axis at the centroid: e is the whole point of the
  correction; setting r_n = r_c would divide by zero in the Winkler
  stress and erase the hyperbolic gradient.
- Using the tube closed form on an invalid section: the annulus outer
  radius must stay below r_c (the section must clear the center of
  curvature) and a_i must be 0 or positive, or the function raises
  ValueError; feeding a_o >= r_c silently corrupts the square root
  instead if you bypass the guard.
- Trusting a raw 2-D grid quadrature of A / integral(dA / rho) for a
  circular section: an independent cell-centered grid over the section
  annulus reproduces the circular closed forms only to about one
  percent (grid and measure sensitive; the prep quadrature note of
  1e-6 class was not independently reproducible in Euclidean section
  measure). Use the closed forms, which are the engineering standard
  for circular-section curved beams and match the spec anchors to
  1e-5. The rectangular closed form, by contrast, is exact to the
  1e-13 class against quadrature.
- Mixing units: radii, area and moment must share one consistent
  system. In the worked example mm and MPa are used with moment in
  N mm and area in mm^2, so N mm / mm^3 = N / mm^2 = MPa; mixing N m
  with mm^2 sections silently scales every stress by 1000.

## Verification

- The contract test asserts the real module outputs above inside the
  spec tolerances: geometry anchors to 1e-5, fiber stresses to 1e-4,
  ratios and margins to 1e-3, and the straight baseline 112.5 MPa
  exactly.
- Identities verified: the rectangular closed form equals a
  400000-bin quadrature of A / integral(dA / rho) to 1.45e-13 (better
  than the 1e-9 class), the neutral-axis radius is independent of the
  out-of-plane width, r_n lies strictly between r_i and r_c, the
  eccentricity is positive for physical sections, the inner-fiber
  magnitude exceeds the outer-fiber magnitude for the same moment, the
  curved-beam amplification grows with the depth-to-radius ratio
  (1.04333, 1.09046, 1.14220, 1.19963 for h = 10, 20, 30, 40 mm at
  r_c = 80 mm), a_i = 0.0 in the tube function reproduces the
  solid-section closed form, a negative moment flips both fiber signs
  exactly, zero moment gives zero stress, and the verdict flips from
  pass to fail exactly at ratio 1.0.
- ValueError rejection: non-physical inputs raise ValueError in every
  function (non-positive radii, r_o <= r_i, negative or equal annulus
  radii, a_o >= r_c, non-positive area, eccentricity, neutral-axis
  radius, fiber radius, depth or allowable).
- Determinism: no random numbers anywhere; identical floats run to
  run. Run the contract test offline: python3
  scripts/test_curved_beam_analysis.py (35 tests, deterministic, well
  under one second).

## Related leaves

- skills/structures/fem/beam-frame-analysis: the straight-member FEM
  sibling; its Euler-Bernoulli element and the cantilever closed forms
  carry no curvature radius, no neutral-axis shift and no fiber-stress
  law, so a curved frame corner belongs here.
- skills/structures/fem/beam-vibration: straight continuous-member
  natural frequencies only, no curved stress state.
- skills/structures/fem/lug-joint-analysis: pin and lug bearing and
  tearout checks of the clevis fitting, not the curved-member bending
  stress of the arc that feeds it.
- skills/structures/composites/peel-stress-bonded-joints: an adhesive
  Winkler-foundation beam model of a flat single-lap bondline; it
  takes no curvature radius and no fiber stress, so it is a different
  Winkler model, not a competitor for curved members.

## Contract test

Run from the repository root:

    python3 skills/structures/fem/curved-beam-analysis/scripts/test_curved_beam_analysis.py

The stdlib unittest contract test runs fully offline and covers the
worked-example anchors of all three load cases (steps 1 to 6 of the
workflow), the circular tube and solid-round closed forms, the
rectangular quadrature identity to the 1e-9 class, the honest
cell-centered grid quadrature agreement of the circular closed form to
about one percent, the width-independence and neutral-axis-position
identities, the amplification ladder, the fiber stress sign and zero
behaviors, the axial contribution identities, the exact verdict
boundary at ratio 1.0 with the fixed pass and fail strings, and the
ValueError rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR-25 is public-domain US
  government work (17 U.S.C. 105) but standards-map.yaml marks it
  gated: false and reference-only: true, so only the summary
  paraphrase above is used, never standard text. The design allowable
  of the worked example is a paraphrased 7075-T6-like value, not a
  quoted table.
- The Winkler curved-beam relations and the closed forms are standard
  engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_curved_beam_analysis.py

The test covers the worked-example geometry and all three load case
stresses inside the spec bounds, the circular tube and solid-round
neutral-axis closed forms, the rectangular quadrature identity, the
honest tube-grid quadrature agreement, the width independence and
neutral-axis-between-r_i-and-r_c identities, the amplification growth
with h / r_c, the inner-fiber-over-outer-fiber magnitude law, exact
sign flip for a negative moment, zero stress at zero moment, the
axial-tension and P / A identities, the verdict flip exactly at ratio
1.0 with the fixed pass and fail strings and the exact dict keys, and
ValueError rejection of every non-physical input, all deterministic
and offline in under a second.

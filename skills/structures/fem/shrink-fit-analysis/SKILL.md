---
name: shrink-fit-analysis
description: "Use when you must compute the shrink-fit contact pressure and stresses of a two-cylinder radial-interference assembly: convert the total radial interference into the interface contact pressure from the Lame thick-cylinder radial compliance of both members, recover the bore radial and hoop stresses at the critical bore of each member, form the von-Mises yield margin of each bore against its yield strength, and close with the governing member and the maximum allowable radial interference before that bore yields. Produces the interference-fit contact pressure, the bore radial and hoop stresses of both members, the von-Mises yield margins of both bores, the governing member and the allowable radial interference that gate the shrink-fit design check. Trigger: shrink fit, press fit, interference fit, contact pressure, radial interference, Lame solution, thick cylinder, bore hoop stress, yield margin."
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
  tags: [shrink-fit-analysis, interference-fit-contact-pressure, lame-thick-cylinder-stress, bore-hoop-stress, von-mises-yield-margin, allowable-interference]
  version: 0.1.0
  author: AeroSkills
---

# Shrink Fit Analysis (structures/fem/shrink-fit-analysis)

Compute the closed-form stress state of a bushing, sleeve or bearing race
pressed or shrunk into a lug, hub or race: the two-cylinder Lame radial
compliance of the interference fit converts the total radial interference
delta into the interface contact pressure p, the bore radial and hoop
stresses of both members follow from the exact Lame extreme-fiber values,
and the von-Mises yield margin of each bore closes with the governing
member and the maximum allowable radial interference before that bore
yields. Deterministic closed-form core only in pure Python, stdlib only:
no FEA, no iteration, no plasticity. This leaf owns the fitted-joint
pre-stress territory that sibling leaves fence off: it does NOT do
deformation-driven fastener hole-fill and head-geometry checks
(solid-rivet-installation-quality, whose hole-fill quick reference
declares interference fits out of scope), finite element contact
enforcement machinery (contact-analysis, which computes contact mechanics
quantities, not the closed-form stress solution, and lists bushing-sleeve
interfaces only as finite element application examples), pin-loaded lug
proportioning under an axial load with no pre-stress from a pressed-in
bushing (lug-joint-analysis), thin-shell external-pressure stability
(cylindrical-shell-buckling) and membrane-theory pressure domes
(pressure-bulkhead). It pairs with structures/fem/lug-joint-analysis for
the load path that hosts the fitted bushing and with
structures/fem/contact-analysis for the finite element side of the same
interfaces.

## Domain quick reference

- Interface contact pressure from radial interference (the two-cylinder
  Lame form, a paraphrase of the standard Shigley/Juvinall class press
  fit relation): p = delta / [ (r_c / E_i) * ((r_c**2 + r_i**2) /
  (r_c**2 - r_i**2) - nu_i) + (r_c / E_o) * ((r_o**2 + r_c**2) /
  (r_o**2 - r_c**2) + nu_o) ], where r_i is the inner member bore, r_c
  the interface radius and r_o the outer member outer radius, delta the
  total RADIAL interference, E and nu the member moduli and Poisson
  ratios.
- Displacement forms behind the formula: the inner member (bore r_i,
  interface radius r_c) carries only the external pressure p, so its
  inward interface displacement is u_inner = -(p r_c / E_i) *
  ((r_c**2 + r_i**2) / (r_c**2 - r_i**2) - nu_i); the outer member
  (bore r_c, outer radius r_o) carries only the internal pressure p, so
  its outward bore displacement is u_outer = +(p r_c / E_o) *
  ((r_o**2 + r_c**2) / (r_o**2 - r_c**2) + nu_o). Compatibility
  delta = u_outer - u_inner gives the formula above.
- Sign convention: the COMPRESSED inner member carries the -nu_i term
  and the EXPANDED outer member the +nu_o term (the two nu terms cancel
  only for identical materials). Swapping the two signs is the common
  transcription error and shifts p by several percent (17 percent
  over-read on the worked example).
- Critical bore planes (exact Lame extreme-fiber values): the inner
  member bore (r = r_i) is a free surface, sigma_r = 0.0 there, and its
  hoop is the most compressive value in the assembly, sigma_theta =
  -2.0 * p * r_c**2 / (r_c**2 - r_i**2). The outer member bore
  (r = r_c) carries sigma_r = -p and the maximum tensile hoop
  sigma_theta = p * (r_o**2 + r_c**2) / (r_o**2 - r_c**2). The inner
  member interface hoop at r_c, -p (r_c**2 + r_i**2) / (r_c**2 -
  r_i**2), is smaller in magnitude than its bore hoop and is not the
  critical location.
- Von-Mises yield margin (plane stress, sigma_z = 0, distortion
  energy): sigma_vm = sqrt(sigma_theta**2 - sigma_theta * sigma_r +
  sigma_r**2) and margin = sy - sigma_vm, positive below yield.
- Governing member and allowable interference: every stress is linear
  in p (elastic, small strain), so the assembly scales linearly to the
  yield point of the governing (least-margin) bore:
  governing_contact_pressure = p * sy_gov / sigma_vm_gov and
  allowable_interference = delta * sy_gov / sigma_vm_gov.
- Units: all radii share one length unit, all stresses one stress unit
  and all moduli and pressures the same stress unit. In the worked
  example: mm for radii and delta, MPa for stress, modulus and pressure.
- FAR-25 and CS-25 frame the airframe bushing-in-lug context; the
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.

## Workflow

1. Fix the assembly geometry, materials and interference: inner bore
   r_i, interface radius r_c and outer radius r_o in one length unit,
   the total radial interference delta > 0, the member moduli E_i and
   E_o, Poisson ratios nu_i and nu_o in (0, 0.5) and yield strengths
   sy_i and sy_o in one stress unit.
2. Convert the radial interference into the interface contact pressure:
   run contact_pressure (the Lame radial-compliance pass) on delta,
   r_i, r_c, r_o, E_i, nu_i, E_o, nu_o to get p. Cross-check the sign
   convention by re-deriving both compliance terms by hand.
3. Recover the critical bore stress state: run stress_distributions on
   p, r_i, r_c, r_o (the bore-stress pass) for the inner member bore
   radial and hoop stresses (free surface at sigma_r = 0.0, most
   compressive hoop) and the outer member bore stresses (sigma_r = -p,
   maximum tensile hoop).
4. Form the von-Mises yield margins of both bores: run
   von_mises_margin (the yield-margin pass) on each bore plane stress
   state, with sy_i for the inner member and sy_o for the outer member,
   and read sigma_vm and margin = sy - sigma_vm.
5. Close with the governing member and the allowable radial
   interference: run allowable_interference (the governing-member pass)
   on the full input set including sy_i and sy_o, and read
   governing_member ("inner" or "outer"), governing_contact_pressure
   and allowable_interference, the radial interference that takes the
   governing bore exactly to yield.
6. Verify the closed-form identities: confirm the compatibility
   identity delta = u_outer - u_inner at the returned contact pressure
   from the displacement forms above, confirm p scales linearly with
   delta at fixed geometry and materials, and confirm that at delta
   equal to the returned allowable interference the governing bore
   margin returns to zero.
7. Confirm the deterministic checks: rerun the offline contract test
   scripts/test_shrink_fit_analysis.py and confirm all 33 methods pass
   (deterministic, stdlib math only, no RNG).

## Worked example

Steel bushing pressed into an aluminum lug (the corpus geometry): inner
member steel bushing E_i = 207000 MPa, nu_i = 0.30, Sy_i = 620 MPa with
bore r_i = 6 mm and interface (outer) radius r_c = 8 mm; outer member
aluminum lug E_o = 71000 MPa, nu_o = 0.33, Sy_o = 276 MPa with bore
r_c = 8 mm and outer radius r_o = 16 mm; total radial interference
delta = 0.02 mm (real module outputs):

- contact_pressure(0.02, 6.0, 8.0, 16.0, 207000.0, 0.30, 71000.0,
  0.33) = 56.91381 MPa, inside the 50 to 150 MPa sanity band for a
  0.02 mm interference over 6 to 16 mm radii in steel on aluminum. The
  swapped-sign variant of the same formula returns about 66.6 MPa, a 17
  percent over-read.
- stress_distributions(56.91381, 6.0, 8.0, 16.0): inner member bore
  sigma_r = 0.00000 MPa and sigma_theta = -260.17743 MPa (compression,
  the largest hoop magnitude in the assembly); outer member bore
  sigma_r = -56.91381 MPa and sigma_theta = +94.85635 MPa (tension).
  The interface hoop of the bushing at r_c is -203.26361 MPa, smaller
  in magnitude than its bore hoop.
- von_mises_margin(620.0, 0.0, -260.17743): sigma_vm = 260.17743 MPa,
  margin = 359.82257 MPa (steel bushing bore, comfortable).
- von_mises_margin(276.0, -56.91381, 94.85635): sigma_vm =
  132.79889 MPa, margin = 143.20111 MPa (aluminum lug bore). The lug
  bore is the governing location: the soft aluminum sees only
  2.3333 p von-Mises, but its yield strength is less than half the
  steel's.
- allowable_interference(0.02, 6.0, 8.0, 16.0, 207000.0, 0.30,
  71000.0, 0.33, 620.0, 276.0): governing_member "outer",
  governing_contact_pressure = 118.28571 MPa, allowable_interference =
  0.04157 mm. The 0.02 mm design interference holds a 1.07 margin ratio
  on the lug (276 / 132.79889) and the fit can take 0.04157 mm before
  the aluminum lug bore yields.
- Compatibility identity at the returned p: u_outer(r_c) = +0.01280 mm
  and u_inner(r_c) = -0.00720 mm, so u_outer - u_inner = 0.02000 mm,
  exactly the input delta (roundoff 1e-15 class).
- Identical-members check (E_i = E_o, nu_i = nu_o, sy_i = sy_o): the
  governing member flips to "inner", because the inner bore hoop factor
  2 r_c**2 / (r_c**2 - r_i**2) = 4.5714 exceeds the outer bore von-Mises
  factor sqrt(1.6667**2 + 1.6667 + 1) = 2.3333.

## Verification

- Confirm contact_pressure(0.02, 6.0, 8.0, 16.0, 207000.0, 0.30,
  71000.0, 0.33) returns 56.91381 MPa within 1e-4, and doubling delta
  doubles p exactly (linear scaling).
- Confirm stress_distributions returns the four documented bore-stress
  values within 1e-4 with sigma_r continuous across the interface at
  -p, inner bore sigma_r = 0.0 exactly (free surface) and the inner
  bore hoop as the largest hoop magnitude in the assembly.
- Confirm the von-Mises margins 359.82257 MPa (inner) and
  143.20111 MPa (outer) within 1e-3 and the uniaxial identity
  sigma_vm = |sigma| at sigma_r = 0.
- Confirm allowable_interference returns governing_member "outer",
  governing_contact_pressure = 118.28571 MPa and
  allowable_interference = 0.04157 mm, and flips to "inner" for
  identical members.
- Confirm the compatibility identity delta = u_outer - u_inner
  reproduces the input delta within 1e-12 at the returned p, and that
  at delta equal to the returned allowable interference the governing
  bore margin returns to 0 within 1e-9.
- Confirm ValueError rejection of every non-physical input class: delta
  zero or negative, r_i zero, r_c <= r_i, r_o <= r_c, zero or negative
  moduli, Poisson ratios at 0, 0.5 and above, and non-positive yield
  strengths, across every function.
- Run the deterministic contract test offline: python3
  scripts/test_shrink_fit_analysis.py (33 tests, sub-second).

## Related leaves

- structures/fem/lug-joint-analysis: the pin-loaded fitting that hosts
  the pressed-in bushing, proportioned under an axial load with no
  pre-stress from the fit.
- structures/fem/contact-analysis: finite element contact enforcement
  for the same bushing-sleeve interfaces, where this leaf's closed-form
  stress solution is the analytical cross-check.
- structures/fem/curved-beam-analysis: curved member stress analysis
  for the lug bodies that carry fitted bushings.
- structures/fem/pressure-bulkhead: membrane-theory pressure domes,
  outside this leaf's thick-wall radial-interference model.
- structures/fem/cylindrical-shell-buckling: thin-shell external
  pressure stability of the same cylinders, outside this leaf's elastic
  stress state.

## Pitfalls

- Swapping the nu signs: the compressed inner member takes -nu_i and
  the expanded outer member +nu_o; transposing them over-reads the
  contact pressure by 17 percent on the worked example (66.6 MPa
  against 56.9 MPa).
- Reading the interface hoop as the inner member critical stress: the
  bushing interface hoop at r_c (-203.26 MPa) is smaller in magnitude
  than its bore hoop (-260.18 MPa); the bore is the critical plane.
- Expecting the soft member to govern by strength alone: the aluminum
  lug governs here (margin 143.2 MPa against 359.8 MPa) even though its
  von-Mises factor 2.3333 p is half the steel bore's 4.5714 p, because
  its yield strength is less than half the steel's. With identical
  members the inner bore governs instead.
- Comparing stresses across members without a shared unit scheme: all
  radii share one length unit and all stresses, moduli and pressures
  one stress unit; mixing mm with m or MPa with Pa silently shifts the
  contact pressure.
- Treating the fit as a thin-shell problem: the Lame thick-cylinder
  radial compliance needs r_c**2 terms in both members, not the thin
  shell hoop-only membrane result.
- Using exact float equality on computed sums: assert module outputs
  with a tolerance (the contract test uses assertAlmostEqual with an
  explicit delta or math.isclose throughout).

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline, sub
second):

    python3 scripts/test_shrink_fit_analysis.py

The test covers the worked-example anchors (contact pressure
56.91381 MPa within 1e-4 and the 50 to 150 MPa sanity band, bore hoop
-260.17743 MPa and +94.85635 MPa within 1e-4), the sign-convention
guard against the swapped-nu variant, linear p-delta scaling, the exact
bore-stress dict keys and the free-surface sigma_r = 0.0, the von-Mises
yield margins of both bores within 1e-3 with the uniaxial and
equibiaxial identities, the governing-member pass results (outer on the
worked geometry within 1e-3 / 1e-5, inner for identical members), the
yield-crossing identity at the allowable interference, the
compatibility identity delta = u_outer - u_inner within 1e-12,
determinism, and ValueError rejection of every non-physical input class
across all four functions.

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 frame the
  airframe bushing, bearing and lug fit context (standards-map.yaml
  ids, both reference-only, the fem-pack convention used by
  lug-joint-analysis); the Lame relations above are standard
  engineering methodology (Shigley/Juvinall class press-fit relations),
  summary-only, never verbatim standard text.
- compliance: STANDARDS-REF, gated: false.

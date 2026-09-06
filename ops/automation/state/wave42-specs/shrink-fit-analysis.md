# Wave-42 leaf spec: shrink-fit-analysis (structures, fem pack)

- Path: skills/structures/fem/shrink-fit-analysis/
- Pack: fem (verified present at prep with beam-frame-analysis,
  beam-vibration, buckling-analysis, calculix-linear,
  calculix-nonlinear, contact-analysis, cylindrical-shell-buckling,
  diagonal-tension-field-webs, lug-joint-analysis, modal-analysis,
  plate-buckling, pressure-bulkhead, torsion-shear-flow, truss-analysis).
  Closest siblings are the ones this leaf fences against:
  solid-rivet-installation-quality (manufacturing-quality/assembly;
  its frontmatter claim covers hole-fill clearance checks of
  deformation-driven fasteners, and its own body draws the fence with
  the hole-fill quick reference "Interference fits are out of scope
  for this check", rejecting a hole at or below the shank diameter
  with ValueError, so the fitted-joint pre-stress territory is
  declared unclaimed there), contact-analysis (structures/fem;
  finite element contact machinery whose body states it "computes
  the contact mechanics quantities, not the global solve", with
  bushing-sleeve interfaces listed only as finite element application
  examples, never as a closed-form stress solution), lug-joint-analysis
  (structures/fem; its frontmatter claim is a metallic pin-loaded
  fitting under an axial load with per-mode margins against material
  allowables: the pin transfers load with no pre-stress from a
  pressed-in bushing), cylindrical-shell-buckling (thin-shell
  external-pressure stability, not thick-wall radial interference) and
  pressure-bulkhead (thin membrane domes, membrane theory only).
  Whole-tree greps at prep: "shrink.?fit", "interference.?fit",
  "thick.?cylind" and "Lam[eé]" hit exactly two SKILL.md lines, both
  the solid-rivet-installation-quality exclusion quoted above;
  "bushing | press.?fit" hits only contact-analysis in a finite
  element context. GENUINE STRUCTURES gap (fresh probe): no leaf
  computes the two-cylinder Lame radial-interference stress state; the
  shrink-fit contact pressure, bore hoop stresses and yield margins of
  a bushing pressed into a lug are unowned.
- Standards ids: far-25 and cs-25 (reference-only; both resolve in
  standards-map.yaml with reference-only: true). Ledger Standard:
  far-25.
- Family: structures

## Claim

Compute the two-cylinder Lame stress state of a radial-interference
shrink or press fit (bushing in lug, bearing race, shaft-hub): convert
the total radial interference delta into the interface contact pressure
p from the Lame thick-cylinder radial compliance of both members, the
inner member compressed under the external pressure p at the interface
radius and the outer member expanded under the internal pressure p at
its bore, recover the critical radial and hoop stresses at the inner
bore of each member (the compressed inner member's bore hoop is
negative, the expanded outer member's bore hoop positive), form the
von-Mises yield margin of each bore against its yield strength, and
close with the governing member and the maximum allowable radial
interference before that bore yields, all in pure closed form.
Produces the interference-fit contact pressure, the bore radial and
hoop stresses of both members, the von-Mises yield margins of both
bores, the governing member and the allowable radial interference that
gate the shrink-fit design check. Does NOT do: hole-fill and
head-geometry checks of deformation-driven fasteners
(solid-rivet-installation-quality); finite element contact enforcement
machinery (contact-analysis); pin-loaded lug proportioning under an
axial load (lug-joint-analysis); thin-shell external-pressure
stability (cylindrical-shell-buckling); membrane-theory pressure domes
(pressure-bulkhead). Deterministic closed-form core only; no FEA, no
iteration, no plasticity.

## Model (implement exactly)

Functions (pure stdlib, math only):

- contact_pressure(delta, r_i, r_c, r_o, E_i, nu_i, E_o, nu_o) ->
  float: the interface contact pressure
  p = delta / [ (r_c / E_i) * ((r_c**2 + r_i**2) / (r_c**2 - r_i**2) -
  nu_i) + (r_c / E_o) * ((r_o**2 + r_c**2) / (r_o**2 - r_c**2) +
  nu_o) ], the exact two-cylinder Lame form (paraphrase of the
  standard Shigley/Juvinall class press-fit relation). Derivation
  conventions, documented in the docstring and the SKILL body: the
  inner member (bore r_i, interface radius r_c) carries only the
  external pressure p, so its interface hoop is -p (r_c**2 + r_i**2) /
  (r_c**2 - r_i**2) and its inward interface displacement is u_inner =
  -(p r_c / E_i) ((r_c**2 + r_i**2) / (r_c**2 - r_i**2) - nu_i); the
  outer member (bore r_c, outer radius r_o) carries only the internal
  pressure p, so its bore hoop is +p (r_o**2 + r_c**2) / (r_o**2 -
  r_c**2) and its outward bore displacement is u_outer = +(p r_c / E_o)
  ((r_o**2 + r_c**2) / (r_o**2 - r_c**2) + nu_o). Compatibility
  delta = u_outer - u_inner gives the formula above. Sign convention
  note: the COMPRESSED inner member carries the -nu_i term and the
  EXPANDED outer member the +nu_o term (the two nu terms cancel only
  for identical materials; a swap of the two signs is the common
  transcription error and shifts p by several percent). delta is the
  total RADIAL interference, delta > 0. ValueError if delta <= 0,
  r_i <= 0, r_c <= r_i, r_o <= r_c, E_i <= 0, E_o <= 0, or any Poisson
  ratio outside (0, 0.5).
- stress_distributions(p, r_i, r_c, r_o) -> dict with exactly the keys
  {"inner_bore_sigma_r", "inner_bore_sigma_theta",
  "outer_bore_sigma_r", "outer_bore_sigma_theta"}: the critical bore
  planes of the two members at the interface pressure p. Inner member
  bore (r = r_i) is a free surface, so sigma_r = 0.0 there, and the
  hoop is the most compressive value in the assembly,
  sigma_theta = -2.0 * p * r_c**2 / (r_c**2 - r_i**2). Outer member
  bore (r = r_c) carries sigma_r = -p and the maximum tensile hoop
  sigma_theta = p * (r_o**2 + r_c**2) / (r_o**2 - r_c**2). These are
  the exact Lame extreme-fiber values (paraphrase of the classical
  thick-cylinder result); the interface hoop of the inner member,
  -p (r_c**2 + r_i**2) / (r_c**2 - r_i**2), is smaller in magnitude
  than its bore hoop and is not the critical location. ValueError if
  p <= 0 or the radii violate 0 < r_i < r_c < r_o.
- von_mises_margin(sy, sigma_r, sigma_theta) -> dict with exactly the
  keys {"sigma_vm", "margin"}: sigma_vm =
  sqrt(sigma_theta**2 - sigma_theta * sigma_r + sigma_r**2), the plane
  stress (sigma_z = 0) distortion-energy equivalent of the bore plane
  stress state, and margin = sy - sigma_vm, positive below yield.
  ValueError if sy <= 0.
- allowable_interference(delta, r_i, r_c, r_o, E_i, nu_i, E_o, nu_o,
  sy_i, sy_o) -> dict with exactly the keys {"governing_member",
  "governing_contact_pressure", "allowable_interference"}: evaluates
  contact_pressure and stress_distributions, forms von_mises_margin at
  both bores with sy_i (inner member) and sy_o (outer member), and,
  because every stress is linear in p (elastic, small strain), scales
  linearly to the yield point of the governing (least-margin) bore:
  governing_contact_pressure = p * sy_gov / sigma_vm_gov and
  allowable_interference = delta * sy_gov / sigma_vm_gov, where
  governing_member is the string "inner" or "outer". ValueErrors as in
  contact_pressure, plus sy_i <= 0 or sy_o <= 0.

All radii share one length unit, all stresses one stress unit and all
moduli and pressures the same stress unit: in the worked example mm and
MPa, E in MPa and delta in mm. No magic numbers; no module constants
needed beyond the closed forms themselves.

Identity to test: p scales linearly with delta at fixed geometry and
materials; the compatibility identity delta = u_outer - u_inner holds
with u_outer and u_inner evaluated from the closed forms above at the
returned p; sigma_r is continuous across the interface at -p on both
members; at the worked geometry with identical members (E_i = E_o,
nu_i = nu_o, sy_i = sy_o) the governing member flips from outer to
inner, because the inner bore hoop factor 2 r_c**2 / (r_c**2 - r_i**2)
= 4.5714 exceeds the outer bore von-Mises factor
sqrt(1.6667**2 + 1.6667 + 1) = 2.3333; at delta = allowable_interference
the governing bore margin returns exactly 0.

## Worked example

Steel bushing pressed into an aluminum lug (the corpus geometry):
inner member steel bushing E_i = 207000 MPa, nu_i = 0.30, Sy_i =
620 MPa with bore r_i = 6 mm and interface (outer) radius r_c = 8 mm;
outer member aluminum lug E_o = 71000 MPa, nu_o = 0.33, Sy_o =
276 MPa with bore r_c = 8 mm and outer radius r_o = 16 mm; total
radial interference delta = 0.02 mm.

Geometry (run the module and take the real outputs as assert targets;
the values below are prep-verified, computed by running the prep anchor
script /tmp/w42spec/anchor_shrink_fit_analysis.py with stdlib math
only, exit code 0):

- contact_pressure(0.02, 6.0, 8.0, 16.0, 207000.0, 0.30, 71000.0,
  0.33) = 56.91381 MPa, inside the 50 to 150 MPa sanity band for a
  0.02 mm interference over 6 to 16 mm radii in steel on aluminum.
  Note the sign convention matters: the derived compliance uses
  -nu_i on the compressed bushing and +nu_o on the expanded lug; the
  swapped-sign variant of the same formula returns about 66.6 MPa, a
  17 percent over-read, which is why the derivation is pinned above.
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
  0.04157 mm. The 0.02 mm design interference holds a 1.07 margin
  ratio on the lug (276 / 132.79889) and the fit can take 0.04157 mm
  before the aluminum lug bore yields.
- Compatibility identity at the returned p: u_outer(r_c) = +0.01280 mm
  and u_inner(r_c) = -0.00720 mm, so u_outer - u_inner = 0.02000 mm,
  exactly the input delta (roundoff 1e-15 class).

Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds from
/tmp/w42spec/anchor_shrink_fit_analysis.py.

## Validation list (contract test must include)

- contact_pressure(0.02, 6.0, 8.0, 16.0, 207000.0, 0.30, 71000.0,
  0.33) = 56.91381 within 1e-4; doubling delta doubles p exactly
  (linear scaling); ValueErrors at delta 0 and negative, r_i 0, r_c ==
  r_i, r_o == r_c, E 0 and negative, nu 0, 0.5 and 0.6.
- stress_distributions(56.913811912628034, 6.0, 8.0, 16.0):
  inner_bore_sigma_r = 0.0 exactly, inner_bore_sigma_theta =
  -260.17743 within 1e-4, outer_bore_sigma_r = -56.91381 within 1e-4,
  outer_bore_sigma_theta = 94.85635 within 1e-4; interface sigma_r
  continuity at -p; dict keys exactly as documented; ValueErrors at
  p 0 and negative and at degenerate radii.
- von_mises_margin(620.0, 0.0, -260.17743): sigma_vm 260.17743 and
  margin 359.82257 within 1e-3; von_mises_margin(276.0, -56.91381,
  94.85635): sigma_vm 132.79889 and margin 143.20111 within 1e-3;
  uniaxial identity sigma_vm == |sigma| when sigma_r = 0; ValueErrors
  at sy 0 and negative.
- allowable_interference(0.02, 6.0, 8.0, 16.0, 207000.0, 0.30,
  71000.0, 0.33, 620.0, 276.0): governing_member "outer",
  governing_contact_pressure = 118.28571 within 1e-3,
  allowable_interference = 0.04157 within 1e-5; identical-members call
  (sy_i = sy_o = 620.0, E and nu equal) returns governing_member
  "inner" (inner bore hoop factor 4.5714 versus outer von-Mises factor
  2.3333); at delta equal to the returned allowable_interference the
  governing margin is 0 within 1e-9 (yield-crossing identity);
  ValueErrors as in contact_pressure plus non-positive sy_i or sy_o.
- Closed-form identities: compatibility delta = u_outer - u_inner
  reproduces the input delta within 1e-12 at the returned p, using
  u_outer = +(p r_c / E_o) ((r_o**2 + r_c**2) / (r_o**2 - r_c**2) +
  nu_o) and u_inner = -(p r_c / E_i) ((r_c**2 + r_i**2) / (r_c**2 -
  r_i**2) - nu_i); p scales linearly with delta.
- Determinism; fixed strings "inner" and "outer"; fixed dict keys.

## Corpus fragment (eval/hit1-wave42-shrink-fit-analysis.yaml)

Query 1 (copy verbatim):
  "Compute the shrink-fit contact pressure and bore hoop stress when a steel sleeve is fit over an aluminum hub with 0.05 mm radial-interference, using the lame-contact-pressure thick-cylinder solution, and check the von-Mises yield margin at the inner bore."
  intent: "structures; two-cylinder Lame interference fit contact pressure and bore hoop stress with von-Mises yield margin"
  expected_skill: "structures/fem/shrink-fit-analysis"
Query 2 (copy verbatim):
  "Size the interference fit of a steel bushing into an aluminum lug: contact pressure from the radial-interference, shrink-fit-bore-hoop-stress at the bushing bore, and the maximum allowable interference before the lug bore yields."
  intent: "structures; bushing-in-lug interference fit sizing, contact pressure and allowable radial interference before the lug bore yields"
  expected_skill: "structures/fem/shrink-fit-analysis"
Task ids: w42-shrink-fit-analysis-1 and -2. Queries steer around the
manufacturing-quality leaf that excludes interference fits by contract
and around the finite element contact leaf by leading with
"shrink-fit", "lame-contact-pressure" and "radial-interference", which
appear in no sibling claim.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the shrink-fit contact
pressure and stresses of a two-cylinder radial-interference assembly:"
and include the outputs in the Claim (interference-fit contact
pressure, bore radial and hoop stresses, von-Mises yield margins,
governing member, allowable radial interference). First tag:
shrink-fit-analysis. Additional tags ONLY:
interference-fit-contact-pressure, lame-thick-cylinder-stress,
bore-hoop-stress, von-mises-yield-margin, allowable-interference.
NEVER single generic words (fit, interference, stress, cylinder,
bushing, lug, pressure, margin, bore, hoop). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): rivet, driven head, installation
quality (solid-rivet-installation-quality); penalty method, lagrange,
FEM contact stiffness (contact-analysis); lug bearing stress, net
tension, tearout (lug-joint-analysis); cylindrical shell buckling
(cylindrical-shell-buckling, plate-buckling). Keep every one of those
out of the description, the tags and the Claim outputs: the exclusion
fences in the Pack paragraph above are the only place sibling paths
appear.

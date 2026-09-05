---
name: multiaxial-yield-criteria
description: "Use when you must compute the multiaxial yield margin of an isotropic metal part: evaluate the von Mises equivalent stress in plane stress sqrt(sx^2 - sx*sy + sy^2 + 3*txy^2) and in full 3D, resolve the plane-stress principal stresses from the Mohr circle, compute the Tresca equivalent stress as the maximum principal stress difference including the zero out-of-plane principal, compute the yield margin yield/equivalent - 1, run the von Mises combined bending-plus-torsion margin for a shaft section, and check whether a biaxial tension point falls inside the von Mises yield envelope. Produces the von Mises and Tresca equivalent stresses, the principal stresses, the yield margins and the envelope verdict that gate metallic part hand checks. Trigger: multiaxial-yield-criteria, von-mises-equivalent-stress, tresca-margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
gated: false
domain: structures
pack: materials
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: materials
  tags: [multiaxial-yield-criteria, von-mises-equivalent-stress, tresca-margin]
  version: 0.1.0
  author: AeroSkills
---

# Multiaxial Yield Criteria (structures/materials/multiaxial-yield-criteria)

Use when the task is a hand yield check of an isotropic metal part
under a multiaxial stress state: von Mises and Tresca equivalent
stresses, Mohr-circle principal stresses, yield margins, and the von
Mises envelope verdict for the biaxial plane. It pairs with the
materials pack siblings around it: ramberg-osgood builds the uniaxial
stress-strain curve whose yield point feeds these criteria, and
mmpsd-allowables supplies the statistically based yield strength
design value that Sy comes from. Anisotropic composite ply strength
work (composites pack) and finite-element equivalent stress
post-processing (fem pack) are different tasks; this leaf evaluates an
isotropic metal stress state by hand with the classical criteria.

## Domain quick reference

- von Mises equivalent stress in plane stress (sx, sy, txy):
  vm = sqrt(sx**2 - sx*sy + sy**2 + 3*txy**2). Uniaxial tension s
  reduces it to |s|; pure shear tau reduces it to sqrt(3)*tau.
- von Mises equivalent stress in full 3D (sx, sy, sz, txy, tyz, tzx):
  vm = sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2) +
  3*(txy**2 + tyz**2 + tzx**2)).
- Mohr circle plane-stress principals: center (sx+sy)/2, radius
  sqrt(((sx-sy)/2)**2 + txy**2), so sigma_1 >= sigma_2 with
  sigma_1,2 = (sx+sy)/2 +/- sqrt(((sx-sy)/2)**2 + txy**2).
- Tresca equivalent stress: the maximum principal stress difference.
  In plane stress the out-of-plane principal is zero, so tresca =
  max(sigma_1 - sigma_2, sigma_1, -sigma_2): uniaxial tension gives
  sigma, pure shear gives 2*tau, and the Tresca to von Mises ratio for
  pure shear is 2/sqrt(3) = 1.1547.
- Yield margin: margin = Sy/equivalent - 1, positive below yield, zero
  at yield, negative past yield (Sy = tensile yield strength).
- Shaft under combined bending sigma_b and torsion tau: von Mises
  equivalent sqrt(sigma_b**2 + 3*tau**2), the classical hand form.
- von Mises yield envelope in the biaxial (sx, sy) plane:
  sx**2 - sx*sy + sy**2 <= Sy**2; the boundary counts as within. The
  pure shear edge of the envelope sits at tau = Sy/sqrt(3).
- For the same plane-stress state the Tresca equivalent never falls
  below the von Mises equivalent; the ratio reaches 2/sqrt(3) in pure
  shear.

## Workflow

1. Collect the plane-stress state (sigma_x, sigma_y, tau_xy) and the
   tensile yield strength Sy in one consistent unit (MPa or Pa).
2. Compute the von Mises equivalent stress in plane stress with
   von_mises_plane_stress, or in full 3D with von_mises_3d when
   sigma_z and the out-of-plane shears are present.
3. Resolve the plane-stress principal stresses from the Mohr circle
   with plane_stress_principals (sigma_1 >= sigma_2).
4. Compute the Tresca equivalent stress with tresca_plane_stress, the
   maximum principal stress difference including the zero
   out-of-plane principal; use tresca_equivalent(sigma_1, sigma_3)
   when the ordered extremes are known directly.
5. Form the yield margins with yield_margin on the von Mises and on
   the Tresca equivalent stress; the governing (lower) margin decides
   the hand check.
6. Run the von Mises combined bending-plus-torsion margin for a shaft
   section with combined_bending_torsion_margin.
7. Issue the von Mises yield envelope verdict for the biaxial point
   with is_within_von_mises_envelope.
8. Confirm every computed number with the contract test
   scripts/test_multiaxial_yield_criteria.py.

## Worked example

Plane stress sx = 200 MPa, sy = -50 MPa, txy = 60 MPa, Sy = 400 MPa:

- von_mises_plane_stress = 251.594913 MPa.
- plane_stress_principals = (213.654246, -63.654246) MPa, sigma_1 at
  +69.1 deg by the Mohr circle geometry.
- tresca_plane_stress = 277.308492 MPa.
- yield_margin on von Mises = 400/251.594913 - 1 = 0.589857.
- yield_margin on Tresca = 400/277.308492 - 1 = 0.442437.
- is_within_von_mises_envelope(200, -50, 400) = True.
- The Tresca margin governs: 0.442437 versus 0.589857 on von Mises.

Combined bending and torsion sigma_b = 180 MPa, tau = 100 MPa,
Sy = 350 MPa:

- von Mises sqrt(180**2 + 3*100**2) = 249.799920 MPa.
- combined_bending_torsion_margin = 350/249.799920 - 1 = 0.401121.

Pure shear checks: von_mises_plane_stress(0, 0, 100) = 173.205081 MPa
= sqrt(3)*100; the envelope edge for pure shear sits at
tau = Sy/sqrt(3) = 230.940108 MPa.

## Verification

- Confirm the worked anchors: von Mises 251.594913 MPa, principals
  (213.654246, -63.654246) MPa, Tresca 277.308492 MPa within 1e-4;
  margins 0.589857 and 0.442437 within 1e-5; envelope verdict True.
- Confirm the combined case 249.799920 MPa and margin 0.401121.
- Confirm the closed-form identities: uniaxial von Mises equals |s|,
  pure shear von Mises equals sqrt(3)*tau, von_mises_3d with
  sz = tyz = tzx = 0 equals the plane-stress form exactly, the Tresca
  equivalent never falls below the von Mises equivalent, the uniaxial
  point (Sy, 0) sits on the envelope boundary, and the biaxial corner
  (Sy, -Sy) lies outside.
- Confirm non-physical inputs raise ValueError: a zero or negative
  equivalent stress, a zero or negative yield strength, and
  unordered principals in tresca_equivalent.
- Run the contract test offline: python3
  scripts/test_multiaxial_yield_criteria.py (35 tests, deterministic).

## Related leaves

- structures/materials/ramberg-osgood: the uniaxial stress-strain
  curve whose 0.2 percent offset yield point feeds Sy here.
- structures/materials/mmpsd-allowables: statistically based design
  values that set the yield strength Sy used by the margins.
- structures/materials/fracture-toughness: crack instability after
  the part passes its yield check.
- structures/composites/failure-criteria: anisotropic lamina strength
  assessment for composite plies, the fence on this leaf.
- structures/fem/calculix-linear: element-basis equivalent stress
  post-processing of a solved model, not a hand yield check.

## Pitfalls

- Mixing units: every stress and the yield strength must share one
  unit (MPa or Pa); the sqrt form is unit-homogeneous, so a Pa/MPa mix
  quietly shifts the margin.
- Using the principal difference sigma_1 - sigma_2 alone for Tresca in
  plane stress: the zero out-of-plane principal matters, and the
  maximum is over sigma_1 - sigma_2, sigma_1 and -sigma_2, so a
  uniaxial compression state governs on -sigma_2.
- Assuming the Tresca von Mises ratio is always 2/sqrt(3): that ratio
  belongs to pure shear; the ratio is not fixed for general biaxial
  states, so compute both equivalents and take the governing margin.
- Reading a yield margin of zero as a pass: zero sits exactly at
  yield, so any margin at or below zero fails the hand check.
- Forgetting the -sx*sy cross term in the plane-stress von Mises form:
  dropping it overstates the equivalent stress for biaxial tension
  and understates it for tension-compression states.
- Confusing the envelope verdict with the margin: the envelope takes a
  biaxial (sx, sy) point with no shear and returns a bool, while the
  margin is a number on an equivalent stress.
- Applying isotropic criteria to a composite lamina: anisotropic
  strength work belongs to structures/composites/failure-criteria.

## Behavior contract (gate 3)

The von Mises, Tresca, principal stress, margin, shaft, and envelope
logic is exercised by the gate 3 contract test:
scripts/test_multiaxial_yield_criteria.py against
scripts/multiaxial_yield_criteria_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_multiaxial_yield_criteria.py

## Compliance

- Standards referenced, not reproduced: MMPDS (SAE) is proprietary and
  is named only as the source of statistically based metallic yield
  strength design values; no tables or values are copied. The von
  Mises and Tresca yield criteria and the Mohr circle are classical
  strength-of-materials methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

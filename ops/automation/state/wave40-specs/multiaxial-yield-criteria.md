# Wave-40 leaf spec: multiaxial-yield-criteria (structures, materials pack)

- Path: skills/structures/materials/multiaxial-yield-criteria/
- Pack: materials. Closest siblings: failure-criteria (composites pack;
  its SKILL body opens "Use when the task is lamina failure assessment
  for a composite ply: Tsai-Wu, Tsai-Hill, and max-stress failure
  indices under in-plane stress." and its Domain quick reference says
  "A lamina has strength allowables in material axes: fiber tension Xt,
  fiber compression Xc, transverse tension Yt, transverse compression
  Yc, and in-plane shear S." - ANISOTROPIC lamina criteria only, no
  isotropic metal yield content), calculix-linear (fem pack; its SKILL
  description says "determine margin of safety from allowables versus
  FEA stresses, validate unit discipline before post-processing, and
  check von Mises stress results" and workflow step 5 is "Check
  equivalent stress with von_mises where a scalar" - von Mises there is
  FEA element-basis post-processing of a solved model, not a hand
  yield check), ramberg-osgood (its description computes "the total
  strain at a given stress with strain = stress/E + 0.002*(stress/
  sigma_0.2)^n, invert the implicit equation by bisection for the
  stress at a required total strain" - a UNIAXIAL stress-strain curve
  model, no multiaxial criterion), mmpsd-allowables (A-basis/B-basis
  tolerance statistics from coupon data, no stress-state evaluation),
  material-selection (property-index trades that read yield strength as
  an input), fracture-toughness (K_IC crack instability, not yielding),
  creep-rupture. Whole-tree greps at prep: "tresca" = 0 hits in
  skills/; "von mises"/"von-mises" owning content = calculix-linear
  scripts only (FEA post-processing); zero yield-criterion evaluation in
  the materials pack (ramberg-osgood builds the curve, mmpsd-allowables
  reduces coupon data). GENUINE STRUCT gap (fresh probe).
- Standards id: mmpsd (reference-only; materials-pack convention, same
  as mmpsd-allowables and creep-rupture). Ledger Standard: mmpsd.
- Family: structures

## Claim

Evaluate an isotropic metal stress state against the classical yield
criteria by hand: compute the von Mises equivalent stress in plane
stress sqrt(sx^2 - sx*sy + sy^2 + 3*txy^2) and in full 3D, resolve the
plane-stress principal stresses by the Mohr circle, compute the Tresca
equivalent as the maximum principal stress difference including the
zero out-of-plane principal, compute the yield margin
yield/equivalent - 1, run the von Mises combined bending-plus-torsion
margin for a shaft section, and check whether a biaxial tension point
falls inside the von Mises yield envelope. Produces the von Mises and
Tresca equivalent stresses, the principal stresses, the yield margins
and the envelope verdict that gate metallic part hand checks. Does NOT
do: composite lamina anisotropic criteria Tsai-Wu/Tsai-Hill/max-stress
(failure-criteria); FEA element-basis von Mises post-processing
(calculix-linear); uniaxial stress-strain curve modeling (ramberg-
osgood); statistical A/B-basis allowables (mmpsd-allowables).

## Model (implement exactly)

Functions (pure stdlib, stresses in Pa or MPa consistently):
- von_mises_plane_stress(sigma_x, sigma_y, tau_xy) -> float
  sqrt(sigma_x**2 - sigma_x*sigma_y + sigma_y**2 + 3*tau_xy**2).
- von_mises_3d(sigma_x, sigma_y, sigma_z, tau_xy, tau_yz, tau_zx) ->
  float sqrt(0.5*((sx-sy)**2 + (sy-sz)**2 + (sz-sx)**2) +
  3*(txy**2 + tyz**2 + tzx**2)), i.e. the task form with the 6*
  shear term inside the 0.5 factor.
- plane_stress_principals(sigma_x, sigma_y, tau_xy) -> tuple
  (sigma_1, sigma_2) with sigma_1 >= sigma_2 from the Mohr circle
  (sx+sy)/2 +- sqrt(((sx-sy)/2)**2 + txy**2).
- tresca_equivalent(sigma_1, sigma_3) -> float sigma_1 - sigma_3;
  ValueError if sigma_1 < sigma_3 (principals must be ordered).
- tresca_plane_stress(sigma_x, sigma_y, tau_xy) -> float
  max(sigma_1 - sigma_2, sigma_1, -sigma_2) over the three principal
  difference pairs, the out-of-plane principal being zero in plane
  stress, so uniaxial tension gives sigma and pure shear gives 2*tau
  (the classical Tresca-von Mises ratio sqrt(3)/2 is not assumed).
- yield_margin(equivalent_stress, yield_strength) -> float
  yield_strength/equivalent_stress - 1; ValueError if equivalent_stress
  <= 0 or yield_strength <= 0.
- combined_bending_torsion_margin(bending_stress, torsional_stress,
  yield_strength) -> float margin on the shaft von Mises equivalent
  sqrt(bending_stress**2 + 3*torsional_stress**2); ValueErrors as in
  yield_margin.
- is_within_von_mises_envelope(sigma_x, sigma_y, yield_strength) ->
  bool sigma_x**2 - sigma_x*sigma_y + sigma_y**2 <=
  yield_strength**2 (on the boundary counts as within); ValueError if
  yield_strength <= 0.

Identity to test: uniaxial tension sigma reduces von Mises to |sigma|;
pure shear tau reduces von Mises to sqrt(3)*tau; von_mises_3d with
sigma_z = tau_yz = tau_zx = 0 equals von_mises_plane_stress exactly;
the Tresca equivalent never falls below the von Mises equivalent for
the same plane-stress state; the uniaxial point (yield, 0) sits on the
envelope boundary; the biaxial corner (yield, -yield) lies outside.

## Worked example

Plane stress sx = 200 MPa, sy = -50 MPa, txy = 60 MPa, Sy = 400 MPa:
- von_mises_plane_stress = 251.594913 MPa.
- plane_stress_principals = (213.654246, -63.654246) MPa.
- tresca_plane_stress = 277.308492 MPa.
- yield_margin on von Mises = 400/251.594913 - 1 = 0.589857.
- yield_margin on Tresca = 400/277.308492 - 1 = 0.442437.
- is_within_von_mises_envelope(200, -50, 400) = True.
Combined bending and torsion sigma_b = 180 MPa, tau = 100 MPa,
Sy = 350 MPa:
- von Mises sqrt(180^2 + 3*100^2) = 249.799920 MPa.
- combined_bending_torsion_margin = 350/249.799920 - 1 = 0.401121.
Pure shear check: von_mises_plane_stress(0, 0, 100) = 173.205081 MPa =
sqrt(3)*100; the envelope edge for pure shear sits at tau =
Sy/sqrt(3) = 230.940108 MPa.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds (reproduced at prep with stdlib
math, see /tmp/w40spec/anchors_multiaxial.py).

## Validation list (contract test must include)

- Worked anchors: von Mises 251.594913 within 1e-4, principals
  (213.654246, -63.654246) within 1e-4, Tresca 277.308492 within 1e-4.
- Margins 0.589857 and 0.442437 within 1e-5; envelope verdict True.
- Combined case 249.799920 within 1e-4 and margin 0.401121 within 1e-5.
- Uniaxial identity: von_mises_plane_stress(s, 0, 0) = |s| for signed s.
- Pure shear identity: von_mises_plane_stress(0, 0, tau) = sqrt(3)*tau.
- 3D/plane consistency to float precision for sz = tyz = tzx = 0.
- Tresca >= von Mises across a signed grid of plane-stress states.
- Plane stress pure shear: Tresca = 2*tau and von Mises = sqrt(3)*tau,
  ratio 2/sqrt(3) = 1.1547.
- Envelope: (400, 0) within True; (400, -400) within False; pure shear
  boundary at tau = 230.940108 within 1e-4.
- Margin zero at equivalent = yield; positive below; negative above.
- ValueErrors: yield_margin(0, 400), yield_margin(-1, 400),
  yield_margin(200, 0), tresca_equivalent(100, 200),
  is_within_von_mises_envelope(100, 100, 0).
- Determinism; tuple and bool return types exactly as documented.

## Corpus fragment (eval/hit1-wave40-multiaxial-yield-criteria.yaml)

Query 1 (copy verbatim):
  "compute the multiaxial-yield-criteria von-mises-equivalent-stress and the yield margin for the plane-stress state on the isotropic aluminum part"
  intent: "structures; isotropic von Mises plane-stress equivalent and yield margin"
  expected_skill: "structures/materials/multiaxial-yield-criteria"
Query 2 (copy verbatim):
  "check the isotropic part against the tresca-margin for the biaxial plane-stress state and report the governing equivalent stress"
  intent: "structures; Tresca margin and principal stress check for isotropic metal yield"
  expected_skill: "structures/materials/multiaxial-yield-criteria"
Task ids: w40-multiaxial-yield-criteria-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the multiaxial yield
margin of an isotropic metal part:" and include the outputs in the
Claim. First tag: multiaxial-yield-criteria. Additional tags ONLY:
von-mises-equivalent-stress, tresca-margin. NEVER single generic words
(yield, stress, von, mises, tresca, margin, equivalent, criterion,
metal, isotropic). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): tsai-wu, tsai-hill, max-stress,
failure-index, lamina, ply-allowables, composite-lamina (failure-
criteria); fea, calculix, ccx, element-basis, finite-element, unit-
discipline, static-analysis (calculix-linear); ramberg-osgood, stress-
strain-curve, plastic-strain, secant-modulus, tangent-modulus, offset-
yield-strength, elastic-plastic (ramberg-osgood); a-basis, b-basis,
k-factor, sample-statistics, design-values (mmpsd-allowables);
fracture-toughness, stress-intensity (fracture-toughness); goodman-
diagram (fatigue mean-stress leaf).

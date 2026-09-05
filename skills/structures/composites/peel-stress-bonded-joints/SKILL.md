---
name: peel-stress-bonded-joints
description: "Use when you must compute the peel stress at the overlap end of a single-lap bonded joint: find the Goland-Reissner bending moment factor from the load per unit width, the adherend thickness, modulus and Poisson ratio, and the overlap half length, form the edge moment at the overlap end, resolve the peak peel stress from the adhesive Winkler-foundation beam model with the peel decay coefficient, and rate the peel margin against an allowable peel strength. Produces the bending moment factor, the edge moment, the peel decay coefficient, the peak peel stress and the peel margin that gate the peel-critical joint check. Trigger: goland-reissner peel stress, adherend bending, peel critical joint, overlap end peel stress, bonded joint peel margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: cmh-17
    reference-only: true
gated: false
domain: structures
pack: composites
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [peel-stress-bonded-joints, goland-reissner, bending-moment-factor, adherend-bending, peel-margin]
  version: 0.1.0
  author: AeroSkills
---

# Peel Stress in Bonded Joints (structures/composites/peel-stress-bonded-joints)

Use when the task is the peel stress at the overlap end of a
single-lap bonded joint between two identical adherends of a
composite or metallic structure: the classical Goland-Reissner
bending moment factor, the edge moment that the load path eccentricity
puts into the adherends, and the maximum peel stress that the
adhesive bondline sees at the overlap end from the Winkler-foundation
beam model. This leaf implements the Goland-Reissner analysis in pure
Python, stdlib only, and reports the peel margin that gates the
peel-critical joint check in the CMH-17 composite context. The
sibling structures/composites/adhesive-bonded-joints owns the in-plane
bondline shear transfer of the same single-lap geometry and
self-declares peel and adherend bending out of scope; this leaf fills
that gap for peel-critical designs. It also pairs with
structures/composites/composite-bolted-joints, the mechanical fastener
alternative, and with laminate-stiffness for the adherend side of the
joint.

## Domain quick reference

- Geometry: balanced single-lap joint, two identical adherends of
  thickness t and modulus E with Poisson ratio nu, bonded over an
  overlap of total length 2 c (c the overlap half length) by an
  adhesive layer of modulus E_a and thickness t_a. All quantities are
  per unit width: the load per unit width is P_pw = P / b.
- Goland-Reissner bending moment factor:
  u^2 = (3 (1 - nu^2) / 2) * P_pw / (E t^3), then
  k = cosh(u c) / (cosh(u c) + 2 sqrt(2) sinh(u c)). k lies in (0, 1]:
  it tends to 1 as the load or the overlap half length tends to zero
  (the no-bending limit) and falls toward the classical floor of about
  0.261 for very long overlaps, so the edge moment never grows without
  bound with the overlap.
- Edge moment at the overlap end: M0 = k * P_pw * t / 2, the moment
  that the eccentric load path applies to each adherend at the edge of
  the bondline.
- Adherend flexural rigidity: D = E t^3 / (12 (1 - nu^2)).
- Winkler-foundation beam parameter:
  lambda^4 = 3 (1 - nu^2) E_a / (E t^3 t_a) with lambda in 1/m.
- Peel stress at the overlap end: the edge moment M0 deflects the
  adherend beam on the adhesive foundation, w0 = M0 / (2 lambda^2 D),
  and the adhesive strains with that deflection,
  sigma_peel = (E_a / t_a) * w0 in Pa.
- Peel decay coefficient: beta = sqrt(6 E_a / (t_a E t)) in 1/m, the
  classical exponential peel-decay parameter that measures how fast
  the peel stress dies away from the overlap end.
- Peel margin: margin = peel_strength_allowable / sigma_peel. The
  joint passes the peel-critical check when the margin is at least
  one, that is when the peak peel stress does not exceed the
  allowable.
- Sensitivity: sigma_peel scales with sqrt(E_a) and with
  1 / sqrt(t_a), so doubling the adhesive modulus raises the peel
  stress by about sqrt(2) and doubling the adhesive thickness lowers
  it by the same factor; a stiffer or thinner adhesive layer is not
  automatically a safer bondline.
- SI units throughout: N, m, Pa. CMH-17 frames the bonded joint data
  context; the relations above are standard engineering methodology,
  summary-only.
- The model boundary: this is the Goland-Reissner peel analysis of
  the overlap end only; the in-plane bondline shear transfer along
  the overlap belongs to the adhesive-bonded-joints leaf, and full
  finite-element peel modeling is out of scope here.

## Workflow

1. Fix the joint geometry and materials: load per unit width P_pw
   (load_per_unit_width), adherend thickness t (adherend_thickness),
   adherend modulus E (adherend_modulus), Poisson ratio nu
   (poisson_ratio), overlap half length c (overlap_half_length),
   adhesive modulus E_a (adhesive_modulus), adhesive thickness t_a
   (adhesive_thickness), and the peel strength allowable
   (peel_strength_allowable).
2. Compute the Goland-Reissner bending moment factor with
   bending_moment_factor; k falls from 1 toward the 0.261 floor as
   the load or the overlap grows, so it carries the whole bending
   state of the joint into the peel check.
3. Compute the peel decay coefficient with peel_decay_coefficient;
   beta sets the exponential decay of the peel stress away from the
   overlap end.
4. Resolve the peel stress at the overlap end with
   peel_stress_at_overlap_end, which forms the edge moment
   M0 = k P_pw t / 2, solves the adhesive Winkler-foundation beam
   response at the overlap end, and returns the dict
   {peel_stress, edge_moment, lambda}.
5. Rate the joint with peel_margin against the peel strength
   allowable; the margin is allowable over peel stress, and a margin
   below one fails the peel-critical joint check.
6. Confirm the deterministic checks by running the contract test
   scripts/test_peel_stress_bonded_joints.py.

## Worked example

Aluminum adherends E = 70 GPa, nu = 0.33, t = 1.6 mm; epoxy adhesive
E_a = 1.5 GPa, t_a = 0.25 mm; overlap 25 mm (half length c = 12.5
mm); load P = 4000 N over a 25 mm width, so P_pw = 1.6e5 N/m.

- Average adherend stress sigma_avg = P_pw / t = 100 MPa.
- bending_moment_factor(1.6e5, 1.6e-3, 70e9, 0.33, 0.0125) = 0.518201.
- Edge moment M0 = k P_pw t / 2 = 66.3298 N m/m.
- lambda = 486.335 1/m, and the peel stress at the overlap end is
  3.13768e7 Pa = 31.3768 MPa, about 0.31 of the average adherend
  stress for this joint.
- peel_decay_coefficient(1.5e9, 0.25e-3, 70e9, 1.6e-3) =
  566.947 1/m.
- peel_margin(31.3768e6, 35e6) = 1.11547: the 35 MPa allowable
  clears the peak peel stress. peel_margin(31.3768e6, 25e6) =
  0.796767: the 25 MPa allowable fails the peel-critical check even
  though the same joint passes an in-plane shear check.

Lower-load case P_pw = 8.0e4 N/m (sigma_avg = 50 MPa): k = 0.598868,
M0 = 38.3275 N m/m, and the peel stress falls to 18.1306 MPa, so the
peel stress is monotone increasing with the load.

## Pitfalls

- Reading the peel stress as uniform through the bondline: the peel
  stress is strongly concentrated at the overlap end where the edge
  moment acts; the margin must be checked against the peak value at
  the end, not against any average across the overlap.
- Stopping at the in-plane shear analysis: a joint can clear the
  adhesive shear allowable and still fail in peel, because the
  adherend bending from the eccentric load path adds a through-
  thickness stress the shear model never sees; peel-critical designs
  need this Goland-Reissner check.
- Expecting a stiffer or stronger adhesive to always help: the peel
  stress grows with sqrt(E_a), so doubling the adhesive modulus
  raises the peak peel stress by about sqrt(2) and can consume the
  margin the stronger adhesive was meant to buy.
- Ignoring adhesive thickness control: the peel stress scales with
  1 / sqrt(t_a), so a thin bondline region drives up the peel stress
  at the overlap end; the worked example's 0.5 mm bondline halves the
  31.38 MPa peak down to 22.19 MPa.
- Assuming the bending moment factor saturates at one: for long
  overlaps k falls toward the classical floor near 0.261, and the
  edge moment M0 = k P_pw t / 2 follows it down; using k = 1
  overstates the moment for a long joint.
- Treating a margin of one as a comfortable pass: margin =
  allowable / peel stress, so one means the peak peel stress exactly
  equals the allowable with no reserve; only a margin above one
  passes with margin to spare.
- Feeding non-physical joint inputs: negative load per unit width,
  zero or negative thicknesses and moduli, a zero overlap half
  length, Poisson ratios outside (-1, 0.5), and non-positive
  allowables all raise ValueError instead of producing a stress.

## Verification

- Confirm bending_moment_factor(1.6e5, 1.6e-3, 70e9, 0.33, 0.0125)
  returns 0.518201 within 1e-5, that the factor is 1.0 at zero load
  and 0.999924 at a near-zero load, and that it reaches 0.261204 at
  a 1 m overlap half length, the classical long-overlap floor.
- Confirm the factor is monotone decreasing in the overlap half
  length (0.928308 at 1 mm down through 0.287155 at 50 mm) and in
  the load per unit width (0.805922 at 10 N/mm, 0.518201 at 160
  N/mm, 0.417725 at 400 N/mm).
- Confirm peel_stress_at_overlap_end returns 31.3768 MPa peel stress,
  66.3298 N m/m edge moment and 486.335 1/m lambda within the spec
  tolerances, that the peel stress grows monotonically with the load
  (18.1306, 31.3768 and 63.23 MPa at 80, 160 and 400 N/mm), that
  doubling E_a raises it to 44.37 MPa and doubling t_a lowers it to
  22.19 MPa, and that the dict keys are exactly peel_stress,
  edge_moment and lambda.
- Confirm peel_decay_coefficient(1.5e9, 0.25e-3, 70e9, 1.6e-3) =
  566.947 1/m within 0.01 and peel_margin(31.3768e6, 35e6) =
  1.11547 within 1e-3.
- Confirm negative loads, zero or negative thicknesses and moduli,
  zero overlap half length, Poisson ratio 0.6, and zero allowables
  all raise ValueError.
- Spec note recorded as an assumption: the prep checkpoint 0.287155
  for the overlap traverse is realized at a 50 mm overlap half
  length, and the checkpoint 0.805922 at 10 N/mm, not at the 80
  N/mm level of the worked example; the module follows the formula
  exactly and the tests assert the values at the half lengths and
  loads where the formula actually produces them.
- Run the contract test offline: python3
  scripts/test_peel_stress_bonded_joints.py (34 tests,
  deterministic).

## Related leaves

- structures/composites/adhesive-bonded-joints: the in-plane
  bondline shear transfer of the same single-lap geometry, which
  self-declares peel and adherend bending out of scope; this leaf
  supplies the peel check those joints need.
- structures/composites/composite-bolted-joints: the mechanical
  fastener alternative for joining composite laminates.
- structures/composites/failure-criteria: ply-level failure checks of
  the adherends either side of the bondline.
- structures/composites/laminate-stiffness: adherend modulus and
  thickness inputs for laminate adherends.
- structures/composites/cmh17-allowables: composite material and
  joint data context behind the CMH-17 reference.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_peel_stress_bonded_joints.py

The test covers the worked example anchors (moment factor 0.518201,
edge moment 66.3298 N m/m, lambda 486.335 1/m, peel stress 31.3768
MPa, decay coefficient 566.947 1/m, margins 1.11547 and 0.796767),
the no-bending limit k to 1 at zero load and the classical 0.261
floor at a long overlap, the monotone traverses of k in the overlap
half length and in the load, the monotone peel growth with the load,
the sqrt(2) sensitivity to doubled adhesive modulus and thickness,
the exact dict keys, the peel margin round trip, the determinism of
repeated calls, and ValueError rejection of negative loads, zero
thicknesses and moduli, zero overlap half length, Poisson ratio 0.6
and zero allowables.

## Compliance

- Standards referenced, not reproduced: CMH-17 is a SAE-published
  composite materials handbook (sae.org/publications/cmh-17); the
  Goland-Reissner single-lap relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: plastic-collapse-analysis
description: "Use when you must find the plastic collapse (limit) load of a beam or a simple frame: compute the fully plastic moment Mp = sigma_y*Zp from the plastic section modulus Zp (rectangle b*h^2/4, circle d^3/6, I-beam with the plastic neutral axis in the web), the shape factor nu = Zp/Z, and the plastic hinge mechanisms of statically indeterminate beams and rectangular frames, applying the kinematic (virtual work) and static (equilibrium plus yield) theorems to give the plastic collapse load, the collapse load factor against the applied load and the ultimate margin in the 1.5 ultimate-factor context of FAR 25.303. Produces the plastic section moduli and shape factors, fully plastic moments, plastic collapse loads with hinge mechanisms, and the load factor and ultimate margin verdicts that gate metallic beam and frame strength checks. Trigger: plastic collapse, plastic hinge, collapse mechanism, fully plastic moment, shape factor."
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
  tags: [plastic-collapse-analysis, plastic-hinge, collapse-mechanism, limit-analysis-beam, fully-plastic-moment, shape-factor, collapse-load-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# Plastic Collapse Analysis (structures/fem/plastic-collapse-analysis)

Use when you must find the plastic collapse (limit) load of a beam or a
simple frame. This leaf analyzes the limit state of rigid-perfectly-
plastic bending: the fully plastic moment Mp = sigma_y*Zp built from
the plastic section modulus Zp, the shape factor nu = Zp/Z as the
section reserve between first yield and full plasticity, and the
plastic hinge mechanisms of statically indeterminate beams and frames
whose collapse loads come from the kinematic (virtual work) and static
(equilibrium plus yield) theorems. It pairs with the elastic side of
the pack: beam-frame-analysis solves the same rigid-jointed frames
elastically and stops at the member end actions, while this leaf
carries the member into the plastic mechanism state, so the two bound
the strength check from below (first yield) and above (plastic
collapse).

## Domain quick reference

- Fully plastic moment: Mp = sigma_y*Zp with Zp the first moment of
  area about the equal-area axis (plastic neutral axis). Closed forms:
  rectangle Zp = b*h**2/4; solid circle Zp = d**3/6; doubly symmetric
  I-beam with the plastic neutral axis in the web Zp = b*t_f*(d - t_f)
  + t_w*(d - 2*t_f)**2/4, the flanges at full stress at their lever
  arms about the mid-depth plus the two half-webs.
- Elastic section modulus: rectangle Z = b*h**2/6; circle Z = pi*d**3/32;
  I-beam I = (b*d**3 - (b - t_w)*(d - 2*t_f)**3)/12 and Z = 2*I/d.
- Shape factor: nu = Zp/Z is exactly 3/2 for the rectangle, exactly
  16/(3*pi) = 1.69765272631 for the circle, and the closed-form
  quotient for the I-beam (about 1.10 to 1.25 for rolled shapes).
  First-yield moment My = sigma_y*Z = Mp/nu: the moment at which the
  extreme fibre reaches sigma_y. Flanged sections put the material far
  from the neutral axis, so first yield and full plasticity nearly
  coincide and the reserve is smallest.
- Hinge count rule: a collapse mechanism needs r + 1 plastic hinges
  for r-fold static indeterminacy: 1 (simply supported, r = 0),
  2 (propped cantilever, r = 1), 3 (fixed-fixed beam, r = 2),
  2 (pinned-base frame sway, r = 1), 4 (fixed-base frame sway, r = 3).
- Kinematic theorem per case (virtual work W*delta = sum of Mp*theta_i
  with delta = theta*L/2 under the central load): simply supported
  Wc = 4*Mp/L; propped cantilever Wc = 6*Mp/L; fixed-fixed beam
  Wc = 8*Mp/L. Portal sway under a top lateral load H on columns of
  height h (delta = theta*h): pinned bases Hc = 2*Mp/h, fixed bases
  Hc = 4*Mp/h.
- Static theorem: at the collapse load the equilibrium moment diagram
  of the mechanism state has |M| <= Mp everywhere with |M| = Mp exactly
  at the hinge stations.
- Elastic first-yield context loads: W_y = 4*My/L (simply supported,
  peak W*L/4), W_y = 16*My/(3*L) (propped cantilever, hogging peak
  3*W*L/16 at the fixed end), W_y = 8*My/L (fixed-fixed, peaks W*L/8 at
  both ends). Collapse-to-yield ratios Wc/Wy = nu, 9*nu/8 and nu.
- FAR 25.303 context: ultimate load is 1.5 times the limit load, so
  the plastic collapse load factor lambda = collapse load / limit load
  must reach 1.5 and the ultimate margin lambda/1.5 clears 1 exactly
  when the collapse load clears the 1.5-factor ultimate load.
- Units are SI throughout (m, N, Pa). Scope: rigid-perfectly-plastic
  bending, small-deflection mechanisms, constant Mp along each member,
  no axial-moment interaction, no distributed-load collapse, no
  combined mechanisms beyond the sway mechanism, no strain hardening.

## Workflow

1. Establish the section reserves of the cross section: run
   plastic_section_modulus, elastic_section_modulus and shape_factor on
   the shape dims (rectangle (b, h); circle (d); I-beam (d, b, t_f,
   t_w)) and read the shape factor as the reserve between first yield
   and full plasticity.
2. Establish the yield capacity of the member: fully_plastic_moment
   with the yield stress and the plastic section modulus for Mp, and
   divide by the shape factor for the first-yield moment My = Mp/nu.
3. Form the plastic hinge mechanism of the single-span beam and compute
   the plastic collapse load under the central point load with
   collapse_load_beam, the kinematic (virtual work) theorem applied to
   the r + 1 hinge mechanism.
4. Cross-check the mechanism state with the static theorem: sample the
   collapse-state equilibrium moment diagram (reactions Wc/2 each end,
   or 4*Mp/L at the fixed end and 2*Mp/L at the pin of the propped
   cantilever) and confirm |M| <= Mp with equality only at the hinge
   stations.
5. Get the elastic first-yield context loads W_y from My and the
   collapse-to-yield ratios Wc/Wy (nu, 9*nu/8, nu) for the reserve
   report.
6. Get the sway mechanism collapse loads of a simple rectangular frame
   under a top lateral load with portal_sway_collapse_load on the
   column height, the fully plastic moment and the base condition.
7. Express the reserve against the applied limit load: collapse_load_factor
   for lambda and ultimate_margin for the FAR 25.303 1.5 ultimate-factor
   verdict, adequate when the collapse load clears 1.5 times the limit
   load.
8. Confirm the deterministic checks with the contract test
   scripts/test_plastic_collapse_analysis.py.

## Worked example

sigma_y = 250 MPa; rectangle 50 x 100 mm (b = 0.05, h = 0.1), circle
d = 0.1 m, I-beam 400 x 200 x 12 x 8 mm (d = 0.4, b = 0.2, t_f =
0.012, t_w = 0.008). All values below are the real module outputs.

- Section reserves: rectangle Zp = 0.000125 m^3 (125 cm^3), Z =
  8.33333333333e-05 m^3, nu = 1.5 exactly, Mp = 31250 N m, My =
  20833.3333333 N m. Circle Zp = 0.000166666666667 m^3 (166.7 cm^3),
  Z = 9.81747704247e-05 m^3, nu = 16/(3*pi) = 1.69765272631, Mp =
  41666.6666667 N m, My = 24543.6926062 N m. I-beam Zp =
  0.001213952 m^3, Z = 0.00108074325333 m^3, nu = 1.12325660721, Mp =
  303488 N m, My = 270185.813333 N m. The shape-factor ladder 1.6977
  (circle) > 1.5 (rectangle) > 1.1233 (I-beam) is the reserve ordering:
  the I-beam material sits in the flanges, far from the neutral axis.
- Single-span beams at rectangle Mp = 31250 N m, L = 3 m, one central
  point load: Wc = 4*Mp/L = 41666.6666667 N (1 hinge at midspan) simply
  supported, Wc = 6*Mp/L = 62500 N (2 hinges, fixed end and under the
  load) propped cantilever, Wc = 8*Mp/L = 83333.3333333 N (3 hinges,
  both supports and midspan) fixed-fixed.
- Static theorem check at collapse: sampling the collapse-state moment
  diagram at 2001 stations gives max |M| = 31250 N m = Mp with
  overshoot above Mp exactly 0.0 for all three cases; the fixed-fixed
  collapse state runs linearly from -Mp at x = 0 through +Mp under the
  load to -Mp at x = L with reactions Wc/2 = 41666.6667 N.
- Elastic first-yield context loads: W_y = 27777.7777778 N,
  37037.037037 N and 55555.5555556 N, giving Wc/Wy = 1.5 (= nu),
  1.6875 (= 9*nu/8) and 1.5 (= nu): the propped cantilever gains the
  extra 12.5% because only its fixed-end peak yields first.
- Portal frame with I-beam columns, Mp = 303488 N m, h = 4 m, top
  lateral load: pinned bases Hc = 2*Mp/h = 151744 N (2 top-corner
  hinges), fixed bases Hc = 4*Mp/h = 303488 N (4 corner hinges),
  exactly double.
- Margin logic at a 60000 N limit: pinned portal lambda =
  2.52906666667, ultimate load required 90000 N, margin 1.68604444444,
  adequate; fixed portal lambda = 5.05813333333, margin 3.37208888889,
  adequate. The pinned-base limit load that fails at ultimate is
  Hc/1.5 = 101162.666667 N. Fixed-fixed beam at a 40000 N limit:
  lambda = 2.08333333333, margin 1.38888888889, adequate; at a 60000 N
  limit: lambda = 1.38888888889, margin 0.925925925926, inadequate:
  the plastic mechanism forms below the FAR 25.303 ultimate load.

## Verification

- Confirm plastic_section_modulus("rectangle", 0.05, 0.1) returns
  0.000125 and the closed forms equal b*h**2/4, d**3/6 and the I-beam
  expression by construction.
- Confirm the shape factors 1.5, 1.69765272631 and 1.12325660721 with
  the ordering 1.6977 > 1.5 > 1.1233, and the nu = Mp/My identity for
  every section (anchor residual 2.22044604925e-16).
- Confirm the collapse loads 41666.6666667, 62500 and 83333.3333333 N
  equal the closed forms 4*Mp/L, 6*Mp/L and 8*Mp/L with the r + 1
  hinge counts and station texts.
- Confirm max |M| over the 2001-station sampled collapse-state diagram
  equals Mp = 31250 with overshoot no greater than 1e-9 relative for
  all three beam cases (anchor 0.0) and equality only at the hinge
  stations.
- Confirm the portal sway values 151744 N (pinned) and 303488 N
  (fixed), the fixed-base sway exactly double the pinned-base value.
- Confirm ultimate margins 1.38888888889 (adequate) and
  0.925925925926 (inadequate) with the verdict flip exactly where the
  collapse load crosses 1.5 times the limit load.
- Confirm every non-physical input raises ValueError: unknown shape,
  wrong dims arity, nonpositive dims, I-beam with d <= 2*t_f or
  t_w >= b, sigma_y <= 0, unknown beam case, span = 0, mp <= 0,
  unknown frame base, height = 0, nonpositive limit load and
  ultimate_factor = 0 (13 anchor cases).
- Run the contract test offline: python3
  scripts/test_plastic_collapse_analysis.py (34 tests, deterministic).

## Related leaves

- structures/fem/beam-frame-analysis: the elastic complement in this
  pack, the stiffness-method frame solution that stops at the member
  end actions with no yield stress and no hinge.
- structures/materials/ramberg-osgood: the material stress-strain curve
  at a point, the input material model context for the yield stress.
- structures/materials/multiaxial-yield-criteria: pointwise yield
  margins of a stress state, the first-yield side of the check.
- structures/fem/buckling-analysis: elastic instability of slender
  compression members, the alternative ultimate failure mode.
- structures/fem/cylindrical-shell-buckling: elastic ovalization
  collapse of curved shell sections, a different geometry and
  mechanism.

## Pitfalls

- Reading the shape factor as a strength margin: nu = Zp/Z is a section
  reserve, not a factor on the applied load. The fixed-fixed beam
  collapses at nu times its first-yield load, but the propped
  cantilever reaches 9*nu/8 because only its single hogging peak yields
  first, so the load reserve depends on the elastic moment diagram, not
  on the section alone.
- Treating the collapse load as an ultimate load: collapse at the
  plastic mechanism is itself failure. The FAR 25.303 check is
  lambda = collapse load / limit load >= 1.5, so a mechanism that forms
  below 1.5 times the limit load (margin below 1.0, verdict inadequate)
  fails the ultimate requirement even though the elastic stresses at
  the limit load look acceptable.
- Assuming a 50/50 reaction split at collapse: the propped cantilever
  collapse state carries 4*Mp/L at the fixed end against 2*Mp/L at the
  pin, and only that asymmetric diagram satisfies the static theorem
  with |M| = Mp at both hinge stations.
- Using the elastic section modulus for the fully plastic moment: Mp
  needs the plastic section modulus Zp about the equal-area axis, not
  the extreme-fibre Z; on the worked rectangle the two differ by the
  shape factor 1.5, which is exactly the reserve the plastic check
  exploits.
- Counting hinges instead of mechanisms: a set of r + 1 hinges is only
  a collapse mechanism when it forms a kinematically admissible
  mechanism at a load that satisfies equilibrium with |M| <= Mp, which
  is why the kinematic and static theorems are applied together.
- Applying I-beam closed forms outside the web: the Zp expression and
  its shape-factor range hold only for a doubly symmetric I-beam with
  the plastic neutral axis in the web (d > 2*t_f and t_w < b); the
  module rejects proportions outside that scope with ValueError.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_plastic_collapse_analysis.py

The test covers the section-reserve pass (plastic and elastic section
moduli and shape factors of the three worked sections), the yield
capacity pass (fully plastic moments and first-yield moments), the
plastic hinge mechanisms and collapse loads of the three single-span
beam cases by the kinematic theorem, the static theorem cross-check on
the 2001-station collapse-state moment diagram, the elastic first-yield
context loads and collapse-to-yield ratios, the pinned and fixed base
portal sway mechanisms, the collapse load factor and the FAR 25.303
ultimate margin verdicts, the 13 ValueError rejection cases and the
determinism check.

## Compliance

- Standards referenced, not reproduced: FAR 25.303 and CS 25.303
  (structure must withstand 1.5 times the limit loads without failure)
  frame the ultimate-factor context of the margin; the relations above
  are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

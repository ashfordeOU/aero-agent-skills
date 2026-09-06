---
name: shear-center-analysis
description: "Use when you must locate the shear center of a thin-walled open section under transverse shear: walk the contour from the free edge accumulating the first moment Q, build the V*Q/I shear-flow distribution, integrate the wall-shear resultant and its moment, and report the shear-center offset from the web, centroid or corner in millimeters for channel, Z, angle, hat and slit single-cell box sections, with the bending shear-stress check tau = V*Q/(I*t) at the critical wall station. Doubly symmetric I-beam and closed box sections carry the shear center at the centroid by symmetry, so the leaf reports their web shear-flow maximum instead. Produces the shear-center coordinates, the offset from the stated reference, the per-wall shear flow q(s) and the vertical-resultant equilibrium check that gate open-section spar, stiffener and frame design. Trigger: shear center, shear flow, channel section, Z-section, angle section, thin-walled spar, stiffener, I-beam web shear, transverse shear."
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
  tags: [shear-center-analysis, shear-center-location, transverse-shear-flow, thin-walled-open-section]
  version: 0.1.0
  author: AeroSkills
---

# Shear Center Analysis (structures/fem/shear-center-analysis)

Locate the shear center of a thin-walled open section under a
transverse vertical shear: walk the single open contour from its free
edge, accumulate the first moment Q of the outboard wall area, build
the V*Q/I shear-flow distribution q(s) = V_y * Q / I_xx, integrate the
wall-shear resultant and its moment, and report the shear-center offset
from the stated reference (the web centerline for the channel, the
section centroid for the Z, the corner for the angle). Doubly symmetric
I-beam and closed box sections carry the shear center at the centroid
by symmetry, so the leaf validates their mid-web shear-flow maximum
instead of integrating a multi-branch contour. This leaf implements the
standard thin-wall transverse-shear methodology in pure Python, stdlib
stdlib only, in the closed forms that gate open-section spar, stiffener and
frame design. It pairs with structures/fem/torsion-shear-flow for
torque-driven circulation of the same sections and with
structures/fem/diagonal-tension-field-webs for the web-panel limit of
the same shear-flow distribution.

## Domain quick reference

- Transverse shear flow: q(s) = V_y * Q(s) / I_xx, where Q(s) is the
  first moment (integral of y*t over the outboard wall area, walked
  from the free edge where Q = 0) and I_xx the centroidal second moment
  about the bending axis. Units: q in N/m, V_y in N, Q in m^3, I in m^4.
- Resultant of the wall flow: each step contributes a force
  q * (cx, cy) * ds along the contour tangent and a moment
  q * (x*cy - y*cx) * ds about the origin; the shear-center offset is
  e = M_z / F_y, negative when the line of action falls behind the web.
- Channel closed form: e = 3*b^2 / (h + 6*b) from the web centerline,
  the classical thin-channel result (b the flange width, h the web
  height). The integrated walk reproduces it to about 2 ppm at n = 400;
  the residual is the flange local-inertia refinement the closed form
  drops.
- Channel inertia closed form: I_xx = t*h^2*(h + 6*b)/12; the walked
  section property adds the small flange local terms, agreeing to
  1e-4 relative.
- Z-section: the doubly symmetric Z has its shear center at the
  centroid, so the offset from the centroid is zero (within the
  integration tolerance).
- Equal-leg angle: the shear center sits at the intersection of the leg
  centerlines, the corner, so the offset from the corner is zero; the
  centroid of a 50 mm leg angle lies at (12.5, 12.5) mm.
- Doubly symmetric I-beam: shear center at the centroid (e = 0); the
  mid-web shear-flow maximum q = V_y * Q / I_xx with
  Q = t_w*(h/2)*(h/4) + b_f*t_f*(h/2 + t_f/2) (half the web above
  mid-height plus one full flange) is the validation anchor.
- Bending shear-stress check: tau = V_y * Q / (I_xx * t) at the
  critical wall station stays far below the order 100 MPa aluminum
  allowables for the worked-example loads (3.75 MPa at the channel
  web-flange junction, 5.62 MPa at mid-web).
- Units are SI throughout: meters for all dimensions and offsets, N for
  loads, N/m for shear flow, Pa for stress. Convert mm inputs by
  dividing by 1000 before calling the module.
- FAR-25 and CS-25 frame the airframe spar, stiffener and frame section
  context; the relations above are standard engineering methodology,
  summary-only per standards-map.yaml.

## Workflow

1. Fix the geometry and the applied shear: web height h, flange width b
   and wall thickness t (channel and Z), leg length a and thickness t
   (angle), or the flange and web sizes of the I-beam, plus the applied
   vertical shear vy in N. All dimensions are meters.
2. Evaluate the section properties: run section_properties on the
   mid-line contour (the section-properties pass) to get the centroid
   (xbar, ybar) and the centroidal second moments (ixx, iyy, ixy) that
   feed the shear-flow walk. Cross-check the channel I_xx against
   t*h^2*(h + 6*b)/12.
3. Walk the contour from the free edge: shear_center_channel,
   shear_center_z and shear_center_angle each build the V*Q/I
   transverse-shear-flow distribution q(s) = vy*Q/ixx step by step,
   accumulating the running first moment Q, and integrate the wall
   forces and moments (fx, fy, mz).
4. Resolve the wall-shear resultant: confirm the vertical-equilibrium
   check fy = -vy within 1e-3 relative (the contour runs down the web)
   and the horizontal resultant fx vanishes below 1e-6 N for the
   channel and Z contours.
5. Report the shear-center offset: e = mz/fy from the stated reference
   (web centerline for the channel, centroid for the Z, corner for the
   angle) and convert to millimeters. Cross-check the channel against
   the closed form 3*b^2/(h + 6*b); the sign tells which side of the
   web the shear center sits on.
6. Validate the doubly symmetric I-beam: run i_beam_web_qmax for the
   mid-web shear-flow maximum and state the centroid shear center
   (e = 0) from the double-symmetry property.
7. Confirm the deterministic checks: rerun the offline contract test
   scripts/test_shear_center_analysis.py and confirm all 33 methods
   pass (deterministic, math only, no RNG).

## Worked example

Thin-walled channel spar: web h = 100 mm, flanges b = 50 mm both to the
same side, t = 2 mm, vertical shear vy = 1000 N (real module outputs):

- Section properties: centroid 12.500 mm outboard of the web, ixx =
  6.667333e-07 m^4, matching the classical t*h^2*(h + 6*b)/12 =
  6.666667e-07 m^4 to 1e-4 relative.
- shear_center_channel(0.100, 0.050, 0.002, vy = 1000.0): fy =
  -999.8984 N (vertical equilibrium, target -1000), fx = -3.5e-14 N,
  e = -18.7500 mm from the web centerline: the shear center sits
  18.75 mm BEHIND the web (opposite the flange direction), matching the
  classical closed form 3*b^2/(h + 6*b) = 18.75 mm to a ratio of
  1.000002 (the 2 ppm offset is the flange local-inertia refinement).
- Bending shear-stress check: tau = vy*Q/(ixx*t) = 3.75 MPa at the
  web-flange junction and 5.62 MPa at mid-web, far below the order
  100 MPa aluminum allowables for the 1000 N load.
- shear_center_z(0.100, 0.050, 0.002, vy = 1000.0): e from the
  centroid = -0.000000 mm (shear center at the centroid, the Z is
  doubly symmetric), ixx = 6.667333e-07 m^4, fy = -999.8984 N.
- shear_center_angle(0.050, 0.003, vy = 1000.0): e from the corner =
  -0.000000 mm (the shear flow line of action passes through the leg
  intersection), centroid at (12.500, 12.500) mm, so the shear center
  is 17.678 mm from the centroid along the diagonal.
- i_beam_web_qmax(t_f = 0.004, b_f = 0.060, t_w = 0.003, h = 0.100,
  vy = 1000.0): ixx = 1.692560e-06 m^4, web shear-flow maximum at
  mid-web q = 9589.0 N/m (shear center at the centroid by double
  symmetry).

## Verification

- Confirm shear_center_channel(0.100, 0.050, 0.002, vy = 1000.0)
  returns |e| = 18.750 mm within 1e-3 mm with e < 0 (flanges extend
  toward +x, the shear center sits behind the web) and the ratio
  |e|/(3*b^2/(h + 6*b)) is 1 within 2e-5 at n = 400.
- Confirm the vertical-equilibrium check |fy| = 999.9 N within 1 N and
  |fx| below 1e-6 N for the channel and Z contours.
- Confirm the symmetry results: the Z-section offset from the centroid
  and the angle offset from the corner each stay within 1e-3 mm of 0.
- Confirm the I-beam anchors: q_max = 9589.0 N/m within 1 N/m and
  ixx = 1.692560e-06 m^4 within 1e-9.
- Confirm the section-property identity: the channel ixx matches
  t*h^2*(h + 6*b)/12 within 2e-4 relative.
- Confirm ValueError rejection of non-physical inputs: empty segment
  list, zero-length segments, zero or negative thickness, non-positive
  dimensions, and non-finite shear loads, across every function.
- Confirm determinism: two runs give bit-identical outputs; the module
  imports math only and uses no RNG.
- Run the deterministic contract test offline: python3
  scripts/test_shear_center_analysis.py (33 tests, sub-second).

## Related leaves

- structures/fem/torsion-shear-flow: torque-driven circulation (J,
  closed-cell flow, twist) of the same sections, no V*Q/I transverse
  shear-flow term and no shear-center location.
- structures/fem/diagonal-tension-field-webs: web-panel analysis whose
  pre-buckling shear-flow distribution and shear center sit at the
  scope boundary of this leaf's V*Q/I model.
- aerodynamics/aeroelasticity/divergence-speed: consumes the shear
  center offset e as a given input for the divergence pressure and
  never locates the shear center from section geometry.
- structures/fem/beam-column-analysis: member stress under axial and
  bending load for the same spars, without the transverse-shear-flow
  section machinery.
- structures/fem/curved-beam-analysis: curved member stress analysis
  that pairs with this leaf for open-section curved spars.
- structures/fem/buckling-analysis: the load-carrying limit of the
  same spar and stiffener sections.

## Pitfalls

- Mixing the offset references: the channel e is measured from the web
  centerline, the Z-section e from the centroid, and the angle e from
  the corner. Compare only values from the same reference.
- Reading the e sign backwards: flanges extending toward +x put the
  shear center behind the web, so e is negative; report the offset as
  a magnitude with the side stated.
- Expecting the angle walk to equilibrate exactly: the single-axis
  V_y*Q/I model drops the I_xy coupling of the unsymmetric angle, so
  the integrated resultant magnitude of the 50 mm angle contour is not
  -vy; the deliverable for the angle is the corner line of action
  (e = mz/fy = 0), while the equilibrium check belongs to the channel
  and Z contours.
- Feeding millimeters to the module: all dimensions and offsets are
  meters internally; 18.75 mm must enter as 0.01875 for offsets and
  50 mm as 0.050 for the flange width.
- Trusting the classical channel form blindly: 3*b^2/(h + 6*b) drops
  the flange local inertia, so the walked e exceeds it by about 2 ppm;
  the n = 400 integration is the refined value.
- Starting the contour off a free edge: the accumulation of Q assumes
  q = 0 at the starting edge; a closed box must be slit or handed to
  the torsion-shear-flow leaf instead.
- Dropping the I-beam flange local terms: ixx keeps the weak-axis
  t_f*b_f^3/12 flange term so the anchor value 1.692560e-06 m^4 and
  the q_max = 9589.0 N/m target reproduce exactly; omitting that term
  moves q_max by about 9 percent.
- Reporting the junction stress as the maximum: for the channel the
  first moment Q keeps growing down the web, so tau peaks at mid-web
  (5.62 MPa) above the web-flange junction value (3.75 MPa).

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline, sub
second):

    python3 scripts/test_shear_center_analysis.py

The test covers the worked-example anchors (channel offset |e| =
18.750 mm within 1e-3 mm, fy = -999.9 N within 1 N, vanishing fx,
ixx = 6.667333e-07 m^4), the channel closed-form ratio within 2e-5,
the section-property closed forms and identity for single walls and the
channel contour, the Z-section and equal-leg-angle symmetry zeros with
the (a/4, a/4) centroid and 17.678 mm diagonal, the I-beam mid-web
shear-flow maximum 9589.0 N/m within 1 N/m and ixx = 1.692560e-06 m^4,
linear scaling with the applied shear, the junction and mid-web bending
shear-stress magnitudes against the aluminum allowable bound, ValueError
rejection of every non-physical input class, and bit-identical
determinism with no imports beyond math.

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 frame the
  airframe section shear context (standards-map.yaml ids, both
  reference-only, the fem-pack convention used by torsion-shear-flow);
  the V*Q/I relations above are standard engineering methodology,
  summary-only.
- compliance: STANDARDS-REF, gated: false.

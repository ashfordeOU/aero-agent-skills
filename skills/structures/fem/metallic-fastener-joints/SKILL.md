---
name: metallic-fastener-joints
description: "Use when you must analyze a metallic multi-fastener joint: split the applied load into the per-fastener share of a symmetric bolt or rivet pattern, check the fastener shear in single or double shear, the sheet bearing P/(D*t), net-section tension across the row and shear-out at the edge distance, and resolve an eccentric bolt group by the polar moment method for a load applied off the pattern centroid. Produces the per-fastener loads, the shear, bearing, net-section and shear-out stresses, the group torque with the per-bolt direct and secondary resultants, the max-loaded fastener, and the margin of safety of each mode against MMPDS-style allowables stated as module parameters, under MoS = allowable/(factor*applied) - 1 with the 1.5 ultimate factor. Trigger: metallic fastener joints, bolt group analysis, eccentric bolt group, fastener shear margin, single lap splice."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
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
  tags: [metallic-fastener-joints, bolt-group-analysis, eccentric-bolt-group, fastener-shear-margin, fastener-load-share]
  version: 0.1.0
  author: AeroSkills
---

# Metallic Fastener Joints (structures/fem/metallic-fastener-joints)

Use when you must analyze a metallic multi-fastener joint, a bolt or
rivet pattern in a metal sheet, under its applied load: the equal
per-fastener share of a symmetric row, the fastener shear check in
single or double shear, the sheet bearing, net-section tension and
shear-out checks with a margin of safety per mode against MMPDS-style
allowables, and the polar moment method for an eccentric bolt group
whose load line misses the pattern centroid. This leaf implements the
closed-form elastic analysis in pure stdlib Python, SI units (N, mm,
MPa), offline and deterministic. Assumptions recorded: elastic equal
sharing only, one fastener type per pattern, all bolts identical, and
the sheet bearing allowable valid at the edge distance ratio e/D >= 2
used here; load redistribution from fastener flexibility, joint slip,
secondary bending, fatigue and mixed fastener types are out of scope.
It pairs with the single-pin lug leaf for one-pin fittings and with the
composite-panel joint leaf for laminate joints; those leaves own their
fiber and contour failure modes, not the metallic sheet modes below.

## Domain quick reference

- Per-fastener share of a symmetric pattern of n identical fasteners:
  P_f = P/n.
- Fastener shear area: A = pi*D^2/4; shear stress on one fastener over
  `planes` shear planes: tau = P_f/(planes*A). planes = 1 is single
  shear on one plane, planes = 2 is double shear on two.
- Sheet bearing stress under one fastener: sigma_b = P_f/(D*t).
- Net-section tension at a row of `holes` fasteners across the width:
  sigma_nt = P/((w - holes*D)*t); the net width w - holes*D must stay
  positive and carries the FULL row load P, not the per-fastener share.
- Sheet shear-out (tear-out) at the free edge: tau_so = P_f/(2*e*t),
  two shear planes each of length e (edge distance from the hole center
  to the free edge along the load direction) and thickness t.
- Margin of safety: MoS = allowable/(factor*applied_limit) - 1 with the
  default design ultimate factor 1.5 on limit stresses (FAR 25.303
  style); factor = 1.0 recovers the plain allowable/applied - 1 form.
  A zero margin means the factored applied stress equals the allowable.
- Bearing to shear-out relation: sigma_b/tau_so = 2e/D, so at the
  worked edge distance e = 2D the ratio is exactly 4.
- Eccentric group polar method: bolt group centroid (x_c, y_c), polar
  moment J = sum_i((x_i - x_c)^2 + (y_i - y_c)^2); applied force
  (fx, fy) at (ax, ay) gives the torque about the centroid M =
  (ax - x_c)*fy - (ay - y_c)*fx. Every bolt takes the equal direct
  share (fx, fy)/n plus the secondary share F_sec,i = (M/J)*(-dy_i,
  dx_i) at its radius offset (dx_i, dy_i), magnitude |M|*r_i/J
  perpendicular to the radius, so the secondary forces sum to zero and
  their moments sum exactly to M.
- Allowables are module parameters in the MMPDS style (BOLT_F_SU the
  fastener shear ultimate of a steel MS-class bolt, SHEET_F_BRU,
  SHEET_F_TU and SHEET_F_SU the 2024-T3 sheet bearing, tension and
  shear ultimates), representative defaults stated as module constants,
  never a reproduced design-value table.

## Workflow

1. Split the symmetric pattern into per-fastener shares: run
   splice_joint_analysis with the row limit load P, the fastener count
   n, diameter D, sheet thickness t, joint width w, edge distance e and
   the allowables, and read off per_fastener_load_N = P/n.
2. Shear-check the fasteners: fastener_shear_stress on the per-fastener
   load with planes = 1 (single shear) or 2 (double shear); double
   shear halves the stress exactly.
3. Bearing-check the sheet: bearing_stress = P_f/(D*t) under each
   fastener against the sheet bearing allowable.
4. Net-section tension check: net_section_stress = P/((w - holes*D)*t)
   with the full row load over the net width.
5. Shear-out check at the sheet edge: shear_out_stress = P_f/(2*e*t)
   against the sheet shear allowable.
6. Apply the margin convention: margin_of_safety(allowable,
   applied_limit, factor) returns MoS = allowable/(factor*applied) - 1;
   splice_joint_analysis already applies it to every mode and reports
   the governing (lowest) margin and the pass verdict.
7. Resolve the eccentric bolt group by the polar moment method:
   bolt_group_properties gives the centroid and polar moment J, then
   eccentric_bolt_group_loads(fx, fy, ax, ay, bolts) returns the torque
   about the centroid, the per-bolt direct and secondary resultants
   with magnitudes, the max-loaded fastener and its indices.
8. Size the bracket fasteners from the max-loaded fastener: apply
   fastener_shear_stress to max_magnitude_N with the candidate bolt
   diameter and margin_of_safety against the fastener shear allowable
   to pick the passing bolt size.

## Worked example

Example A: a representative single-lap shear splice with four 1/4-in MS
bolts (D = 6.35 mm) in a symmetric row across a 2024-T3 sheet of
thickness t = 2.5 mm, width w = 90 mm, edge distance e = 12.7 mm
(e/D = 2), carrying a limit load P = 20000 N.

- Per-fastener share P/4 = 5000.0000 N exactly; fastener area
  pi*D^2/4 = 31.669217 mm^2.
- Fastener shear (steel MS bolt F_su = 655 MPa): single shear
  tau = 157.882019 MPa, MoS = +1.765778; double shear tau =
  78.941010 MPa, MoS = +4.531557, exactly half the single-shear stress.
- Sheet bearing (F_bru = 620 MPa): sigma = 5000/(6.35*2.5) =
  314.960630 MPa, MoS = +0.312333, the GOVERNING mode.
- Net-section tension (F_tu = 427 MPa): net width w - 4D = 64.6000 mm,
  sigma = 20000/(64.6*2.5) = 123.839009 MPa, MoS = +1.298683.
- Sheet shear-out (F_su = 255 MPa): tau = 5000/(2*12.7*2.5) =
  78.740157 MPa, MoS = +1.159000; bearing/shear-out = 4.000000 = 2e/D.
- splice_joint_analysis verdict: margins {fastener_shear: 1.765778,
  bearing: 0.312333, net_section: 1.298683, shear_out: 1.159000},
  governing bearing, min margin +0.312333, passes True. The same
  splice at 2.0x limit (P = 40000 N) gives bearing margin -0.343833,
  governing stays bearing, passes False; the joint is bearing-critical.
- Convention check: MoS(F, F/1.5) = 0.000000 exactly; MoS(F, F) =
  -0.333333; factor = 1.0 gives MoS(2F, F) = +1.000000 exactly.

Example B: an eccentric bracket bolt group of four bolts at (+/-25,
+/-25) mm carrying a 27000 N force in +x applied at (0, +100) mm,
100 mm off the pattern centroid.

- bolt_group_properties: centroid (0.000000, 0.000000), J =
  5000.000000 mm^2; per-bolt radius r = 35.355339 mm.
- Torque about the centroid M = (ax-xc)*fy - (ay-yc)*fx = -100*27000
  = -2700000 N*mm (clockwise); direct share (6750.00, 0.00) N per bolt.
- Per-bolt totals (direct + secondary), magnitude in N:
  bolt (25, 25): (20250.00, -13500.00), 24337.4711; bolt (-25, 25):
  (20250.00, 13500.00), 24337.4711; bolt (-25, -25): (-6750.00,
  13500.00), 15093.4588; bolt (25, -25): (-6750.00, -13500.00),
  15093.4588. Max-loaded magnitude 24337.471109 N on indices [0, 1],
  the two top bolts tying by mirror symmetry about the load plane.
- Equilibrium: bolt loads sum to (27000.00, 0.00) N and the moments
  sum to -2700000 N*mm, exactly the applied force and torque.
- Bracket fasteners sized as 3/8-in MS bolts (D = 9.525 mm, area
  71.256 mm^2): max bolt shear stress = 341.551030 MPa, MoS =
  +0.278481 (passes); the same group with 1/4-in bolts gives
  768.489817 MPa and MoS -0.431786 (fails): the bracket needs the
  3/8-in bolts.
- Force line through the centroid (M = 0): every bolt magnitude =
  6750.000000 N, the equal share P/4 exactly.

## Verification

- Confirm fastener_area(6.35) = 31.669217 mm^2, fastener_shear_stress
  (5000, 6.35, 1) = 157.882019 MPa and the planes = 2 halving identity
  2*tau_double = tau_single within 1e-9 relative.
- Confirm bearing_stress(5000, 6.35, 2.5) = 314.960630 MPa,
  net_section_stress(20000, 90, 4, 6.35, 2.5) = 123.839009 MPa (net
  width 64.6 mm) and shear_out_stress(5000, 12.7, 2.5) =
  78.740157 MPa; the bearing/shear-out ratio at e = 2D is exactly 4.
- Confirm the margin convention: MoS(427, 427/1.5) = 0 within 1e-12,
  MoS(427, 427) = -1/3 within 1e-9 and MoS(200, 100, factor = 1.0) =
  1.0 exactly.
- Confirm the worked-example splice margins (bearing 0.312333
  governing at 20000 N, -0.343833 failing at 40000 N) and the
  eccentric group anchors (torque -2700000 N*mm, max magnitude
  24337.471109 N, max_indices [0, 1], equilibrium sums).
- Confirm every non-physical input raises ValueError: D <= 0; planes
  outside (1, 2); negative fastener or row loads; t <= 0; e <= 0;
  holes < 1; net width w - holes*D <= 0; n < 1; allowable, applied
  limit or factor <= 0; empty bolt group; zero applied force; all
  bolts coincident (J = 0).
- Confirm determinism: repeated eccentric runs are bit-identical, no
  imports beyond math, no RNG.
- Run the contract test offline: python3
  scripts/test_metallic_fastener_joints.py (35 tests, deterministic,
  passes under /usr/bin/python3 and the pyenv 3.13.12 hook
  interpreter).

## Pitfalls

- Dividing the row load by n on the net section: the net-section
  tension carries the FULL row load P over the net width
  w - holes*D; only the fastener shear, bearing and shear-out checks
  use the per-fastener load share (row load divided by fastener
  count). Feeding that per-fastener share into net_section_stress
  understates the net-section stress by the pattern count.
- Confusing bearing and shear-out areas: bearing is P_f/(D*t) against
  the hole, shear-out is P_f/(2*e*t) over the two edge shear planes;
  their ratio is 2e/D, so a short edge distance (small e) drives the
  shear-out margin down while leaving bearing untouched.
- Reading a zero margin as failure at the limit load: with the 1.5
  ultimate factor, MoS(F_allow, F_limit) = -1/3 and a positive margin
  requires the allowable to clear 1.5x the limit stress; the plain
  form is recovered only with factor = 1.0.
- Treating single and double shear as the same check: double shear
  puts the load across two planes and halves the shear stress, so a
  double-shear joint passes at roughly half the single-shear stress.
- Summing eccentric secondary loads like a force: the secondary
  shares are a self-equilibrating couple, they sum to zero and their
  moments sum to the applied torque about the centroid; the bolt load
  is the VECTOR sum of the direct and secondary shares, and the two
  top bolts of the worked square tie at the maximum by mirror
  symmetry.
- Misplacing the torque sign or lever arm: the torque arm is the
  applied load point offset from the GROUP centroid, not from the
  pattern origin; a load line through the centroid gives M = 0 and
  every bolt carries the plain equal share P/n.
- Applying the bearing allowable outside its validity: the 2024-T3
  F_bru module value holds for edge distance e/D >= 2; closer holes
  change the bearing failure mode and need a reduced value.
- Claim creep toward the sibling leaves: the single-pin lug contour
  tearout, the laminate joint with its bypass load share, distributed
  web attachment shear flows and installation process quality all
  belong to their own leaves, listed in Related leaves.

## Related leaves

- structures/fem/lug-joint-analysis: the single-pin metallic lug
  fitting with round-end proportioning and contour tearout planes.
- structures/composites/composite-bolted-joints: the bolted joint in a
  fiber-reinforced panel under bearing and bypass loading.
- structures/fem/diagonal-tension-field-webs: distributed web
  attachment shear flows and post-buckled web margins.
- structures/fem/beam-column-analysis: eccentrically loaded column
  secant-formula checks, not bolt-group loads.
- manufacturing-quality/assembly/fastener-installation-quality and
  manufacturing-quality/assembly/solid-rivet-installation-quality:
  installation process quality (grip, torque, collar), not stress.
- cross-cutting/tolerancing/fastener-position-tolerance-calc: hole
  positional tolerancing, not joint stress.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_metallic_fastener_joints.py

The test covers the worked-example splice contract (per-fastener share
5000 N, single and double shear stresses 157.882019/78.941010 MPa with
the exact halving identity, bearing 314.960630 MPa governing at margin
+0.312333, net-section 123.839009 MPa, shear-out 78.740157 MPa, and the
2x overload flipping the bearing margin to -0.343833 with passes False),
the margin-of-safety convention (zero at factored-equal, -1/3 at plain
ultimate, +1 exactly with factor 1.0), the eccentric bolt group contract
(centroid, J = 5000 mm^2, torque -2700000 N*mm, per-bolt direct and
secondary resultants, max-loaded fastener 24337.471109 N on indices
[0, 1], equilibrium sums, zero-torque equal share), the 3/8-in vs 1/4-in
bracket bolt sizing, ValueError rejection of every non-physical input in
the Verification list, bit-identical determinism and the math-only import
rule. It passes under both /usr/bin/python3 and the pyenv 3.13.12
interpreter the pre-push hook uses.

## Compliance

- Standards referenced by name and paraphrased, never reproduced:
  MMPDS (F_su, F_bru, F_tu design values are module parameters, no
  tables quoted), FAR 25.303 (1.5 ultimate factor convention) and
  CS-25 (equivalent airworthiness context). The relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

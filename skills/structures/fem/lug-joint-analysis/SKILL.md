---
name: lug-joint-analysis
description: "Use when you must analyze a metallic pin-loaded lug fitting under an axial load: compute the hole bearing stress, the net section tension stress across the lug width, the tearout shear stress on the two planes from the hole tangent to the round outer contour, the per-mode margins against the material tension, shear and bearing allowables, the governing failure mode and the pass/fail verdict, the limiting allowable capacity, and the governing-mode map over the edge distance ratio for a round-end lug with w = 2e. Produces the applied stresses, per-mode margins, governing mode and margin, pass/fail, capacity, and the short-lug tension, intermediate tearout and long-lug bearing e/D sweep. Trigger: lug joint analysis, pin-loaded lug, lug bearing stress, lug tearout shear, lug net section tension, lug edge distance ratio, round-end lug."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
gated: false
domain: structures
pack: fem
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [lug-joint-analysis, pin-loaded-lug, lug-bearing-stress, lug-net-section-tension, lug-tearout-shear, lug-edge-distance-ratio, round-end-lug]
  version: 0.1.0
  author: AeroSkills
---

# Lug Joint Analysis (structures/fem/lug-joint-analysis)

Use when you must analyze a metallic pin-loaded lug fitting under an
axial pin load: the bearing stress on the hole, the net section
tension stress across the lug width, the tearout shear stress on the
two planes tangent to the hole running to the outer contour, the
margin of each mode against the material allowables, the governing
failure mode (lowest margin), and the governing-mode capacity map over
the edge distance ratio e/D (short-lug net tension, intermediate
tearout, long-lug bearing). This leaf implements the round-end lug
convention w = 2e in pure stdlib Python, SI units, offline and
deterministic. It pairs with the single-row bolted joint analysis for
fiber-reinforced panels (no lug proportioning there) and with the
finite element contact boundary analysis for pin-to-hole contact
detail. It does not size pin-jointed frames: beam-frame-analysis and
truss-analysis own those structures.

## Domain quick reference

- Round-end lug: hole of diameter D centered in a round head of radius
  e, so the lug width is w = 2e; thickness t carries axial pin load P.
  Edge distance e must exceed D/2 and width w must exceed D.
- Bearing stress on the hole: sigma_b = P / (D t).
- Net section tension across the remaining width: sigma_nt = P /
  ((w - D) t), net section width (w - D).
- Tearout shear on the two planes from the hole tangent to the outer
  contour: sigma_te = P / (2 t L_te), with each shear plane length
  L_te = sqrt(e^2 - (D/2)^2).
- Margin per mode: m = allowable / applied - 1, using the bearing
  ultimate F_bru for bearing, the tension ultimate F_tu for net
  section tension and the shear ultimate F_su for tearout.
- Governing mode: smallest margin; the lug passes when min margin >= 0.
- Per-mode allowable load (load that makes that mode margin zero):
  bearing F_bru D t, net section tension F_tu (w - D) t, tearout
  F_su 2 t L_te; the limiting mode has the smallest capacity.
- Allowables are material inputs, for example MMPDS chapter 9 lug
  ultimate data for the lug alloy (referenced by name, never
  reproduced). FAR 25.307 frames proof-of-structure fitting
  substantiation context.
- Governing behavior over e/D for typical aluminum allowables:
  net section tension below about 1.03, tearout between about 1.03 and
  1.74, bearing above about 1.74.
- Units SI throughout: N, m, Pa.

## Workflow

1. Fix the lug geometry: hole_diameter_m, thickness_m, lug_width_m,
   edge_distance_m, and the axial pin load load_n, then get the applied
   mode stresses with lug_stresses (returns bearing_pa,
   net_tension_pa, tearout_pa, tearout_plane_length_m,
   net_section_width_m).
2. Choose the material allowables f_tu_pa, f_su_pa, f_bru_pa from the
   lug alloy data, and form the per-mode margins with lug_margins.
3. Run the full margin check with lug_analysis: applied stresses,
   margins, governing_mode, min_margin, passes, plus e_over_d,
   d_over_t and the tearout plane geometry.
4. For a margin-of-safety style capacity statement, run
   lug_allowable_capacity at the round-end geometry (w = 2e is assumed
   inside) to get the per-mode allowable loads, the limiting mode and
   the limiting capacity.
5. For the short-lug / intermediate / long-lug map, run
   lug_governing_map with the material allowables at fixed D and t; it
   sweeps e/D from 0.6 to 2.5 with e = ratio * D and w = 2e and
   returns the governing mode and limiting capacity per sample.
6. Confirm the deterministic checks with the contract test
   scripts/test_lug_joint_analysis.py.

## Worked example

7075-T6 lug: D = 20 mm, t = 12 mm, e = 24 mm (e/D = 1.2), w = 48 mm,
F_tu = 572 MPa, F_su = 331 MPa, F_bru = 1050 MPa, P = 90 kN. Real
module outputs:

- Stresses: bearing 375.0 MPa, net section tension 267.857 MPa,
  tearout 171.881 MPa with L_te = 21.817 mm and net section width
  28 mm.
- Margins: bearing +1.800, net section tension +1.135, tearout
  +0.926.
- Governing mode tearout, min margin +0.926, passes True.
- Same lug at P = 200 kN: tearout stress 381.958 MPa, margin -0.133,
  governing stays tearout, passes False.
- Allowable capacities: bearing 252000 N, net section tension
  192192 N, tearout 173318 N; limiting mode tearout at 173318 N.
- Governing map (D = 20 mm, t = 12 mm, 7075 allowables): net section
  tension governs below e/D about 1.03, tearout governs the middle
  band (for example 168060 N at e/D = 1.17), bearing governs above
  e/D about 1.74 at the constant 252000 N. All three modes govern
  across the sweep.

## Verification

- Confirm lug_analysis(90000, 0.020, 0.012, 0.048, 0.024, 572e6,
  331e6, 1050e6) returns bearing margin 1.8, net section tension
  margin 1.135, tearout margin 0.926, governing tearout and passes
  True.
- Confirm the same lug at 200000 N gives tearout margin -0.133 and
  passes False with tearout still governing.
- Geometry identity: at e/D = 1 the tearout plane length is
  sqrt(3)/2 * D = 0.8660254 D and the net section width is 2e - D.
- Capacity identity: lug_allowable_capacity per-mode loads equal the
  applied load that drives that margin to zero (checked for all three
  modes in the contract test), and the limiting mode matches the
  governing mode of lug_analysis at the same geometry.
- Governing map: all three modes appear as governing over [0.6, 2.5],
  capacity is monotonically non-decreasing in e/D and the bearing
  capacity is constant in e/D.
- Rejection: negative load, non-positive dimensions, edge distance
  not above D/2, width not above D and non-positive allowables all
  raise ValueError in every entry point that uses them.
- Determinism: pure stdlib, no random numbers, identical floats
  run-to-run.

## Related leaves

- structures/composites/composite-bolted-joints: the single-row
  bolted joint sibling for fiber-reinforced panels; this leaf is the
  metallic lug with e/D proportioning, head geometry and tearout
  planes from the hole contour, with no load-sharing split concept.
- structures/fem/contact-analysis: the finite element contact
  boundary sibling for pin-to-hole bearing detail.
- structures/fem/beam-frame-analysis and structures/fem/truss-analysis:
  pin-jointed frame analysis siblings; they do not size lug fittings.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_lug_joint_analysis.py

The test covers the 7075-T6 worked lug anchors (stresses, margins,
governing tearout, pass/fail at 90 kN and 200 kN), the e/D = 1
geometry identity, per-mode allowable capacity and margin-zero
identities, the three-mode governing sweep with monotone capacity, the
convenience dict keys, and ValueError rejection of negative loads,
non-positive dimensions, degenerate e/D and w/D relations and
non-positive allowables.

## Compliance

- Standards referenced by name only, not reproduced: MMPDS chapter 9
  lug ultimate data heritage (mmpsd) and FAR 25.307 proof-of-structure
  context for fitting substantiation; the stress and margin relations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: delta-wing-vortex-lift
description: "Use when you must estimate the vortex lift of a sharp-edged delta wing: apply the Polhamus leading-edge suction analogy to split the total lift into the attached potential term Kp sin(alpha) cos^2(alpha) and the leading-edge-separation vortex term Kv cos(alpha) sin^2(alpha), with the slender-wing potential slope Kp = pi AR / 2 and the vortex factor Kv growing linearly from 3.14 at AR 0 to about 3.45 at AR 4. Produces the total lift coefficient, the potential and vortex lift split, the vortex fraction, the drag due to lift CL tan(alpha), and the angle where vortex lift overtakes potential lift. Valid for sharp leading edges, subsonic flow, aspect ratio about 0.5 to 2.0, alpha up to about 25 degrees. Trigger: Polhamus suction analogy, leading edge suction, vortex lift, slender delta wing, nonlinear lift."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: cfd
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: cfd
  tags: [delta-wing-vortex-lift, polhamus-suction-analogy, leading-edge-vortex, slender-delta-wing, vortex-lift-split, drag-due-to-lift, nonlinear-lift]
  version: 0.1.0
  author: AeroSkills
---

# Delta Wing Vortex Lift (aerodynamics/cfd/delta-wing-vortex-lift)

Use when the task is the separated-flow lift of a sharp-edged slender
delta wing: the Polhamus leading-edge suction analogy (NASA TN D-3767,
1966) that adds a leading-edge-separation vortex term to the attached
potential term. The leaf is the only separated-flow vortex-lift model in
the library; it covers the regime the attached-flow siblings exclude. It
pairs with aerodynamics/cfd/vortex-lattice-method, which owns the
horseshoe-vortex attached-flow linear range, and with
aerodynamics/high-lift/high-lift-systems for the mechanical-device
alternatives. Valid for sharp leading edges, subsonic flow, aspect ratio
about 0.5 to 2.0, alpha up to about 25 degrees. Does not model vortex
breakdown onset (empirical charts only, not modeled), circulation
control, blown flaps, or ice accretion.

## Domain quick reference

- Aspect ratio of a full delta: AR = 4 / tan(Lambda_LE); 76 deg sweep
  gives about 1.0 and 45 deg gives 4.0.
- Total lift (TN eq. 15): CL = Kp sin(a) cos^2(a) + Kv cos(a) sin^2(a),
  the sum of the potential term and the vortex term.
- Potential term: CL_pot = Kp sin(a) cos^2(a), with the slender-wing
  small-angle slope Kp = pi * AR / 2.
- Vortex term: CL_vort = Kv cos(a) sin^2(a), where Kv is the leading
  edge suction force coefficient, linear from 3.14 at AR 0 to 3.45 at
  AR 4 (clamped beyond 4).
- Drag due to lift: CD_i = CL * tan(a), the product of the total lift
  coefficient and the tangent of the angle of attack.
- Crossing angle: tan(a) = Kp / Kv, where the vortex term equals the
  potential term; slender wings are vortex dominated earlier.
- All angles in degrees on input; CL(0) = 0 exactly.

## Workflow

1. Get the aspect ratio: delta_aspect_ratio from the leading-edge sweep
   angle of the full delta, or supply the AR directly.
2. Compute the model factors: slender_delta_kp for Kp and delta_kv for
   Kv at that aspect ratio.
3. Split the lift at the angle of attack: polhamus_cl_potential and
   polhamus_cl_vortex, then polhamus_cl for the total.
4. Find the drag due to lift with cd_due_to_lift on the total lift.
5. Check which term dominates: vortex_potential_crossing_deg for the
   angle where the vortex term overtakes the potential term.
6. For a one-call breakdown use delta_lift_summary (aspect ratio by
   default, or pass sweep=True with the leading-edge sweep angle in
   degrees), returning the aspect ratio, kp, kv, alpha, the lift split,
   cd_due_to_lift, vortex_fraction and crossing_deg keys.
7. Confirm the deterministic checks with the contract test
   scripts/test_delta_wing_vortex_lift.py.

## Worked example

AR 1.0 delta (Lambda_LE = 76 deg) at alpha = 15 deg, and an AR 0.5
delta (about 82.9 deg sweep).

- delta_aspect_ratio(76) = 0.9973, about 1.0; delta_aspect_ratio(45) =
  4.0000.
- slender_delta_kp(1.0) = 1.5708 = pi / 2; delta_kv(1.0) = 3.2175,
  delta_kv(0) = 3.14, delta_kv(4) = 3.45.
- Alpha 15, AR 1.0: CL_potential = 0.3793, CL_vortex = 0.2082,
  CL_total = 0.5875, with the vortex term 35.4% of the lift.
- Sweep at AR 1.0: CL(5) = 0.1602, CL(10) = 0.3601, CL(15) = 0.5875,
  CL(20) = 0.8281, CL(25) = 1.0661, monotone increasing.
- cd_due_to_lift(15 deg) = 0.5875 * tan(15) = 0.1574.
- AR 0.5, alpha 20: CL_total = 0.5866 with the vortex term 59.6% of
  the lift, about 60% against 35% for the AR 1 case at 15 deg.
- Crossing: AR 1.0 at 26.0 deg, AR 0.5 at 13.9 deg, the slender wing
  vortex dominated much earlier.
- Identity: CL(0) = 0 exactly.

## Verification

- Confirm delta_aspect_ratio(76) about 1.0 and delta_aspect_ratio(45)
  about 4.0, and that sweeps <= 0 or >= 90 deg raise ValueError.
- Confirm delta_kv anchors 3.14 at AR 0 and 3.45 at AR 4 with linear
  interpolation between.
- Confirm CL(0) = 0 exactly and CL positive and increasing over 5 to
  25 deg at AR 1.0.
- Confirm the vortex fraction grows as AR shrinks (AR 0.5 alpha 20
  about 60% against AR 1.0 alpha 15 about 35%).
- Confirm the crossing angle shrinks with AR, and that at the crossing
  angle the potential and vortex terms are equal.
- Confirm delta_lift_summary returns exactly its documented keys and
  identical floats run to run.
- Confirm ValueError rejection of non-physical inputs: sweep <= 0 or
  >= 90, aspect ratio < 0, kv <= 0 for the crossing angle.

## Related leaves

- aerodynamics/cfd/vortex-lattice-method: attached-flow linear sibling;
  this leaf covers the separated vortex regime it excludes.
- aerodynamics/high-lift/high-lift-systems: mechanical high-lift
  devices, the attached-flow alternative to vortex lift.
- aerodynamics/high-speed/swept-wing-aerodynamics: simple-sweep cosine
  corrections for attached subsonic swept wings.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_delta_wing_vortex_lift.py

The test covers the aspect ratio identity, the Kp and Kv anchors, the
AR 1 alpha 15 potential/vortex/total split (35.4% vortex), the 5 to
25 deg sweep values and monotonicity, drag due to lift, the AR 0.5
alpha 20 high-vortex-fraction case, the crossing angles at AR 1 and AR
0.5 with the potential-equals-vortex identity, summary-dict keys,
determinism, and ValueError rejection of non-physical inputs.

## Compliance

- NASA TN D-3767 (Polhamus 1966) is the primary methodology source,
  named and paraphrased (public-domain NTRS, reference-only, no
  reproduction). NACA Report 824 anchors the section-data context per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

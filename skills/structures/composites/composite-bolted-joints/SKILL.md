---
name: composite-bolted-joints
description: "Use when you must analyze a bolted joint in a composite laminate under bearing and bypass loading: compute the bolt bearing stress from the applied load, bolt diameter, and laminate thickness, the net-tension stress across the net section, the shear-out stress at the edge distance, and the joint margin against each allowable. Produces the applied stresses, the governing failure mode, the pass or fail verdict, and the margins for the fastener row with the bypass load share. Trigger: bolted joint, bearing stress, bypass loading, net-tension, shear-out, bolt diameter, edge distance, fastener, joint margin, composite laminate joint."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [composites, bolted-joints, bearing, bypass, net-tension, shear-out, fastener, joint-margin]
  version: 0.1.0
  author: AeroSkills
---

# Composite Bolted Joints (structures/composites/composite-bolted-joints)

Use when the task is analyzing a bolted joint in a composite
laminate: bearing and bypass loading, bolt bearing stress,
net-tension, shear-out, and joint margins.

## Domain quick reference

- A bolted joint transfers load through a fastener (bolt) of
  diameter D in a laminate of thickness t. The joint is sized
  against three local failure modes, each with its own allowable.
- Bearing stress: sigma_b = P_b / (D * t), where P_b is the load
  transferred through the bolt. The bearing allowable F_bru is the
  laminate or bolt bearing strength, whichever governs.
- Net-tension stress: sigma_nt = P / ((w - D) * t), where w is the
  joint width (or the tributary width per fastener, min(w, pitch)
  for a multi-fastener row). The net section w - D must be positive.
- Shear-out stress: sigma_so = P / (2 * e * t), where e is the edge
  distance from the hole center to the free edge in the load
  direction; two shear planes carry the load over length e.
- Bypass loading: with a bypass ratio r, the fraction of the total
  load carried around the hole through the laminate, P_bp = r * P
  and the bearing load P_b = (1 - r) * P. The net section still
  carries the full load P for a single fastener row.
- Joint margin: M = allowable / applied - 1. A margin of zero means
  the applied stress equals the allowable; negative margins fail.
- Joint efficiency: eta = (w - D) / w, the net-section to
  gross-section width ratio of the joint.
- Units are self-consistent (N, mm, MPa, or lbf, in, psi); stresses
  and allowables must share one unit system.

## Workflow

1. Collect the joint geometry and load: applied load P, bolt
   diameter D, laminate thickness t, joint width w, edge distance e,
   and pitch p when a fastener row is involved.
2. Split the load with bypass_split(P, r) when a bypass ratio is
   specified; otherwise the full load is bearing load.
3. Compute the three applied stresses: bearing_stress(P_b, D, t),
   net_tension_stress(P, w, D, t), shear_out_stress(P, e, t).
4. Compute the margins with margin_of(allowable, applied) against
   the bearing, net-tension, and shear-out allowables.
5. Use joint_analysis(...) for the one-shot report: stresses,
   margins, governing mode (lowest margin), pass or fail verdict,
   joint efficiency, and effective width.

## Pitfalls

- A bolt diameter at or above the joint width destroys the net
  section: the logic raises ValueError.
- A bypass ratio outside [0, 1] is physically impossible: the logic
  raises ValueError.
- Reading the margin sign backwards: positive margins pass, a
  negative margin is a failure in that mode.
- Using the gross width instead of the net section (w - D) for the
  net-tension stress, or forgetting the two shear planes (factor 2)
  in the shear-out stress.
- Mixing unit systems: stresses and allowables must be in the same
  units for the margins to mean anything.
- Applying the single-fastener formulas to a complex multi-row
  joint without checking the tributary width per fastener (pitch).

## Behavior contract (gate 3)

The bearing, bypass, net-tension, shear-out, and margin logic is
exercised by the gate 3 contract test: scripts/test_composite_bolted_joints.py
against scripts/composite_bolted_joints_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_composite_bolted_joints.py

## Compliance

- FAR-25 and CS-25 are referenced only as the certification context
  for structural joint substantiation; the formulas are standard
  mechanical joint analysis methodology (summary, no quoted text).
- compliance: STANDARDS-REF, gated: false.

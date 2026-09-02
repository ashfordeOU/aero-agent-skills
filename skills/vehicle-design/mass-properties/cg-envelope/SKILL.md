---
name: cg-envelope
description: "Use when you must analyze the center-of-gravity envelope of a vehicle: derive the cg station from component weights and arms, check the operating cg against the forward and aft limits, test an operating point against the envelope polygon in the cg versus weight plane, compute the static margin from the neutral point normalized by the mean aerodynamic chord, and track the cg excursion as the fuel burns between loading states. Produces the cg station, the limit verdict, the polygon membership with the violated limit, the static margin verdict, and the fuel-burn cg shift that gate the loading analysis. Trigger: cg envelope, static margin, neutral point, forward limit, aft limit, envelope polygon, cg excursion, fuel burn."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: mass-properties
  tags: [cg-envelope, static-margin, neutral-point, forward-limit, aft-limit, envelope-polygon, cg-excursion, fuel-burn]
  version: 0.1.0
  author: Aero Agent Skills
---

# CG Envelope (vehicle-design/mass-properties/cg-envelope)

Use when the task is center-of-gravity envelope analysis for a
vehicle: cg station from component weights and arms, forward and
aft limit checks, envelope polygon membership, static margin
against the neutral point, and the cg excursion as the fuel burns.

## Domain quick reference

- Center of gravity: x_cg = sum(w_i * x_i) / sum(w_i) over the
  components; the same rule applies to the z stations for the
  vertical cg.
- Forward and aft limits: the operating cg must satisfy
  forward_limit <= x_cg <= aft_limit; a cg ahead of the forward
  limit is a forward violation, behind the aft limit an aft
  violation.
- Envelope polygon: the allowed operating points (x_cg, weight)
  form a convex polygon; an operating point outside the polygon
  violates the forward or the aft limit at its weight.
- Static margin: SM = (x_neutral_point - x_cg) / MAC, with MAC the
  mean aerodynamic chord; a margin at or above the minimum
  (typically 0.05) passes.
- CG excursion: as fuel burns the total weight drops and the cg
  shifts; the excursion is the cg difference between the two fuel
  states, positive when the cg moves aft.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context
  for transport-category loading; the envelope and margin math is
  common mass-properties practice.

## Workflow

1. Collect component weights and stations: x arms for the
   longitudinal cg, z stations when the vertical cg matters.
2. Compute the cg with cg_position or cg_position_2d.
3. Check the operating cg against the forward and aft limits with
   cg_limits_verdict.
4. Test an operating point against the envelope polygon with
   point_in_envelope; read the violated limit from the verdict.
5. Compute the static margin from the neutral point with
   static_margin_verdict; confirm the margin against the minimum.
6. Track the loading states with cg_excursion to see how the cg
   moves as the fuel burns.
7. Confirm the deterministic checks with the contract test
   scripts/test_cg_envelope.py.

## Pitfalls

- Mismatched weights and arms lists producing a wrong cg.
- Zero total weight dividing by zero.
- Reversed forward and aft limits making every verdict fail.
- A non-convex or degenerate envelope polygon; the module raises
  ValueError because the boundary logic assumes a convex polygon.
- A zero or negative MAC in the static margin.
- Mixing stations: x arms for the longitudinal cg, z stations for
  the vertical cg.
- Reading the excursion sign backwards: shift = cg_after -
  cg_before, positive is aft.

## Behavior contract (gate 3)

The cg, limit, polygon, margin, and excursion logic is exercised by
the gate 3 contract test: scripts/test_cg_envelope.py against
scripts/cg_envelope_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_cg_envelope.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; the cg
  envelope and static margin relations are common mass-properties
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

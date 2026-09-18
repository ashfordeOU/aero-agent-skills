---
name: q40-operational-safety
description: "Evaluate the operational safety provisions of an ECSS-Q-ST-40C clause 6.6 programme: rank every declared control against the design-elimination to procedure-and-training precedence, refuse a catastrophic ground hazard resting on procedure alone, require a verification behind each control, compare the reaction time a mission-control constraint needs with the time the operator has, and report the hazardous phases - transport, handling, integration, launch-site work - left with no operation. Use when ground-operations hazards are controlled, a flight-operations constraint is written, or an operations readiness review asks whether the set is covered. Trigger: ecss, q-st-40c, ecss-operational-safety-constraint, ecss-ground-operations-hazard-control, mission-control-reaction-margin, hazard-control-precedence-rank, launch-site-handling-hazard."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-40c-safety-assurance-scope, q40-operational-safety, ecss-operational-safety-constraint, ecss-ground-operations-hazard-control, mission-control-reaction-margin, hazard-control-precedence-rank, launch-site-handling-hazard]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Operational Safety (space-systems/ecss/q40-operational-safety)

Use when the task is clause 6.6 of ECSS-Q-ST-40C: the hazards that belong to
operating the item rather than to its design, split between the ground set --
transport, handling, integration, launch-site work -- and the flight set,
where a mission-control constraint is only as good as the time it leaves the
operator.

## Domain quick reference

- The two sets carry different obligations. A ground operation is graded on
  whether personnel are protected by something stronger than a procedure; a
  flight constraint is graded on whether the reaction it demands fits inside
  the time available.
- Controls rank, they do not merely exist. Eliminating the hazard by design
  beats an engineered safety device, which beats a warning device, which
  beats procedure and training -- and the severity of the consequence fixes
  how far down that order the control is allowed to sit.
- A catastrophic hazard may not rest on a procedure. Procedures are obeyed by
  people under schedule pressure at a launch site, so the clause pushes the
  control up the order rather than adding another signature to the paperwork.
- A control with no verification is a claim. Every declared control carries
  the evidence that it is installed and works, and an unverified one is
  reported as open even when its type is strong enough.
- A zero reaction margin is not a pass. Needing exactly the time available
  means a single late detection breaks the constraint, so an exactly equal
  pair is a finding, recognised through a named tolerance rather than by
  shaving the required time.
- Coverage is separate from control quality. A phase the programme declared
  hazardous and then left with no operation at all is the gap that a
  per-operation review never shows, because there is no row to grade.

## Workflow

1. Refuse an operation record carrying an unknown key, an unknown phase,
   severity or control type, a blank hazard or a non-positive duration.
2. Sort each operation into the ground set or the flight set from its phase.
3. Rank the declared control and compare it with the weakest rank the
   severity allows; report an absent control outright.
4. Require a verification behind every declared control.
5. For a flight-phase constraint, compute the reaction margin and grade it
   positive, exhausted or negative; a constraint with no budget declared at
   all is itself a finding.
6. For a ground operation exposing personnel, require something stronger than
   procedure and training.
7. Compare the phases actually covered with the phases the programme declared
   hazardous and report each uncovered phase, then roll every finding up into
   one verdict.

## Pitfalls

- Accepting a procedure as a control because it is written and signed. The
  precedence rank, not the existence of paperwork, is what the severity is
  graded against.
- Grading flight constraints on the control type alone. A perfectly
  engineered constraint that needs more seconds than the pass allows is still
  a broken constraint.
- Rounding an exactly equal reaction pair into a pass. The equality is the
  worst case, not the boundary case, and it is reported.
- Reading a clean per-operation table as a covered programme. The phases with
  no rows at all never appear in that table.
- Applying the personnel-exposure rule to flight phases. Nobody is standing
  next to the item in orbit, and firing the rule there buries the ground
  findings it exists to raise.

## Behavior contract (gate 3)

The record validation, the ground and flight phase split, the control
precedence ranking against severity, the verification requirement, the
reaction-margin computation with its exhausted-margin tolerance, the
personnel-exposure rule and the declared-phase coverage check are exercised
by the gate 3 contract test: scripts/test_q40_operational_safety.py against
scripts/q40_operational_safety_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_operational_safety.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

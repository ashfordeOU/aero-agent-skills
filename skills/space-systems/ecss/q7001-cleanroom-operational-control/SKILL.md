---
name: q7001-cleanroom-operational-control
description: "Evaluate whether a clean-area work session is actually under control: gowning, materials, tooling, traffic and the headcount the ventilation can carry. Use when people, hardware and tools are about to enter a clean area and somebody must say whether the planned session holds the class or quietly breaks it. Computes occupant particle generation from the activity mix, converts it to a steady-state concentration against the air change rate and room volume, inverts that into the occupancy the room supports, names every garment the class demands and the wearer lacks, refuses fibre-shedding materials and tooling with no cleaning record, and flags defeated interlocks and excess transits. Trigger: ecss, q-st-70-01, cleanroom-operational-control, cleanroom-gowning-shortfall, cleanroom-occupancy-limit, cleanroom-material-restriction, airlock-interlock-discipline."
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
  tags: [ecss, q-st-70-cleanliness-control-scope, q7001-cleanroom-operational-control, cleanroom-operational-control, cleanroom-gowning-shortfall, cleanroom-occupancy-limit, cleanroom-material-restriction, airlock-interlock-discipline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Control — Clean-Area Operational Control (space-systems/ecss/q7001-cleanroom-operational-control)

Use when the task is running work inside a clean area rather than
certifying the empty room — sizing the session against what the
ventilation can carry, and checking the gowning, materials, tooling and
traffic discipline that decide whether the class survives the shift.

## Domain quick reference

- In an occupied clean area the occupants are the source. A certified
  room with a filtered supply contributes almost nothing; the people in
  it contribute nearly everything, so the session is sized on them.
- The rate depends on activity far more than on headcount. Standing
  still, working with the hands at a bench and moving about the room
  span two orders of magnitude, so a plan that counts bodies without
  naming what they are doing has not sized anything.
- Dilution is the only removal path. The room settles where generation
  equals the volume flow the air change rate and the room volume
  produce, and inverting that gives the occupancy the class can carry.
  It is routinely lower than the occupancy the floor area suggests, and
  that gap is where a certified room quietly runs out of class.
- Gowning belongs to the class, not to the habit of the team. The
  useful output is the garment a named person is missing, produced at
  the airlock, because a shortfall argued about after the session has
  already put the particles into the room.
- Materials are screened at the boundary. Fibre-shedding and abrading
  items - board, untreated foam, ordinary paper and pencils - are
  refused whatever they are wrapped in, because the shedding happens
  inside where nothing can be recovered.
- A tool with no cleaning record is refused however clean it looks. The
  record is the only part of the tool's condition that survives to the
  review, and a tool admitted without one contaminates the audit trail
  as well as the hardware.
- Traffic is part of the class. A defeated interlock or a transit rate
  above what the airlock was sized for unfilters the room for as long as
  it lasts, and neither shows up in a certificate taken last quarter.

## Workflow

1. Validate the area: class, threshold particle size, volume, air
   change rate and the transit rate the airlock was sized for.
2. Validate the session: occupants with unique identifiers and a known
   activity each, the materials and tooling proposed, the interlock
   discipline and the transit rate.
3. Sum occupant generation from the activity mix and divide by the
   removal flow to get the concentration the room settles at.
4. Compare that with the class ceiling, treating a value sitting on the
   ceiling as inside it rather than outside.
5. Invert the same relation at the heaviest activity present, with a
   safety factor, to get the occupancy the room supports, and compare
   it with the headcount actually planned.
6. Grade gowning against the class band and name the missing garments
   person by person.
7. Screen the materials against the refused list and the tooling
   against its cleaning records, naming what is refused and why.
8. Check the interlock and the transit rate, then report the verdict
   with every finding and the numbers behind it.

## Pitfalls

- Sizing a session by headcount alone. Three people at a bench and
  three people walking hardware across the hall are different rooms.
- Treating the room certificate as the operating condition. It was
  taken with nobody working, which is the one state the session is not
  in.
- Reporting a gowning failure as a count. "Two shortfalls" cannot be
  fixed at the airlock; "TECH-1 has no gloves" can.
- Admitting a tool because it looks clean. The missing record is the
  finding, and it is the finding that reappears at the review.
- Letting an interlock be defeated for a trolley. It is a few seconds
  of an unfiltered corridor feeding straight into the cleanest space in
  the building, and nothing afterwards records that it happened.

## Behavior contract (gate 3)

Removal flow, activity-based generation, the steady-state concentration
against the class ceiling, the inverted occupancy limit, per-person
gowning shortfalls by class band, refused materials, tooling without a
cleaning record, interlock discipline and the transit ceiling are
exercised by the gate 3 contract test:
scripts/test_q7001_cleanroom_operational_control.py against
scripts/q7001_cleanroom_operational_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_cleanroom_operational_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

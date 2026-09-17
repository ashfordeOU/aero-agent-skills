---
name: q60-class-2-ground-support-equipment-parts
description: "Determine which electronic parts inside ground support equipment sit within the Class 2 control boundary under clause 5.1.5 of ECSS-Q-ST-60C: walk each part's downstream chain to the flight connector, refuse a looping bench, break the chain only at a qualified isolation stage, grade what survives as direct or indirect, credit a verified protective element by exactly one obligation rung and never below the identity floor, then match obligations raised against evidence held and return the closure fraction over in-scope parts. Use when a Class 2 bench parts list, umbilical chain or test equipment control scope is in front of you. Trigger: ecss, q-st-60c, q60c2-gse-connection-directness, q60c2-gse-qualified-isolation-credit, q60c2-gse-protective-element-credit, q60c2-gse-obligation-tier, q60c2-gse-closure-fraction."
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
  tags: [ecss, q-st-60c, q-st-60c-eee-class-2-scope, q60-class-2-ground-support-equipment-parts, q60c2-gse-connection-directness, q60c2-gse-qualified-isolation-credit, q60c2-gse-protective-element-credit, q60c2-gse-obligation-tier, q60c2-gse-closure-fraction, q60c2-gse-control-scope-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Ground Support Equipment Parts Directly Connected to Class 2 Hardware (space-systems/ecss/q60-class-2-ground-support-equipment-parts)

Use when the task is clause 5.1.5 of ECSS-Q-ST-60C: electronic parts fitted
inside ground support equipment that is directly connected to Class 2 flight
hardware. This leaf decides, part by part, which of them sit inside that
boundary, how far back they sit, and what the Class 2 parts control therefore
obliges of each one.

## Domain quick reference

- The boundary is topological, not organisational. Ground equipment is not
  flight hardware, and the habit is to read that as an exemption for the whole
  rack. What actually decides is whether an electrical chain runs from the part
  to the flight connector. A regulator wired into a harness under test is
  inside; the same regulator powering the rack's cooling fan is not, and the two
  can sit in the same drawer.
- A bench is a graph and it has to be walked. A part three hops back still
  reaches the flight side, and a chain that loops is a modelling error the
  reviewer has to see rather than a walk to keep following. Counting the hops is
  what lets Class 2 do something Class 1 does not: a part on the connector and a
  part three hops behind it are both in scope, and they are not owed the same.
- Isolation breaks a chain only when the isolation itself was qualified. An
  opto-coupler or transformer nobody qualified is another component on the path;
  crediting it is how an exposed part vanishes from a parts list. The
  unqualified stage is worth reporting in its own right, because it looks like
  protection to everyone reading the schematic.
- A verified protective element is the Class 2 relief, and it is one rung, not
  an exemption. A fuse or current limiter that was actually verified moves the
  part one step down the obligation ladder; it never takes a connected part
  below its identity and its lot, because a part whose number nobody recorded
  cannot be traced after it fails no matter what stood in front of it.
- An unverified protective element earns nothing at all. It is the same object
  as the verified one on the drawing and a different object in the evidence
  file, and the drawing is what people read.
- Closure counts over obligations raised, not over parts. One connected part
  with four open items and nine untouched rack parts is not ninety percent
  controlled, and naming the governing part stops the average from hiding it.

## Workflow

1. Validate the bench topology: every node declares its kind and what it feeds,
   every downstream reference resolves, an isolation stage declares whether it
   was qualified, a protective element declares whether it was verified, the
   flight interface feeds nothing onward, at least one flight interface exists,
   and no chain loops.
2. Grade each part on the attributes without which it cannot be placed on that
   topology, and stop there when any is absent: an incomplete record is not a
   scope decision and must not be reported as one.
3. Walk the part's chain from its node onward without traversing a qualified
   isolation stage, taking the shortest surviving route so an alternative open
   path is never hidden by a stage standing on a longer one.
4. Grade the survivor by hop count: on the connector is direct, further back is
   indirect, reachable only through a qualified stage is outside the boundary,
   and no chain at all was never inside it.
5. Raise the obligation set that grade earns, scaled by whether the part can
   drive the flight side or only observe it, then apply at most one rung of
   credit for a verified protective element and stop at the identity floor.
6. Match evidence held against obligations raised on the obligation name,
   insensitive to case and padding, and name every item that has none.
7. Form the closure fraction over in-scope parts only, report the in-scope part
   carrying the most open items as the governing one, compare closure with the
   required level while absorbing representation error with a named tolerance,
   and return one bench verdict with findings ranked worst first.

## Pitfalls

- Exempting the rack because it stays on the ground. The clause is about what a
  fault inside a ground part can reach, and the answer is a property of the
  wiring, not of where the box sits.
- Treating direct and indirect as the same in-scope state. They are both inside
  the boundary and they are not owed the same evidence; collapsing them either
  over-demands from the back of the bench or under-demands at the connector.
- Crediting an isolation stage nobody qualified, or a protective element nobody
  verified. Both look like boundaries on the schematic and neither is one; the
  part stays in scope and the stage itself is a finding.
- Letting the protective-element credit run past one rung. Two rungs of relief
  on a sourcing part takes it below its own identity, and an untraceable part on
  the flight connector is the outcome the clause exists to prevent.
- Averaging closure across every part in the rack. Out-of-scope parts raise no
  obligations, and counting them as closed dilutes a real gap into a rounding
  difference.
- Widening the required closure so an exactly-met case passes. An equality at
  the boundary is a representation question, handled by the tolerance inside the
  comparison; the required level stays as agreed.

## Behavior contract (gate 3)

The topology validation, loop refusal, blocked-traversal chain walk, direct and
indirect grading, qualified isolation and protective-element credit with its
identity floor, evidence matching, closure over in-scope obligations,
governing-part selection and ranked findings are exercised by the gate 3
contract test:
`scripts/test_q60_class_2_ground_support_equipment_parts.py` against
`scripts/q60_class_2_ground_support_equipment_parts_logic.py` (stdlib unittest,
offline). Run:
`python3 scripts/test_q60_class_2_ground_support_equipment_parts.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

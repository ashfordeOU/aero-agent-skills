---
name: q60-class-1-ground-support-equipment-parts
description: "Determine which electronic parts inside ground support equipment are directly connected to Class 1 flight hardware under clause 4.1.5 of ECSS-Q-ST-60C: walk each part's downstream chain to the flight connector, refuse a looping bench topology, break the chain only at an isolation stage that is itself qualified, keep a part behind an unqualified stage inside the boundary, then raise on every connected part the parts-control obligations the flight programme carries and return the obligation closure fraction, the governing part and ranked findings. Use when a ground support equipment parts list, umbilical chain or test bench control scope is in front of you. Trigger: ecss, q-st-60c, q60-gse-direct-connection-path, q60-gse-isolation-stage-qualification, q60-gse-part-inherited-obligations, q60-gse-obligation-closure-fraction, q60-gse-control-scope-verdict."
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
  tags: [ecss, q-st-60-eee-components-scope, q-st-60c, q60-class-1-ground-support-equipment-parts, q60-gse-direct-connection-path, q60-gse-isolation-stage-qualification, q60-gse-part-inherited-obligations, q60-gse-obligation-closure-fraction, q60-gse-control-scope-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Ground Support Equipment Parts Directly Connected to Class 1 Hardware (space-systems/ecss/q60-class-1-ground-support-equipment-parts)

Use when the task is clause 4.1.5 of ECSS-Q-ST-60C: electronic parts fitted
inside ground support equipment that is directly connected to Class 1 flight
hardware. This leaf decides, part by part, which of them sit inside that
boundary, and what the flight programme's parts control therefore obliges of
each one.

## Domain quick reference

- The boundary is topological, not organisational. Ground equipment is not
  flight hardware, and the habit is to read that as an exemption for the whole
  rack. What actually decides is whether an electrical chain runs from the part
  to the flight connector. A regulator wired into a harness under test is
  inside; the same regulator powering the rack's cooling fan is not, and the
  two can sit in the same drawer.
- A bench is a graph, and it has to be walked rather than eyeballed. A part
  three hops back still reaches the flight side, and a chain that loops back on
  itself is a topology error the reviewer has to see, not a walk to keep
  following. Counting the hops is worth doing: the count is what tells a later
  reader why a part nobody thought about turned out to be in scope.
- Isolation only breaks a chain when the isolation itself has been qualified.
  An opto-coupler, a transformer or a series element that nobody qualified is
  simply another component on the path; crediting it is how an exposed part
  disappears from a parts list. The unqualified stage is worth reporting in its
  own right, because it looks like protection to everyone who reads the
  schematic.
- Obligations scale with what the part can do to the flight side, not with its
  price. A part that can source into flight hardware owes approval, lot
  traceability, derating evidence and a handling record. A part that can only
  observe still owes its identity and its lot, because a failure inside it can
  load or short the line it watches — but asking it for derating evidence it
  cannot need turns the control list into noise.
- Closure is counted over obligations raised, not over parts. One connected
  part with four open items and nine untouched rack parts is not ninety percent
  controlled, and naming the governing part stops the average from hiding it.

## Workflow

1. Validate the bench topology: every node declares its kind and what it feeds,
   every downstream reference resolves, an isolation stage declares whether it
   was qualified, the flight interface feeds nothing onward, and at least one
   flight interface exists.
2. Grade each part on the attributes without which it cannot be placed on that
   topology, and stop there when any is absent: an incomplete record is not a
   scope decision and must not be reported as one.
3. Walk the part's chain from its node onward, refusing a loop and refusing a
   chain longer than the topology guard allows.
4. Take the part out of scope only when the chain terminates away from the
   flight side, or when a qualified isolation stage stands on it. Record any
   unqualified stage on the chain as a separate finding rather than as credit.
5. For a part still in scope, raise the obligation set its drive capability
   earns, compare it against the evidence actually held — matching on the
   obligation name, insensitive to case and padding — and name every item that
   has none.
6. Form the closure fraction over the obligations raised across in-scope parts
   only, so a rack full of out-of-scope parts neither improves nor worsens it,
   and report the in-scope part carrying the most open items as the governing
   one.
7. Compare closure with the required level, absorbing floating-point
   representation error at the boundary with a named tolerance rather than by
   lowering the level, and return one bench verdict with findings ranked worst
   first.

## Pitfalls

- Exempting the rack because it stays on the ground. The clause is about what
  a fault inside a ground part can reach, and the answer is a property of the
  wiring, not of where the box sits.
- Crediting an isolation stage that was never qualified. It looks like a
  boundary on the schematic and is not one; the part behind it stays in scope
  and the stage itself is a finding.
- Judging scope by the immediate neighbour instead of walking the chain. A part
  two or three hops from the umbilical is as connected as one bolted to it.
- Averaging closure across every part in the rack. Out-of-scope parts raise no
  obligations, and counting them as closed dilutes a real gap into a rounding
  difference.
- Demanding the full obligation set from a part that can only observe. The set
  has to follow what the part can do to the flight side, or the list fills with
  items nobody can act on and the real ones stop being read.
- Widening the required closure so an exactly-met case passes. An equality at
  the boundary is a representation question, handled by the tolerance inside
  the comparison; the required level stays as agreed.

## Behavior contract (gate 3)

The topology validation, chain walk with loop refusal, qualified and
unqualified isolation handling, obligation inheritance by drive capability,
evidence matching, closure fraction over in-scope obligations, governing-part
selection and ranked findings are exercised by the gate 3 contract test:
`scripts/test_q60_class_1_ground_support_equipment_parts.py` against
`scripts/q60_class_1_ground_support_equipment_parts_logic.py` (stdlib
unittest, offline). Run:
`python3 scripts/test_q60_class_1_ground_support_equipment_parts.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q60-class-3-ground-support-equipment-parts
description: "Determine which electronic parts inside ground support equipment are directly connected to Class 3 flight hardware under clause 6.1.5 of ECSS-Q-ST-60C: walk each part's chain towards the flight interface, refuse a looping bench topology, break the chain only at an isolation stage whose own qualification is established, hold a part behind an unqualified or unassessed stage inside the boundary, raise the flight parts-control obligations on every connected part, then return the boundary, the governing part, the closure fraction and ranked findings. Use when a Class 3 test bench parts list, umbilical chain or control-scope review is in front of you. Trigger: ecss, q-st-60c, q60-class-3-ground-support-equipment-parts, q60-c3-gse-direct-connection-chain, q60-c3-gse-isolation-stage-qualification, q60-c3-gse-inherited-control-obligations, q60-c3-gse-obligation-closure-fraction, q60-c3-gse-governing-part."
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
  tags: [ecss, q-st-60-eee-components-scope, q-st-60c, q60-class-3-ground-support-equipment-parts, q60-c3-gse-direct-connection-chain, q60-c3-gse-isolation-stage-qualification, q60-c3-gse-inherited-control-obligations, q60-c3-gse-obligation-closure-fraction, q60-c3-gse-governing-part]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Ground Support Equipment Parts Connected to Class 3 Hardware (space-systems/ecss/q60-class-3-ground-support-equipment-parts)

Use when the task is clause 6.1.5 of ECSS-Q-ST-60C: deciding which electronic
parts sitting inside ground support equipment are close enough to Class 3
flight hardware that the flight programme's parts control reaches them. The
question is answered by the connection chain, not by which cabinet a part is
screwed into.

## Domain quick reference

- Direct connection is a property of the path, not of the label on the box. A
  part two hops back down a harness that reaches the flight connector with
  nothing in between is connected; a part sitting in the same rack whose chain
  ends elsewhere is not. Walking the chain is the only way to tell them apart,
  and it is the step benches usually skip.
- Only an isolation stage whose own qualification is established breaks the
  chain. A stage that is unqualified passes the connection straight through,
  and — the case that gets waved past — so does a stage nobody has assessed.
  An unassessed stage is an open question, never evidence of isolation, and
  treating it as a boundary quietly drops everything behind it out of scope.
- A bench that loops back on itself has no walkable chain. That is an input
  error in the topology description and has to be refused as one; reporting
  the looping parts as merely unconnected turns a modelling mistake into a
  clean sheet.
- A chain ending on a node the bench never declares is a third outcome again.
  It is neither connected nor isolated: nobody knows what is on the far end,
  so it is reported rather than resolved either way.
- The governing part is the connected part fewest hops from the flight
  interface. It is the one whose failure reaches the hardware with the least
  in the way, and it is what the control scope should be argued around.
- Closure is a fraction over every obligation the boundary raises, not a count
  of parts with some paperwork. A part with no parts-control record at all is
  a different finding from one with a record that still has items open, and
  the two need different corrections.

## Workflow

1. Validate the topology: every part names the node it connects towards, and
   every isolation stage names both its onward node and the state of its own
   qualification. A node used as both a part and a stage is an input error.
2. Walk each part's chain towards the flight interface, following parts and
   passing through any stage that is not qualified. Refuse the whole input if
   the walk revisits a node.
3. Record the outcome of each walk as one of three things: it reaches the
   flight interface, it is broken by a qualified stage, or it dangles on an
   undeclared node.
4. Keep the parts that reach the interface. Note their hop distance and note
   every unassessed stage the walk passed through, because each one is a
   boundary that has not been earned.
5. Take the connected part with the fewest hops as the governing part, breaking
   a tie on the identifier so the result is stable.
6. Raise the flight parts-control obligations on every part inside the
   boundary, separate a part with no record from a part with open items, and
   compute the closure fraction over the whole boundary.
7. Compare the closure with the agreed level, absorbing floating-point
   representation error at the boundary with a named tolerance rather than by
   lowering the level, and return one verdict with findings ranked worst first.

## Pitfalls

- Reading the cabinet a part sits in as the answer. Only the chain decides,
  and a bench drawing is not a chain until it has been walked.
- Letting an unassessed isolation stage act as a boundary. It is the most
  effective way to make a control scope look small, and it is not supported by
  anything: the stage's own qualification is exactly what is missing.
- Reporting a looping topology as a set of unconnected parts. The loop is a
  defect in the description of the bench; answering it as a result hides the
  defect and produces a scope nobody can rely on.
- Collapsing a dangling chain into "not connected". An undeclared far end is
  unknown, not absent, and the bench owner is the only one who can close it.
- Counting parts that hold some record as closed. Closure is over obligations,
  and a part missing one item is not the same as a part missing all of them.
- Widening the required closure so an exactly-met bench passes. An equality at
  the boundary is a representation question handled by the tolerance inside the
  comparison; the agreed level stays where it was agreed.

## Behavior contract (gate 3)

The topology validation, chain walk with loop refusal, qualified-stage break,
unassessed-stage retention, dangling-chain outcome, governing-part selection,
inherited obligation raising, closure fraction and ranked findings are
exercised by the gate 3 contract test:
`scripts/test_q60_class_3_ground_support_equipment_parts.py` against
`scripts/q60_class_3_ground_support_equipment_parts_logic.py` (stdlib
unittest, offline). Run:
`python3 scripts/test_q60_class_3_ground_support_equipment_parts.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

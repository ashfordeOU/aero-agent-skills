---
name: q60-class-3-parts-control-organization
description: "Identify the unit accountable for electronic part control on a class 3 programme under ECSS-Q-ST-60C clause 6.1.2.1: refuse a candidate the project organization never declared, one naming no accountable role, one not holding part selection approval, one sitting inside the design authority, one whose escalation path passes the ceiling and one whose mandate sits below the floor under a named tolerance; name every function nobody holds and every function two units claim; then nominate on mandate, escalation path and unit identifier. Use when a thin class 3 parts function has to become one named accountable unit. Trigger: ecss, q-st-60c-clause-6-1-2-1, class-3-part-control-accountability, part-control-mandate-share-floor, part-control-escalation-depth-ceiling, contested-part-control-function, unassigned-part-control-function."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q60-class-3-parts-control-organization, q-st-60c-clause-6-1-2-1, class-3-part-control-accountability, part-control-mandate-share-floor, part-control-escalation-depth-ceiling, contested-part-control-function, unassigned-part-control-function]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 3 — Part Control Accountability (space-systems/ecss/q60-class-3-parts-control-organization)

Use when the task is clause 6.1.2.1 of ECSS-Q-ST-60C: naming the unit
accountable for the electronic part control activities of a class 3 programme.
This leaf turns a declared project organization into one named accountable
unit, or into the reason no unit can be named.

## Domain quick reference

- Accountability is a name, not a box on a chart. A unit the project
  organization document never declared cannot be held to anything, however
  busy it is, and a unit with no accountable role named holds the mandate
  nowhere a reviewer can reach.
- Approving what goes into the equipment is the function that cannot be
  delegated away. A unit holding every other part control function and not
  that one is a support function, not the accountable unit.
- Independence from the design authority is what makes the mandate real. A
  part control unit reporting into the people choosing the parts records the
  choice rather than controlling it.
- The escalation path is part of the mandate. A unit that has to climb four
  levels to stop a procurement holds an authority it cannot exercise inside
  the time a part decision allows.
- A thin class 3 function is expected to combine duties, so the test is the
  share of the mandate one unit carries, not whether it does nothing else.
- A function nobody holds and a function two units both claim fail in
  different directions and neither is visible from a chart. The first leaves
  the work undone; the second leaves two people each assuming the other did it.
- The nomination has to be deterministic. Largest mandate, then the shorter
  escalation path, then the lower unit identifier, so the same organization
  always names the same unit.

## Workflow

1. Read each candidate's declared part control functions in report order,
   keeping names the programme does not recognise visible.
2. Take each candidate's mandate as the share of the part control functions it
   holds.
3. Test every candidate for admissibility: declared in the project
   organization, an accountable role named, part selection approval held, no
   unrecognised function, a stated escalation depth inside the ceiling,
   independence from the design authority and a mandate at or above the floor
   under the stated tolerance.
4. Name every function no declared unit holds and every function more than one
   declared unit claims.
5. Nominate the accountable unit from the admissible candidates: largest
   mandate, ties broken by the shorter escalation path and then by the lower
   unit identifier.
6. Return one disposition: accountability-assigned, accountability-split when
   two units claim the same function, or accountability-unassigned when a
   function is unheld or no candidate is admissible.

## Pitfalls

- Naming the unit that does the work rather than the unit the project declared.
  An undeclared team can be told to stop and has nothing to answer with.
- Reading combined duties as a disqualification. A class 3 programme is thin by
  design, and one unit carrying several duties is the expected shape.
- Nominating a unit without part selection approval because its mandate looks
  large. Everything else can be supported; the approval cannot be borrowed.
- Ignoring where the unit reports. A part control function inside the design
  authority approves its own choices and the record shows no disagreement
  because none was possible.
- Treating the escalation path as an organizational nicety. The path is the
  response time on a procurement that has already started.
- Declaring the mandate placed while a function sits with nobody. The chart
  looks complete and the alert nobody owns arrives anyway.
- Leaving two units on the same function as harmless redundancy. Shared
  accountability is the condition where each assumed the other had it.

## Behavior contract (gate 3)

The function ordering, mandate share, per-unit admissibility defects, the
unheld and contested function lists, the deterministic nomination and the
accountability disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_3_parts_control_organization.py against
scripts/q60_class_3_parts_control_organization_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_parts_control_organization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

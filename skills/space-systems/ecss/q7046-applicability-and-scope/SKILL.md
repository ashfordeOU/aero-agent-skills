---
name: q7046-applicability-and-scope
description: "Determine whether a procured item falls under the threaded-fastener requirements of ECSS-Q-ST-70-46, and which clause groups it then owes. Use when a procurement or parts-control question turns on whether the standard bites: take the verdict from the item kind first, so a bolt, screw, stud or threaded insert is in and a rivet or plain pin never is while a nut rides in only inside a procured set, then from the application, parse the metric thread designation, and derive the clause groups from the criticality and the size rather than handing every item a full programme. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-standard-applicability, fastener-scope-decision, metric-thread-designation-parsing, small-size-fastener-reduced-set, fastener-clause-group-derivation."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-applicability-and-scope, fastener-standard-applicability, fastener-scope-decision, metric-thread-designation-parsing, small-size-fastener-reduced-set, fastener-clause-group-derivation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Applicability and Scope (space-systems/ecss/q7046-applicability-and-scope)

Use when the task is the applicability clause of ECSS-Q-ST-70-46:
deciding whether a particular procured item is a threaded fastener the
standard controls, and if it is, which of its clause groups that item
actually owes.

## Domain quick reference

- The item kind decides first. Bolts, screws, studs and threaded inserts
  are what the standard is written about. Rivets, plain pins, clamps,
  clips and bonded or welded studs carry no thread the standard can
  control, and no amount of criticality brings them in.
- Nuts, washers and locking elements are the awkward middle. They are in
  scope as members of a procured fastener set and out of scope bought
  loose, because the requirements are written against the set the joint
  is made from rather than against the part in isolation.
- The application decides second. Flight hardware is in. Ground support
  equipment and test rigs are out unless the item sits in a load path
  flight hardware depends on, which is the case people miss: a lifting
  fitting bolt is ground equipment and it can drop a spacecraft.
- Both gates have to pass. An in-scope kind on out-of-scope hardware is
  out, and the record says which gate closed it, because the two are
  appealed in completely different ways.
- Size decides what an in-scope item owes, not whether it is in. Below
  the small-size threshold the destructive part of a test programme
  consumes the part, so acceptance rests on process control and
  inspection instead, and that is a reduced set rather than a waiver.
- Criticality trims the same list from the other end. A minor item does
  not owe a qualification test programme; it still owes specifications,
  materials, manufacturing, procurement, inspection, acceptance,
  application, storage and records.
- A missing thread designation is a finding, not a refusal. The scope
  verdict does not depend on it; only the reduced-set question does, and
  saying so is more useful than declining to answer.

## Workflow

1. Take the item kind and produce its verdict, with the set-membership
   flag deciding the nut, washer and locking-element case.
2. Take the application and produce its verdict, with the flight-load
   flag deciding the ground-support case.
3. Combine: out at either gate is out, and record both reasons whichever
   way the verdict fell.
4. Parse the thread designation where one is given, taking the coarse
   pitch from the table when no pitch is stated and refusing a diameter
   the table does not carry unless the pitch is stated explicitly.
5. Derive the clause groups from the verdict, the criticality and the
   small-size flag, in the order the standard works through them.
6. Report the verdict, both gate verdicts, the reasons, the parsed
   thread, the clause groups and the findings.

## Pitfalls

- Letting the application gate pass because the part is a flight-grade
  bolt. Grade is a property of the part; scope follows the hardware it
  is installed on and the load path it sits in.
- Excluding ground support equipment as a category. The flight-load
  exception is the whole reason the gate is not a single lookup.
- Treating a small fastener as exempt. The size reduces what can be
  tested, not what the item is; procurement, records and inspection
  survive intact, and calling it a waiver removes them.
- Handing a minor item a full qualification programme because it is in
  scope. Scope and requirement depth are two decisions, and collapsing
  them costs a supplier a test campaign nobody asked for.
- Assuming the coarse pitch for a diameter the table does not carry. An
  invented pitch propagates into stress area and preload downstream, so
  an untabulated size has to state its pitch.
- Reporting one reason. A reader who sees only the kind reason will
  appeal the kind, and the application gate will close the item again.

## Behavior contract (gate 3)

The kind gate with its set-membership case, the application gate with
its flight-load exception, the combined verdict, the metric designation
parser with its coarse-pitch table and its refusals, the small-size
threshold and the criticality-and-size clause-group derivation are
exercised by the gate 3 contract test:
scripts/test_q7046_applicability_and_scope.py against
scripts/q7046_applicability_and_scope_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_applicability_and_scope.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q7046-manufacturing-process-control
description: "Audit the manufacturing route of a threaded fastener and the capability of the processes on it, from blank making through heat treatment, threading and final inspection. Use when a traveller or a process change has to be judged before parts are run: hold the route to the canonical order so an operation cannot be swapped with the one it would undo, add the operations the property class and the plating route make mandatory, hold the relief bake to its window after plating, grade every controlled characteristic on the distance from its mean to the nearer window edge in three standard deviations, and retire a qualification whose parameter has drifted past tolerance. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-route-operation-order, fastener-mandatory-operation-set, fastener-process-capability-grading, fastener-process-requalification-trigger, fastener-relief-bake-window."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-manufacturing-process-control, fastener-route-operation-order, fastener-mandatory-operation-set, fastener-process-capability-grading, fastener-process-requalification-trigger, fastener-relief-bake-window, fastener-shop-order-rollup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Manufacturing Process Control (space-systems/ecss/q7046-manufacturing-process-control)

Use when the task is the manufacturing clause of ECSS-Q-ST-70-46 --
judging the route a fastener is made by, the operations that route has
to contain, and whether the processes on it are holding their
characteristics or merely being inspected after the fact.

## Domain quick reference

- A route is an ordered sequence, not a set of operations. Every
  admitted operation carries a position in the canonical order, and
  the declared route has to run non-decreasing through those
  positions, because the pairs that destroy each other when swapped
  are exactly the pairs that look interchangeable on a traveller.
- Blank making is a fork, not a step. Cold heading and hot forging
  occupy the same position, so either may appear, but an operation
  placed before its predecessor is an error of sequence whatever the
  shop's reason.
- Which operations are mandatory follows from the property class and
  the finish route, not from habit. A quenched and tempered class owes
  a heat treatment. An electroplated part owes a surface treatment and
  the relief bake after it. Every route owes a final inspection.
- The relief bake is a window, not a task. Hydrogen keeps diffusing
  from the moment the part leaves the tank, so a bake started late is
  a different operation from a bake started promptly, and the record
  carries the delay rather than a tick.
- A process is controlled when its characteristic sits inside its
  window with capability to spare. Capability is the distance from the
  process mean to the nearer window edge measured in three standard
  deviations, which is what separates a centred process with a wide
  spread from an off-centre process with a narrow one.
- Capability grades into three bands, not two. Above the capable floor
  the process runs; between the marginal and capable floors it runs
  under increased sampling; below the marginal floor the process is
  not holding the characteristic at all, and the inspection downstream
  is sorting rather than controlling.
- A qualified process is qualified at its parameters. A proposed
  change past the declared tolerance on any qualified parameter
  retires the qualification, and that is stated before the first part
  is run, not after the lot is rejected.

## Workflow

1. Validate the declared route against the canonical order and reject
   a repeated or reversed operation rather than reading past it.
2. Derive the mandatory operations from the property class and the
   plating route, and list every one the traveller leaves out.
3. Where the part is plated, take the relief bake delay and compare it
   against the window, reporting the overrun rather than a pass.
4. For every controlled characteristic, check the mean is inside its
   window first, then grade the capability index into the three bands.
5. Compare each qualified parameter against its proposed value and
   name the operations whose qualification the change retires.
6. Take the worst characteristic as the route disposition and the
   worst route as the shop-order disposition, then list the
   uncontrolled parts and the parts owing a requalification.

## Pitfalls

- Reading a traveller as a checklist. Every mandatory operation can be
  present and the route still be wrong, because the damage lives in
  the order: a thread formed before the hardening it was sized for is
  a conforming operation in the wrong place.
- Treating the relief bake as a task with a tick box. The diffusion
  starts when the part leaves the tank, so a bake run a shift later
  has not done the same job, and a record with no delay on it cannot
  show which it was.
- Grading capability on the spread alone. A narrow process parked
  against one window edge passes a spread check and puts half its
  output over the line the moment it drifts.
- Collapsing capability into pass and fail. The marginal band is the
  one that carries information, and folding it into either neighbour
  either stops a usable process or lets a drifting one run
  unsampled.
- Treating a parameter change as a shop decision. The qualification
  was earned at a parameter set, and a change past tolerance retires
  it whether or not the parts look the same.
- Comparing a capability index or a drift fraction against its floor
  by bare arithmetic. Both are quotients of measured floats, so a case
  exactly on a floor can land a few units in the last place under it;
  the comparison absorbs that while the floor stays untouched.

## Behavior contract (gate 3)

The canonical route ordering, mandatory-operation derivation, relief
bake window, capability index and three-band grading, requalification
trigger, route assessment and shop-order roll-up are exercised by the
gate 3 contract test:
scripts/test_q7046_manufacturing_process_control.py against
scripts/q7046_manufacturing_process_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7046_manufacturing_process_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

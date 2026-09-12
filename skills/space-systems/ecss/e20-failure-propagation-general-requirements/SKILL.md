---
name: e20-failure-propagation-general-requirements
description: "Use when verify that a single hardware fault inside one spacecraft electrical item cannot spread to a neighbouring circuit, component or interface under ECSS-E-ST-20C clause 4.2.1.1: categorize each postulated fault mode into its propagation family (conducted overcurrent, conducted overvoltage, loss of continuity, dielectric breakdown), enumerate the coupling paths tying the faulted item to each neighbour, credit a declared containment barrier only where it covers that family on that path, and size the series protection device so it clears before the upstream source current-limits. Trigger: ecss, e-st-20-electrical-scope, fault-propagation, fault-containment, single-fault-tolerance, protection-selectivity, coupling-path, containment-barrier, electrical-fault-isolation."
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
  tags: [ecss, e-st-20-electrical-scope, e20-failure-propagation-general-requirements, fault-propagation, fault-containment, single-fault-tolerance, protection-selectivity, containment-barrier]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Design — Failure Propagation, General Requirements (space-systems/ecss/e20-failure-propagation-general-requirements)

Use when the task is the single-fault containment argument of
ECSS-E-ST-20C clause 4.2.1.1 -- showing that one hardware fault in an
electrical item stays inside that item and does not propagate into a
neighbouring circuit, component or interface, either by a conducted
path, by a loss of continuity shared with a neighbour, or by a
dielectric or thermal coupling.

## Domain quick reference

- A containment argument is made per (fault mode, coupling path,
  neighbour) triple, not per item. The fault mode is first reduced to
  its propagation family, because a barrier that stops one family is
  transparent to another: conducted overcurrent (short to ground,
  short to supply, pin-to-pin short, shorted part), conducted
  overvoltage (regulator runaway, transient overvoltage), loss of
  continuity (open circuit, connector disconnect, broken
  interconnect), and dielectric breakdown (insulation breakdown,
  surface arc tracking).
- The coupling paths recognised by this leaf are the ones a
  neighbouring item actually shares with the faulted item: shared
  power bus, shared return path, harness adjacency, common connector
  pin, shared signal net, and thermal coupling. A neighbour that
  shares none of these has no propagation route and is not part of
  the argument.
- A barrier is credited only where it covers both the family and the
  path. A series protection device interrupts conducted overcurrent
  on the bus and on a common pin but does nothing for a loss of
  continuity; a dedicated return removes the shared-return path but
  not harness adjacency; galvanic isolation cuts conducted and
  dielectric coupling across a signal net or connector pin;
  a clamping network addresses overvoltage, not overcurrent; physical
  separation addresses adjacency and dielectric coupling; a redundant
  supply branch is the only provision that contains a loss of
  continuity. Crediting a barrier outside its coverage is the most
  common way a containment argument fails review.
- Containment by a series protection device is also a sizing problem,
  not just a topology one. The device rating must sit above the
  neighbour's steady demand by a load margin (so it does not nuisance
  trip) and below the upstream source's current limit by a clearing
  margin (so the device, not the source, clears the fault). If the
  source current-limits first, every load on that bus browns out and
  the fault has propagated despite the barrier being present.

## Workflow

1. List each fault mode postulated for the item and map it to its
   propagation family; reject an unrecognised fault mode before it
   enters the argument.
2. List each neighbouring item and the coupling path it shares with
   the faulted item; reject an unrecognised path. Drop neighbours
   with no shared path.
3. For every (fault mode, path) pair, test the declared barrier set:
   the pair is contained when at least one barrier covers that family
   on that path. Record the crediting barrier by name.
4. Record every uncontained pair as a propagation finding naming the
   fault mode, the family, the path and the neighbour.
5. Where a series protection device is credited, evaluate its
   selectivity: rating over steady demand against the load margin,
   and source current limit over rating against the clearing margin.
   A device failing either check is a protection finding even though
   the topology check passed.
6. The item is single-fault contained only when the propagation list
   and the protection list are both empty.

## Pitfalls

- Crediting one barrier for the whole item. Coverage is per family
  and per path; a fuse on the power feed says nothing about a
  pin-to-pin short into a neighbour's connector or an arc across an
  adjacent harness run.
- Treating a loss of continuity as self-contained. An open circuit in
  a shared feed propagates as loss of function to every item on that
  feed; only a redundant branch contains it, and the check must be
  run, not assumed.
- Passing the topology check and skipping the sizing check. A
  correctly placed protection device whose rating exceeds the
  upstream current limit never clears, and the source limits instead
  -- the fault reaches every neighbour on the bus.
- Setting the protection rating just above the steady demand with no
  load margin, producing nuisance trips that are then removed in
  operations, silently deleting the barrier the argument rests on.
- Leaving a neighbour out of the list because it is in a different
  unit. Adjacency and connector sharing cross unit boundaries; the
  argument is over shared paths, not over boxes.

## Behavior contract (gate 3)

The fault-family mapping, barrier-coverage, propagation-containment
and protection-selectivity logic is exercised by the gate 3 contract
test: scripts/test_e20_failure_propagation_general_requirements.py
against scripts/e20_failure_propagation_general_requirements_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e20_failure_propagation_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

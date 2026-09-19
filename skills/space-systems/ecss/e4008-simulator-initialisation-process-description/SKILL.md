---
name: e4008-simulator-initialisation-process-description
description: "Audit a simulator initialisation process description against the eleven normative items of ECSS-E-ST-40-08C clause 4.4.3. Use when the written initialisation sequence is reviewed before a simulator is accepted: confirming the phases are declared as an ordered sequence with identifiers used once and stated entry and exit conditions, ordering the declared dependencies and reporting a cycle instead of guessing, enforcing the platform precedences so instances are created before links resolve, links resolve before fields are configured, fields are configured before entry points are registered and the schedule is armed only after initialisation, and confirming the terminal phase names its standby state. Trigger: ecss, e-st-40-08c, simulator-initialisation-process, initialisation-phase-ordering, initialisation-entry-exit-conditions, initialisation-precedence-rules, initialisation-dependency-cycle, simulator-standby-state-declaration."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-simulator-initialisation-process-description, simulator-initialisation-process, initialisation-phase-ordering, initialisation-entry-exit-conditions, initialisation-precedence-rules, initialisation-dependency-cycle, simulator-standby-state-declaration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling Platform — Simulator Initialisation Process Description (space-systems/ecss/e4008-simulator-initialisation-process-description)

Use when the task is the initialisation process description of
ECSS-E-ST-40-08C clause 4.4.3 -- grading the written account of how a
simulator gets from a loaded assembly to the state it waits in, against
the eleven items the clause carries. Everything here is answerable from
the description; nothing needs the simulator to be run.

## Domain quick reference

- The eleven items fall into three groups. Six are about the document:
  an ordered sequence of phases, identifiers used once, an entry
  condition and an exit condition on every phase, dependencies that
  name phases that exist, and a dependency set that is acyclic and
  consistent with the order as written. Four are the precedences the
  platform imposes. The last is where the process ends.
- The four platform precedences are the substance: instances are
  created before links are resolved, links are resolved before fields
  are configured, fields are configured before entry points are
  registered, and the schedule is armed only after every instance has
  reported initialised. Each is graded on its own, so a description
  that gets three right and one wrong says which one.
- A precedence is checked on spans, not on single positions. If a kind
  of phase appears more than once, the last occurrence of the earlier
  kind has to sit before the first occurrence of the later kind, or
  some part of the later work runs against a state that is still being
  built.
- A dependency cycle is not a deep order, it is no order. The
  dependency walk reports the phases it could not place rather than
  inventing a sequence, because any sequence it invented would be a
  guess the description does not support.
- The declared order and the dependency graph are two separate claims,
  and both are graded. A phase listed before something it depends on
  is a description defect even when the graph itself is acyclic: a
  reader following the document top to bottom would perform the phases
  in an order the dependencies forbid.
- A supporting activity -- loading datasets, opening a log, attaching
  an external interface -- is a legitimate phase kind that participates
  in the sequence without taking part in the four precedences. It is
  ordered by its own dependencies and nothing else.
- The terminal phase has one job beyond being last: naming the state
  the simulator is left in. A description that ends without naming its
  standby state leaves the operator with no defined condition to check
  before commanding a run.

## Workflow

1. Normalize every phase: a legal identifier, a declared kind, a
   dependency list of legal identifiers, and no phase depending on
   itself.
2. Grade the document items: the sequence flag and a phase count above
   one, identifiers used once, an entry condition and an exit condition
   stated on every phase, and dependencies that resolve.
3. Order the phases by dependency. Report a cycle as a cycle, naming
   the phases that could not be placed, and separately report any
   phase listed ahead of something it depends on.
4. Take the first and last declared position of each phase kind, and
   grade the four platform precedences on those spans, reporting a
   missing kind as a failure of the precedence that needed it.
5. Grade the terminal phase: it has to be the standby declaration, and
   it has to name the standby state.
6. Report all eleven items with their own verdicts, count the satisfied
   ones, and roll them into one verdict plus the standby state the
   description commits to.

## Pitfalls

- Grading the description against a simulator that starts successfully.
  A missing precedence does not fail loudly; it produces a simulator
  that works wherever the enumeration order happened to match and stops
  working on the next machine or the next build of the same one.
- Treating a missing phase kind as neutral. A description with no
  link-resolution phase has not satisfied the creation-before-linking
  precedence in some weaker sense -- it has failed it, because the work
  the precedence governs is not described at all.
- Checking a precedence on first occurrences only. A second instance
  creation phase inserted after linking is exactly the defect the
  precedence exists to catch, and it is invisible unless the last
  occurrence is the one compared.
- Sorting the phases into an order the description does not declare.
  The declared order is one of the eleven claims being graded;
  reordering it to make the dependencies work grades a document nobody
  wrote.
- Reporting a dependency cycle as an ordering failure and moving on.
  The cycle blocks every downstream question about sequence, so the
  phases that could not be placed are named, and the order is reported
  as absent rather than as a partial list.
- Accepting a terminal phase that is last but unnamed. Being last makes
  it terminal; naming the standby state is what makes the end of the
  process checkable by whoever operates the simulator.

## Behavior contract (gate 3)

The phase validation, duplicate-identifier and unknown-dependency
detection, dependency ordering with cycle reporting, declared-order
violation detection, kind-span precedence checks, terminal-phase and
standby-state grading and the eleven-item roll-up are exercised by the
gate 3 contract test:
scripts/test_e4008_simulator_initialisation_process_description.py
against
scripts/e4008_simulator_initialisation_process_description_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e4008_simulator_initialisation_process_description.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

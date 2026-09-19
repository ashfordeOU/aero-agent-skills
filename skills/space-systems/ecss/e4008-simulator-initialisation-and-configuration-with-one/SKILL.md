---
name: e4008-simulator-initialisation-and-configuration-with-one
description: "Verify that a simulator holding a single Schedule was initialised and configured the way ECSS-E-ST-40-08C clause 5.5.2 requires. Use when the task is walking the build, connect, initialise and standby states once each and in order, confirming that exactly one Schedule service is registered rather than none or a pair, proving every configuration write landed before the model tree was published, and posting the initialisation entry points in a dependency order that repeats run after run. Grades a run against the four normative items. Trigger: ecss, e-st-40-08c, simulator-state-sequence, single-schedule-service, simulator-configuration-window, initialisation-entry-point-order, late-configuration-write, model-tree-publication."
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
  tags: [ecss, e-st-40-08-simulation-scope, e4008-simulator-initialisation-and-configuration-with-one, simulator-state-sequence, single-schedule-service, simulator-configuration-window, initialisation-entry-point-order, late-configuration-write]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Infrastructure — Initialisation and Configuration with One Schedule (space-systems/ecss/e4008-simulator-initialisation-and-configuration-with-one)

Use when the task is the start-up path of ECSS-E-ST-40-08C clause 5.5.2
-- the states a simulator holding a single Schedule passes through
between creation and the point it can be told to run, and what may still
be written to the model tree along the way. The clause carries four
normative items and a run is graded against all of them.

## Domain quick reference

- The start-up walk is fixed: build the tree, connect the models to the
  infrastructure services, run the initialisation entry points, then sit
  in standby. Each state is entered once, and the order is the order the
  models were written to expect.
- A single Schedule is the reproducibility guarantee. Two Schedule
  services means two posting queues, and the interleaving between them
  is decided by registration accident rather than by the design; zero
  means the initialisation entry points have nowhere to be posted at
  all, so the run silently skips them.
- Publication of the model tree closes the configuration window. Up to
  that point a field write reaches every reader; after it, the models
  that already latched the field hold the previous value and the write
  produces two versions of one number inside one run.
- Initialisation entry points carry a priority, but priority is a
  preference, not an ordering constraint. A dependency outranks it: an
  entry point that needs another to have run cannot be posted first
  however low its priority number is.
- Two entry points on the same priority still need a deterministic
  order, and declaration order supplies it. Leaving the tie to the
  container's iteration order is what makes a scenario replay differ
  from the run it is meant to reproduce.
- A late write and a missing state are different defects with the same
  symptom: a model that reads a value nobody expected. Grading them
  separately is what lets the finding point at the cause.

## Workflow

1. Collect the observed state walk and compare it with the required
   sequence: every state present, entered once, and in order. Report a
   foreign state rather than folding it into the nearest neighbour.
2. Tally the registered services and count the Schedule ones. Report the
   names when there is more than one, because the finding has to say
   which pair of queues is competing.
3. Grade every configuration write by the state it happened in. A write
   inside the build state is applied; anything later is a late write and
   names the field it corrupted.
4. Validate the initialisation entry points: unique names, integer
   priorities, declared dependencies that exist, and no cycle.
5. Produce the required posting order by a deterministic topological
   walk -- ready entry points sorted by priority, ties broken by
   declaration order -- and compare it with the order actually posted.
6. Grade the four normative items and report the findings with the
   offending state, service, field or entry point named, not a bare
   pass or fail.

## Pitfalls

- Reading a repeated state as harmless. Entering the connect state twice
  means the models were connected twice, and a model that allocates on
  connect now holds two allocations it will only release once.
- Counting Schedule services by looking for one and stopping. The defect
  that matters is the second one, so the tally has to run to the end of
  the service list.
- Allowing a configuration write during initialisation because the run
  has not started yet. The tree is already published by then; the value
  reaches the models that read it late and misses the ones that did not.
- Sorting initialisation entry points by priority alone. It works until
  two entry points that depend on each other are given priorities in the
  wrong order, and then the dependency is violated by a stable sort that
  looks entirely correct.
- Leaving a priority tie to iteration order. Both entry points run, the
  run passes, and the replay a month later produces a different result
  with no change anywhere in the model tree.
- Reporting a single pass or fail for the whole start-up. The four items
  fail for different reasons and a merged verdict cannot say whether to
  look at the state machine, the service registry or the schedule.

## Behavior contract (gate 3)

State-sequence comparison, Schedule service tallying, the configuration
window, entry-point validation, the deterministic topological posting
order and the four-item grading are exercised by the gate 3 contract
test: scripts/test_e4008_simulator_initialisation_and_configuration_with_one.py
against
scripts/e4008_simulator_initialisation_and_configuration_with_one_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e4008_simulator_initialisation_and_configuration_with_one.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

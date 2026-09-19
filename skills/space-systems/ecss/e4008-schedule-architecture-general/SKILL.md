---
name: e4008-schedule-architecture-general
description: "Assess a simulator schedule architecture against the five general normative items of ECSS-E-ST-40-08C clause 4.2.4.1. Use when a schedule is reviewed before it is armed: resolving every scheduled item onto an entry point the assembly actually provides, requiring a positive cycle on each cyclic item and a single release on each one-shot, holding each offset inside its own cycle, summing worst-case execution over cycle time to the utilisation and grading it against the declared budget, and enumerating the hyperperiod for releases that share an instant and a priority, which leaves the execution order undetermined. Trigger: ecss, e-st-40-08c, simulator-schedule-architecture, schedule-entry-point-resolution, schedule-cycle-offset-validity, schedule-utilisation-budget, schedule-hyperperiod-release-collision, deterministic-schedule-ordering."
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
  tags: [ecss, e-st-40-08-simulation-modelling-scope, e4008-schedule-architecture-general, simulator-schedule-architecture, schedule-entry-point-resolution, schedule-cycle-offset-validity, schedule-utilisation-budget, schedule-hyperperiod-release-collision, deterministic-schedule-ordering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Simulation Modelling Platform — Schedule Architecture General (space-systems/ecss/e4008-schedule-architecture-general)

Use when the task is the general schedule-architecture requirements of
ECSS-E-ST-40-08C clause 4.2.4.1 -- grading the list of scheduled items
a simulator will arm against the five items the clause carries, before
anything runs.

## Domain quick reference

- A schedule item asks the simulator to call one entry point of one
  instance, either once or on a repeating cycle, at an offset, with a
  priority, and with a declared worst-case execution time. Those five
  fields are exactly what the five normative items are about.
- The five items: every scheduled entry point resolves onto something
  the assembly provides; every cyclic item declares a positive cycle
  and every one-shot is released once; every offset lands inside its
  own cycle; the summed load stays inside the utilisation budget; and
  no two items share a release instant and a priority.
- Utilisation is the sum of worst-case execution time over cycle time
  across the cyclic items. A one-shot contributes no cyclic load, so it
  is excluded from that sum -- which is also why a heavy one-shot has
  to be reasoned about separately rather than averaged away.
- The determinism check needs the hyperperiod, the least common
  multiple of the cycle times. Two items only ever collide at instants
  where their cycles coincide, so the hyperperiod is the shortest
  window in which every possible collision appears at least once.
- Cycle times are carried as whole microseconds. A hyperperiod computed
  from floating-point periods drifts, and the least common multiple of
  two drifting numbers is meaningless; converting to integers first
  makes the window exact and lets the clause refuse a period finer than
  the platform resolution.
- An offset equal to its own cycle is not a late start, it is the same
  release a cycle later, so the item has been declared twice over.
  Offsets are therefore held strictly below the cycle.
- Sharing a priority is fine. Sharing a priority at the same release
  instant is not: the platform then runs the two in whatever order it
  enumerates them, and a run reproducible on one build stops being
  reproducible on the next.

## Workflow

1. Normalize every item: check the name, the kind, the integer
   priority, and convert cycle, offset and execution time to whole
   microseconds, refusing a value finer than the resolution.
2. Refuse a repeated item name outright -- a schedule that addresses
   two items by one name cannot report a finding against either.
3. Parse each entry-point reference into an absolute instance path and
   an entry-point identifier, and resolve it against the entry points
   the assembly provides.
4. Check cycles and offsets: a positive cycle on every cyclic item, and
   an offset that is non-negative and strictly inside its own cycle.
5. Sum worst-case execution over cycle time across the cyclic items and
   compare the utilisation against the declared budget.
6. Compute the hyperperiod, enumerate the releases inside it, group
   them by instant and priority, and report every group holding more
   than one item.
7. Grade the five items separately, then roll them into one verdict.

## Pitfalls

- Checking the schedule against the model catalogue rather than the
  assembly. A definition provides an entry point; only an instance
  provides one at a path, and the schedule addresses paths.
- Computing the hyperperiod from seconds as floating-point numbers. The
  periods are not exactly representable, so the least common multiple
  is either wrong or enormous, and the determinism check then either
  misses collisions or refuses to run.
- Reading utilisation inside the budget as proof the schedule fits. It
  is a necessary condition and not a sufficient one: the sum says
  nothing about the instant where several items are released together,
  which is why the determinism check is a separate item.
- Excluding one-shots from utilisation and then forgetting them. They
  genuinely add no cyclic load, and a long one-shot can still overrun
  the cycle it lands in, so it is reported rather than silently
  dropped.
- Allowing an offset equal to the cycle. It reads as a harmless late
  start and is in fact a duplicate release, which then shows up as a
  determinism finding at every coincidence instead of being caught
  where it was declared.
- Comparing the utilisation against the budget by bare arithmetic. It
  is a sum of quotients, so a schedule that exactly fills its budget
  can land a few units in the last place above it; the comparison
  absorbs that representation error while the budget stays untouched.

## Behavior contract (gate 3)

The microsecond normalization, entry-point parsing and resolution, item
validation, utilisation summation, hyperperiod computation, release
enumeration, priority-collision search and the five-item grading are
exercised by the gate 3 contract test:
scripts/test_e4008_schedule_architecture_general.py against
scripts/e4008_schedule_architecture_general_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e4008_schedule_architecture_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

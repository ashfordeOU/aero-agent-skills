---
name: e7041-obcp-execution-observability-level
description: "Determine the execution observability level an on-board control procedure should run at, under ECSS-E-ST-70-41C clause 6.18.4.2. Use when the task is trading how deep the ground can see inside a running procedure against the downlink it costs: reading off the coarsest level that makes a required execution event visible, applying an engine ceiling that quietly grants less than was asked, costing each level in octets per hour, and downgrading the costliest procedure first when a fleet will not fit its budget, never below a mandated floor. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, obcp-observability-level, obcp-step-level-reporting, obcp-execution-event-visibility, obcp-observability-downlink-budget, obcp-engine-observability-ceiling."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-obcp-execution-observability-level, obcp-observability-level, obcp-step-level-reporting, obcp-execution-event-visibility, obcp-observability-downlink-budget, obcp-engine-observability-ceiling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — OBCP Execution Observability Level (space-systems/ecss/e7041-obcp-execution-observability-level)

Use when the task is the execution observability level of
ECSS-E-ST-70-41C clause 6.18.4.2 -- how deep inside a running on-board
control procedure the engine's reporting goes, and what that depth
costs on the downlink.

## Domain quick reference

- A procedure runs without the ground watching, so the only picture the
  ground gets is whatever the engine was told to emit. The
  observability level is that setting, and it is a link-budget decision
  wearing an operations costume.
- Four levels, coarsest first. None emits nothing and the procedure
  runs blind. Procedure level reports the run starting, completing and
  aborting -- enough to know it ran and how it ended. Step level adds
  each step start and completion -- enough to locate a failure to one
  step. Instruction level reports every instruction, which is a
  debugging posture rather than an operating one.
- The levels are cumulative. A level shows everything the coarser
  levels show plus its own events, which makes the sizing question
  answerable in one move: take the deepest event the operator must see
  and read off the level that first makes it visible.
- Cost scales with structure, not with wall-clock time. Procedure level
  costs two events a run whatever the procedure does; step level costs
  two per step; instruction level costs one per instruction. A short
  procedure run often is dearer at step level than a long one run
  rarely.
- An engine supports only some of the levels. A request above what the
  engine carries is not refused -- it is quietly granted at the
  engine's ceiling, and the ground sees less than it asked for with
  nothing in the downlink saying so. Compute the shortfall or nobody
  learns of it.
- A floor is the operator's side of the same argument: the level below
  which this procedure is not worth running unobserved. A budget that
  can only be met by going under a floor has not been met.

## Workflow

1. Collect the execution events the operator must actually see, and
   take the coarsest level that makes all of them visible. That is the
   request, not a guess at a level name.
2. Resolve the engine ceiling from the levels the engine supports, and
   grant the coarser of request and ceiling. Report the shortfall and
   name the events lost to it.
3. Refuse outright a mandated floor the engine's ceiling cannot reach:
   the procedure cannot be flown observably at all on that engine.
4. Validate each reporting profile: at least one step, at least as many
   instructions as steps, a positive event size and a positive
   execution rate.
5. Cost each procedure at its assigned level in octets per hour, from
   event counts that follow the level's structure.
6. Sum the fleet against the downlink budget. Treat a total that lands
   exactly on the budget as fitting.
7. While the fleet is over budget, downgrade one level at a time, the
   costliest procedure first and ties broken on id so the same fleet
   always yields the same plan. Never go below a procedure's floor.
8. Report the disposition honestly: within budget, downgraded to fit,
   or still over budget with everything at its floor. The last one is a
   finding for the mission, not a plan.

## Pitfalls

- Choosing a level by name because it sounds prudent. Derive it from
  the events that must be visible; a level picked by feel is either
  paying for instruction traces nobody reads or hiding the step that
  failed.
- Assuming a request above the engine ceiling produces an error. It
  produces silence at a coarser level, which looks exactly like a
  procedure that behaved.
- Sizing observability from the procedure's duration. The cost follows
  step and instruction counts and how often it runs, not how long a run
  takes.
- Downgrading through a floor to make a budget close. The plan then
  reports a number that is met and a posture that is not flyable.
- Downgrading in an unstable order. Without a tie-break the same fleet
  produces different plans on different runs and no review can be
  repeated.
- Deciding budget fit with a strict inequality on a rate. The rate is a
  product of integer octet counts and a possibly fractional execution
  rate, so a plan exactly on budget can land either side of it; compare
  with a relative tolerance.

## Behavior contract (gate 3)

The level ordering, cumulative event visibility, minimum level for a
required event set, engine ceiling and shortfall, profile validation,
per-level event and octet costing, hourly rate, exact-budget
acceptance, costliest-first downgrade, floor protection and the grouped
plan report are exercised by the gate 3 contract test:
scripts/test_e7041_obcp_execution_observability_level.py against
scripts/e7041_obcp_execution_observability_level_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_obcp_execution_observability_level.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2040-device-development-plan-data-item
description: "Review a device development plan against the contents ECSS-E-ST-20-40C Annex B makes mandatory, then check that its four areas actually refer to each other: every task owned by a role the organisation declares, every tool a task names declared with a qualification state, every declared role and tool genuinely used, every task inside a milestone the schedule holds and finishing on or before its date, and milestone dates rising in declared order. Use when a development plan is being drafted or reviewed before baselining. Trigger: ecss, e-st-20-electrical-scope, device-development-plan-data-item, plan-organisation-roster, task-owner-traceability, tool-qualification-state, milestone-overrun-check, development-plan-slack."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-development-plan-data-item, device-development-plan-data-item, plan-organisation-roster, task-owner-traceability, tool-qualification-state, milestone-overrun-check, development-plan-slack]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Development Plan Data Item (space-systems/ecss/e2040-device-development-plan-data-item)

Use when the task is the contents duty of ECSS-E-ST-20-40C Annex B --
saying whether a device development plan holds the organisation, the
tasks, the tooling and the schedule the data item asks for, and whether
those four describe one coherent plan rather than four separate lists.

## Domain quick reference

- Presence is the cheap half. All four areas can be there, each one
  readable on its own, and the plan still not be a plan. What makes it
  one is that the areas point at each other, so the checks worth
  running are referential rather than editorial.
- Every task is owned by a role the organisation actually declares. An
  owner that appears nowhere in the roster is the commonest defect,
  and it survives review because the task list reads perfectly well by
  itself.
- The reverse direction matters just as much. A declared role that owns
  no task is either a role the plan does not need or a task the plan
  forgot, and the plan cannot say which until somebody looks.
- Tooling carries a qualification state, and a task depending on a tool
  that is unqualified or still in qualification is a schedule risk
  recorded nowhere else in the plan. A tool declared and used by
  nothing is the mirror defect.
- The schedule is the frame the tasks hang on. A task belongs to a
  declared milestone, finishes on or before that milestone's date, and
  has a positive duration; the milestones themselves rise in declared
  order. A task finishing exactly on its milestone date is compliant,
  so the comparison absorbs representation error rather than failing on
  the last bit.
- Dates are carried as day numbers on one project timeline. That keeps
  the arithmetic exact, keeps calendars and working-day conventions out
  of the check, and lets the plan span and the slack to the final
  milestone fall straight out.

## Workflow

1. Refuse an unknown top-level area outright, then report a mandatory
   area that is absent and, separately, one that exists and is empty.
2. Resolve the roster: unique role names, the holder, and the
   responsibilities each role carries. A role declared twice is an
   input defect and is refused, not reported.
3. Resolve the tooling: unique identifiers, version, and a
   qualification state folded onto the three recognised names. A tool
   with no state declared is treated as unqualified rather than
   assumed good.
4. Resolve the schedule as ordered milestones with day numbers, and the
   tasks with their owner, tools, start, finish and milestone.
5. Run the referential checks in both directions: task to role, role to
   task, task to tool, tool to task, task to milestone.
6. Grade each task against its milestone date and each milestone
   against the one before it.
7. Report the plan span from earliest start to latest finish, and the
   slack between the last task finish and the last milestone.

## Pitfalls

- Reviewing the four areas one at a time. Every defect that matters
  lives between them, and a section-by-section read is exactly the
  review that misses all of them.
- Accepting an owner name that is not a declared role. The task looks
  owned, nobody in the roster is accountable for it, and the gap is
  found when the task slips.
- Leaving a declared role with no task. It reads as thoroughness and is
  usually a missing task, so it is reported rather than tidied away.
- Treating an undeclared tool state as qualified. A plan that depends
  on a tool still in qualification carries a schedule risk that appears
  nowhere else, and defaulting the state hides it.
- Grading a task that finishes exactly on its milestone date as an
  overrun. On-date is on time, and a strict comparison against a
  computed day number turns a compliant plan red.

## Behavior contract (gate 3)

The area presence checks, roster, tooling, schedule and task
validation, the two-way referential checks, the milestone grading and
the span and slack figures are exercised by the gate 3 contract test:
scripts/test_e2040_device_development_plan_data_item.py against
scripts/e2040_device_development_plan_data_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_development_plan_data_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

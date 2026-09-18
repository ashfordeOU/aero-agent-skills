---
name: q1009-action-implementation
description: "Implement and track the actions a nonconformance carries under ECSS-Q-ST-10-09C clause 5.4.1. Use when agreed actions need owners and due dates, when the register has to be rolled up for a review board, or when an NCR is asking to progress while actions are still running: validate each entry, refuse a state jump the register cannot justify, count what is overdue and by how much, insist on evidence before an action counts as verified, and hold the nonconformance until every binding action has come to rest. Trigger: ecss, q-st-10-09c, ncr-action-register, action-owner-assignment, action-due-date-tracking, implementation-effectiveness-evidence, ncr-progression-hold, overdue-action-rollup."
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
  tags: [ecss, q-st-10-09c-nonconformance-scope, q1009-action-implementation, ncr-action-register, action-owner-assignment, action-due-date-tracking, implementation-effectiveness-evidence, ncr-progression-hold, overdue-action-rollup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Action Implementation and Tracking (space-systems/ecss/q1009-action-implementation)

Use when the task is the implementation step of ECSS-Q-ST-10-09C clause
5.4.1 — carrying agreed nonconformance actions from a list of good
intentions to a register a review board can read, and deciding whether
the nonconformance has earned the right to move on.

## Domain quick reference

- An agreed action is not an implemented one. Three things sit between
  them: a named owner who can actually carry it, a date it is due by,
  and evidence that what was done works. An action missing any of the
  three is not being tracked, it is being remembered.
- Five states describe an action: open, in-work, implemented, verified
  and cancelled. Only verified and cancelled are states an action rests
  in; the other three are places it is passing through.
- Implemented and verified are not the same claim. Implemented says the
  work was done. Verified says somebody checked it against evidence and
  it holds. An NCR that progresses on implemented actions is
  progressing on an untested assertion.
- State changes follow a path. An action does not jump from open to
  implemented, because the register would then hold no record that the
  work was ever underway; and a verified action that turns out not to
  hold is reopened into work rather than quietly re-marked.
- Cancellation is a decision, not an absence. A cancelled action
  carries the reason it was withdrawn, otherwise the register cannot
  distinguish a superseded action from one that was simply dropped.
- Lateness is measured against the due date, and only for actions still
  running. A verified action that finished after its date is a
  schedule fact, not an open item, and mixing the two inflates the
  overdue count the board is trying to act on.
- Mandatory and optional actions are tracked together but gate
  differently. The nonconformance waits on the binding ones; an
  improvement action agreed alongside them does not hold hardware.

## Workflow

1. Build the register from the agreed actions: identifier, description,
   owner, due date, state, whether the action is binding, and the
   evidence held against it. Reject duplicate identifiers rather than
   merging two actions under one row.
2. Validate each entry against the reporting date. Record who owns it,
   whether it is past its date and by how many days, and whether the
   state it claims is supported by what is in the record.
3. Apply state changes through the allowed transitions so the register
   keeps a defensible history; refuse the jump rather than editing the
   state in place.
4. Roll the register up: counts per state, the proportion actually
   verified, the overdue list ordered worst first, and the actions with
   nobody carrying them.
5. Separate binding actions from the rest, and check each binding one
   has come to rest — verified against evidence, or cancelled with a
   reason.
6. Where binding actions are still running, report whether the hold is
   about work outstanding or about evidence outstanding; they call for
   different interventions from the board.
7. Permit progression only when every binding action rests, and carry
   the findings forward so the closure step has them.

## Pitfalls

- Assigning an action to a team rather than a person or a named role.
  A register line owned by everybody is worked by nobody, and it is the
  line that is still open at the next board.
- Marking an action verified because it was reported done. Verification
  needs evidence of effect; without it the state is implemented, and
  the difference is exactly what the clause is protecting.
- Counting closed-late actions in the overdue list. The board acts on
  what is still running; a finished action that ran late belongs in a
  schedule review, not in the outstanding count.
- Cancelling an action to clear the register before a milestone.
  Cancellation is legitimate when something supersedes it, and the
  superseding record is the reason — an unexplained cancellation reads
  as an action that was quietly abandoned.
- Letting an optional improvement action block hardware, or letting a
  binding action be quietly re-marked optional so it stops blocking.
  Both distort the same gate from opposite sides.
- Progressing the nonconformance because the last action is due
  tomorrow. Due is not done; the gate is the state of the register on
  the day, not its projected state.

## Behavior contract (gate 3)

The entry validation, state-transition rules, overdue arithmetic,
register roll-up, ownership check and the progression gate are
exercised by the gate 3 contract test:
scripts/test_q1009_action_implementation.py against
scripts/q1009_action_implementation_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q1009_action_implementation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

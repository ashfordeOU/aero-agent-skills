---
name: e7041-disable-the-event-action-function
description: "Determine what a request to switch the event-action function off actually changes on board under ECSS-E-ST-70-41C clause 6.19.6.2. Use when the whole function is being disabled and the question is what survives it: the function status moves to disabled, every event-action definition keeps the enable state it already held, and no action is dispatched while the function is off even for a definition still marked enabled. Covers the repeated disable that changes nothing, the events that keep being reported while their actions are withheld, and a dispatch decision a reviewer can replay. Trigger: ecss, e-st-70-41-packet-utilization-scope, event-action-function-status, disable-event-action-function, event-action-action-dispatch, event-action-definition-enable-state."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-disable-the-event-action-function, event-action-function-status, disable-event-action-function, event-action-action-dispatch, event-action-definition-enable-state]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Disable The Event-Action Function (space-systems/ecss/e7041-disable-the-event-action-function)

Use when the task is the function-level disable of ECSS-E-ST-70-41C
clause 6.19.6.2 -- the request that switches the event-action function
off as a whole, with the three normative items that clause places on
what the transition changes and, more importantly, on what it does not.

## Domain quick reference

- The event-action function has one status of its own, separate from
  the enable state each definition carries. Two switches sit in series:
  an action is dispatched only when the function is on and the
  definition that binds it is enabled.
- Disabling the function is the outer switch. It is the operator's way
  of taking every on-board reaction out of the loop at once, without
  having to know what is in the store.
- The per-definition enable states are preserved across the disable.
  That is the whole point of the outer switch: the store is left
  exactly as it was so the function can be switched back on later and
  resume the same reactions.
- Events keep being detected and reported while the function is off.
  Only the action is withheld. A ground operator still sees the event
  report; what disappears is the on-board response to it.
- Disabling a function that is already disabled is accepted and
  changes nothing. A repeated command is a normal consequence of a
  ground procedure being re-run, not an error to report.
- A dispatch decision is worth recording as two separate reasons -- the
  function was off, or the definition was disabled -- because the
  operator action that fixes each of them is different.

## Workflow

1. Normalize the on-board state first: the function status and the
   definition store. Reject a duplicate event identifier, a missing
   action binding or a non-boolean enable flag outright, because a
   store that cannot be read cannot be reasoned about.
2. Record the enable state of every definition before the transition,
   so the preservation claim can be checked rather than asserted.
3. Apply the disable: set the function status to disabled and copy the
   definition store across untouched.
4. Compare the enable states before and after and raise a finding for
   any definition whose flag moved. Nothing should have moved.
5. Mark the request idempotent when the function was already off, and
   report that as an accepted no-change rather than as a failure.
6. Replay dispatch for any event occurrence of interest against the
   new state, returning a withheld verdict with the reason that
   actually applies.

## Pitfalls

- Clearing the per-definition enable flags while disabling the
  function. The store then comes back empty of intent and every
  definition has to be re-enabled by hand after the function is
  restored.
- Treating a second disable as a failure. Ground procedures are
  re-run, and a rejected no-change command sends an operator hunting
  for a fault that does not exist.
- Suppressing the event reports along with the actions. The operator
  loses the very visibility the disable was meant to preserve.
- Reporting a withheld action as "definition disabled" when the real
  reason was the function status. The operator then edits the store
  instead of switching the function back on.
- Deleting definitions instead of disabling the function. A disable is
  reversible and a deletion is not.
- Assuming an enabled definition implies a dispatched action. Both
  switches have to be on, and only checking the inner one is how a
  silent function-level disable goes unnoticed for a whole pass.

## Behavior contract (gate 3)

The state normalization, enable-state snapshot, disable transition,
preservation check, idempotent re-disable and the two-reason dispatch
replay are exercised by the gate 3 contract test:
scripts/test_e7041_disable_the_event_action_function.py against
scripts/e7041_disable_the_event_action_function_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_disable_the_event_action_function.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

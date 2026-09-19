---
name: e7041-enable-the-event-action-function
description: "Verify the outer enable switch of the event-action function and what it must leave untouched, under ECSS-E-ST-70-41C clause 6.19.6.1. Use when the whole function was shut for a critical operation and the table came back armed differently, or when a definition staged while the function was off never took effect: enabling and disabling the function by request, gating rather than rewriting the per-definition statuses, proving across a disable-and-enable round trip that every status returned as it was, letting a definition be armed while the function is off, and computing the set that actually releases. Trigger: ecss, e-st-70-41c, event-action-function-enable, event-action-two-level-switch, event-action-status-preserved-across-toggle, event-action-staged-while-disabled, event-action-effective-armed-set."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-enable-the-event-action-function, event-action-function-enable, event-action-two-level-switch, event-action-status-preserved-across-toggle, event-action-staged-while-disabled, event-action-effective-armed-set]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Enabling the Event-Action Function (space-systems/ecss/e7041-enable-the-event-action-function)

Use when the task is the function-level enabling of ECSS-E-ST-70-41C
clause 6.19.6.1 -- the three requirements that switch the event-action
function as a whole and fix the one thing that switch is not allowed
to touch.

## Domain quick reference

- There are two switches, not one. The function has an enable status
  and every definition in the table has its own. A binding releases
  only when both are on, so "enabled" is an ambiguous word until the
  level is named.
- The outer switch gates, it does not write. Disabling the function
  does not disarm the definitions and enabling it does not arm them.
  The per-definition statuses are the same before and after, and that
  is the whole point of the clause.
- That property is what makes the outer switch usable. An operator can
  shut the function for a critical operation and restore it
  afterwards without reissuing one request per entry, and without
  re-arming something that was deliberately disarmed.
- An implementation that clears or sets the statuses on a toggle fails
  quietly. The table is still full, the entries are all there, and
  only the statuses are now whatever the toggle wrote -- which looks
  exactly like a table somebody reconfigured on purpose.
- Definition-level requests do not depend on the function switch. A
  definition can be armed while the function is off, and it takes
  effect the moment the function returns. That is how an operation is
  staged rather than scrambled at the last second.
- A repeated request is not an error. Enabling an enabled function
  leaves it enabled; the request is worth reporting because it usually
  means the ground's model disagrees with the spacecraft, but the
  state is correct either way.
- An enabled function with nothing armed is a real configuration and a
  suspicious one. Every event is detected, no action is released, and
  nothing in the function's own status says so.

## Workflow

1. Build the state from the table's keys, the function switch and the
   set of armed definitions, refusing a repeated key or an armed key
   that is not in the table.
2. Normalise each request: a function-level request names no
   definition, a definition-level request must name one as a
   two-part key.
3. Apply a function-level request by setting the switch, reporting a
   request that found the switch already in that position.
4. Snapshot the per-definition statuses on either side of every
   function-level request and raise a breach finding for any that
   changed -- the check runs on the implementation, not on trust.
5. Apply a definition-level request by setting that definition's own
   status, reporting a request that changed nothing and a definition
   armed while the function was off.
6. Refuse a request naming a definition the table does not hold,
   without creating it.
7. Run a disable-and-enable round trip as an explicit proof, leaving
   the function switch where it was found, and report whether every
   status came back.
8. Compute the effective armed set -- both switches on -- and report
   an enabled function with nothing armed.

## Pitfalls

- Saying "the event-action function is enabled" and stopping there.
  Nothing releases unless a definition is armed as well.
- Clearing the per-definition statuses when the function is disabled.
  The function comes back and the table is inert, one entry at a time
  to repair, usually during the operation that needed it.
- Re-arming everything when the function is enabled. The definition
  somebody disarmed for a reason is now live again, and no request in
  the log says so.
- Treating a definition-level request issued while the function is off
  as an error. It is the normal way to stage an operation; the useful
  response is to report it, not to refuse it.
- Reading a repeated enable as a fault. The state is right; what is
  wrong is the ground's picture of it, which is a different
  investigation.
- Proving preservation by inspection rather than by comparing
  snapshots. The failure mode is silent and only a before-and-after
  comparison catches it.

## Behavior contract (gate 3)

The two-level state construction, key and request validation,
already-in-that-position reporting, status preservation across every
function-level request, the explicit disable-and-enable round-trip
proof that restores the original switch position, definition arming
while the function is off, unknown-definition refusal, the effective
armed set and the enabled-but-nothing-armed finding are exercised by
the gate 3 contract test:
scripts/test_e7041_enable_the_event_action_function.py against
scripts/e7041_enable_the_event_action_function_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_enable_the_event_action_function.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

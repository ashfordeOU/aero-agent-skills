---
name: e7041-delete-all-event-action-definitions
description: "Analyze a request that clears the whole event-action store in one step under ECSS-E-ST-70-41C clause 6.19.8.4. Use when ground wipes every on-board reaction at once and the first question is whether the request is admissible at all: it is refused while the event-action function is still enabled, so a live reaction chain cannot vanish mid-pass, and it is admitted only once the function has been switched off. Covers the wholesale clearance that spares no definition enabled or disabled, the action bindings that go with them, the untouched function status and the accepted no-change on an already-empty store. Trigger: ecss, e-st-70-41-packet-utilization-scope, delete-all-event-action-definitions, event-action-store-clearance, event-action-function-precondition, empty-event-action-store."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-delete-all-event-action-definitions, delete-all-event-action-definitions, event-action-store-clearance, event-action-function-precondition, empty-event-action-store]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Delete All Event-Action Definitions (space-systems/ecss/e7041-delete-all-event-action-definitions)

Use when the task is the wholesale clearance of ECSS-E-ST-70-41C
clause 6.19.8.4 -- the request that empties the event-action store in
a single step, with the three normative items that clause places on
its precondition, on its reach and on what it leaves behind.

## Domain quick reference

- This is the one request in the set with no identifier list. It does
  not name what it removes, which is exactly why its precondition
  matters more than any per-instruction judgement would.
- The precondition is the function status. While the event-action
  function is enabled the request is refused, because a live reaction
  chain would disappear between one event and the next with nothing
  on board able to restore it.
- Switching the function off first is therefore part of the
  procedure, not a courtesy. Disable the function, confirm it, then
  clear the store.
- The clearance spares nothing. A definition that is still enabled
  individually goes with the rest -- the per-definition protection of
  the named deletion does not apply here, because the function-level
  precondition has already taken its place.
- Every action binding leaves with its definition. There is no
  residue holding store capacity after the clearance.
- The function status itself is not touched by the deletion. It was
  disabled before the request and it stays disabled after it, so the
  operator has to switch it back on deliberately.
- A clearance on an already-empty store is accepted and removes
  nothing. Re-running a ground procedure should not produce a failure
  report.

## Workflow

1. Normalize the on-board state: the definition store, the function
   status and the declared capacity. Reject a store that repeats an
   event identity before deciding anything about clearing it.
2. Test the precondition first. An enabled function refuses the
   request outright and the store is returned untouched, with a
   finding that names the disable the operator has to send first.
3. Once the precondition holds, empty the store completely, dropping
   every definition and its action binding together regardless of any
   individual enable flag.
4. Carry the function status across unchanged and confirm it did not
   move.
5. Count what was removed and what capacity came back, and report a
   clearance of an already-empty store as an accepted no-change
   rather than as a failure.
6. Verify the result before returning it: an accepted clearance must
   leave no definition behind at all.

## Pitfalls

- Clearing the store while the function is still enabled. Reactions
  vanish mid-pass and the spacecraft silently stops responding to
  conditions the operator believes are still covered.
- Applying the named deletion's per-definition rule here and skipping
  the enabled ones. The request then half-succeeds and the store ends
  up holding exactly the definitions that were most active.
- Disabling the function as an implicit side effect so the clearance
  can proceed. Two commands became one, and the operator's record of
  what the spacecraft did no longer matches what happened.
- Re-enabling the function after clearing. The store is empty, so the
  function comes back on with no reactions and an operator reading
  the status believes protection exists.
- Reporting a clearance of an empty store as a failure, which sends
  an operator hunting a fault in a procedure that worked.
- Leaving action bindings behind. Capacity accounting then disagrees
  with the store's own contents.

## Behavior contract (gate 3)

The state normalization, function-status precondition, refusal that
returns the store untouched, complete clearance including enabled
definitions and their action bindings, freed-capacity accounting,
untouched function status and the accepted no-change on an empty store
are exercised by the gate 3 contract test:
scripts/test_e7041_delete_all_event_action_definitions.py against
scripts/e7041_delete_all_event_action_definitions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_delete_all_event_action_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e7041-add-event-action-definitions
description: "Validate a request that adds event-action definitions to the on-board store under ECSS-E-ST-70-41C clause 6.19.8.1. Use when new on-board reactions are uplinked and every instruction is judged on its own: an event identity the store already holds is a duplicate and fails for that instruction, a repeated identity or an empty instruction list is malformed, an instruction that would take the store past its capacity is refused, and an action that is itself an event-action management request is refused as recursive. Covers the initial enable state a new definition takes and the accepted, partially accepted or rejected verdict. Trigger: ecss, e-st-70-41-packet-utilization-scope, add-event-action-definition, event-action-store-capacity, event-action-recursive-action, duplicate-event-action-identity."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-add-event-action-definitions, add-event-action-definition, event-action-store-capacity, event-action-recursive-action, duplicate-event-action-identity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Add Event-Action Definitions (space-systems/ecss/e7041-add-event-action-definitions)

Use when the task is the addition request of ECSS-E-ST-70-41C clause
6.19.8.1 -- putting new event-action definitions into the on-board
store, with the eight normative items that clause places on each
instruction, on the store it lands in and on the verdict earned.

## Domain quick reference

- An event-action definition is an identity plus a payload. The
  identity is the event it reacts to, the raising application process
  together with the event definition; the payload is the request the
  on-board software runs when that event occurs.
- The identity is unique in the store. One event has at most one bound
  action, so an add naming an identity already held is a duplicate and
  cannot be quietly treated as an update.
- A duplicate fails only its own instruction. The rest of the batch is
  still added and the request earns a partial verdict.
- A repeated identity inside one request is malformed instead. The
  ground segment cannot have meant to bind two actions to one event,
  and nothing in the request is applied.
- The store is finite. An instruction that would take it past capacity
  is refused, and the refusal is deterministic: instructions are
  admitted in request order so the same batch always fills the same
  slots.
- The action carried by an instruction has to be a request the service
  can actually run. An action drawn from the event-action management
  service itself is refused: a definition able to add or delete
  definitions turns one event into an unbounded chain.
- A new definition lands disabled unless the instruction asks
  otherwise. The safe default is a binding that exists but does not
  fire until an operator says so.

## Workflow

1. Normalize the on-board state: the definition store, the function
   status and the store capacity. Reject a store that already repeats
   an identity before judging anything added to it.
2. Normalize the request into an ordered instruction list, refusing an
   empty list and a repeated identity outright.
3. Validate each instruction's action: it needs a request identity and
   a service type, and a service type belonging to event-action
   management is refused as recursive.
4. Walk the instructions in order against a working copy of the store,
   failing a duplicate identity and failing an instruction that would
   exceed capacity, while admitting the rest.
5. Give each admitted definition its enable state from the
   instruction, defaulting to disabled.
6. Set the verdict from the split and return the resulting store, the
   admitted identities and one finding per refused instruction.

## Pitfalls

- Treating a duplicate identity as an update. The operator believes
  the old action was replaced when it was not, and the spacecraft
  keeps reacting the way it used to.
- Failing the whole batch on one duplicate, which throws away the
  additions that were fine and costs a pass to rebuild.
- Admitting instructions out of order once capacity is short. Which
  definitions survive then depends on an implementation detail rather
  than on what the operator wrote.
- Accepting an action that manages event-action definitions. One event
  can then rewrite the store, and the on-board reaction chain stops
  being reviewable from the ground.
- Adding a definition already enabled by default. The reaction goes
  live the moment the uplink completes, before anyone has checked it.
- Counting capacity against the original store rather than the working
  copy. A batch then appears to fit when its own earlier instructions
  have already consumed the room.

## Behavior contract (gate 3)

The store normalization, instruction normalization, action validation
with the recursion guard, duplicate-identity refusal, ordered capacity
admission, default enable state and the acceptance verdict are
exercised by the gate 3 contract test:
scripts/test_e7041_add_event_action_definitions.py against
scripts/e7041_add_event_action_definitions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_add_event_action_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e7041-delete-event-action-definitions
description: "Verify and apply a request that deletes named event-action definitions under ECSS-E-ST-70-41C clause 6.19.8.3. Use when stale on-board reactions are being cleared and each instruction earns its own verdict: an identity the store does not hold fails for that instruction alone, a definition still enabled is refused because a live reaction must not be removed under it, and a repeated identity or an empty instruction list is malformed so nothing is applied. Covers the action binding that goes with the definition, the disable-then-delete order a clean-up needs, and the store capacity a deletion frees. Trigger: ecss, e-st-70-41-packet-utilization-scope, delete-event-action-definition, enabled-definition-deletion-refusal, event-action-store-capacity-freed, event-action-instruction-verdict."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-delete-event-action-definitions, delete-event-action-definition, enabled-definition-deletion-refusal, event-action-store-capacity-freed, event-action-instruction-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Delete Event-Action Definitions (space-systems/ecss/e7041-delete-event-action-definitions)

Use when the task is the deletion request of ECSS-E-ST-70-41C clause
6.19.8.3 -- removing named event-action definitions from the on-board
store, with the seven normative items that clause places on each
instruction, on the precondition a deletion carries and on the verdict
the request earns.

## Domain quick reference

- A deletion is irreversible from the spacecraft's side. The action
  binding goes with the definition, so restoring the reaction means
  uplinking the whole thing again on a later pass.
- Because it is irreversible, it carries a precondition: a definition
  that is still enabled is not deleted. An operator who wants it gone
  disables it first and deletes it second, and the two-step order is
  the protection.
- A refused deletion leaves the definition exactly as it was, still
  enabled and still bound. Nothing half-happens.
- An identity the store does not hold fails for its own instruction.
  It is reported rather than silently treated as an already-successful
  deletion, because the two are indistinguishable to ground otherwise.
- A repeated identity inside one request, or an empty instruction
  list, is malformed. Neither is applied in part.
- Everything that can be deleted is deleted. One refusal does not stop
  the rest of the batch, and the request earns a partial verdict.
- The deletion frees store capacity and touches nothing else. The
  function status and every surviving definition's enable flag are
  left where they were.

## Workflow

1. Normalize the on-board state: definition store, function status and
   capacity. Reject a store that repeats an event identity.
2. Normalize the request into an ordered instruction list, refusing an
   empty list and a repeated identity outright.
3. Walk the instructions in request order and categorize each: held
   and disabled, held but still enabled, or not held at all.
4. Delete every instruction in the first group, removing the
   definition and its action binding together.
5. Raise one finding per refusal, naming which of the two reasons
   applies, because the operator's next command differs -- a disable
   for one, nothing at all for the other.
6. Set the verdict from the split and report the surviving store, the
   freed capacity and the unchanged function status.

## Pitfalls

- Deleting an enabled definition on request. The reaction disappears
  mid-pass with no record that it was ever armed, and the two-step
  protection the service is built around is gone.
- Reporting an unheld identity as a successful deletion. Ground then
  believes a clean-up completed when a definition it never named is
  still on board.
- Failing the whole batch on one enabled definition, which throws away
  deletions that were correct and costs a pass.
- Disabling the definition instead of refusing the deletion. The
  request asked to remove it, not to arm a later removal, and the
  store ends up in a state nobody commanded.
- Leaving the action binding behind after the definition is gone. It
  consumes capacity that the freed-slot count then reports as
  available.
- Treating the deletion as reversible in planning. There is no undo
  from on board; the binding has to come up from ground again.

## Behavior contract (gate 3)

The store normalization, instruction normalization, malformed-request
refusal, three-way instruction categorization, enabled-definition
refusal, action-binding removal, freed-capacity accounting and the
acceptance verdict are exercised by the gate 3 contract test:
scripts/test_e7041_delete_event_action_definitions.py against
scripts/e7041_delete_event_action_definitions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_delete_event_action_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

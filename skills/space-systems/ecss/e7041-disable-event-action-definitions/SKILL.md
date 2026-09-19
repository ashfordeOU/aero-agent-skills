---
name: e7041-disable-event-action-definitions
description: "Assess what a request that disables named event-action definitions leaves behind under ECSS-E-ST-70-41C clause 6.19.7.2. Use when ground takes individual on-board reactions out of the loop and each instruction earns its own verdict: an identity the store does not hold fails for that instruction alone, a repeated identity or an empty instruction list is malformed and nothing is applied, and disabling an already-disabled definition is accepted without change. Covers the definition that stays in the store rather than being removed, the event that keeps being reported while its action is withheld, and the deletion eligibility a disable creates. Trigger: ecss, e-st-70-41-packet-utilization-scope, disable-event-action-definition, event-action-action-withheld, event-action-deletion-eligibility, event-action-instruction-verdict."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-disable-event-action-definitions, disable-event-action-definition, event-action-action-withheld, event-action-deletion-eligibility, event-action-instruction-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Disable Event-Action Definitions (space-systems/ecss/e7041-disable-event-action-definitions)

Use when the task is the definition-level disable of ECSS-E-ST-70-41C
clause 6.19.7.2 -- the request that switches named event-action
definitions off one at a time, with the eight normative items that
clause places on the instruction list, on what stays behind and on the
verdict the request earns.

## Domain quick reference

- A disable is not a deletion. The definition stays in the store with
  its action binding intact, and the only thing that moves is its own
  enable flag. That is what makes it reversible on a later pass.
- What the disable buys is the withheld action. The event is still
  detected and still reported to ground; the on-board reaction to it
  simply does not run.
- Disabling is also the precondition for deleting. A definition that
  is still enabled cannot be removed from the store, so a disable is
  routinely the first half of a two-command clean-up.
- The request is a batch of instructions and each one is judged alone.
  An identity the store does not hold fails for that instruction and
  is reported; the rest are still applied.
- A repeated identity inside one request, or an empty instruction
  list, is malformed on its face. Neither is applied in part -- the
  request is refused before the store is touched.
- Disabling an already-disabled definition is accepted and changes
  nothing. The commanded state was already reached.
- The function status is a separate switch and a definition-level
  disable never moves it. Disabling every definition is not the same
  operation as disabling the function, even when the effect looks
  identical from the ground for one pass.

## Workflow

1. Normalize the on-board state and reject a store that repeats an
   event identity, carries a non-boolean flag or binds no action.
2. Normalize the request into an ordered instruction list, refusing an
   empty list and a repeated identity outright.
3. Resolve each instruction against the store in request order and
   split the identities into those held and those not.
4. Apply the disable to every resolved instruction, recording whether
   the flag moved or was already off, and leave the action binding and
   the store membership untouched.
5. Set the verdict from the split -- accepted, partially accepted or
   rejected -- with one finding per unresolved identity.
6. Report what the disable enabled downstream: the definitions now
   eligible for deletion, and the events whose action is withheld
   while still being reported.

## Pitfalls

- Removing the definition instead of clearing its flag. The action
  binding is lost and has to be uplinked again to restore the
  reaction, which is the expensive half of the operation.
- Suppressing the event report along with the action. Ground then
  loses sight of the condition exactly when it stopped being handled
  on board.
- Failing the whole batch over one stale identity, forcing a rebuild
  and a re-uplink of instructions that were correct.
- Treating a second disable as an error. The store is in the
  commanded state and a failure report only starts a fault hunt.
- Disabling the function when the request named definitions. The
  blast radius is every reaction on board rather than the named few.
- Assuming a disabled definition is gone. It still occupies store
  capacity, and an add request for the same event identity still
  collides with it.

## Behavior contract (gate 3)

The store normalization, instruction normalization, malformed-request
refusal, identity resolution, per-instruction disable outcome,
store-membership preservation, deletion eligibility and the acceptance
verdict are exercised by the gate 3 contract test:
scripts/test_e7041_disable_event_action_definitions.py against
scripts/e7041_disable_event_action_definitions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_disable_event_action_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

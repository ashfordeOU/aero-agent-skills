---
name: e7041-enable-event-action-definitions
description: "Evaluate a request that enables named event-action definitions under ECSS-E-ST-70-41C clause 6.19.7.1. Use when ground turns individual on-board reactions back on and every instruction has to be judged on its own: an instruction naming a definition the store does not hold fails for that instruction alone, a repeated event identity inside one request makes the whole request malformed, an empty instruction list is refused, and enabling an already-enabled definition is accepted without change. Covers the per-instruction verdict, the independence of a definition flag from the function status, and the enabled set a receiver can check afterwards. Trigger: ecss, e-st-70-41-packet-utilization-scope, enable-event-action-definition, event-action-definition-enable-state, event-action-instruction-verdict, unknown-event-action-definition."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-enable-event-action-definitions, enable-event-action-definition, event-action-definition-enable-state, event-action-instruction-verdict, unknown-event-action-definition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — Enable Event-Action Definitions (space-systems/ecss/e7041-enable-event-action-definitions)

Use when the task is the definition-level enable of ECSS-E-ST-70-41C
clause 6.19.7.1 -- the request that switches named event-action
definitions on one at a time, with the eight normative items that
clause places on the instruction list and on the verdict it earns.

## Domain quick reference

- The request carries a list of instructions, not a single target. It
  is a batch, and a batch is where per-instruction judgement starts to
  matter: one bad identity should not cost the operator the rest.
- An instruction identifies its definition by the event it reacts to:
  the application process that raises the event plus the event
  definition within it. Neither half identifies a definition alone.
- An identity the store does not hold is failed for that instruction
  and reported. The remaining instructions are still carried out, so
  the request earns a partial verdict rather than an all-or-nothing
  one.
- A repeated identity inside one request is a different kind of
  problem. It is malformed on its face, the ground segment cannot have
  meant it, and it is refused before anything is applied.
- An empty instruction list is refused too. Unlike a report request,
  an empty enable does not mean "everything"; it means the uplink
  built the request wrong.
- Enabling a definition that is already enabled is accepted and
  changes nothing. Ground procedures get re-run and the store should
  end up in the commanded state either way.
- The definition flag and the function status are independent. A
  definition can be enabled while the function is off; the action
  simply stays withheld until the function comes back.

## Workflow

1. Normalize the on-board state and reject a store that repeats an
   event identity, carries a non-boolean flag or binds no action.
2. Normalize the request into an ordered instruction list. Refuse an
   empty list and refuse a repeated identity outright -- both are
   malformed, and neither is applied in part.
3. Resolve each instruction against the store, preserving request
   order, and split the identities into those held and those not.
4. Apply the enable to every resolved instruction, recording whether
   it changed the flag or found it already on.
5. Set the verdict from the split: accepted when every instruction
   resolved, partially accepted when some did, rejected when none did,
   with one finding per unresolved identity.
6. Return the resulting state and the enabled set, leaving the
   function status exactly as it was found.

## Pitfalls

- Failing the whole request because one identity is stale. The
  operator then has to rebuild and re-uplink a batch that was mostly
  correct, on a pass that may not come again soon.
- De-duplicating a repeated identity silently. It hides a ground tool
  defect that will keep producing malformed requests.
- Reading an empty instruction list as "enable everything". That
  inverts the safest reading of an ambiguous request into the most
  dangerous one.
- Rejecting an already-enabled definition. The commanded state was
  reached; reporting a failure sends an operator looking for a fault.
- Enabling the function as a side effect of enabling a definition. The
  outer switch is a separate decision and a separate command.
- Assuming an enabled definition means its action will run. The
  function status still gates it, and conflating the two is how a
  reaction is believed active while it is withheld.

## Behavior contract (gate 3)

The store normalization, instruction normalization, malformed-request
refusal, identity resolution, per-instruction enable outcome,
acceptance verdict and function-status independence are exercised by
the gate 3 contract test:
scripts/test_e7041_enable_event_action_definitions.py against
scripts/e7041_enable_event_action_definitions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_enable_event_action_definitions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

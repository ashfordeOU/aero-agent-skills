---
name: e5053-effect-on-receipt
description: "Verify the effect-on-receipt subclause of a SpaceWire service primitive against ECSS-E-ST-50-53 clause 5.2.2.4. Use when a protocol service definition states what the receiving entity does with each primitive and that behaviour has to hold as a state machine: build the transition table from the declared effects, refuse two effects giving one state and primitive different destinations, report a state that declares no handling for a primitive it can receive, require a discard effect to leave the state unchanged, find states nothing can reach from the initial state, and replay a primitive sequence through the table. Trigger: ecss, e-st-50-53, service-primitive-effect-on-receipt-subclause, receipt-transition-table, receipt-determinism, receipt-handling-coverage, unreachable-protocol-state, spacewire-service-definition."
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
  tags: [ecss, e-st-50-spacewire-scope, e5053-effect-on-receipt, service-primitive-effect-on-receipt-subclause, receipt-transition-table, receipt-determinism, unreachable-protocol-state, spacewire-service-definition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire Service Primitive — Effect On Receipt Subclause (space-systems/ecss/e5053-effect-on-receipt)

Use when the task is the effect-on-receipt subclause of ECSS-E-ST-50-53
clause 5.2.2.4 — what the receiving protocol entity does when a primitive
reaches it, and whether the collected effects of a service definition
still form a state machine an implementer can build.

## Domain quick reference

- An effect-on-receipt entry is a transition: the primitive received, the
  state the receiver is in, the action it takes, and the state it is in
  afterwards. Written that way the subclause is checkable; written as
  narrative it is not.
- Determinism is the first property to establish. One state receiving one
  primitive has exactly one destination. Two entries disagreeing on the
  destination is not an edge case to be ranked by order of appearance —
  it is the defect, and an implementation will pick whichever it read
  last.
- Coverage is the second. A primitive that can arrive in a state the
  specification never gives a handling for leaves the receiver with no
  defined behaviour at exactly the moment it needs one. Declaring the
  handling as a discard is a complete answer; saying nothing is not.
- A discard is a handling with no state change. An entry that calls
  itself a discard and moves the receiver to another state is describing
  something else, and the mismatch usually means the action text was
  edited and the destination was not.
- Reachability closes the audit. A state nothing can reach from the
  initial state is dead: every entry written for it, and every primitive
  handled only there, is unreachable text.
- Replaying a primitive sequence through the finished table is what turns
  the audit into a usable answer. It shows where a given exchange leaves
  the receiver and refuses at the first primitive the table cannot
  handle.

## Workflow

1. Validate the declared state set, the initial state, the primitive
   catalogue and, when given, the per-state list of primitives that can
   arrive there; an initial state outside the state set is malformed
   input.
2. Validate each transition: state, primitive and destination all resolve
   against the declared sets, the action text is present, and the discard
   flag is a boolean.
3. Build the transition table keyed on state and primitive, collecting
   every entry that lands on the same key.
4. Report determinism conflicts: a key whose entries do not all agree on
   one destination. Repeated entries that agree are redundant, not a
   conflict.
5. Report coverage gaps against the per-state arrival sets, falling back
   to the whole catalogue when a state declares no arrival set.
6. Report discard entries that change state, then walk the table from the
   initial state and report every state nothing reaches.
7. Replay any supplied primitive sequence, returning the trace and the
   final state, and refusing at the first key the table has no entry for.

## Pitfalls

- Reading determinism off the first matching entry. A table with two
  entries on one key is ambiguous even when one of them is the one the
  author meant; ranking by position hides the defect instead of
  reporting it.
- Treating an unlisted primitive as an implicit discard. Silence is not
  a handling, and the implementations that guess differently are exactly
  the ones that fail to interoperate.
- Marking an entry as a discard while giving it a destination. The two
  statements contradict and only one of them will be implemented.
- Computing reachability from the transition table alone without the
  initial state. Every state is reachable from itself, so the audit has
  to start somewhere the specification actually names.
- Replaying a sequence and reporting the final state without the trace.
  When the sequence is wrong, the trace is the only thing that says
  where it went wrong.

## Behavior contract (gate 3)

The set validation, transition validation, table construction,
determinism conflict detection, coverage-gap reporting, discard
consistency, reachability walk and sequence replay are exercised by the
gate 3 contract test:
scripts/test_e5053_effect_on_receipt.py against
scripts/e5053_effect_on_receipt_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5053_effect_on_receipt.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e5053-when-generated
description: "Evaluate the when-generated subclause of a SpaceWire service primitive against ECSS-E-ST-50-53 clause 5.2.2.3. Use when a protocol service definition states the conditions under which each primitive is issued and those conditions have to be checked against the declared protocol state machine: resolve every generation rule to a declared state and a declared originating event, find a primitive no rule can ever issue, find two rules firing on one state and event with no distinguishing guard, report events never used and terminal states that still generate, and grade the whole rule set. Trigger: ecss, e-st-50-53, service-primitive-when-generated-subclause, primitive-generation-rule, originating-event-mapping, generation-nondeterminism, unreachable-primitive, spacewire-service-definition."
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
  tags: [ecss, e-st-50-spacewire-scope, e5053-when-generated, service-primitive-when-generated-subclause, primitive-generation-rule, originating-event-mapping, generation-nondeterminism, spacewire-service-definition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire Service Primitive — When Generated Subclause (space-systems/ecss/e5053-when-generated)

Use when the task is the when-generated subclause of ECSS-E-ST-50-53
clause 5.2.2.3 — the statement of what has to be true for a service
primitive to be issued, and whether the set of those statements is
consistent with the protocol state machine the same specification
declares.

## Domain quick reference

- A generation rule is a triple: the primitive issued, the protocol state
  the entity is in, and the originating event. The event is one of a
  small closed set — an upper-layer request, an arriving protocol data
  unit, a timer expiry or a locally detected error — and naming it is
  what makes the rule checkable rather than narrative.
- A primitive with no generation rule is dead specification. Nothing can
  ever issue it, so every parameter and every receipt effect written for
  it is unreachable text, and the defect is invisible when primitives are
  read one at a time.
- Two rules sharing one state and one event, with no guard to separate
  them, leave the implementer to choose which primitive is issued. Two
  implementations will choose differently and the service will not
  interoperate, which is the failure mode this subclause exists to
  prevent.
- Guards resolve that ambiguity only when they actually differ. Two rules
  carrying the same guard text on the same state and event are the same
  defect wearing a guard, so the comparison is on the normalised guard,
  not on its presence.
- An event no rule ever consumes and a terminal state that still issues
  primitives are both signs that the state machine and the primitive
  catalogue were edited at different times. Neither is fatal on its own
  and both belong in the report.

## Workflow

1. Validate the declared sets first: states, events, primitives and the
   subset of states marked terminal. A terminal state that is not in the
   state set is a malformed specification, not a finding.
2. Validate each generation rule: its primitive, state and event all
   resolve against the declared sets, and its guard, when present, is
   text rather than a flag.
3. Build the generation map keyed on state and event, collecting every
   rule that lands on the same key.
4. Report non-determinism: a key carrying more than one rule where the
   guards do not all differ once normalised. A key whose rules all carry
   distinct guards is deterministic and is reported as guarded rather
   than as a finding.
5. Report the coverage gaps: primitives no rule issues, events no rule
   consumes, and rules that issue a primitive from a state declared
   terminal.
6. Roll the rule set up: counts of rules, distinct keys, guarded keys and
   findings, with a single compliant flag that is true only when no
   finding was raised.

## Pitfalls

- Accepting a rule that names a trigger in prose without an event from
  the closed set. It reads as complete and cannot be checked against
  anything, so the ambiguity survives to implementation.
- Treating the presence of a guard as resolving non-determinism. Only
  guards that differ separate two rules; identical guard text on one key
  is the original defect.
- Reporting unreachable primitives from the primitive catalogue alone. A
  primitive absent from the catalogue but named by a rule is the mirror
  defect and has to be refused, otherwise the rule silently invents a
  primitive.
- Leaving an unused event out of the report because nothing breaks. An
  event nothing consumes usually means a rule was deleted rather than
  that the event is spare, and it is the cheapest place to catch that.
- Comparing guards with their case and spacing intact. Two spellings of
  one guard then look distinct and the non-determinism goes unreported.

## Behavior contract (gate 3)

The set validation, rule validation, generation-map construction,
non-determinism detection, unreachable-primitive and unused-event
reporting, terminal-state checking and roll-up are exercised by the gate
3 contract test:
scripts/test_e5053_when_generated.py against
scripts/e5053_when_generated_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e5053_when_generated.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

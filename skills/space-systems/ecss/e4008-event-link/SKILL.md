---
name: e4008-event-link
description: "Assess the event links of an SMP Level-2 assembly artefact against ECSS-E-ST-40-08C clause 5.2.7.3: resolve each endpoint onto a declared event element with the right role, refusing a sink used as an emitter or a source used as a receiver, then compare the argument the source carries with the argument the sink expects, treating the void argument as a type of its own rather than an absent one. Fan-out from one source is admitted, fan-in into one sink raises an invocation-order advisory, and an identical link declared twice is refused. Use when an event never reaches its handler or an assembly rejects a wiring. Trigger: ecss, e-st-40-08c, smp-level-2, assembly-event-link, event-source-sink-role, event-argument-compatibility, event-fan-out-ordering, void-event-argument."
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
  tags: [ecss, e-st-40-08c-smp-level-2, e4008-event-link, smp-assembly-artefact, event-source-sink-binding, event-argument-compatibility, event-link-fan-out, void-event-argument]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SMP L2 — Event Link (space-systems/ecss/e4008-event-link)

Use when the task is an event link of an SMP Level-2 assembly artefact per
ECSS-E-ST-40-08C clause 5.2.7.3 — wiring an event source published by one
instance to an event sink published by another, and deciding whether the
emission will actually reach the handler.

## Domain quick reference

- An event element has a fixed role. A source emits; a sink receives. The two
  are not symmetric ends of one concept, so a link written with the roles
  swapped resolves to two real elements and still connects nothing.
- The argument is part of the contract, not decoration. A source that carries a
  duration and a sink that expects an integer are both well formed on their
  own; the link between them is what is not, and it is the only place the
  mismatch can be seen.
- The void argument means "this event carries no value". It is a declared
  argument type, distinct from an argument that was omitted from the model.
  Treating void as a wildcard lets a typed emission reach a handler that has
  nowhere to put it.
- Fan-out is the normal shape: one source reaching many sinks is how a single
  tick drives a whole subsystem, and none of those links constrains the others.
- Fan-in is legal but not neutral. Several sources reaching one sink are
  invoked in the order the assembly declares them, so the assembly file becomes
  load-bearing for behaviour; that deserves an advisory even when every link is
  individually valid.

## Workflow

1. Resolve the emitting endpoint onto a declared event element and require its
   declared role to be source; do the same for the receiving endpoint with the
   sink role, so a reversed link is named as such.
2. Read the argument type each end declares, defaulting an unstated argument to
   void rather than to "any".
3. Compare the two arguments for identity. Admit a void sink receiving a
   carried argument only when the assembly explicitly permits the argument to
   be discarded.
4. Refuse a link whose source and sink sit on the same instance unless the
   assembly permits self-links.
5. Form the (source path, sink path) signature and refuse a second link with a
   signature already present.
6. Group the accepted links by source to produce the fan-out map, and by sink
   to find the fan-in cases that need an invocation-order advisory.
7. Report the accepted links, the fan-out map, advisories and findings
   separately, so an ordering caution never reads as a rejection.

## Pitfalls

- Reading void as a wildcard. It makes every source appear connectable to every
  argument-less sink, and the defect only appears when the handler needs the
  value that was never delivered.
- Accepting a link because both endpoints exist. Existence is the first check,
  not the whole one; a sink named at the emitting end is a declared element and
  a wrong one.
- Reporting fan-in as an error. Several sources into one sink is a normal
  pattern; the risk is the hidden ordering dependency, which an advisory
  surfaces without failing a valid assembly.
- Deduplicating on the link name instead of the endpoint pair. Two differently
  named links between the same source and sink deliver the event twice, and
  only an endpoint-pair signature sees it.
- Assuming the argument is optional because the model compiled. Argument
  agreement is an assembly-time question; the two components are built
  separately and neither one can detect the mismatch on its own.

## Behavior contract (gate 3)

The role-checked endpoint resolution, argument-compatibility rule including the
void case and the discard option, self-link rule, duplicate-signature detection,
fan-out mapping and fan-in advisory are exercised by the gate 3 contract test:
scripts/test_e4008_event_link.py against
scripts/e4008_event_link_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e4008_event_link.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

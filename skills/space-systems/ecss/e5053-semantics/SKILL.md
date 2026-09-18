---
name: e5053-semantics
description: "Validate the semantics subclause of a SpaceWire service primitive against ECSS-E-ST-50-53 clause 5.2.2.2. Use when a protocol service definition declares its per-primitive parameter lists and they have to hold together before baseline: check every parameter for a name, a type and a presence category, refuse a conditional parameter with no stated condition, reject duplicate or unnamed entries, then align each request against its paired indication, response and confirm so no mandatory parameter is dropped across the pair and no parameter appears that the originator never supplied. Trigger: ecss, e-st-50-53, service-primitive-semantics-subclause, primitive-parameter-list, parameter-presence-category, conditional-parameter-condition, request-indication-pair-alignment, spacewire-service-definition."
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
  tags: [ecss, e-st-50-spacewire-scope, e5053-semantics, service-primitive-semantics-subclause, primitive-parameter-list, parameter-presence-category, request-indication-pair-alignment, spacewire-service-definition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS SpaceWire Service Primitive — Semantics Subclause (space-systems/ecss/e5053-semantics)

Use when the task is the semantics subclause of ECSS-E-ST-50-53 clause
5.2.2.2 — the parameter list a service primitive carries, the presence
category of each parameter, and whether the four primitives of one
service still describe the same exchange when read together.

## Domain quick reference

- The semantics subclause is the only place a primitive's parameters are
  declared. Each entry needs three things to be implementable: a name a
  caller can bind, a type that fixes its representation, and a presence
  category saying whether it is always there, there under a stated
  condition, or at the user's discretion.
- Conditional presence without the condition is the defect that looks
  like a complete entry. An implementer reading it has to guess when to
  supply the parameter, and two implementations will guess differently.
- A service is specified as up to four primitives around one exchange:
  request and confirm at the originating user, indication and response at
  the peer. They are not independent lists. A parameter the originator
  must always supply cannot vanish on the way to the indication, and the
  indication cannot require a parameter the request never carried unless
  the service provider itself generates it.
- Relaxation across a pair is legitimate in one direction only. A
  mandatory request parameter may arrive as conditional at the indication
  when the provider may legitimately withhold it; the reverse, a
  conditional request parameter that is mandatory at the indication, is
  unimplementable.
- Duplicate parameter names inside one primitive are a specification
  error rather than a finding: the list can no longer be indexed, so
  nothing downstream of it can be graded.

## Workflow

1. Validate each parameter entry: name present and non-empty, type
   present and non-empty, presence category inside the closed set of
   mandatory, conditional and optional, and a condition supplied for
   every conditional entry.
2. Build the per-primitive parameter index, refusing a list that names
   one parameter twice once case and surrounding space are normalised.
3. Split each primitive name into its service and its kind so the four
   primitives of a service can be grouped without relying on ordering.
4. Group the specification by service and check that a service declares
   at most one primitive of each kind.
5. For each service holding a request, align every partner primitive
   against it: report a mandatory request parameter absent from the
   partner, a partner parameter that the request never declared and that
   is not listed as provider generated, and a partner parameter whose
   presence category is stronger than the one the request gave it.
6. Roll the per-primitive and per-service findings up into a compliant
   count against the total so a partially clean service definition can be
   reported without hiding the failures.

## Pitfalls

- Grading a primitive in isolation. Every entry can be well formed and
  the service still be unimplementable, because the defect lives in the
  relationship between the request and its indication.
- Treating an optional parameter as free. Optional at the request and
  mandatory at the indication is the same unimplementable pairing as the
  conditional case, only harder to see.
- Accepting conditional presence with the condition written in the
  additional comments subclause. The condition has to sit with the
  parameter, otherwise the entry is incomplete wherever the reader is.
- Matching parameter names case sensitively. A list carrying both a
  lowercase and a capitalised spelling of one name is a duplicate, and
  passing it through produces two bindings for one field.
- Adding a provider-generated parameter to an indication without
  declaring it as such. It then reads as a request parameter that was
  lost, and the real finding is buried under a false one.

## Behavior contract (gate 3)

The parameter validation, presence-category enforcement, duplicate
rejection, primitive-name splitting, service grouping, pair alignment and
roll-up are exercised by the gate 3 contract test:
scripts/test_e5053_semantics.py against scripts/e5053_semantics_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e5053_semantics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

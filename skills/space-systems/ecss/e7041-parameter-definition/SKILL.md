---
name: e7041-parameter-definition
description: "Validate the on-board parameter definitions the parameter management service works from under ECSS-E-ST-70-41C clause 6.20.3. Use when a parameter catalogue is being reviewed before any report or set request is built against it: enforcing one unique parameter identifier per application process while letting two processes reuse a name, requiring every definition to declare the representation of its value, deriving the representable domain of an integer definition from its width and signedness rather than a hand-typed bound, narrowing that domain by any declared engineering limits, and deciding whether a candidate value belongs to a definition at all. Trigger: ecss, e-st-70-41-packet-utilization-scope, on-board-parameter-definition, parameter-identifier-uniqueness, parameter-value-representation, parameter-value-domain-check."
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
  tags: [ecss, e-st-70-41-packet-utilization-scope, e7041-parameter-definition, on-board-parameter-definition, parameter-identifier-uniqueness, parameter-value-representation, parameter-value-domain-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilization — On-board Parameter Definition (space-systems/ecss/e7041-parameter-definition)

Use when the task is the parameter definition of ECSS-E-ST-70-41C
clause 6.20.3 -- the two normative items that say what an on-board
parameter the parameter management service handles must be, before
any request to report or set one can be written.

## Domain quick reference

- Two items carry the whole clause, and both are about making a
  request answerable: a parameter must be nameable, and its value
  must be checkable.
- Nameable means a unique parameter identifier within its application
  process. Uniqueness is scoped to the process, so two processes may
  each hold a parameter of the same name and they are two parameters.
- Checkable means the definition declares how the value is
  represented -- what kind of value it is and, for an integer, how
  many bits it occupies and whether it is signed.
- The representable domain follows from that declaration. It is
  derived with integer arithmetic from the width and signedness, not
  typed in by hand, because a hand-typed bound drifts from the width
  it is supposed to describe.
- Engineering limits are a separate, narrower thing. A definition may
  declare limits inside the representable domain; limits outside it
  are a defect in the definition, not a wider domain.
- The effective domain a value must satisfy is the intersection:
  representable and within limits. Checking only one of the two lets
  a value through that the other rejects.
- A boolean takes exactly two values, an enumerated parameter exactly
  the codes it declares, and an octet string any byte sequence up to
  its declared length. Each needs its own membership rule.
- Read-only is a property of the definition, so it belongs here even
  though only the set request acts on it.

## Workflow

1. Normalize one definition at a time: identifier, application
   process, representation, and whatever the representation requires
   -- width and signedness for an integer, codes for an enumerated
   parameter, a length for an octet string.
2. Reject a representation the service does not handle rather than
   falling through to a permissive default.
3. Derive the representable domain from the declaration using integer
   arithmetic, so the bound and the width can never disagree.
4. Read any declared engineering limits, reject a lower limit above
   an upper one, and reject limits that fall outside the representable
   domain.
5. Intersect the two into the effective domain the definition will
   accept, and carry both so a rejection can say which one bit.
6. Normalize the catalogue, rejecting a repeated identifier inside one
   application process and allowing the same name under another.
7. Decide membership for a candidate value against the effective
   domain and the representation's own membership rule, and return the
   reason rather than a bare verdict.

## Pitfalls

- Making an identifier unique across the whole spacecraft. Two
  application processes then cannot each hold a parameter of the same
  name, which the clause allows and real catalogues rely on.
- Making an identifier unique per catalogue file rather than per
  application process. The same name under one process passes because
  it arrived in two files.
- Typing the representable bound in by hand next to the width. The
  two drift, and the definition then accepts a value the on-board
  representation cannot hold.
- Deriving an integer bound through floating-point exponentiation.
  It is not correctly rounded, so a wide parameter's bound lands one
  count out on one platform and not another.
- Treating engineering limits as the whole domain. A value inside the
  limits but outside the representation is accepted and truncates on
  the way down.
- Treating the representation as the whole domain. A value the
  hardware can hold but the subsystem cannot survive is accepted.
- Accepting a boolean as the integers zero and one. The set request
  then writes an integer into a parameter nothing will read as one.
- Leaving read-only off the definition. The set request has nowhere
  to look and writes a parameter that was never writable.

## Behavior contract (gate 3)

The definition normalization, representation handling, integer domain
derivation, engineering limit validation, effective domain
intersection, per-process identifier uniqueness, representation
membership rules and value decision are exercised by the gate 3
contract test: scripts/test_e7041_parameter_definition.py against
scripts/e7041_parameter_definition_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_parameter_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e7041-parameter
description: "Validate the parameters an on-board control procedure is started with under ECSS-E-ST-70-41C clause 6.18.3.2, where every procedure declares its parameters and an argument list is usable only when it matches that declaration. Use when the task is binding supplied arguments positionally or by name, checking arity and order, refusing a type the declared parameter cannot hold, refusing a value outside its declared range or outside its enumerated set, applying declared defaults for omitted optional parameters, and computing the encoded octet size of the bound set the start request has to carry. Trigger: ecss, e-st-70-41c, obcp-parameter-declaration, obcp-argument-binding, obcp-parameter-range-check, obcp-parameter-enumeration-membership, obcp-parameter-default-value, obcp-parameter-encoded-size."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-parameter, obcp-parameter-declaration, obcp-argument-binding, obcp-parameter-range-check, obcp-parameter-enumeration-membership, obcp-parameter-encoded-size]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — OBCP Parameter (space-systems/ecss/e7041-parameter)

Use when the task is the on-board control procedure parameter of
ECSS-E-ST-70-41C clause 6.18.3.2 -- the declared interface between a
start request and the procedure it starts, and the only place the
arguments in that request can be checked before the procedure runs on
them.

## Domain quick reference

- A parameter is a declaration, not a slot. It carries a name, a type,
  a width, and the values it is allowed to take -- a numeric range or
  an enumerated set. An argument is usable only against that
  declaration, and everything checkable here is checkable on the ground
  before the request is built.
- Order is part of the interface when arguments are positional. A start
  request that carries values in the declared order binds correctly; the
  same values in another order bind to the wrong parameters and each of
  them can still be individually in range, so the binding is silently
  wrong rather than rejected.
- Type compatibility is asymmetric and worth being strict about. A
  boolean is not a small unsigned integer, an integer is an acceptable
  real, and a real is not an acceptable unsigned integer. Accepting a
  real where an unsigned was declared moves a truncation decision into
  the on-board encoder, where nobody sees it.
- Optional parameters have declared defaults, and a default is applied
  rather than invented. A parameter omitted with no declared default is
  a missing argument, not a zero, and the distinction is the difference
  between a refused request and a procedure that runs on a value nobody
  chose.
- The encoded size follows from the declaration, not from the values.
  Every parameter contributes its declared width whatever value it
  takes, and the bound set rounds up to whole octets, which is what
  decides whether the start request fits at all.

## Workflow

1. Validate the declaration parameter by parameter: a non-empty unique
   name, a known type, a positive width in bits for the numeric types,
   a range whose lower bound does not exceed its upper, an enumerated
   set that is non-empty, and a default that itself satisfies the
   declaration.
2. Reject a declaration that places an optional parameter before a
   required one, because positional binding past that point is
   ambiguous.
3. Accept arguments either as an ordered sequence or as a mapping of
   name to value, and refuse a mapping naming a parameter the
   declaration does not have.
4. Bind: too many positional arguments is its own finding, and a
   missing required argument is another. An omitted optional parameter
   takes its declared default.
5. Check each bound value: type compatibility first, then the numeric
   range or the enumerated membership, so a value of the wrong type is
   never range-checked into a misleading second finding.
6. Compute the encoded size: sum the declared widths of the bound set
   and round up to whole octets.
7. Report the bound set, the findings and whether the argument list is
   usable, where usable means no finding at all rather than no fatal
   finding.

## Pitfalls

- Binding by position without checking the declared order. Every value
  can be in range and every one of them in the wrong parameter.
- Taking a boolean for a one-bit unsigned. The declaration says which
  one the procedure reads, and the two are not interchangeable.
- Substituting zero for an omitted parameter with no declared default.
  That is a value nobody chose, delivered to a procedure that cannot
  tell it apart from a deliberate one.
- Range-checking a value whose type was already wrong. The second
  finding is noise and it hides the first.
- Sizing the request from the values. A small value in a wide parameter
  still occupies the declared width.

## Behavior contract (gate 3)

The declaration validation, optional-after-required ordering rule,
positional and by-name binding, type-then-range checking, enumerated
membership, default application and encoded-size computation are
exercised by the gate 3 contract test:
scripts/test_e7041_parameter.py against
scripts/e7041_parameter_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_parameter.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

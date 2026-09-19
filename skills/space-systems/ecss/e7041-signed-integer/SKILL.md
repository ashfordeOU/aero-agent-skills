---
name: e7041-signed-integer
description: "Convert between a signed parameter value and its field code under ECSS-E-ST-70-41C clause 7.3.5, where negatives are held in two's complement and the leading bit carries the sign. Use when a telemetry value jumps to a huge positive number the moment it should go negative, or when a signed field is being sized: deriving the asymmetric range that reaches one further below zero than above it, sign extending on decode from the declared width, naming the most negative code that has no positive counterpart, and showing what the same code becomes when the field is read at the wrong width. Trigger: ecss, e-st-70-41-packet-utilisation-scope, pus-signed-integer-parameter-type, twos-complement-parameter-field, signed-field-sign-extension, asymmetric-signed-range, most-negative-parameter-code, signed-field-width-sizing."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-signed-integer, pus-signed-integer-parameter-type, twos-complement-parameter-field, signed-field-sign-extension, asymmetric-signed-range, most-negative-parameter-code, signed-field-width-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Signed Integer Parameter Type (space-systems/ecss/e7041-signed-integer)

Use when the task is the signed integer parameter type of
ECSS-E-ST-70-41C clause 7.3.5 -- the three normative items that put
the sign in the leading bit, hold negatives in two's complement, and
make the decode a sign extension from the declared field width.

## Domain quick reference

- The sign is not a separate flag. A negative value is the two's
  complement pattern for its magnitude, so the leading bit is set as
  a consequence rather than as a stored sign. A sign-and-magnitude
  reading of the same octets gives a different number for every
  negative value and the same number for every positive one, which is
  why the error survives a positive-only test campaign.
- The range is asymmetric and that is structural. A field of n bits
  spans minus-two-to-the-n-minus-one up to one below its magnitude,
  because zero takes one of the codes on the positive side. An eight
  bit field therefore reaches minus 128 but only plus 127.
- The most negative code has no positive counterpart. Negating it
  inside the same field overflows, so an absolute value, a sign flip
  or a symmetric limit check applied to it produces the same negative
  number back rather than an error.
- Decoding is a sign extension from the declared width, not from an
  octet boundary. A twelve bit signed field has its sign in bit
  twelve; extending from bit sixteen because the field happens to sit
  in two octets turns every negative value into a large positive one.
- Sizing a signed field is a two-ended question. The width has to
  cover the lowest value and the highest one, and the asymmetry means
  a range that is symmetric on paper may still cost an extra bit at
  the top while leaving a spare code at the bottom.
- A signed width is never the unsigned width plus nothing. One bit of
  the field pays for the sign, so a parameter reaching 127 needs
  eight signed bits where seven unsigned bits would have done.

## Workflow

1. Validate the field width, refusing a single bit field: there is no
   room for a sign and a magnitude together.
2. Derive the range from the width rather than accepting a declared
   one, so the asymmetry is always present and always consistent.
3. Categorize the value as below the floor, inside, or above the
   ceiling. Report the ceiling case with the reminder that it sits
   one short of the magnitude of the floor.
4. Encode an in-range value by masking it to the field width, which
   produces the two's complement pattern for a negative directly, and
   refuse anything outside the range rather than truncating it.
5. Decode by bounds-checking the code against the field, then sign
   extending from the declared width: a code at or above half the
   capacity is the negative branch.
6. When a value sits exactly on the floor, record that it has no
   positive counterpart, because every symmetric operation applied to
   it later will misbehave.
7. When a decode looks wrong, reproduce the value the same code gives
   at the width the reader actually used. That comparison identifies
   a sign-extension fault immediately.

## Pitfalls

- Reading the field as sign-and-magnitude. Positive values agree, so
  a test set without negatives passes completely, and every negative
  value in flight is wrong by a large and systematic amount.
- Extending the sign from an octet boundary instead of the declared
  width. A twelve bit minus one reads as 4095, which is in range for
  the containing field and looks like a real measurement.
- Assuming the range is symmetric. Limit checks written as plus or
  minus the same magnitude silently exclude the floor value, and a
  scaling that maps to the full symmetric span overflows at one end.
- Negating or taking the absolute value of the floor inside the same
  field. The result is the floor again, so a magnitude comparison
  against it succeeds when it should have raised an overflow.
- Sizing the field from the largest magnitude alone. The sign costs a
  bit and the two ends are not equivalent, so the width has to be
  derived from the pair of bounds, never from one of them.

## Behavior contract (gate 3)

The width validation, asymmetric range derivation, two's complement
encode, sign-extending decode, floor-value reporting, wrong-width
misread reproduction, two-ended width sizing and field assessment are
exercised by the gate 3 contract test:
scripts/test_e7041_signed_integer.py against
scripts/e7041_signed_integer_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e7041_signed_integer.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

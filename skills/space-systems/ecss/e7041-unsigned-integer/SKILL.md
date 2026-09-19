---
name: e7041-unsigned-integer
description: "Determine the unsigned integer parameter encoding of ECSS-E-ST-70-41C clause 7.3.4, where a sign-free whole number occupies a field whose width the format code fixes and whose bits run most significant first. Use when a counter reads back far lower than it should, or a parameter is being moved to a narrower field: computing the range from the width by exact bit arithmetic, refusing an over-range value instead of wrapping it, separating a negative value that needs a signed type from one that merely needs more bits, and saying whether a field is a whole number of octets before it is packed alone. Trigger: ecss, e-st-70-41-packet-utilisation-scope, pus-unsigned-integer-parameter-type, unsigned-field-width-range, big-endian-parameter-packing, unsigned-wraparound-refusal, parameter-field-narrowing, octet-aligned-parameter-field."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-unsigned-integer, pus-unsigned-integer-parameter-type, unsigned-field-width-range, big-endian-parameter-packing, unsigned-wraparound-refusal, parameter-field-narrowing, octet-aligned-parameter-field]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Unsigned Integer Parameter Type (space-systems/ecss/e7041-unsigned-integer)

Use when the task is the unsigned integer parameter type of
ECSS-E-ST-70-41C clause 7.3.4 -- the three normative items that fix
the range from the field width, lay the value down most significant
bit first, and leave no room for a value outside that range.

## Domain quick reference

- The width fixes the range and nothing else does. A field of n bits
  carries zero up to one below two-to-the-n, so an eight bit field
  tops out at 255 and a sixteen bit field at 65535. Both ends are
  properties of the width, not of the parameter's physical meaning.
- Zero is always representable and there is no sign. A parameter that
  can legitimately go below zero is not an unsigned parameter at all;
  widening the field does not make it one, and the fix is a change of
  parameter type rather than a change of width.
- Bits run most significant first. A field that happens to be a whole
  number of octets therefore packs straight into big-endian octets
  with no further rule; a field that is not, such as a twelve bit
  counter, only exists beside its neighbours inside a shared octet
  run and cannot be lifted out on its own.
- Sizing is exact integer arithmetic. The narrowest field for a value
  is the bit length of that value, so 255 takes eight bits and 256
  takes nine. A rounded logarithm lands on the wrong side of exactly
  those boundaries, and differently on different machines.
- An over-range value is a rejected value. Two's complement hardware
  and most languages will happily wrap it, and the wrapped number is
  perfectly plausible -- a counter that reads 4 after 260 increments
  looks like a counter, not like a fault.
- Narrowing a parameter is a range question, not a storage question.
  The move is lossless only if the largest value the parameter can
  actually reach still fits the destination, and the observed maximum
  from a past mission is evidence, not a bound.

## Workflow

1. Validate the field width against the permitted range and derive
   the value range from it, keeping the range derived rather than
   declared so the two can never disagree.
2. Categorize the value against that range before encoding: below
   zero, inside, or above the ceiling. The three cases have different
   repairs and must not collapse into one "does not fit".
3. For an in-range value, produce the bit pattern most significant
   bit first at exactly the declared width.
4. For an over-range value, report the width the value would need,
   computed as its bit length, and refuse the encoding rather than
   letting the value wrap.
5. For a negative value, report that the parameter type is wrong
   rather than the width, because no unsigned width can carry it.
6. Check octet alignment before packing a field on its own, and pack
   an aligned field big endian. Report an unaligned width with the
   octet count it would occupy alone.
7. When a narrowing is proposed, test the largest value the parameter
   can reach against the destination range and state the result as a
   lossless or lossy move.

## Pitfalls

- Letting an over-range value wrap. The wrapped value is in range, is
  monotonic-looking, and passes every downstream check; the anomaly
  surfaces months later as a counter that appears to have reset.
- Widening the field to accommodate a negative value. No unsigned
  width represents a negative number, so the extra bits change the
  ceiling and nothing else while the sign error stays exactly where
  it was.
- Deriving the width from a rounded logarithm. The interesting cases
  are the powers of two, and that is precisely where the rounding
  differs between platforms; the bit length of the value is exact.
- Lifting an unaligned field out on its own. A twelve bit counter has
  no standalone octet representation; reading it as a two octet value
  drags in four bits of whatever parameter shares the run.
- Reading the observed maximum as the range when narrowing. The
  largest value seen in flight is a sample, and narrowing a field to
  it hands the parameter a ceiling it was never designed against.

## Behavior contract (gate 3)

The width validation, range derivation, alignment test, exact minimum
width, encode refusal on an over-range and a negative value, big
endian octet packing, narrowing test and field assessment are
exercised by the gate 3 contract test:
scripts/test_e7041_unsigned_integer.py against
scripts/e7041_unsigned_integer_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e7041_unsigned_integer.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

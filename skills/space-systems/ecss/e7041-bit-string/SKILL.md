---
name: e7041-bit-string
description: "Validate a bit-string parameter field against ECSS-E-ST-70-41C clause 7.3.7, where an ordered run of bits with no numeric meaning is carried either at a length the format code fixes or behind a count field. Use when a status word comes back one bit adrift, or when a variable pattern is outgrowing its count field: holding a fixed field to exactly its declared length rather than padding or truncating it, appending pad bits only at the trailing end and keeping them out of the value, bounding a variable pattern by what its count field can announce, and treating a zero-length pattern as legitimate only where the length travels with it. Trigger: ecss, e-st-70-41-packet-utilisation-scope, pus-bit-string-parameter-type, bit-string-octet-padding, bit-string-count-field-width, fixed-length-bit-field, variable-length-bit-field, bit-string-declaration-order."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-bit-string, pus-bit-string-parameter-type, bit-string-octet-padding, bit-string-count-field-width, fixed-length-bit-field, variable-length-bit-field, bit-string-declaration-order]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Bit-String Parameter Type (space-systems/ecss/e7041-bit-string)

Use when the task is the bit-string parameter type of
ECSS-E-ST-70-41C clause 7.3.7 -- the eight normative items covering
how the length is fixed or announced, how the run is laid down and
padded, and what the pad is and is not allowed to mean.

## Domain quick reference

- A bit-string is a pattern, not a number. It has no value in the
  arithmetic sense, so leading zeros are part of it, a shorter run is
  never equal to a longer one that begins the same way, and nothing
  downstream may normalise it.
- The length arrives one of two ways and only one of them travels
  with the data. A fixed field takes its length from the parameter's
  format code, which both ends already hold; a variable field carries
  a count ahead of the bits, and the count field has its own width.
- A fixed field is exactly its declared length. Padding a short
  pattern out adds bits the sender never set, and truncating a long
  one drops bits the sender did set. Both produce a well-formed field
  that carries the wrong pattern, so both are refused rather than
  repaired.
- A variable field is bounded by its count, not by the packet. A
  count field of n bits announces at most two-to-the-n minus one
  bits, so a pattern that outgrows the count field cannot be carried
  however much room the packet has left.
- Bits go down in declaration order, first declared bit first. The
  order is a property of the parameter definition, and any encoding
  that reverses it inside an octet delivers a mirrored status word
  that still passes every length check.
- A run that is not a whole number of octets is padded at the
  trailing end to reach the boundary. The pad goes after the last
  declared bit, never before the first, and it takes a fixed value so
  two encodings of the same pattern compare equal octet for octet.
- The pad is not part of the value. A reader that takes the whole
  octet instead of the declared length reads a longer pattern than
  was sent, and the extra bits look like real status flags sitting at
  their inactive value.
- A zero-length pattern is legitimate for a variable field and
  meaningless for a fixed one. The variable case sends a count of
  zero and no payload octet; the fixed case has a declared length
  that an empty pattern cannot satisfy.

## Workflow

1. Validate the pattern as an ordered run of zeros and ones. A
   pattern handed over as an integer has already lost its leading
   zeros and its length, and cannot be recovered.
2. Read the format code to decide which length regime applies:
   variable with a count field, or fixed at the declared length.
3. For a fixed field, compare the pattern length with the declared
   length and refuse both the short and the long case by name, so the
   report says whether bits would be invented or dropped.
4. For a variable field, validate the count field width and refuse a
   pattern longer than that width can announce, naming the ceiling.
5. Compute the pad from the length: the bits needed to reach the next
   octet boundary, zero when the length is already a multiple.
6. Pack by appending the pad after the last declared bit at the fixed
   pad value, then laying the padded run down most significant bit
   first so declaration order is preserved.
7. Unpack by cutting the run back to the declared or announced
   length, discarding the pad. Refuse a declared length longer than
   the octets carry, and refuse a trailing remainder of a whole octet
   or more, which means the field boundaries do not line up.
8. Report the pad count alongside the result so a reader can see how
   many bits of the last octet carry nothing.

## Pitfalls

- Handling the pattern as an integer. The length and the leading
  zeros both vanish, and a four bit pattern of zeros becomes
  indistinguishable from a one bit pattern of zero.
- Padding a short pattern into a fixed field. The field then looks
  correct at every later stage, and the invented bits sit at their
  inactive value, which is exactly what a healthy status word looks
  like.
- Taking the whole final octet on decode. The pad bits are read as
  real flags, so a five bit status word delivers eight flags of which
  three are permanently inactive and nobody questions them.
- Sizing the count field from today's longest pattern. The count
  field width is part of the packet layout and cannot be widened
  later without a format change, so a pattern that grows past its
  ceiling stops being transmissible.
- Putting the pad ahead of the pattern, or reversing the run inside
  an octet. Both keep the length correct and shift every bit's
  meaning, and neither is caught by a length check or a checksum.

## Behavior contract (gate 3)

The pattern validation, fixed-length enforcement in both directions,
count-field ceiling, trailing pad computation, order-preserving pack
and unpack, pad stripping, length-aware equality and field assessment
are exercised by the gate 3 contract test:
scripts/test_e7041_bit_string.py against
scripts/e7041_bit_string_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_bit_string.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

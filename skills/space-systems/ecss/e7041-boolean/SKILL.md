---
name: e7041-boolean
description: "Validate and encode a boolean parameter field under ECSS-E-ST-70-41C clause 7.3.2, where the boolean type admits exactly one format code and occupies exactly one bit. Use when the task is laying out on-board flags or reading them back off the wire: accepting only the one defined type pair, refusing the integers 0 and 1 and the string forms that a looser encoder would quietly accept as truth values, packing a run of flags most significant bit first so the first field of the definition is the first bit, and counting the pad bits a short run leaves carrying nothing. Trigger: ecss, e-st-70-41c, pus-packet-field-type, boolean-parameter-field, one-bit-boolean-field, boolean-field-truth-value, boolean-flag-bit-packing, boolean-field-padding-bits."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-boolean, boolean-parameter-field, one-bit-boolean-field, boolean-field-truth-value, boolean-flag-bit-packing, boolean-field-padding-bits]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Boolean Parameter Field (space-systems/ecss/e7041-boolean)

Use when the task is the boolean packet field type of ECSS-E-ST-70-41C
clause 7.3.2 -- the narrowest parameter field there is, one bit wide,
with a single defined format code, and the one whose encoding goes
wrong most often precisely because it looks too simple to check.

## Domain quick reference

- The boolean type defines exactly one format code. That is not a
  default among several; anything else in the format position means
  the definition names a different type, most often an enumerated
  field of one bit, which is a different thing on the ground side.
- The field is one bit. It is not one octet with seven bits ignored,
  and a definition that gives it an octet has not made it safer, it
  has made the structure disagree with the standard layout.
- A set bit is true and a clear bit is false. The mapping is fixed, so
  an implementation that inverts it locally produces a packet that
  parses perfectly and reports every flag backwards.
- Only a genuine truth value may be encoded. The integers 0 and 1, the
  strings "true" and "", and a null are all refused, because each of
  them silently reaches a plausible bit through a language's own
  truthiness rules rather than through the field definition.
- Bit order within an octet is most significant first, so the first
  boolean of the definition is the leading bit on the wire. Reversing
  it produces a mirror image that only shows up when the flags are not
  symmetric.
- Padding is not a field. A run of two flags travels in one octet with
  six pad bits, and decoding takes its count from the definition, not
  from the octets received, or the padding comes back as six false
  flags nobody declared.
- A lone boolean in its own structure spends seven of its eight
  transmitted bits on nothing. That is legal and sometimes necessary,
  but it is worth surfacing whenever neighbouring flags could share
  the octet.

## Workflow

1. Validate the type pair: the boolean type code with its one defined
   format code, both as whole numbers. A truth value in either
   position is an input error, not a zero or a one.
2. Report the width as one bit; never let a caller supply it.
3. Encode each value, accepting a genuine truth value only and
   refusing every convertible stand-in with the value and its type
   named in the message.
4. Pack the run into octets most significant bit first, appending
   clear pad bits to reach the next octet boundary, and report the
   fields, the bits used and the pad bits separately.
5. Decode a bit back to a truth value, refusing anything that is not
   the integer 0 or 1.
6. Unpack a run using the field count from the definition, refusing a
   count the octets cannot carry, and never decoding the padding.
7. Assess a structure of boolean fields: validate every field's pair
   and name, pack, round-trip to confirm the layout reverses, and
   report the octets, the pad bits, the round-trip result and the
   findings for wasted bits, a lone flag and duplicate names.

## Pitfalls

- Accepting the integer 1 as true. Every value except zero then
  becomes true, including the 2 that meant an error code, and the flag
  reads as set for the rest of the mission.
- Reading a non-empty string as true. The string "false" is non-empty,
  and a configuration file that spells the flag out sets it.
- Giving the field a whole octet. The structure parses in isolation
  and desynchronises the moment a real definition packs it beside
  other flags.
- Packing least significant bit first. The octet looks reasonable, the
  round trip inside one implementation succeeds, and the ground system
  reads the flags in reverse order.
- Decoding as many flags as the octets can hold. The pad bits come
  back as declared-looking false flags and shift every field after
  them if the run is part of a larger structure.
- Treating the padding count as an error. It is information: the
  finding is about whether nearby flags should share the octet, not
  about the field being wrong.

## Behavior contract (gate 3)

The single type pair validation, the one-bit width, the refusal of
non-truth values on encode, the bit decode, the most-significant-bit
first packing with pad bits, the unpack that takes its count from the
definition, the round trip and the structure findings are exercised by
the gate 3 contract test: scripts/test_e7041_boolean.py against
scripts/e7041_boolean_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e7041_boolean.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

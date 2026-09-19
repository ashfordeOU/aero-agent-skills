---
name: e7041-packet-field-type-code-general
description: "Derive the width of a parameter field, and the bit layout of the structure holding it, from the packet field type code and format code pair of ECSS-E-ST-70-41C clause 7.3.1. Use when the task is reading or writing a parameter structure and the widths have to come from the type pair rather than from a guess: looking a tabulated format up for the integer, real and time types, deriving a width from the format code itself for the enumerated and string types, refusing an undefined pair outright, leaving a deduced field to the containing definition, then accumulating bit offsets and reporting the padding to the next octet boundary. Trigger: ecss, e-st-70-41c, pus-packet-field-type, packet-field-type-code-pair, packet-field-format-code, parameter-field-bit-width, parameter-structure-bit-offset, packet-field-octet-alignment."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-packet-field-type-code-general, packet-field-type-code-pair, packet-field-format-code, parameter-field-bit-width, parameter-structure-bit-offset, packet-field-octet-alignment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Packet Field Type Code, General (space-systems/ecss/e7041-packet-field-type-code-general)

Use when the task is the general packet field type code rules of
ECSS-E-ST-70-41C clause 7.3.1 -- how the type code and the format code
together name a parameter field's kind and its width, and what that
width does to the bit layout of the structure the field sits in.

## Domain quick reference

- A field type is an ordered pair, and neither half is meaningful
  alone. The type code says what kind of value the field carries; the
  format code selects one member within that kind. The same format code
  number means different widths under different type codes.
- Types fall into three groups by how the width is obtained. One group
  looks the format code up in a tabulated set -- the integers, the
  reals, the two time types. One group derives the width from the
  format code arithmetically: an enumerated field is that many bits, a
  string is that many octets or characters. One type, the deduced one,
  has no width at all until the containing definition supplies it.
- The signed and unsigned integer types share a format code table. That
  is a convenience, not an identity: the same pair gives the same
  width but a different interpretation, so a width match is never
  enough to confirm a type.
- An undefined pair is refused, never rounded to the nearest defined
  one. A field silently given a plausible width shifts every field
  after it and the corruption appears far from its cause.
- A deduced field defaulted to any width is the same defect wearing a
  reasonable number. Its width is external input; absence of that input
  is an error in the definition.
- Offsets accumulate in bits, not octets. A structure is only a whole
  number of octets when its fields happen to sum to a multiple of
  eight, and the pad bits to the next boundary are part of the layout.
- A field that begins on an octet boundary is read whole octets at a
  time whatever its width. The awkward one begins part way into an
  octet and does not finish inside it, because extracting it needs a
  mask and a shift across two octets.

## Workflow

1. Validate the type code against the defined set and the format code
   as a non-negative whole number. A boolean value in either position
   is an input error, not a zero or a one.
2. For a tabulated type, look the format code up and refuse one the
   table does not define, naming the codes that are defined.
3. For a derived type, check the format code against the span the type
   allows and multiply by the unit: one bit for an enumerated field,
   eight for an octet or character string.
4. For the deduced type, return no width and require the containing
   definition to supply one; refuse a supplied width that is not a
   positive whole number.
5. Walk the fields in order, giving each the running bit offset and
   its octet offset, and accumulate the total width.
6. Compute the pad bits to the next octet boundary and the resulting
   whole octet size.
7. Name the fields that begin mid-octet and run past that octet.
8. Report the resolved fields, the total in bits and octets, the
   padding, the straddling fields and any duplicate field name.

## Pitfalls

- Reading the format code as a width for every type. It is the width
  only for the enumerated and string types; for the integers and reals
  it is a table index, and 13 means sixteen bits rather than thirteen.
- Assuming a format code defined under one type is defined under
  another. The tables differ, and the pair is what has to be checked.
- Defaulting a deduced field to thirty-two bits. Every field after it
  is then misaligned in a structure that still parses.
- Accumulating offsets in octets. Sub-octet fields collapse into the
  same offset and the layout silently loses them.
- Reporting a structure size in octets without its pad bits. The
  reported size and the summed field widths then disagree by less than
  one octet, which is the hardest size mismatch to spot.
- Calling every multi-octet field a straddling field. An aligned
  thirty-two bit field crosses boundaries and costs nothing; the
  finding is about fields that start mid-octet.

## Behavior contract (gate 3)

The type and format code validation, the tabulated and derived width
resolution, the refusal of an undefined pair, the deduced field
contract, the bit offset accumulation, the octet alignment and padding
computation, the straddling field detection and the structure report
are exercised by the gate 3 contract test:
scripts/test_e7041_packet_field_type_code_general.py against
scripts/e7041_packet_field_type_code_general_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_packet_field_type_code_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

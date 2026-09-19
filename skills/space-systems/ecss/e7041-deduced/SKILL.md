---
name: e7041-deduced
description: "Determine the type a deduced parameter takes from an earlier field of the same packet, under ECSS-E-ST-70-41C clause 7.3.12. Use when a packet definition leaves a parameter untyped until run time: checking that the deducing field precedes the field it settles, that every value the selector admits maps to a type the reader knows, and that the mapping covers the selector value space, because one unmapped value does not spoil a single parameter, it moves every field after it and leaves the rest of the packet unreadable. Trigger: ecss, e-st-70-41c, pus-deduced-data-type, run-time-parameter-type-deduction, selector-field-precedence, deduced-type-mapping-coverage, unmapped-selector-value, variable-layout-packet-sizing."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-deduced, pus-deduced-data-type, run-time-parameter-type-deduction, selector-field-precedence, deduced-type-mapping-coverage, variable-layout-packet-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Deduced Data Type (space-systems/ecss/e7041-deduced)

Use when the task is the deduced data type of ECSS-E-ST-70-41C clause
7.3.12 — the three normative items that let a parameter's type be
settled while the packet is being read instead of in its definition,
and the structural conditions that have to hold for the reading to
work at all.

## Domain quick reference

- Almost every parameter has its type fixed in the packet definition.
  A deduced parameter does not: its type comes from the value of
  another field of the same packet — the parameter identifier ahead of
  a value in a housekeeping report, the type code ahead of a payload
  in a memory-load command.
- The deducing field has to come earlier. A reader consumes a packet
  in order, so a selector that sits after the field it settles has
  never been read when the decision is needed. This is a position
  check on the definition, and it is decidable at review time.
- Every value the selector admits maps to exactly one known type. The
  reader gets no second attempt: an unmapped value leaves it unable to
  say how many bits this field occupies.
- That is the consequence people miss. A deduced field does not make
  one parameter uncertain, it makes the remainder of the packet
  uncertain. Everything after it has moved, so a single unmapped
  selector value turns a readable packet into an unreadable one.
- The type each value maps to must itself be known and sized. A
  mapping onto a type name the catalogue does not carry is the same
  failure one step later.
- Coverage of the mapping over the selector's value space is the
  review-time measure. A three-bit selector has eight values whatever
  the definition lists; the gap between the values it admits and the
  values the mapping settles is where the unreadable packets live.
- Chains resolve as long as each link is settled before it is needed.
  A deduced field may settle a later one; a cycle, or a selector
  placed after what it selects, resolves nothing.
- A layout containing a deduced field is variable-length by
  construction. Two selector values giving two widths is the normal
  case, not a defect — but a length budget taken from one of them is.

## Workflow

1. Normalise the layout in order, recording each field's position and
   refusing a duplicate name, so a selector reference is unambiguous.
2. Refuse a deduced field whose selector has not already appeared. It
   is the one condition no run-time check can recover from.
3. Normalise the catalogue of types and their widths; a deduced field
   is only as resolvable as the types its mapping names.
4. Measure coverage: the selector's value space against the values the
   mapping settles, and the values the selector admits against the
   same. Report both gaps — an admitted-but-unmapped value is a
   readability defect, a mapped-but-never-admitted value is stale
   definition debt.
5. Resolve a concrete packet by walking the layout with the selector
   values in hand, settling each deduced field as it is reached and
   accumulating the width.
6. Report the total width, the octet alignment and the distinct widths
   the sample selector sets produce, so the variable length is stated
   rather than discovered.

## Pitfalls

- Placing the selector after the field it settles. The definition
  reads sensibly and no packet using it can be decoded.
- Mapping only the values currently in use. The selector's field width
  admits every value it can hold, and an unused code eventually gets
  used.
- Treating an unmapped value as one bad parameter. The reader has lost
  its position; every field after it is wrong too.
- Sizing the packet from one selector value. A deduced layout has as
  many lengths as the mapping has widths.
- Leaving mapping entries for selector values the definition no longer
  admits. They look like coverage and settle nothing.
- Assuming a catalogue type exists because the mapping names it. A
  name is not a width.

## Behavior contract (gate 3)

The catalogue normalisation, ordered layout validation, selector
precedence refusal, mapping-coverage measurement, selector-value
resolution, whole-layout sizing with octet alignment and the structural
assessment are exercised by the gate 3 contract test:
scripts/test_e7041_deduced.py against scripts/e7041_deduced_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_deduced.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

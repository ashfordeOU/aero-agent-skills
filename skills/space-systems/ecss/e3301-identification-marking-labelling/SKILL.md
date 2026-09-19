---
name: e3301-identification-marking-labelling
description: "Evaluate the identification and marking plan for delivered mechanism hardware against ECSS-E-ST-33-01 clause 4.2.4.1. Use when parts, subassemblies and the assembled mechanism all have to leave the factory carrying a readable, unique identity a review can trace back to its parent. Builds each identity from part number and serial, detects a repeated identity and an orphan subassembly, sizes the character height the marking field can support, and routes an item to a shallower method or to an attached tag when direct marking would be illegible or would cut too deep into a thin or fracture-critical wall. Trigger: ecss, e-st-33-01, mechanism-hardware-identification, mechanism-part-marking-method, marking-character-height, bag-and-tag-identification, mechanism-serial-uniqueness, mechanism-subassembly-traceability."
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
  tags: [ecss, e-st-33-mechanisms-scope, e3301-identification-marking-labelling, mechanism-hardware-identification, mechanism-part-marking-method, marking-character-height, mechanism-serial-uniqueness, mechanism-subassembly-traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Identification, Marking and Labelling (space-systems/ecss/e3301-identification-marking-labelling)

Use when the task is clause 4.2.4.1 of ECSS-E-ST-33-01 — making sure
every delivered mechanism, part and subassembly carries an identity, and
that the way that identity is applied neither damages the hardware nor
becomes unreadable.

## Domain quick reference

- The identity of a delivered item is the part number together with its
  serial number. The part number alone says what it is; only the serial
  ties a life record, a test history and a non-conformance to the
  physical object in the box.
- A marking method has a smallest character it can reliably produce, and
  the part has a finite marking field. Whether an identity fits is
  therefore arithmetic: the field area shared among the characters, each
  a fixed fraction of its height wide, sets the height available, and
  that is compared with the method's minimum.
- Every marking that penetrates the surface removes material. On a thin
  wall that penetration is a meaningful fraction of the section, and on
  a fracture-critical item it is a stress concentration in a part whose
  whole justification is that it has none.
- Methods trade durability against invasiveness. Engraving survives
  handling and cleaning but cuts; ink survives neither but cuts nothing;
  a label or a tag touches the part not at all and can be lost. The
  order of preference runs from most durable to least, and the first
  permitted method that fits is the answer.
- An indirect identification is a real answer, not a failure, but it is
  a reportable one. A tagged item is identified only as long as the tag
  stays with it, so the plan has to say which items depend on that.
- A subassembly is traceable only through a parent that is itself
  identified. A parent missing from the delivery, or present but
  unserialised, breaks the chain at that link no matter how well the
  child is marked.

## Workflow

1. Validate each item: identifier, part number, surface finish, marking
   field area, wall thickness and delivery status, with a serial number
   required of anything delivered. An unknown finish or a non-positive
   dimension is an input error.
2. Build the identity string for each item and count the characters it
   has to carry.
3. Compute the character height the marking field supports for that
   character count and row layout, remembering that an odd count over
   two rows reserves an unused cell.
4. Test each method in order of durability: refuse a finish it does not
   suit, refuse a penetrating method on a fracture-critical item, and
   refuse a penetration deeper than the allowed fraction of the wall,
   absorbing representation error at the boundary with a named
   tolerance.
5. Take the first permitted method whose minimum character height the
   field supports; where the method uses a tag or a label rather than
   the part surface, the field test does not apply but the fallback is
   recorded.
6. Detect a repeated identity across the delivered items and check every
   declared parent exists, is not the item itself, and carries a serial.
7. Report per-item routes, the fraction of items directly marked, and
   every finding.

## Pitfalls

- Marking a part number without a serial on delivered hardware. The item
  then has a type but no identity, and two of them on the same bench
  cannot be told apart by any record.
- Choosing a marking method from the drawing note without checking the
  field. A method that is correct for the material still produces
  characters below its own minimum if the flat it is applied to is too
  small, and the result is unreadable rather than wrong.
- Stamping a thin-walled or fracture-critical item. The identity is
  permanent and so is the notch; a part qualified on the absence of
  stress raisers acquires one at the last operation before delivery.
- Treating a tag as equivalent to a marking. It is an acceptable route
  when nothing else works, but the item is identified only while the tag
  is attached, and the plan owes an explicit list of which items are in
  that state.
- Marking a subassembly whose parent has no serial. The child is
  traceable to a part type, not to an assembly, so the as-built record
  cannot be reconstructed from the hardware alone.
- Reusing a serial number across a build standard change. Two physical
  items then share one identity, and every life and test record after
  that point belongs to an ambiguous object.

## Behavior contract (gate 3)

The item validation, identity construction, character-height sizing,
method permission rules, route selection, duplicate detection and
parent traceability are exercised by the gate 3 contract test:
scripts/test_e3301_identification_marking_labelling.py against
scripts/e3301_identification_marking_labelling_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_identification_marking_labelling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

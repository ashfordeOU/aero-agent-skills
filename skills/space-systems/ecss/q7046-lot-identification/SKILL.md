---
name: q7046-lot-identification
description: "Define the identity a threaded fastener lot carries into stores: the composed lot identifier, the marking the part can physically hold, the traceability chain behind it and the package it ships in. Use when a lot is about to be marked, labelled and packed and someone must say whether it can be told apart later: compose the identifier from manufacturer, part, heat, charge and date code over a restricted character set, size the marking against the area a hexagon head actually offers, hold the stamp depth to a fraction of the head height, keep the mark off the run-out of a fatigue part, and refuse a package holding two production lots. Trigger: ecss, q-st-70-46-threaded-fasteners, fastener-lot-identifier-composition, fastener-head-marking-capacity, fastener-marking-depth-limit, fastener-traceability-chain-gap, fastener-mixed-lot-package."
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
  tags: [ecss, q-st-70-46-threaded-fasteners, q7046-lot-identification, fastener-lot-identifier-composition, fastener-head-marking-capacity, fastener-marking-depth-limit, fastener-traceability-chain-gap, fastener-mixed-lot-package, fastener-package-label-content]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Lot Identification (space-systems/ecss/q7046-lot-identification)

Use when the task is the identification and packaging part of the
ECSS-Q-ST-70-46 manufacturing clause -- giving a finished fastener lot
an identity that survives the store, the kit and the bench, and
proving that identity leads back to the melt.

## Domain quick reference

- A lot identifier is composed, not written. It carries the
  manufacturer code, the part code, the material heat, the
  heat-treatment charge and the date code, each over a restricted
  character set, so two lots cannot collide and a reader can take the
  identifier apart again without a key.
- The separator has to be excluded from the fields. A field containing
  the separator parses into a different number of fields, which is how
  an identifier that composed cleanly reads as a different lot
  downstream.
- Marking is bounded by the part, not by the wish list. The area a
  hexagon head offers follows from its width across flats, only part
  of it is markable once the recess, chamfer and edge distance are
  taken out, and each character needs its spacing as well as its own
  body. A small head holds the property class and little else.
- The answer to marking that does not fit is to move it, not to shrink
  it. The surplus goes on the package and that move is recorded, so
  the evidence still exists even though the part cannot carry it.
- Depth is the second bound. A stamp deeper than a fraction of the
  head height is a notch, and a notch in a head is still a notch.
- Location is the third. The shank and the thread run-out are exactly
  where a fatigue-critical part is worked hardest, so the mark that
  would be convenient there is barred on that duty and permitted off
  it.
- Traceability is a chain and only as good as its weakest link. Every
  required link from the melt certificate to the package record has to
  be present and non-empty; one gap makes the lot untraceable whatever
  the other links prove.
- A package holds one production lot. Two lot codes in one package is
  a segregation failure no downstream inspection can undo, because the
  evidence for each part has already been mixed.

## Workflow

1. Compose the lot identifier from its five fields, normalizing and
   validating each against the character set and the field length,
   and confirm it parses back to the same fields.
2. Size the markable area from the head width across flats, take the
   character cell including its spacing, and compare the capacity
   against the characters the marking actually needs.
3. Where the marking does not fit, raise the action that moves the
   surplus to the package rather than shrinking the characters.
4. Check the stamp depth against the fraction of head height that
   separates a mark from a notch.
5. Check the marking location against the duty, barring the shank and
   the thread run-out on a fatigue-critical part.
6. Walk the traceability chain for empty or absent links, check the
   package for a second lot code, complete the label, then roll the
   worst consignment up into the delivery disposition.

## Pitfalls

- Writing the identifier free-hand. An identifier assembled by habit
  rather than composed collides with another lot eventually, and the
  collision shows up in a quarantine, which is the worst place to
  discover it.
- Letting the separator into a field. The string looks right and
  parses into the wrong number of fields, so the lot silently becomes
  a different lot to every system that reads it.
- Marking to the drawing without measuring the head. Small heads hold
  a handful of characters, and a marking specification that ignores
  the area either gets stamped too small to read or too deep to
  survive.
- Shrinking the characters to make the marking fit. Legibility is part
  of the requirement, so the surplus moves to the package; a mark that
  cannot be read has the same value as no mark.
- Stamping deeper for legibility. Depth is limited because the mark is
  a notch, and a deep mark on a head is a crack starter dressed as
  good practice.
- Marking the run-out because there is room. That is the most worked
  region of a fatigue-critical part, which is exactly why there is
  room there and why the mark is barred.
- Treating one missing traceability link as a paperwork item. The
  chain either reaches the melt or it does not, and a lot with a gap
  cannot be tied to its evidence however complete the rest looks.
- Accepting a package with two lot codes and sorting it later. The
  evidence was mixed at packing, so no later inspection can say which
  part came from which lot.

## Behavior contract (gate 3)

The identifier composition and round trip, head marking area and
character capacity, marking depth limit, location admissibility,
traceability chain gaps, mixed-lot detection, label completeness and
delivery roll-up are exercised by the gate 3 contract test:
scripts/test_q7046_lot_identification.py against
scripts/q7046_lot_identification_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7046_lot_identification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

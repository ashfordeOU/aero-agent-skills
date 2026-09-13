---
name: e2008-critical-materials-interface-listing
description: "Audit the parts, materials and processes list of a solar array for the critical interface data it owes, anchored at ECSS-E-ST-20-08C clause 4.4. Use when an array declared-materials list is submitted for review: derive from each entry whether it sits at a critical array interface rather than reading a hand-set criticality flag, list the identification data its kind owes and the interface data its criticality adds, screen a bonded non-metallic item against its total-mass-loss and collected-volatile limits, measure the anodic-index separation of a metal-to-metal couple, and accept or reject the list entry by entry. Trigger: ecss, e-st-20-08c, solar-array-pmp-list, photovoltaic-declared-materials-list, critical-interface-data, solar-array-material-outgassing, solar-array-galvanic-couple, array-interface-qualification-reference, cell-to-coverglass-interface, interconnect-to-substrate-interface."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-critical-materials-interface-listing, solar-array-pmp-list, photovoltaic-declared-materials-list, critical-interface-data, solar-array-material-outgassing, solar-array-galvanic-couple, array-interface-qualification-reference]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Critical Materials Interface Listing (space-systems/ecss/e2008-critical-materials-interface-listing)

Use when the task is the listing obligation of ECSS-E-ST-20-08C clause 4.4
-- the interface data an array parts, materials and processes list has to
carry alongside the ordinary identification of each entry, and which
entries of the list actually owe it.

## Domain quick reference

- The list is the array's single reviewable record of what it is made of,
  and its weakness is always the same one: it identifies items well and
  describes the joints between them badly. The clause closes that gap by
  making the interface part of the entry, not a separate drawing note.
- Every entry is one of three kinds -- a delivered part, a bulk material
  or a process applied to one of them -- and the kind alone fixes the
  identification data owed: designation, supplier and specification for
  all three, plus a part number, a material family or a process
  reference respectively.
- Criticality is derived, never declared. An entry that carries a
  criticality flag set by the compiler of the list is asserting the
  conclusion the review is meant to reach. Derive it instead from what
  the entry states: a named array interface (cell to coverglass, cell to
  interconnect, interconnect to substrate, substrate to structure,
  harness to array connector, coating to substrate), an exposed
  front-face environment, a non-metallic item inside a bonded or coated
  joint, or a couple of two unlike metals. Any one driver is enough, and
  the drivers that fired are reported so the reviewer sees why.
- A critical entry owes four further items: what it mates with, how the
  joint is made, the environment the joint sees, and the qualification
  evidence that the joint has been shown to survive it. A field left
  blank is not a shorter entry, it is an absent one -- a blank string
  counts as missing.
- Two conditional obligations sit on top. A non-metallic item inside a
  bonded or coated joint owes its total-mass-loss and collected-volatile
  figures, because the joint is the path by which a volatile condenses
  on the coverglass it was meant to bond to. A metal couple owes the
  mating family, because the couple is the whole question.
- A metal couple is judged on the separation between the two anodic
  indices, never on either index alone: gold against silver is a
  perfectly ordinary interconnect joint, aluminium against copper is
  not, and both contain a noble metal.
- The two outgassing figures are not independent. The collected volatile
  fraction is a part of the total mass loss, so a declaration where it
  exceeds the total is a transcription error in the list and is rejected
  as malformed rather than reported as a failure.
- A limit met exactly is met. A separation computed as a difference can
  land a few units in the last place outside an exactly-met allowance;
  absorb that in the comparison, never by widening the allowance.

## Workflow

1. Normalize the entry: identifier, kind, identification data, interface
   role, and whatever interface data it states. Reject an unknown key, a
   blank identifier, an unknown kind, role, joint type, environment,
   material family or metal name, and a non-numeric figure.
2. Derive the criticality drivers from the role, the environment, the
   material family against the joint type, and the metal pair. Group the
   entry as critical when any driver fired, and carry the driver list
   forward into the record.
3. Assemble the fields the entry owes: the identification set its kind
   fixes, the interface set its criticality adds, and the conditional
   outgassing and mating-family items the drivers add.
4. Name every owed field the entry does not actually state, counting a
   blank string as unstated.
5. If outgassing figures are stated, screen both against their limits;
   demand the pair together and reject an inverted pair as malformed.
6. If the entry couples two unlike metals, measure the anodic-index
   separation and hold it against the allowance.
7. Flag an entry whose mating item repeats its own designation: it
   describes no interface at all.
8. Aggregate across the list: reject a duplicate identifier, name the
   critical entries, count the entries by kind, report the complete
   fraction and accept the list only when no finding remains.

## Pitfalls

- Accepting the compiler's own criticality column and reviewing only the
  rows it ticked -- the rows it did not tick are exactly where the
  missing interface data hides.
- Treating a bulk material as automatically non-critical. A laminate
  declared for its bulk properties becomes critical the moment the entry
  admits an exposed front-face environment.
- Reading a blank qualification reference as "to be supplied" and
  passing the entry anyway; an entry with no evidence of qualification
  is indistinguishable from an unqualified one at the review.
- Judging a metal couple by whether a noble metal is present rather than
  by the separation between the two indices, which is the quantity that
  drives the corrosion.
- Taking the collected volatile fraction as an independent figure and
  accepting a value above the total mass loss -- that pairing is a
  transcription error in the list, not a very bad material.
- Letting an entry name itself as its mating item, which passes every
  completeness check while describing no interface.
- Widening a limit to rescue a figure that misses it by a few units in
  the last place; absorb the representation error in the comparison and
  treat a real miss as a real finding.

## Behavior contract (gate 3)

The criticality derivation, the per-kind and per-criticality field sets,
the missing-field detection, the outgassing screening, the anodic-index
separation of a metal couple and the whole-list acceptance are exercised
by the gate 3 contract test:
scripts/test_e2008_critical_materials_interface_listing.py against
scripts/e2008_critical_materials_interface_listing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_critical_materials_interface_listing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

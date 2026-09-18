---
name: q6005-materials-and-parts-specifications
description: "Audit whether the specification defining a material or piece part procured for hybrid microcircuit construction settles everything an order needs under ECSS-Q-ST-60-05C clause 9.3: build the content set from the core items plus the ones the item's own category adds, read a placeholder such as TBD as undefined rather than declared, compute the completeness ratio over the applicable set alone, confirm the document is approved and dated, and compare the specification issue with the issue the order cites. Use when drafting or reviewing a hybrid material specification. Trigger: ecss, q-st-60-05c, hybrid-material-specification-content, piece-part-specification-completeness, hybrid-specification-approval-state, procurement-issue-alignment, hybrid-specification-release-hold."
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
  tags: [ecss, q-st-60-05-hybrid-materials-and-parts, q6005-materials-and-parts-specifications, hybrid-material-specification-content, piece-part-specification-completeness, hybrid-specification-approval-state, procurement-issue-alignment, hybrid-specification-release-hold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Material and Part Specification Content (space-systems/ecss/q6005-materials-and-parts-specifications)

Use when the task is writing, or reviewing somebody else's, specification for a
material or piece part bought for hybrid microcircuit construction under
ECSS-Q-ST-60-05C clause 9.3 — the document that is the whole definition of what
the supplier is being asked to deliver.

## Domain quick reference

- A hybrid is built from items with no packaged identity of their own. A spool
  of wire, a tub of adhesive and a blank substrate are indistinguishable from
  their cheaper commercial equivalents by inspection, so the specification is
  the only thing that says which one arrives. Whatever it leaves unsaid the
  supplier decides, and the decision surfaces at assembly.
- The content set has two layers. The core items every procured item owes —
  designation, manufacturer and site, part reference, traceability marking,
  storage conditions, acceptance criteria and the lot documentation expected —
  and the layer the item's own category adds. An adhesive owes a cure schedule,
  a pot life and a shelf life; a wire owes a diameter tolerance and a breaking
  load; a substrate owes a metallization system and a surface finish. Grading
  every item against one flat catalogue produces findings nobody can action.
- A field that exists but says nothing has defined nothing. "TBD", "to be
  confirmed", a dash or an empty list is how a draft passes a key count while
  leaving the decision open, which is why definedness is tested at the value
  and not at the key.
- The completeness ratio is computed over the applicable set alone. A
  denominator taken from the declared keys rewards padding, and one taken from
  the full catalogue penalises a wire for having no cure schedule.
- Approval is a separate condition from content. A document can define every
  item and still bind nobody, because it carries no issue, no named approver or
  no date, and a supplier quoting against an unapproved draft is quoting
  against something that can change under them.
- Issue alignment is the condition that gets skipped. The order cites an issue;
  the specification carries one. An order citing nothing is filled against
  whatever the supplier holds, and an order citing an earlier issue buys the
  superseded definition exactly as written — both are procurement findings, not
  documentation findings.

## Workflow

1. Validate the record and normalise every declared content key to one
   canonical form, refusing two keys that collapse to the same item rather than
   silently dropping one of them.
2. Build the applicable set: the core content plus the content the declared
   category adds.
3. Test each applicable item for definedness at the value, reading
   placeholders, empty strings and empty collections alike as undefined.
4. Report the undefined items in applicable order, and separately the declared
   items that sit outside the applicable set.
5. Compute the completeness ratio over the applicable set only.
6. Take the approval state: an issue, a named approver and a real calendar
   approval date, each absence named rather than rolled into one verdict.
7. Compare the specification issue with the issue the procurement order cites.
8. Release for procurement only when the content is complete, the document is
   approved and the citation aligns; otherwise hold, with every finding named.
9. Roll a set of specifications up into one procurement readiness, since a
   hybrid is bought as a bill of materials rather than a document at a time.

## Pitfalls

- Grading every category against one flat content catalogue. A bonding wire
  with no cure schedule is not incomplete, and reporting it as such buries the
  spool identification that genuinely is missing.
- Counting declared keys rather than defined values. A specification with every
  field present and a third of them reading "TBC" scores well on a key count
  and binds the supplier to nothing.
- Letting a surplus item raise the completeness ratio. Report it separately; a
  denominator taken from the declared keys rewards adding content nobody owes.
- Releasing an order on a ratio. Ninety per cent complete means an applicable
  item is still open, and the one left last is the contentious one.
- Reading approval as a formality once the content is finished. An unapproved
  document is a draft however complete it is, and quotations taken against a
  draft are quotations against something that can still move.
- Ignoring which issue the order cites. The commonest way the right
  specification delivers the wrong material is an order still citing the issue
  before the one that fixed the problem.
- Storing storage conditions only in the specification. They are core content
  because they travel to goods-in with the order; a limited-life material
  received against a specification that never named its storage regime cannot
  be dispositioned on arrival.

## Behavior contract (gate 3)

The key normalisation, placeholder detection, category-driven applicable set,
the completeness ratio over that set alone, the approval state, the procurement
issue alignment and the set roll-up are exercised by the gate 3 contract test:
scripts/test_q6005_materials_and_parts_specifications.py against
scripts/q6005_materials_and_parts_specifications_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_materials_and_parts_specifications.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

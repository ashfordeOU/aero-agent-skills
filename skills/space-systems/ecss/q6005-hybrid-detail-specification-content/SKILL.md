---
name: q6005-hybrid-detail-specification-content
description: "Assess whether the detailed product specification of a hybrid microcircuit states what it must state and follows the mandated layout, under ECSS-Q-ST-60-05 clause 7.2. Use when a draft hybrid detail specification is submitted and someone must accept or hold it: name the template sections it omits, flag a heading declared with no content behind it, place a section that sits outside the template, measure how far the written order departs from the template through the longest run already in order, resolve every applicable-document citation against the documents the draft itself lists, and return a completeness ratio with a verdict. Trigger: ecss, q-st-60-05, hybrid-detail-specification-content, hybrid-specification-template-order, hybrid-specification-section-completeness, hybrid-specification-applicable-documents, hybrid-specification-citation-resolution."
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
  tags: [ecss, q-st-60-05-hybrid-microcircuit-scope, q6005-hybrid-detail-specification-content, hybrid-specification-template-order, hybrid-specification-section-completeness, hybrid-specification-applicable-documents, hybrid-specification-citation-resolution, hybrid-specification-accept-or-hold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Microcircuits — Detail Specification Content (space-systems/ecss/q6005-hybrid-detail-specification-content)

Use when the task is the detail-specification step of ECSS-Q-ST-60-05 clause
7.2 — judging whether the detailed product specification written for a hybrid
states everything it has to state and is laid out in the template order, so
the draft is accepted or held with the gap named.

## Domain quick reference

- The detail specification is the procurement contract for one hybrid. It is
  the document a manufacturer builds to and an inspector accepts against, so
  a requirement it does not state is a requirement nobody owes.
- The layout template is identification, scope, applicable documents,
  requirements, verification and quality assurance, delivery and packaging,
  notes. The order is part of the template: a reviewer reads several
  specifications for one build and finds the same subject in the same place.
- Presence and content are two different questions. A heading declared with
  nothing behind it reads as coverage in a table of contents and states
  nothing at all, so it is reported separately from a section that is simply
  absent.
- An applicable-document citation is only meaningful when the document it
  names is in the applicable-documents list of the same specification. A
  citation resolving to nothing is a requirement pointing at a document the
  manufacturer was never told to hold.
- Ordering is measured, not judged. The longest run of sections already in
  template order is the part that stays; every template section outside that
  run is the smallest set that has to move, which is what an author acts on.
- A section outside the template is not automatically wrong — a project annex
  can be legitimate — but it is never silently folded into the mandated set;
  it is reported unless the acceptance explicitly allows additions.

## Workflow

1. Normalise every declared section key to the canonical hyphenated form so
   "Applicable Documents", "applicable_documents" and "applicable-documents"
   are one section, and refuse a draft that declares the same section twice.
2. List the template sections the draft never declares, in template order.
3. List the declared template sections whose content is blank, whitespace or
   an empty list; an empty heading is a finding in its own right.
4. Place every declared section that is outside the template.
5. Compute the longest run of template sections already in template order,
   then report the remaining template sections as the ones to move.
6. Read the applicable-documents list, then resolve every citation made in
   any section against it and report each pair that does not resolve.
7. Return the completeness ratio over the template sections that are both
   declared and filled, and one accept-or-hold verdict carrying every
   finding rather than the first one found.

## Pitfalls

- Counting a heading as coverage. A table of contents with all seven
  headings and three empty bodies is a four-section specification; the
  content test is what separates the two.
- Reporting every section after a moved one as out of order. Moving one
  section to the front displaces exactly one section, and a measure that
  blames the tail sends the author to rewrite six sections that are already
  right.
- Accepting a citation because the document exists somewhere in the
  programme. The resolution is against the applicable-documents list of this
  specification, which is what is contractually flowed to the manufacturer.
- Folding a project annex into the mandated set because it looks useful. An
  additional section is visible by default, and only an explicit allowance
  makes it acceptable.
- Treating a key spelling difference as a missing section. Normalise first,
  then test for absence, or a draft is held for a section it does declare.
- Reporting the completeness ratio as the verdict. A draft can be filled
  everywhere and still be held for order or for an unresolved citation; the
  ratio is one of the findings, not a substitute for them.

## Behavior contract (gate 3)

The key normalisation, section validation, absence and empty-content
listing, placement of sections outside the template, template-order run and
displacement measure, applicable-document resolution, completeness ratio and
accept-or-hold verdict are exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_detail_specification_content.py against
scripts/q6005_hybrid_detail_specification_content_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_hybrid_detail_specification_content.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

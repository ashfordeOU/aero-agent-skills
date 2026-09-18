---
name: q20-logbook-example
description: "Prepare and assess the logbook cover page of ECSS-Q-ST-20C Annex E, used as the house record header for the Annex C content: hold the field order the worked example fixes, refuse a blank mandatory field, a non-positive issue, a period running backwards or a sheet numbered past its own total, render the header with labels aligned to one column, compute the sheets the entry count needs at the book's ruling, and cross-check the cover serial, period and sheet total against the entries it heads. Use when a logbook is opened, reissued or checked at handover. Trigger: ecss, q-st-20c-annex-e, logbook-cover-page, logbook-record-header, logbook-cover-field-order, logbook-cover-period, logbook-sheet-count."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-logbook-example, logbook-cover-page-header, logbook-cover-field-order, logbook-cover-period-dates, logbook-cover-sheet-count, logbook-cover-to-entry-cross-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Logbook Cover Page (space-systems/ecss/q20-logbook-example)

Use when the task is the Annex E worked logbook cover of ECSS-Q-ST-20C
taken as the standard record header: a logbook is being opened, reissued
or received, and the question is whether its front sheet identifies the
unit and agrees with the entries behind it.

## Domain quick reference

- The example's value is the field order, not the wording. Project, item,
  part number, serial number, manufacturer, logbook number, issue, the
  period the book covers, the sheet numbering and the custodian -- always
  those, always in that order, so a reviewer opening any unit's book finds
  the serial number in the same place.
- The mandatory set is narrower than the printed set. The custodian may be
  blank on a book in transit; the serial number and the logbook number
  never can, because without them the sheet heads nothing in particular.
- Three fields are structural rather than descriptive. The issue counts
  from one, the period runs forwards, and the sheet number sits inside its
  own total. Each is refused on entry rather than reported later, because
  a cover that says sheet 3 of 2 is not a finding about the unit.
- A period of a single day is ordinary. A book opened and closed on the
  same date is a short custody, not a defect, so the period check accepts
  equality and refuses only a reversal.
- The sheet total is computable. The entry count and the ruling of the
  book give the number of sheets the entries actually need, and a book
  declaring fewer has pages that were never bound in. An empty book still
  has its cover sheet.
- The cover is checked against the body, not read alone. A cover for one
  serial number heading entries for another is the failure this header
  exists to make visible, and an entry dated outside the declared period
  means either the period or the entry is wrong.

## Workflow

1. Refuse a cover carrying a field the header has no place for, so a local
   variant is caught rather than silently dropped.
2. Normalise each field by kind: identifiers trimmed and lowered, the
   issue and sheet numbers positive integers, the period dates ISO days.
3. Refuse a blank mandatory field, a reversed period and a sheet number
   past its total.
4. Render the header with every label padded to one column so the sheet is
   the same shape whoever fills it, printing an absent optional field as a
   dash rather than omitting the line.
5. Compute the sheets the entry count needs at the book's ruling, rounding
   a part-used sheet up and giving an empty book one.
6. Cross-check the entries: same serial number, every date inside the
   declared period, and a declared sheet total matching the computed one.
7. Report the period span in days, the entry count and the verdict.

## Pitfalls

- Copying the example's wording instead of its order. The labels can be in
  any house style; the sequence is what makes covers comparable.
- Grading the custodian as hard as the serial number. Treating every
  printed field as mandatory rejects covers that are entirely usable.
- Refusing a single-day period. Equality is legitimate and only a reversal
  is a defect.
- Taking the declared sheet total on trust. It is derivable from the entry
  count, and a book short of sheets is short of entries.
- Reading the cover without the body. Every field can be filled correctly
  and still head the wrong unit's entries.

## Behavior contract (gate 3)

The cover field order, the unknown-field refusal, the mandatory-field,
issue, period and sheet-numbering validation, the aligned rendering, the
sheet count at a given ruling and the cover to entry cross-checks on
serial number, period and sheet total are exercised by the gate 3 contract
test: scripts/test_q20_logbook_example.py against
scripts/q20_logbook_example_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_logbook_example.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

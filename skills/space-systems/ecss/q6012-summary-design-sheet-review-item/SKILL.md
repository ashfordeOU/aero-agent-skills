---
name: q6012-summary-design-sheet-review-item
description: "Review the summary design sheet review item of ECSS-Q-ST-60-12C clause 7.3.14 for a microwave die: confront the condensed one page overview with the characteristics the programme requires it to carry, reconcile every summarised value against the detail source it was copied from within the stated rounding tolerance, find the characteristics quoted with no unit, size the rendered sheet against its single page budget, and compare the sheet issue date against the latest detail issue, then close, action or reject the item. Use when a microwave die design review reaches the one page overview of the die and its key characteristics. Trigger: ecss, q-st-60-12-microwave-die-scope, summary-design-sheet-review, die-key-characteristic-summary, summary-sheet-source-agreement, summary-sheet-single-page-budget, summary-characteristic-unit-declaration, summary-sheet-issue-currency."
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
  tags: [ecss, q-st-60-12-microwave-die-scope, q6012-summary-design-sheet-review-item, summary-design-sheet-review, die-key-characteristic-summary, summary-sheet-source-agreement, summary-sheet-single-page-budget, summary-characteristic-unit-declaration, summary-sheet-issue-currency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Summary Design Sheet Review Item (space-systems/ecss/q6012-summary-design-sheet-review-item)

Use when the task is the summary design sheet review item of
ECSS-Q-ST-60-12C clause 7.3.14 -- reviewing the condensed one page
overview of the die and its key characteristics, rather than reviewing
the detail documents that page was condensed from.

## Domain quick reference

- The sheet is a derived document, so the item is not a design review.
  It is a copy graded against what it was copied from and against the
  form it has to keep. Nothing on the page originates there, which is
  precisely why it is the page everyone downstream quotes.
- Content is counted against the characteristics the programme requires
  of a die. A characteristic the sheet leaves out is not summarised
  somewhere else on the page; it is absent from the only overview most
  readers will ever open.
- Agreement is the heart of the item and it has two forms. A numeric
  value was rounded on the way onto the page, so it is graded against a
  relative rounding tolerance. A textual value was transcribed, so it
  is graded on the canonical text, where case and spacing carry no
  meaning but a different word does.
- A difference inside the tolerance is the sheet doing its job and is
  worth recording, not raising. A difference beyond it means the page
  and the detail disagree about the part, and the page is the one that
  will be quoted into somebody else's specification.
- A number with no unit is not a summary of anything. The page is read
  by people who do not have the detail beside them, so a bare figure
  and an unreferenced value both push the reader back into the record
  the sheet exists to spare them.
- One page is a requirement, not a preference. A sheet that renders
  past its page budget has stopped being a summary, and a sheet already
  at the edge of the budget has no room for the revision that is coming.
  A sheet issued before the detail moved may be quoting numbers the
  detail has already abandoned.

## Workflow

1. Normalize the sheet entries: canonical characteristic, a summary and
   a source of the same kind, an optional unit and source reference,
   and a rendered line count. Reject a characteristic stated twice and
   one the programme does not define.
2. Confront the entries with the required characteristic set and report
   the absent ones together with the coverage share over that set.
3. Reconcile every numeric entry against its detail source on the
   relative rounding tolerance, and every textual entry on the
   canonical text. Keep the values that merely rounded apart from the
   values that disagree.
4. Find the numeric entries quoted with no unit and the entries naming
   no detail document, and carry both as actions rather than as
   blocking findings.
5. Size the rendered sheet, header included, against the page budget.
   Separate a sheet past the budget, which blocks, from a sheet above
   the caution share, which actions.
6. Compare the sheet issue day against the latest detail issue day,
   then close, action or reject the item with the findings that drove
   the verdict.

## Pitfalls

- Grading a summarised number on exact equality. The value was rounded
  onto the page on purpose, so exact equality raises a finding against
  every entry that did its job and buries the entries that genuinely
  disagree with the detail.
- Grading a transcribed text on exact equality too. Case and inner
  spacing carry no meaning on a sheet assembled by several hands, and
  matching on them turns a correct transcription into a contradiction.
- Scaling the difference on the summarised value rather than on the
  source. The source is the thing being reproduced, so scaling on the
  copy makes the tolerance move with the error it is meant to bound.
- Taking a page that fits as a page that is finished. A sheet at the
  edge of its budget fits today and overflows on the next revision,
  which is when the characteristic that gets dropped to make room is
  chosen by whoever is editing rather than by the review.
- Comparing a relative difference, a fill share or an issue day against
  its bound by bare arithmetic. Each is a quotient or difference of
  floating-point quantities, so a value sitting exactly on the bound can
  land a few units in the last place on the wrong side of it; the
  comparison absorbs that representation error while the bound stays
  untouched.

## Behavior contract (gate 3)

The entry normalization, required characteristic coverage, numeric and
textual source agreement, unit and source reference annotation, single
page budget, issue currency and closure verdict are exercised by the
gate 3 contract test:
scripts/test_q6012_summary_design_sheet_review_item.py against
scripts/q6012_summary_design_sheet_review_item_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_summary_design_sheet_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

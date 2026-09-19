---
name: q20-eidp-example-contents
description: "Structure and grade the contents list of an end item data package against the worked example of ECSS-Q-ST-20C Annex G, taken as the house document-set checklist: hold the numbered section order the example fixes, file each document under the section its kind belongs to rather than where the compiler put it, demand a document number, an issue and a page count on every ticked line, run the page ranges on from the first sheet with no gap or overlap, check a tabbed page against the running count, and reconcile the declared total with the last range. Use when a package is assembled, tabbed or checked on receipt. Trigger: ecss, q-st-20c-annex-g, eidp-contents-list, eidp-section-order, eidp-document-slot-map, eidp-page-range-continuity, eidp-checklist-tick."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-eidp-example-contents, eidp-contents-list-checklist, eidp-section-order, eidp-document-slot-map, eidp-page-range-continuity, eidp-tab-page-cross-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Data Package Contents List (space-systems/ecss/q20-eidp-example-contents)

Use when the task is the Annex G worked contents list of ECSS-Q-ST-20C
taken as the standard document-set checklist: a package is being assembled,
tabbed or opened on receipt, and the question is whether the list at the
front is a navigable index of what is actually behind it.

## Domain quick reference

- The contents list is a checklist, not a table of contents copied from a
  word processor. Each line is a slot that is either filled by a delivered
  document at a stated number and issue, or open. An open line is a visible
  claim about what is still owed, which is exactly what makes the list
  worth assembling.
- The sections run in a fixed order and each document kind has one section
  it belongs to. A certificate filed under configuration records and an
  as-built list filed under conformity declarations both produce a package
  a receiving organisation cannot navigate, even though every document is
  present.
- Order is checked by section, not by line. Two documents inside one
  section may be listed either way round; a section appearing after a
  section that belongs later is the defect.
- A tick with no document number and issue is not a tick. It records that
  somebody believed the document existed, which is the failure mode a
  receipt check exists to catch.
- Page ranges are arithmetic, and arithmetic is checkable. Running the page
  counts on from the first sheet produces the range every document should
  occupy; a tab printed with a different first page means the package was
  re-ordered after the list was written.
- The declared total on the cover is a second, independent statement of the
  same number. Reconciling it with the last range is how a missing annexe
  surfaces without opening the binder.

## Workflow

1. Normalise the submitted lines: a document, a section, and on anything
   ticked a document number, an issue and a positive page count; refuse a
   duplicated document and a tab page on an undelivered line.
2. Check each document against the slot map and report a misfiled one,
   including a document kind the example does not place at all.
3. Walk the sections and report any that appear after a section belonging
   later in the fixed order.
4. Report a mandatory section with no delivered document, counting only
   ticked lines as filling it.
5. Lay out the page ranges from the first sheet, and compare any tabbed
   first page with the running count.
6. Reconcile the declared total page count when one is supplied, report the
   completion fraction and the open lines, and return the verdict.

## Pitfalls

- Grading presence and stopping there. A complete set of documents filed
  under the wrong sections is a package nobody can use, and the slot map is
  the only thing that catches it.
- Counting an unticked line as covered because the document exists
  elsewhere. The list is the receipt; a document not entered on it is not
  delivered with the package.
- Ordering by line rather than by section. Two documents inside one section
  are free to swap, and a checker that flags that produces noise reviewers
  learn to ignore.
- Trusting the tab pages. They are printed once and the package is
  re-ordered afterwards, so the running page count is the reference and the
  tab is what gets checked against it.
- Ignoring the declared total on the cover. It is the cheapest independent
  check in the package and it catches a whole annexe dropped in assembly.

## Behavior contract (gate 3)

The line normalisation, the slot-map placement check, the section-order
walk, the mandatory-section rule, the page-range layout with the tabbed
first-page cross-check, the declared total reconciliation and the
completion fraction are exercised by the gate 3 contract test:
scripts/test_q20_eidp_example_contents.py against
scripts/q20_eidp_example_contents_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_eidp_example_contents.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q60-class-1-declared-components-list
description: "Assess the declared components list a supplier issues for one Class 1 equipment item under clause 4.1.4 of ECSS-Q-ST-60C: select the items the clause obliges, grade each delivered file on whether it arrives in an editable exchange format a reviewer can revise rather than a flattened print carrying the same words, match the issued revision against the build standard the item is currently at, check the line count against the parts the item installs, weight covered items by declared part count and return the issue verdict with ranked findings. Use when a declared components list delivery, equipment parts data package or list issue review is in front of you. Trigger: ecss, q-st-60c, q60-editable-declared-components-list, q60-dcl-per-equipment-item-issue, q60-dcl-exchange-format-editability, q60-dcl-revision-currency, q60-dcl-item-coverage-fraction, q60-dcl-issue-verdict."
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
  tags: [ecss, q-st-60-eee-components-scope, q-st-60c, q60-class-1-declared-components-list, q60-editable-declared-components-list, q60-dcl-per-equipment-item-issue, q60-dcl-exchange-format-editability, q60-dcl-revision-currency, q60-dcl-item-coverage-fraction, q60-dcl-issue-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Editable Declared Components List per Class 1 Item (space-systems/ecss/q60-class-1-declared-components-list)

Use when the task is clause 4.1.4 of ECSS-Q-ST-60C: the declared components
list issued for each Class 1 equipment item, and whether what was actually
delivered is a list the customer can work with. This leaf grades a delivery on
three things a covering letter never shows — which item it belongs to, what
file form it arrived in, and which build revision it describes.

## Domain quick reference

- The obligation is per Class 1 equipment item. A programme-wide master
  spreadsheet covering four boxes reads as complete while no box has a list of
  its own, and a reviewer holding one box cannot tell which lines that box
  installs. Items in another product category do not owe a list under this
  clause, so they belong neither in the covered set nor in the shortfall; a
  denominator that quietly includes them understates the coverage of a build
  that is in fact compliant.
- Editable is a property of the file, not of the words in it. A flattened
  print and a spreadsheet can carry an identical parts table, and only one of
  them can be sorted, filtered, diffed against the next issue or fed into the
  customer's own parts database. A delivery that arrives as a scan is a
  delivery the receiving side has to retype before it can use it, which is
  exactly the rework the requirement exists to prevent.
- A list describes a build standard. Two failures look alike in a revision
  column and are not the same problem: a list issued against a superseded
  revision is behind the hardware and needs a re-issue from the supplier, while
  a list issued against a revision the item has not been built to is ahead of
  the hardware and means the two sides disagree about what is being delivered.
- The line count is a cheap independent check on scope. A list holding fewer
  lines than the item's declared installed parts is missing parts whatever its
  format and revision say; a longer list is not a defect, because a supplier
  may legitimately declare alternates and spares on the same sheet.
- Coverage is weighted by declared part count, not counted per item. One
  uncovered high-count item is a larger hole than three uncovered brackets, and
  a plain item count hides that.

## Workflow

1. Validate the build: every equipment item needs an identifier, a product
   category, a current build revision and a strictly positive declared part
   count. A repeated item identifier is an input error, not a duplicate to be
   merged.
2. Select the obliged set — the Class 1 items. Keep the other items in the
   index so a delivery naming one can be reported as outside the obligation
   rather than as an unknown item.
3. Grade each delivery on the attributes an acceptance decision cannot be taken
   without, and stop there when any is absent: an incomplete record is not a
   format failure and must not be reported as one.
4. Resolve the named item. A delivery for an item not in the build is a
   finding on the delivery; a delivery for an item of another category is
   outside the obligation and contributes to neither side of the coverage.
5. Decide editability from the exchange format, then revision currency, then
   line count, reporting the first check that fails so the finding names the
   defect the supplier has to fix first.
6. Accept only a delivery that clears all three. Treat a later delivery for an
   item already closed by an accepted list as a duplicate, but let a corrected
   resubmission after a rejection be assessed on its own merits.
7. Weight the accepted items by declared part count, compare that coverage with
   the required level, absorbing floating-point representation error at the
   boundary with a named tolerance rather than by lowering the level, and
   return one verdict with findings ranked worst first.

## Pitfalls

- Accepting a programme-wide list as covering every item on it. The clause
  raises the obligation per item; a single sheet leaves each item without a
  list of its own even when every part on that sheet is correct.
- Counting items of other product categories in the coverage denominator. They
  owe nothing under this clause, and including them turns a compliant build
  into a false shortfall — or, counted on the other side, hides a real one.
- Reading a parts table inside a flattened print as an editable issue because
  the content is right. The content was never the question; the receiving side
  still cannot revise, sort or diff the file it was given.
- Collapsing stale and ahead-of-build into one revision finding. They are
  opposite defects with opposite fixes, and a single label sends the wrong
  correction to the supplier.
- Treating a resubmission as a duplicate. Only an item already closed by an
  accepted list can produce a duplicate; a corrected file arriving after a
  rejection is the fix, and rejecting it as a duplicate strands the item.
- Widening the required coverage so an exactly-met case passes. An equality at
  the boundary is a representation question, handled by the tolerance inside
  the comparison; the required level stays as agreed.

## Behavior contract (gate 3)

The build validation, obliged-item selection, delivery completeness grading,
exchange-format editability decision, revision-state separation, line-count
check, part-count-weighted coverage and ranked findings are exercised by the
gate 3 contract test: `scripts/test_q60_class_1_declared_components_list.py`
against `scripts/q60_class_1_declared_components_list_logic.py` (stdlib
unittest, offline). Run:
`python3 scripts/test_q60_class_1_declared_components_list.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

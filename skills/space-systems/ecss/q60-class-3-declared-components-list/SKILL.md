---
name: q60-class-3-declared-components-list
description: "Assess the editable declared components list issued for each Class 3 equipment item under clause 6.1.4 of ECSS-Q-ST-60C: select the items the clause obliges, decide editability from the container the file arrived in and from whether it declares a column schema, align the issued build standard with the standard the item is currently at, read the declared line count against the parts the item installs, weight closed items by installed part count and return the issue verdict with ranked findings. Use when a Class 3 list issue, equipment parts data package or build-standard currency review is in front of you. Trigger: ecss, q-st-60c, q60-class-3-declared-components-list, q60-c3-dcl-container-revisability, q60-c3-dcl-column-schema-declaration, q60-c3-dcl-build-standard-currency, q60-c3-dcl-part-count-coverage, q60-c3-dcl-issue-verdict."
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
  tags: [ecss, q-st-60-eee-components-scope, q-st-60c, q60-class-3-declared-components-list, q60-c3-dcl-container-revisability, q60-c3-dcl-column-schema-declaration, q60-c3-dcl-build-standard-currency, q60-c3-dcl-part-count-coverage, q60-c3-dcl-issue-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Editable Declared Components List per Class 3 Item (space-systems/ecss/q60-class-3-declared-components-list)

Use when the task is clause 6.1.4 of ECSS-Q-ST-60C: the declared components
list issued for each Class 3 equipment item, and whether the file actually
issued is one the receiving side can work with. The leaf grades an issue on
three things a transmittal note never shows — which item it belongs to, what
the file itself is, and which build standard it describes.

## Domain quick reference

- The obligation is raised per Class 3 equipment item. One programme-wide
  sheet covering five boxes reads as complete while no box has a list of its
  own, and a reviewer holding one box cannot tell which of those lines that
  box installs. Items of another product category owe nothing under this
  clause, so they belong on neither side of the coverage ratio; a denominator
  that quietly carries them turns a compliant build into a false shortfall.
- Editable is a property of the file, and it takes two things, not one. A
  container that cannot be revised in place is the obvious failure. The quieter
  failure is a revisable container whose rows carry no declared column schema:
  a spreadsheet holding one free-text line per part can be typed into and still
  cannot be sorted, diffed against the next issue or loaded into the customer's
  own parts database, which is the rework the requirement exists to prevent.
- A list describes a build standard, so two findings that look identical in a
  revision column are opposite problems. A list issued behind the hardware is
  stale and needs a re-issue from the supplier; a list issued ahead of it means
  the two sides do not agree on what is being delivered, and chasing a re-issue
  for that one hides a build-standard dispute.
- The declared line count is a cheap independent read on scope. Fewer lines
  than the item installs parts means parts are missing whatever the format and
  standard fields say. More lines is not a defect, because a supplier may
  legitimately declare alternates and spares on the same sheet.
- Coverage is weighted by installed part count, never counted per item. One
  uncovered high-count box is a larger hole than three uncovered brackets, and
  a plain item count hides exactly that.

## Workflow

1. Validate the build: every equipment item needs an identifier, a product
   category, the build standard it currently sits at and a strictly positive
   installed part count. A repeated item identifier is an input error, not a
   duplicate to be silently merged.
2. Select the obliged set — the Class 3 items. Keep the remaining items in the
   index so an issue naming one is reported as outside the obligation rather
   than as an unknown item.
3. Grade each issue on the fields an acceptance decision cannot be taken
   without, and stop there when any is absent. An incomplete record is not a
   format failure and must never be reported as one.
4. Resolve the named item. An issue for an item not in the build is a finding
   on the issue; an issue for an item of another category is outside the
   obligation and contributes to neither side of the coverage.
5. Decide editability in two parts — container first, then declared schema —
   then build-standard alignment, then line count, reporting the first check
   that fails so the finding names what the supplier has to fix first.
6. Accept only an issue that clears all of them. Treat a later file for an item
   an accepted list already closed as a repeat issue, but let a corrected
   resubmission arriving after a rejection be assessed on its own merits.
7. Weight the closed items by installed part count, compare that coverage with
   the agreed level, absorbing floating-point representation error at the
   boundary with a named tolerance rather than by lowering the level, and
   return one verdict with findings ranked worst first.

## Pitfalls

- Accepting a programme-wide sheet as covering every item printed on it. The
  clause raises the obligation per item; that sheet leaves each item without a
  list of its own even when every part line on it is correct.
- Counting items of other product categories in the coverage denominator. They
  owe nothing here, and carrying them either invents a shortfall or, counted on
  the other side, hides a real one.
- Calling a revisable container editable and stopping. Without a declared
  column schema the rows are readable only by eye, and the next issue cannot be
  diffed against this one.
- Collapsing behind-the-build and ahead-of-the-build into one currency finding.
  They have opposite corrections, and a single label sends the wrong one.
- Treating a resubmission as a repeat issue. Only an item already closed by an
  accepted list can produce a repeat; a corrected file after a rejection is the
  fix, and rejecting it as a repeat strands the item.
- Widening the required coverage so an exactly-met build passes. An equality at
  the boundary is a representation question handled by the tolerance inside the
  comparison; the agreed level stays where it was agreed.

## Behavior contract (gate 3)

The build validation, obliged-item selection, issue completeness grading,
two-part editability decision, build-standard alignment, line-count check,
part-count-weighted coverage and ranked findings are exercised by the gate 3
contract test: `scripts/test_q60_class_3_declared_components_list.py` against
`scripts/q60_class_3_declared_components_list_logic.py` (stdlib unittest,
offline). Run:
`python3 scripts/test_q60_class_3_declared_components_list.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

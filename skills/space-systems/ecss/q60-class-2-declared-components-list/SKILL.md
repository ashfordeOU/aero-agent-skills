---
name: q60-class-2-declared-components-list
description: "Verify that an editable declared components list has been issued for every reliability Class 2 equipment item under ECSS-Q-ST-60C clause 5.1.4: refuse an issue with no equipment reference, label, file form or lines, read a flattened print, a scan or a locked file as an uneditable issue whatever it contains, grade each line on the fields a procurement decision needs, separate a list behind the build from one ahead of it, age every board decision that never reached the list, and weight the coverage by installed parts. Use when a delivered list has to become an issue verdict. Trigger: ecss, q-st-60c-clause-5-1-4, reliability-class-2-declared-components-list, dcl-editable-issue-per-equipment-item, dcl-line-field-completeness, dcl-build-revision-synchronisation, dcl-board-decision-update-latency."
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
  tags: [ecss, q-st-60-eee-component-selection-scope, q60-class-2-declared-components-list, reliability-class-2-declared-components-list, dcl-editable-issue-per-equipment-item, dcl-line-field-completeness, dcl-build-revision-synchronisation, dcl-board-decision-update-latency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components -- Class 2 Declared Components List (space-systems/ecss/q60-class-2-declared-components-list)

Use when the task is the clause 5.1.4 issue question of ECSS-Q-ST-60C at
reliability Class 2: lists have been issued for a build, and the
question is whether every Class 2 equipment item has an editable list
that still describes the item as it is built and as the board has
since decided.

## Domain quick reference

- The obligation is per equipment item, not per project. One consolidated
  list covering a whole build satisfies nobody at the point a single
  item is being accepted, so the assessment runs over the items and asks
  which of them has an accepted issue behind it.
- Editability is a property of the file, not of the words. A flattened
  print, a scan and a locked document carry the same content as the
  spreadsheet they were made from and still cannot be revised, which is
  what the reviewer has to do with them.
- The line is the unit a decision is taken on. A list is not graded as
  one object: each line is checked for the part number, manufacturer,
  procurement specification, quality level and quantity a procurement or
  a nonconformance decision cannot be taken without, and the deficient
  lines are named rather than counted.
- The mean line completeness and the line count are different failures.
  A list can hold every line at half the fields, or half the lines at
  every field, and only one of the two figures catches each.
- A revision behind the build and one ahead of it are both wrong and are
  not the same wrong. Behind means the list describes a superseded item;
  ahead means it describes a standard the item has not reached, which is
  usually a list issued against a planned modification.
- A board decision that never reached the list is the defect the issue
  cadence exists to catch. The list is the thing the next buyer reads,
  so a decision sitting in minutes for months is a list that is
  formally current and practically wrong.
- A late incorporation is recorded even though it landed, because the
  interval it was late by is the interval the programme procured against
  the previous list.
- Coverage is weighted by installed parts. Closing the two small items
  and leaving the dense one open reads as two thirds done on a headcount
  and is nothing of the sort.

## Workflow

1. Validate the build: every item carries an identifier, a reliability
   class, a build revision and a positive installed part count, and no
   item appears twice. Select the Class 2 items; an item of another
   class is outside this obligation entirely.
2. Validate and dispose of every issued list. An issue missing its
   label, item, file form, revision or lines cannot be assessed and
   stops there; an empty line set is such a record, not an empty list.
3. Refuse an issue naming an item outside the build, and mark an issue
   against an item of another class as outside the obligation rather
   than as a failure.
4. Decide editability from the file form, then compare the issued
   revision with the item's build revision, keeping behind and ahead
   apart.
5. Grade the lines: compare the line count with the installed part
   count, take the mean line completeness over the mandatory fields, and
   name every line short of them.
6. Age each parts board decision that has to reach the list. One still
   open past the declared response time is an open item; one that landed
   outside it is late but landed; keep the slowest incorporation.
7. Weight the closed items by installed part count, compare with the
   required coverage inside a named tolerance, and close on one verdict:
   lists issuable, or lists not issuable, with the findings ranked most
   severe first.

## Pitfalls

- Accepting a print of the spreadsheet. It reads identically and cannot
  be revised, which is the only property the clause asks the file for.
- Grading the list as a single object. A list that exists, is current
  and is editable can still be unusable line by line, and a per-list
  check never sees it.
- Treating a reissue after a refusal as a duplicate. Only an accepted
  issue closes an item; a corrected file arriving after a rejected one
  is the process working.
- Reporting the coverage without the update latency. A build where every
  item has a current list and three board decisions have been waiting
  two months is covered and out of date at the same time.
- Counting items rather than parts. The dense item is the one whose
  missing list costs the most, and a headcount hides exactly that.

## Behavior contract (gate 3)

The build and obligation selection, the file form editability reading,
the per-line field completeness and its mean, the line count check, the
revision alignment, the board decision ageing with its open, late and
slowest figures, the part-count-weighted item coverage and the issue
verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_2_declared_components_list.py against
scripts/q60_class_2_declared_components_list_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_declared_components_list.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2040-device-pre-tailoring-matrix
description: "Build and check the ready-made applicability table that says which requirements each device category has to answer under ECSS-E-ST-20-40C clause 6.2: fold every cell onto applicable, not-applicable or modified, report the cells nobody filled in instead of reading them as exempt, demand a note on each modified cell, find rows applicable to no category and columns with nothing in them, and overlay a project delta whose removals each carry a justification. Use when a device applicability table is being written or inherited. Trigger: ecss, e-st-20-electrical-scope, device-pre-tailoring-matrix, device-category-applicability, requirement-disposition-cell, modified-requirement-note, tailoring-delta-justification, empty-applicability-column."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-pre-tailoring-matrix, device-pre-tailoring-matrix, device-category-applicability, requirement-disposition-cell, modified-requirement-note, tailoring-delta-justification, empty-applicability-column]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Pre-Tailoring Matrix (space-systems/ecss/e2040-device-pre-tailoring-matrix)

Use when the task is the pre-tailoring duty of ECSS-E-ST-20-40C clause
6.2 -- producing or checking the applicability table that hands a project
a finished decision on which requirements apply to which category of
device, so the project inherits a baseline instead of tailoring each
device from scratch.

## Domain quick reference

- The table is one row per requirement and one column per device
  category, with a disposition in every cell. Its whole value is that
  it is already decided, so an unfilled cell is not a small omission --
  it is the table failing at the one job it has.
- An unset cell is reported as a gap and never read as not-applicable.
  Reading a blank as an exemption is how requirements silently leave a
  baseline, and the reader cannot tell a considered exemption from an
  unfinished row.
- Three dispositions carry the whole table: applicable, not-applicable
  and modified. Input spellings vary between organisations, so the
  spellings are folded onto the canonical three before anything is
  counted, and an unrecognised spelling is refused rather than guessed.
- A modified cell without a note is unusable. The reader knows the
  requirement changed but not what it became, which is strictly worse
  than either of the other two dispositions.
- Two structural defects are invisible cell by cell and obvious across
  the table: a row applicable to no category at all, which is dead
  weight the project still has to read, and a column with nothing
  applicable in it, which is a device category nobody can build to.
  Both are matrix defects rather than properties of any device.
- Project tailoring is a DELTA against this baseline, not a fresh
  decision. What matters is what the project added and what it removed,
  and a removal from a pre-tailored baseline carries a justification or
  the baseline has quietly become arbitrary.

## Workflow

1. Declare the device categories as the column set. Refuse a repeated
   or blank category, because both silently merge or drop a column.
2. Resolve each row: an identifier, a title, the disposition cells and
   any modification notes. Refuse a cell naming a category that is not
   in the column set, and refuse a repeated requirement identifier.
3. Fold every disposition onto the canonical three and refuse an
   unrecognised spelling rather than defaulting it.
4. Collect the unset cells and the modified cells without notes. Report
   both as findings against the table itself.
5. Read the applicable set for each category, counting modified rows as
   applicable, since a modified requirement still has to be answered.
6. Look across the table for the two structural defects: rows applicable
   nowhere and columns with nothing applicable.
7. Where a project delta exists, overlay it per category and report what
   it added, what it removed, the reduction that represents, and any
   removal with no justification attached.

## Pitfalls

- Treating a blank cell as not-applicable. It is the commonest way a
  requirement disappears from a baseline, and it cannot be told apart
  from an unfinished table afterwards.
- Counting modified rows as exempt. A modified requirement still has to
  be answered, just against a changed statement, so it belongs in the
  applicable set with its note attached.
- Accepting free-text dispositions. A column holding both "N/A" and
  "not required" cannot be counted, and folding the spellings after the
  counts have been taken does not repair the count.
- Reading tailoring as an independent decision. The point of a
  pre-tailored baseline is the delta against it; without the comparison
  nobody can see what the project actually changed.
- Letting a removal travel without a justification. One unjustified
  removal turns the inherited baseline into an arbitrary one, and the
  next project inherits that instead.

## Behavior contract (gate 3)

The disposition folding, row and column validation, gap and note
detection, per-category applicable sets, structural defect scan and
tailoring delta are exercised by the gate 3 contract test:
scripts/test_e2040_device_pre_tailoring_matrix.py against
scripts/e2040_device_pre_tailoring_matrix_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_pre_tailoring_matrix.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

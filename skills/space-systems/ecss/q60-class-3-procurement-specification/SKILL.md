---
name: q60-class-3-procurement-specification
description: "Verify that every Class 3 part type is bought against a controlled written purchasing specification rather than against a catalogue line. Use when a Class 3 order is raised or its document control is reviewed: index the library so one controlled document owns one part type, judge whether the document kind cited is admissible at all and refuse a datasheet carrying no issue identifier and held under no configuration control, score the content a Class 3 specification still owes against the completeness the project buys at, reject a line raised against a draft, superseded or withdrawn issue or one released after the order date, compare the revision cited with the revision released, and reconcile ordered types against the library both ways. Trigger: ecss, ecss-q-st-60c-clause-6-3-2, class-3-procurement-specification, class-3-specification-kind-admissibility, class-3-controlled-issue-identifier, class-3-specification-revision-control, class-3-specification-part-type-coverage."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-3-procurement-specification, ecss-q-st-60c-clause-6-3-2, class-3-procurement-specification, class-3-specification-kind-admissibility, class-3-controlled-issue-identifier, class-3-specification-revision-control, class-3-specification-part-type-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 3 EEE Parts — Purchasing Specification (space-systems/ecss/q60-class-3-procurement-specification)

Use when the task is the purchasing specification duty of ECSS-Q-ST-60C
clause 6.3.2 — buying Class 3 parts against a controlled written purchasing
specification held for each part type, rather than against a catalogue line.

## Domain quick reference

- One controlled document owns one part type. A library in which two
  documents claim the same type has no answer to what the part was bought to,
  so the duplicate is refused rather than resolved by picking one.
- Not every document cited as a purchasing specification is one. A project
  specification and a manufacturer detail specification are controlled by
  their nature. A catalogue datasheet is controlled only when it carries an
  issue identifier and is held under configuration control, and a sheet
  meeting neither test is the defect this check exists for.
- Admissibility and content are separate questions. An admissible document
  can still be missing half of what it owes, and an uncontrolled sheet can
  read as complete. Neither result stands in for the other.
- Content is scored as a fraction so a project can state the completeness it
  buys at, and every absent item is still named separately underneath it.
- A case landing exactly on the project minimum is accepted, absorbed with a
  named tolerance rather than by moving the bound, because a completeness
  score is a division and lands where the division lands.
- Issue status and issue date are two independent tests. A released issue
  dated after the order was raised was not available when the buyer bought.
- Revisions are ordered family-aware: B1 comes after B and before C. Citing an
  earlier revision is a superseded citation; citing a later one is a citation
  of a document that was never released, and they are different repairs.
- Lines and the library are reconciled in both directions. A specification
  held for a type nobody ordered is a maintenance finding, not a spare.

## Workflow

1. Index the specification library by part type, refusing a library in which
   two documents claim one type.
2. Confirm the order is declared at the assurance category this check covers,
   and read the order date once.
3. For each ordered line, find its specification. None is a finding in its own
   right, not a reason to skip the line.
4. Judge the document kind: a control-bearing kind passes; a datasheet passes
   only on an issue identifier plus configuration control.
5. Check the issue status against the one status a line may be raised on, and
   separately compare the release date with the order date.
6. Compare the revision the order cites with the revision released, naming a
   superseded citation and an unreleased citation differently.
7. Score the content, and where it falls below the project minimum name every
   absent item.
8. Walk the library for types nobody ordered, then report the per-line
   records, the specified fraction and one order-level verdict.

## Pitfalls

- Accepting a manufacturer catalogue sheet as a purchasing specification
  because it has numbers on it. Without an issue identifier and configuration
  control nobody can say later which sheet was bought to.
- Merging admissibility and content into one score. An uncontrolled sheet that
  happens to be complete still cannot be the document of record.
- Failing a specification that lands exactly on the project minimum because
  the comparison was written as a strict inequality on a division.
- Checking issue status and forgetting the release date. A released issue
  dated after the order did not exist when the order was raised.
- Reading any revision mismatch as one defect. Citing an earlier revision and
  citing one that was never released are repaired in opposite directions.
- Comparing revisions as plain text, which puts B1 before B and AA before B.
- Walking the order only, so a specification held for a type that left the
  design is never noticed.
- Resolving two documents claiming one part type by taking the newer. The
  question the library exists to answer has two answers, which is the defect.
- Reporting a specified fraction as though it were the order verdict.

## Behavior contract (gate 3)

The one-owner library index, document kind admissibility, content
completeness with its tolerance, issue status and release-date tests,
family-aware revision comparison, two-directional coverage, specified
fraction and order-level verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_3_procurement_specification.py against
scripts/q60_class_3_procurement_specification_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q60_class_3_procurement_specification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

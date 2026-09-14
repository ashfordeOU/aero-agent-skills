---
name: q6013-class-1-documentation
description: "Audit whether the record package retained for a class 1 commercial part activity is complete and durable under ECSS-Q-ST-60-13C clause 4.7: refuse a record with no recognized type, identifier, issue, date or approving authority, name every mandatory report the package never produced, derive each retention end from the record date and its whole-year retention and compare it with the horizon the project has to reach, reconcile record coverage against the as-built parts list in both directions, and report completeness as a fraction judged at unity under a named tolerance. Use when a parts record package has to be judged fit to retain. Trigger: ecss, q-st-60-13c-clause-4-7, class-1-parts-record-package, mandatory-parts-report-coverage, parts-record-retention-horizon, as-built-parts-list-traceability, parts-package-completeness-fraction."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-documentation, q-st-60-13c-clause-4-7, class-1-parts-record-package, mandatory-parts-report-coverage, parts-record-retention-horizon, as-built-parts-list-traceability, parts-package-completeness-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 Commercial Parts — Documentation (space-systems/ecss/q6013-class-1-documentation)

Use when the task is the documentation provision of ECSS-Q-ST-60-13C clause
4.7 — the records and reports a commercial electrical, electronic and
electromechanical part activity produces at the highest assurance level, and
what has to still exist, and still be readable, years after the part was
fitted.

## Domain quick reference

- The package is the evidence. A part that was evaluated, screened and
  accepted, but whose reports cannot be produced on request, is a part with no
  assurance history at all — the work happened, the standing did not survive
  it.
- Records are held to the same control as any other project document: a
  recognized type, an identifier, an issue, a date, and the authority that
  approved it. An unapproved draft in the archive is not a record, because
  nobody can say who accepted what it states.
- The mandatory set is a set, not a total. A package can hold ten thick
  reports and still be short the one report the review will ask for, so
  coverage is checked type by type against the required list and each absent
  type is named on its own.
- Retention is two questions, not one. How long the record is kept, and
  whether keeping it that long actually reaches the date the project has to
  reach. A generous retention starting from an early record can still expire
  before the end of a long mission.
- Retention arithmetic is done in whole years on calendar dates, which keeps
  it exact and keeps a leap-day record from drifting. The one representation
  question left is the completeness fraction, a quotient of two counts,
  judged at unity under a named tolerance.
- Traceability runs both ways. A part on the as-built list that no record
  covers is an assurance gap; a record covering a part the list does not carry
  means the package and the build have drifted apart, and either one may be
  the wrong document.

## Workflow

1. Validate the activity: the part number, the lot identifier behind it and
   the project retaining the package.
2. Validate every record — type, identifier, issue, date, approving authority,
   whole-year retention and the parts it covers — and reject a record type
   declared twice in one package.
3. Compare the mandatory record types with the types present, name each absent
   report, and express the result as a completeness fraction.
4. Derive each record's retention end from its own date and its retention in
   whole years, compare the retention against the floor and the end against
   the required horizon, and keep both findings when both apply.
5. Reconcile the parts the records cover against the as-built parts list in
   both directions.
6. Report the per-record entries, the absent types, the completeness fraction,
   the coverage reconciliation and a verdict carrying every finding.

## Pitfalls

- Counting pages instead of types. A package's weight says nothing about
  whether the one report the review asks for is in it.
- Accepting a record with no issue or no approving authority. Whichever copy
  someone happens to hold then becomes the history, and two copies can
  disagree with nothing to settle them.
- Reading a long retention as sufficient. Retention runs from the record's own
  date, so an early record with a long period can still expire before a late
  one with a short period, and only the computed end date shows it.
- Doing retention arithmetic in days. Years converted to days drift, and a
  record dated on a leap day drifts differently from one dated the day after;
  whole-year calendar arithmetic has neither problem.
- Checking traceability one way. A listed part with no record is the obvious
  gap; a record covering a part the build does not carry is the one that
  reveals a mismatched revision of either document.
- Stopping at the first finding. The package owner needs the whole list to
  close it in one archive pass rather than one pass per finding.

## Behavior contract (gate 3)

The activity validation, per-record validation, retention-end derivation and
horizon comparison, mandatory-type coverage, completeness fraction, two-way
parts-list reconciliation and the overall fit-to-retain verdict are exercised
by the gate 3 contract test:
scripts/test_q6013_class_1_documentation.py against
scripts/q6013_class_1_documentation_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_1_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

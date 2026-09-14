---
name: q6013-class-2-documentation
description: "Assess whether the record package retained for an intermediate assurance commercial part activity is complete, controlled and durable under ECSS-Q-ST-60-13C clause 5.7: refuse a record with no recognized type, identifier, issue, date or approving authority, credit a project-held record in full and a supplier-held one only at a declared fraction and only where a right of access is recorded, name every mandatory report the package never produced, derive each retention end from the record date in whole calendar years, compare it with the horizon the project has to reach, and judge credited completeness against its floor under a named tolerance. Use when a parts record package has to be judged fit to retain. Trigger: ecss, q-st-60-13c-clause-5-7, class-2-parts-record-package, supplier-held-record-access-undertaking, mandatory-parts-report-coverage, parts-record-retention-horizon, credited-package-completeness-fraction, parts-record-control-fields."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-2-documentation, q-st-60-13c-clause-5-7, class-2-parts-record-package, supplier-held-record-access-undertaking, mandatory-parts-report-coverage, parts-record-retention-horizon, credited-package-completeness-fraction, parts-record-control-fields]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 2 Commercial Parts — Documentation (space-systems/ecss/q6013-class-2-documentation)

Use when the task is the documentation provision of ECSS-Q-ST-60-13C clause
5.7 — the records a commercial electrical, electronic and electromechanical
part control activity retains at the intermediate assurance level, who is
holding each one, and what has to still exist and still be readable years
after the part was fitted.

## Domain quick reference

- The package is the evidence. A part that was selected, procured, screened
  and accepted, but whose reports cannot be produced on request, is a part
  with no assurance history at all — the work happened, the standing did not
  survive it.
- The intermediate class differs from the highest class in one structural
  way, and the rest follows from it: not every record has to sit in the
  project's own archive. A record the supplier keeps is acceptable evidence
  where the project holds a recorded right of access to it, and is no
  evidence at all where it does not. A document somebody else owns, with no
  undertaking behind it, disappears with a reorganisation.
- So custody is graded rather than binary. A project-held record counts in
  full, a supplier-held record under an access undertaking counts at a
  declared fraction below one, and a supplier-held record with no undertaking
  counts as absent. The fraction is what stops a project outsourcing its
  whole archive and still reporting a complete package.
- Record control comes before any of that arithmetic. A recognized type, an
  identifier, an issue, a date and the authority that approved it are what
  make a document a record. An unapproved draft in an archive is not a
  record, because nobody can say who accepted what it states, and two copies
  can disagree with nothing to settle them.
- The mandatory set is a set, not a total. A package can hold six thick
  reports and still be short the one the review will ask for, so coverage is
  checked type by type and each absent type is named on its own.
- Retention is two questions. How long the record is kept, and whether
  keeping it that long actually reaches the date the project has to reach. A
  generous retention starting from an early record can still expire before
  the end of a long mission, and only the computed end date shows it.
- Retention arithmetic is done in whole calendar years, which keeps a record
  dated on a leap day from drifting against one dated the day after. The one
  representation question left is the credited completeness, a quotient of
  weighted counts, judged against its floor under a named tolerance.

## Workflow

1. Validate the retention and custody policy: the completeness floor, the
   supplier-held credit, the whole-year retention floor and whether an access
   undertaking is required. A credit at or above one, or a floor above one,
   is refused rather than used.
2. Validate the activity — part number, retaining project and the retention
   horizon as a real calendar date.
3. Validate every record: recognized type, identifier, issue, approving
   authority, date, custody, access undertaking and whole-year retention,
   rejecting a type declared twice in one package.
4. Name every record missing an identifier, an issue or an approving
   authority, and close there; an uncontrolled record cannot be counted
   towards anything.
5. Compare the mandatory types against the types present, name each absent
   one and each supplier-held type with no recorded access, and express the
   result as a credited completeness fraction against its floor.
6. Derive each record's retention end from its own date in whole years,
   compare the retention against the floor and the end against the horizon,
   and keep both findings when both apply.
7. Report the per-type findings, the credited completeness, the retention
   results and a verdict: package not established, record control not
   demonstrated, coverage shortfall, retention not sufficient, or package
   meets class two — raising an advisory where any type sits with the
   supplier.

## Pitfalls

- Counting a supplier-held record as one the project holds. It is evidence
  only for as long as the access undertaking is, which is why it is credited
  below one rather than either accepted or refused.
- Accepting an access undertaking that was discussed but not recorded. The
  test is whether the right survives the person who negotiated it.
- Counting pages instead of types. A package's weight says nothing about
  whether the one report the review asks for is in it.
- Accepting a record with no issue or no approving authority. Whichever copy
  someone happens to hold then becomes the history.
- Reading a long retention as sufficient. Retention runs from the record's
  own date, so an early record with a long period can expire before a late
  one with a short period.
- Doing retention arithmetic in days. Years converted to days drift, and a
  record dated on a leap day drifts differently from one dated the day after;
  whole-year calendar arithmetic has neither problem.
- Stopping at the first finding. The package owner needs the whole list to
  close it in one archive pass rather than one pass per finding.

## Behavior contract (gate 3)

The policy validation, activity validation, per-record control checks, the
graded custody credit, mandatory-type coverage, credited completeness against
its floor, retention-end derivation, the horizon comparison and the overall
fit-to-retain verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_documentation.py against
scripts/q6013_class_2_documentation_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_2_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2008-coverglass-data-documentation
description: "Audit the data package a coverglass delivery is released against under ECSS-E-ST-20-08C clause 8.9: name the qualification family nobody wrote up, catch a record citing an issue that no longer governs, hold anything still in draft at delivery, reconcile the delivered batches against the batch data files in both directions, check every file carries a measured row for each piece its batch delivered, and refuse a row reporting on a piece that batch never shipped. Use when a coverglass data package is about to go out with the glass. Trigger: ecss, coverglass-data-package-release, coverglass-qualification-record-set, coverglass-production-batch-data-file, coverglass-batch-file-reconciliation, coverglass-per-piece-measured-row-coverage, coverglass-governing-issue-citation."
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
  tags: [ecss, e-st-20-08-coverglass-scope, e2008-coverglass-data-documentation, e-st-20-08c-clause-8-9, coverglass-data-package-release, coverglass-qualification-record-set, coverglass-production-batch-data-file, coverglass-batch-file-reconciliation, coverglass-per-piece-measured-row-coverage, coverglass-governing-issue-citation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Coverglass Data Documentation (space-systems/ecss/e2008-coverglass-data-documentation)

Use when the task is clause 8.9 of ECSS-E-ST-20-08C: the data package a
coverglass delivery travels with. It carries two tiers -- the record set
standing behind the coverglass type's qualification, written once and cited
by every later delivery, and one data file for each production batch actually
delivered. This leaf grades both together and returns what stands between the
glass and release.

## Domain quick reference

- The two tiers answer different questions and are never merged. The
  qualification tier says the type was ever shown to be good; the batch files
  say what these pieces measured. A package strong in one tier and empty in
  the other is not half a package, it is missing an argument.
- A record cites an issue, and the issue has to be the one that governs this
  delivery. A qualification report against a superseded process document is
  not thin evidence, it is evidence about a different configuration, which is
  why it outranks a record that is merely missing a field.
- The reconciliation runs in both directions. A delivered batch with no file
  is the obvious hole; a file naming a batch this delivery does not contain is
  the one that gets waved through, and it usually means the wrong file was
  copied in.
- Coverage is per piece, not per batch. A batch file can exist, be approved,
  and still leave a delivered piece with no measured row of its own, and a
  file-level check never sees it.
- A row for a piece the batch did not deliver is not a typo to correct. It
  may genuinely describe another batch, and rewriting the identifier destroys
  the only evidence that it did.
- Draft is not delivered. A package released while a record sits pending or
  withdrawn has moved the approval step to after the point where anybody
  could still act on it.
- The findings are collected, not ranked away. A missing family, a superseded
  issue and an unsigned file ask the supplier for three different pieces of
  work, and one merged verdict asks for the same one three times.

## Workflow

1. Validate the documentation policy: whether a row per delivered piece is
   demanded, whether records must be approved, whether the governing issue
   must match, and the least share of qualification families the package may
   carry.
2. Read the governing issue declared for each qualification family; that
   declaration is what every cited issue is tested against.
3. Assess each qualification record with the arms ranked: a superseded issue
   first, then missing fields, then an approval still pending or withdrawn.
4. Name the qualification families that carry no record at all, which is a
   different finding from a record that is present and weak.
5. Reconcile the delivered batches against the batch files in both
   directions, refusing a batch declared twice.
6. Assess each batch file against its own batch: foreign rows first, then
   missing fields, then a delivered piece with no row, then the approval
   state. Report the row coverage share either way.
7. Close on one package verdict, releasable only when every family is
   recorded, every record and file is complete and the batches reconcile,
   with all findings collected in one list.

## Pitfalls

- Counting records instead of families. Three revisions of the same report
  read as three records and leave two families silently empty.
- Accepting a record without checking its issue. It is the finding that looks
  like paperwork and means the glass was built to a document nobody is
  delivering against.
- Reconciling one way only. Checking that every batch has a file and stopping
  there lets a file about another delivery ride along unchallenged.
- Stopping at file level. The delivered piece with no measured row is
  invisible to a per-file check and is exactly the piece that gets queried
  years later.
- Treating a pending signature as a formality. It is the one finding that can
  still be closed in minutes and the one that stops the shipment on the day.
- Merging the tiers into a single percentage. Qualification evidence and
  batch data are not interchangeable, and an averaged score hides which one
  is missing.

## Behavior contract (gate 3)

The policy validation, the qualification field audit, the governing-issue
test, the ranked record verdict, the batch file field audit, the per-piece
row coverage with its foreign-row arm, the two-way batch reconciliation, the
recorded family share and the package release verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_coverglass_data_documentation.py against
scripts/e2008_coverglass_data_documentation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_data_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2008-blocking-diode-data-documentation
description: "Use when a blocking diode data package is offered before release. Audit the supplier data package a blocking diode delivery is released against, per ECSS-E-ST-20-08C clause 12.8: resolve the type qualification tier and the one data file every delivered batch owes, take the governing issue of each family, hold anything still in draft, reconcile screening serials against the diodes each batch delivered in both directions, order the manufacture, screening and delivery dates, and reconcile submitted batch files against the declared batches. Trigger: ecss, e-st-20-08c, clause-12-8, blocking-diode-supplier-data-package, blocking-diode-batch-data-file-reconciliation, blocking-diode-screening-serial-coverage, blocking-diode-governing-issue-rule, blocking-diode-qualification-approval-citation."
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
  tags: [ecss, e-st-20-08-blocking-diode-scope, e2008-blocking-diode-data-documentation, e-st-20-08c-clause-12-8, blocking-diode-supplier-data-package, blocking-diode-batch-data-file-reconciliation, blocking-diode-screening-serial-coverage, blocking-diode-governing-issue-rule, blocking-diode-qualification-approval-citation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes -- Data Documentation (space-systems/ecss/e2008-blocking-diode-data-documentation)

Use when the task is clause 12.8 of ECSS-E-ST-20-08C: the supplier data
package a blocking diode delivery is released against, carrying both the
records standing behind the diode type's qualification and a data file for
every batch that went out.

## Domain quick reference

- The package stands on two tiers and the usual defect is to walk them as
  one list. The qualification tier is issued once for the diode type and
  cited by every batch; the batch tier is one data file per delivered
  batch. A sweep that walks families without walking batches cannot tell
  the difference.
- That is why the batch set is reconciled rather than merely inspected. A
  package holding every qualification record and one immaculate batch file
  passes a family-by-family sweep while three delivered batches have no
  paperwork at all, because nothing in a family sweep names the batches
  that were meant to be there.
- Reconciliation runs both ways. A declared batch with no data file is
  missing; a file for a batch the delivery never declares is not a bonus,
  it is the package and the delivery record disagreeing, and one of them
  is wrong.
- Blocking diodes ship serialized, which adds a second reconciliation an
  unserialized article never needs. The electrical screening record is the
  only document that descends to the individual part, so it can be
  present, approved and at the governing issue while holding forty rows
  for a batch of four hundred delivered diodes. Family-level completeness
  says nothing about part-level coverage, and that check runs both ways
  too: a delivered serial with no row is uncovered, a row for a serial the
  batch never held is foreign data.
- The package also carries dates that have to sit in order, and they read
  as ordinary dates until somebody puts them on a line. Screening that
  predates the completion of the batch it screened did not screen that
  batch; screening dated after the delivery it released was not available
  when the delivery went out. A same-day pair is fine -- the rule is
  not-before, not strictly-after.
- The tiers are tied by a citation. Every batch cites the governing
  qualification approval, and a batch citing a superseded or withdrawn one
  looks complete because the reference it carries is a real reference to a
  real record.
- Inside a family several issues can sit together. The highest governs and
  the lower ones are superseded, not missing, so a package can hold the
  right document at the wrong issue and still pass a name-only check. A
  superseding draft does not inherit the approval of the issue beneath it.
- An approval is a state, not a presence. A record sitting in review or
  still in draft is in the package and is still not evidence.
- Three batch families are owed only because something happened -- a
  nonconformance was raised, a waiver was granted, rework was performed --
  and each flag has to be stated. Inferring it from what was submitted
  makes a missing family invisible: nothing came in, so nothing was owed,
  so the file looks complete.

## Workflow

1. Resolve the qualification tier: group its records, take the governing
   issue of each family, check every family is present and approved, and
   read off the reference and date of the governing approval statement.
2. For each batch data file, resolve the families that batch owes from its
   stated context, requiring every conditional flag rather than defaulting
   an absent one.
3. Take the governing issue of each batch family, check presence and
   approval state, and raise a finding for any family the batch's context
   says is not owed.
4. Reconcile the screening rows against the serials that batch delivered,
   naming uncovered serials and foreign rows separately, and report the
   coverage fraction rather than a bare pass.
5. Put the manufacture, screening and delivery dates on a line and raise a
   finding for either inversion.
6. Check the approval the batch cites against the governing one, treating
   both an absent citation and a superseded reference as blocking.
7. Reconcile the submitted batch files against the declared delivery
   batches in both directions, naming missing batches and undeclared files
   separately.
8. Release only when the finding list is empty, and report per tier, per
   batch and per serial count so one blocking batch is visible rather than
   a bare rejection.

## Pitfalls

- Grading families without grading batches. Every family check can pass on
  a package that is missing most of the delivery, because a family is
  present somewhere and nothing asks where the other batches went.
- Reading the screening record as a family. It is the only document that
  reaches the individual diode, so its presence is the cheapest part of
  the check and its row set is the expensive part.
- Treating a foreign screening row as harmless padding. A row for a serial
  the batch never delivered means the record and the batch identification
  disagree, which is a finding rather than surplus.
- Treating an undeclared batch file as harmless. It contradicts the
  delivery record, and a contradiction is a finding rather than a
  rounding.
- Reading the package dates as metadata. Screening dated before the batch
  completed screened something else, and screening dated after the
  shipment left was not available to release it.
- Accepting any citation that resolves. A superseded approval statement is
  a real document with a real reference; matching the governing one is the
  check, not matching something.
- Inferring the conditional batch families from the submission. An absent
  nonconformance file cannot tell you whether a nonconformance was raised.
- Taking any issue of a family as the family. The governing issue is the
  highest present; the lower ones are superseded rather than absent.
- Counting presence as approval. A draft in the package is still a draft,
  and release turns on the state, not the page count.

## Behavior contract (gate 3)

The two-tier family catalogues, the context-driven resolution of the
families a batch owes, the record validation with its approval-state and
approval-date rules, the highest-issue governing rule with superseded
issues retained, the qualification tier and the approval it names, the
cross-tier citation rule, the per-serial screening reconciliation in both
directions, the manufacture-screening-delivery date ordering, the batch
set reconciliation in both directions and the aggregated package verdict
are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_data_documentation.py against
scripts/e2008_blocking_diode_data_documentation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_data_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

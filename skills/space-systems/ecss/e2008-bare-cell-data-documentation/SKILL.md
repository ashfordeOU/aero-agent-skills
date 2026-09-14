---
name: e2008-bare-cell-data-documentation
description: "Use when a package is offered before release: resolve the families each tier owes, take the governing issue of every record, hold anything still in draft, reconcile the lot files against the declared lots in both directions, and check each lot's measured data table carries a row for every cell that lot delivered. Audit the supplier data package a bare solar cell delivery travels with under ECSS-E-ST-20-08C clause 7.7, where one qualification tier and one data file per delivered lot are graded together. Trigger: ecss, e-st-20-08c, clause-7-7, bare-cell-supplier-data-package, bare-cell-lot-data-file-reconciliation, bare-cell-per-cell-measured-data-coverage, bare-cell-governing-issue-rule, bare-cell-qualification-approval-citation."
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
  tags: [ecss, e-st-20-08-bare-solar-cell-scope, e2008-bare-cell-data-documentation, e-st-20-08c-clause-7-7, bare-cell-supplier-data-package, bare-cell-lot-data-file-reconciliation, bare-cell-per-cell-measured-data-coverage, bare-cell-governing-issue-rule, bare-cell-qualification-approval-citation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells -- Data Documentation (space-systems/ecss/e2008-bare-cell-data-documentation)

Use when the task is clause 7.7 of ECSS-E-ST-20-08C: the supplier data
package a bare-cell delivery is released against, carrying both the
records standing behind the cell type's qualification and a data file for
every lot that went out.

## Domain quick reference

- The package stands on two tiers and the usual defect is to walk them as
  one list. The qualification tier is issued once for the cell type and
  cited by every lot; the lot tier is one data file per delivered lot. A
  sweep that walks families without walking lots cannot tell the
  difference.
- That is why the lot set is reconciled rather than merely inspected. A
  package holding every qualification record and one immaculate lot file
  passes a family-by-family sweep while three delivered lots have no
  paperwork at all, because nothing in a family sweep names the lots that
  were meant to be there.
- Reconciliation runs both ways. A declared lot with no data file is
  missing; a file for a lot the delivery never declares is not a bonus,
  it is the package and the delivery record disagreeing, and one of them
  is wrong.
- Bare cells add a second reconciliation the assembly-level packages do
  not need. The measured electrical data table is the only record that
  descends to the individual cell, so a table can be present, approved
  and at the governing issue while holding forty rows for a lot of four
  hundred delivered cells. Family-level completeness says nothing about
  cell-level coverage, and that check runs both ways too: a delivered
  cell with no row is uncovered, a row for a cell the lot never held is
  foreign data.
- The tiers are tied by a citation. Every lot cites the governing
  qualification approval, and a lot citing a superseded or withdrawn one
  looks complete because the reference it carries is a real reference to
  a real record.
- Inside a family several issues can sit together. The highest governs
  and the lower ones are superseded, not missing, so a package can hold
  the right document at the wrong issue and still pass a name-only check.
  A superseding draft does not inherit the approval of the issue beneath
  it.
- An approval is a state, not a presence. A record sitting in review or
  still in draft is in the package and is still not evidence.
- Two lot families are owed only because something happened -- a
  nonconformance was raised, a waiver was granted -- and each flag has to
  be stated. Inferring it from what was submitted makes a missing family
  invisible: nothing came in, so nothing was owed, so the file looks
  complete.

## Workflow

1. Resolve the qualification tier: group its records, take the governing
   issue of each family, check every family is present and approved, and
   read off the reference and date of the governing approval statement.
2. For each lot data file, resolve the families that lot owes from its
   stated context, requiring every conditional flag rather than
   defaulting an absent one.
3. Take the governing issue of each lot family, check presence and
   approval state, and raise a finding for any family the lot's context
   says is not owed.
4. Reconcile the measured data rows against the cells that lot delivered,
   naming uncovered cells and foreign rows separately, and report the
   coverage fraction rather than a bare pass.
5. Check the approval the lot cites against the governing one, treating
   both an absent citation and a superseded reference as blocking.
6. Reconcile the submitted lot files against the declared delivery lots
   in both directions, naming missing lots and undeclared files
   separately.
7. Release only when the finding list is empty, and report per tier, per
   lot and per cell count so one blocking lot is visible rather than a
   bare rejection.

## Pitfalls

- Grading families without grading lots. Every family check can pass on a
  package that is missing most of the delivery, because a family is
  present somewhere and nothing asks where the other lots went.
- Reading the measured data table as a family. It is the only record that
  reaches the individual cell, so its presence is the cheapest part of
  the check and its row set is the expensive part.
- Treating a foreign data row as harmless padding. A row for a cell the
  lot never delivered means the table and the lot identification
  disagree, which is a finding rather than surplus.
- Treating an undeclared lot file as harmless. It contradicts the
  delivery record, and a contradiction is a finding rather than a
  rounding.
- Accepting any citation that resolves. A superseded approval statement
  is a real document with a real reference; matching the governing one is
  the check, not matching something.
- Inferring the conditional lot families from the submission. An absent
  nonconformance file cannot tell you whether a nonconformance was
  raised.
- Taking any issue of a family as the family. The governing issue is the
  highest present; the lower ones are superseded rather than absent.
- Counting presence as approval. A draft in the package is still a draft,
  and release turns on the state, not the page count.

## Behavior contract (gate 3)

The two-tier family catalogues, the context-driven resolution of the
families a lot owes, the record validation with its approval-state and
approval-date rules, the highest-issue governing rule with superseded
issues retained, the qualification tier and the approval it names, the
cross-tier citation rule, the per-cell measured-data reconciliation in
both directions, the lot-set reconciliation in both directions and the
aggregated package verdict are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_data_documentation.py against
scripts/e2008_bare_cell_data_documentation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_data_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

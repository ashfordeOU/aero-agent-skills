---
name: e2008-sca-data-documentation-package
description: "Verify the documentation package covering a delivery of solar cell assemblies under ECSS-E-ST-20-08C clause 6.6, where a shared qualification tier and one file per delivery lot are graded together. Use when a package is presented for acceptance: resolve the families each tier owes, take the governing revision of every submitted record, reconcile the lot files against the lots the delivery declares in both directions, hold every lot to the governing qualification approval it cites, flag a lot whose manufacture closed before that approval was signed, and name what blocks acceptance. Trigger: ecss, e-st-20-08c, clause-6-6, sca-data-documentation-package, qualification-approval-record-tier, delivery-lot-file-reconciliation, governing-approval-citation-check, lot-built-before-approval-check."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-data-documentation-package, e-st-20-08c, clause-6-6, sca-data-documentation-package-acceptance, qualification-approval-record-tier, delivery-lot-file-reconciliation, governing-approval-citation-check, lot-built-before-approval-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Data Documentation Package (space-systems/ecss/e2008-sca-data-documentation-package)

Use when the task is the clause 6.6 documentation package of ECSS-E-ST-20-08C:
a delivery of cell assemblies is being handed over, and the package has to
carry both the records standing behind the type's qualification approval and a
file for every lot that went out.

## Domain quick reference

- The package stands on two tiers and the usual defect is to run them as one.
  The qualification tier is submitted once for the assembly type and cited by
  every lot; the lot tier is one set of records per delivery lot. A sweep that
  walks families without walking lots cannot tell the difference.
- That is why the lot set is reconciled, not merely inspected. A package
  holding the qualification records and one immaculate lot file passes every
  family check while three delivered lots have no paperwork at all, because
  nothing in the package names the lots that were meant to be there.
- Reconciliation runs both ways. A declared lot with no file is missing; a file
  for a lot the delivery never declares is not a bonus, it is the package and
  the delivery record disagreeing, and one of them is wrong.
- Two rules cross the tiers. Every lot cites the governing qualification
  approval, and a lot citing a superseded or withdrawn one looks complete
  because the reference it carries is real. And a lot whose manufacture closed
  before that approval was signed was built against an approval that did not
  yet exist, which is a different defect from citing the wrong one.
- Inside a tier a family can hold several revisions. The highest governs and
  the lower ones are superseded, not missing, so a package can hold the right
  document at the wrong issue and still pass a name-only check.
- An approval is a state, not a presence. A record sitting in review or still
  in draft is in the package and is still not evidence.
- Two lot families are owed only because something happened -- a nonconformance
  was raised, a waiver was granted -- and each flag has to be stated. Inferring
  it from what was submitted makes a missing family invisible: nothing came in,
  so nothing was owed, so the file looks complete.

## Workflow

1. Resolve the qualification tier: group its records, take the governing
   revision of each family, check every family is present and approved, and
   read off the reference and date of the governing approval statement.
2. For each lot file, resolve the families that lot owes from its stated
   context, requiring every conditional flag rather than defaulting an absent
   one.
3. Take the governing revision of each lot family, check presence and approval
   state, and raise a finding for any family the lot's context says is not
   owed.
4. Check the approval the lot cites against the governing one, treating both an
   absent citation and a superseded reference as blocking.
5. Compare the lot's manufacture completion against the approval date and flag
   a lot that closed before the approval existed.
6. Reconcile the submitted lot files against the declared delivery lots in both
   directions, naming missing lots and undeclared files separately.
7. Accept only when the finding list is empty, and report per tier and per lot
   so one blocking lot is visible rather than a bare rejection.

## Pitfalls

- Grading families without grading lots. Every family check can pass on a
  package that is missing most of the delivery, because a family is present
  somewhere and nothing asks where the other lots went.
- Treating an undeclared lot file as harmless. It contradicts the delivery
  record, and a contradiction is a finding rather than a rounding.
- Accepting any citation that resolves. A superseded approval statement is a
  real document with a real reference; matching the governing one is the check,
  not matching something.
- Checking the citation and stopping. A lot can cite the right approval and
  still have been built before it was signed, and only the dates show that.
- Inferring the conditional lot families from the submission. An absent
  nonconformance file cannot tell you whether a nonconformance was raised.
- Taking any revision of a family as the family. The governing revision is the
  highest present; the lower ones are superseded rather than absent.
- Counting presence as approval. A draft in the package is still a draft, and
  acceptance turns on the state, not the page count.

## Behavior contract (gate 3)

The two-tier family catalogues, the context-driven resolution of the families
a lot owes, the record validation with its approval-state and approval-date
rules, the highest-revision governing rule with superseded revisions retained,
the qualification tier and the approval it names, the cross-tier citation and
build-date rules, the lot-set reconciliation in both directions and the
aggregated package verdict are exercised by the gate 3 contract test:
scripts/test_e2008_sca_data_documentation_package.py against
scripts/e2008_sca_data_documentation_package_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_sca_data_documentation_package.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

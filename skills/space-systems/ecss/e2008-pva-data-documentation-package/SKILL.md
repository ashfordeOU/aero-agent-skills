---
name: e2008-pva-data-documentation-package
description: "Verify the documentation package delivered with each photovoltaic-assembly coupon under ECSS-E-ST-20-08C clause 5.7. Use when a coupon data package has to be accepted or sent back: resolve which record families this coupon owes, including the ones owed only because a nonconformance was raised or a waiver granted, take the governing revision of each submitted record, check every owed family is present at or above the revision its configuration calls for and carries an approval rather than a draft, flag an approval dated after the coupon left, and report what blocks acceptance. Trigger: ecss, e-st-20-08c, clause-5-7, coupon-data-package-completeness, pva-qualification-approval-records, coupon-documentation-revision-control, nonconformance-record-inclusion, waiver-record-inclusion, record-approval-date-check."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-pva-data-documentation-package, e-st-20-08c, clause-5-7, coupon-data-package-completeness, pva-qualification-approval-records, coupon-documentation-revision-control, nonconformance-record-inclusion, record-approval-date-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Coupon Data Package (space-systems/ecss/e2008-pva-data-documentation-package)

Use when the task is the clause 5.7 delivery of ECSS-E-ST-20-08C: a
photovoltaic-assembly coupon is being handed over, and the documentation
package that travels with it has to carry the records standing behind its
qualification approval.

## Domain quick reference

- The package is not one document with a signature on it. It is a set of
  record families — identity and traceability, the parts and materials it
  was built from, the process records of how it was built, the inspection
  results, the test results with the conditions they were taken under,
  and the qualification approval statement that rests on all of them.
- Two families are owed only because something happened. Nonconformance
  records are owed when a nonconformance was raised; waiver and deviation
  records are owed when a waiver was granted. Whether either happened is
  a fact about the coupon that has to be stated, because inferring it
  from what was submitted makes a missing family invisible: nothing was
  submitted, so nothing was owed, so the package looks complete.
- The inference runs the other way too. A family submitted while the
  context says it should not exist is not a bonus — the package and the
  account given of the coupon disagree, and one of them is wrong.
- A family can hold several revisions. The highest governs, and the lower
  ones are superseded, not missing. Reading a superseded revision as the
  governing one is how a package passes on a document that was already
  replaced.
- An approval is a state, not a presence. A record sitting in review or
  still in draft is in the package and is still not evidence, and a
  record approved after the coupon had already left was not what the
  coupon shipped against.

## Workflow

1. Resolve the owed families from the coupon context, requiring every
   conditional flag to be stated rather than defaulting an absent one.
2. Validate each submitted record: family, reference, revision, approval
   state, and — only when approved — the date of approval. An approved
   record with no date and a draft carrying one are both input defects.
3. Group the records by family and take the highest revision as
   governing, keeping the superseded revisions visible beside it.
4. For each owed family check presence, then the governing revision
   against the revision this coupon's configuration calls for, then the
   approval state, then the approval date against the delivery date.
5. Raise a finding for every family submitted that the context says is
   not owed.
6. Accept the package only when the finding list is empty, and report the
   per-family records so a single blocking family is visible rather than
   a bare rejection.

## Pitfalls

- Inferring the conditional families from the submission. An absent
  nonconformance file cannot tell you whether a nonconformance was
  raised, and treating silence as "none" is how the one record that
  mattered goes unmissed.
- Taking any revision of a family as the family. The governing revision
  is the highest one present; a package can hold the right document at
  the wrong issue and still look complete on a name-only check.
- Counting presence as approval. A draft in the package is still a draft,
  and it is the state, not the page count, that the acceptance turns on.
- Ignoring the approval date. A record approved weeks after delivery
  describes a configuration the coupon was never shipped against, which
  is a different defect from the record being absent.
- Dismissing a surplus family as harmless. It contradicts the account
  given of the coupon, and that contradiction is a finding rather than a
  rounding.
- Rejecting the package without naming the family. The per-family record
  is what makes the rejection actionable instead of a second round trip.

## Behavior contract (gate 3)

The context-driven resolution of owed families, the record validation
with its approval-state and approval-date rules, the highest-revision
governing rule with superseded revisions retained, the per-family
presence, revision, approval and date checks, the surplus-family finding
and the aggregated acceptance verdict are exercised by the gate 3
contract test:
scripts/test_e2008_pva_data_documentation_package.py against
scripts/e2008_pva_data_documentation_package_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_pva_data_documentation_package.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

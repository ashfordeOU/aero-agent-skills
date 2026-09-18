---
name: q20-eidp-example-cover
description: "Prepare and assess the end item data package cover page of ECSS-Q-ST-20C Annex F, used as the house header format for the Annex B package: hold the field order the worked example fixes, refuse a blank mandatory field or a non-positive issue and document count, rebuild the package number from the contract and serial number, check the three-signature approval block for one person holding two roles or signatures taken out of order or after the cover issue, and reconcile the declared document count with the index. Use when a package cover is raised, reissued or checked on receipt. Trigger: ecss, q-st-20c-annex-f, eidp-cover-page, eidp-header-format, eidp-number-pattern, eidp-approval-block, eidp-document-count."
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
  tags: [ecss, q-st-20c-quality-assurance-scope, q20-eidp-example-cover, eidp-cover-page-header, eidp-cover-field-order, eidp-number-format, eidp-cover-approval-block-chain, eidp-cover-document-count-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Data Package Cover Page (space-systems/ecss/q20-eidp-example-cover)

Use when the task is the Annex F worked data package cover of
ECSS-Q-ST-20C taken as the standard header format: a package is being
issued, reissued or received, and the question is whether its front sheet
identifies the package, agrees with the index and carries three real
signatures.

## Domain quick reference

- The example's value is the field order and the number pattern, not the
  wording. Project, contract, item, part and serial number, package
  number, issue, issue date, document count, index reference and the
  customer acceptance block -- always those, always in that order.
- The package number is derived, not chosen. Built from the contract
  number and the serial number it is unique by construction, so a cover
  whose number does not rebuild from its own fields is either a copy of
  another package's cover or a package pointing at the wrong item.
- The approval block is three signatures because it is three people. One
  name in two roles makes the check self-made, which is the one defect
  that leaves the block looking complete.
- The signatures have an order and a ceiling. Prepared, then checked, then
  approved -- and none of them after the cover's own issue date, because a
  signature dated later was added to a sheet already sent out. Same-day
  signatures are ordinary and are accepted.
- The document count is reconcilable. It is not a description of the
  package, it is a claim about the index behind the cover, and the index
  is what settles it. A line listed twice inflates the count while the
  package is short.
- The customer acceptance block is the only optional field. It is blank on
  every package at issue and filled on receipt, so grading it as mandatory
  rejects every cover the moment it is raised.

## Workflow

1. Refuse a header carrying a field the cover has no place for, so a local
   variant is caught rather than silently dropped.
2. Normalise each field by kind: identifiers trimmed and lowered, issue
   and document count positive integers, the issue date an ISO day.
3. Refuse a blank mandatory field, leaving the customer acceptance block
   free to be empty.
4. Rebuild the package number from the contract and serial number and
   compare it with the one printed.
5. Validate the approval block by role, refusing an unknown role, then
   raise an unsigned role, a repeated name, a signature out of order and a
   signature later than the cover issue date.
6. Reconcile the declared document count with the index, raising a
   repeated index line separately from the count itself.
7. Render the header with labels aligned to one column and return the
   verdict.

## Pitfalls

- Typing the package number instead of deriving it. A hand-typed number
  survives every check on the page and points at the wrong item.
- Counting signatures rather than signatories. Three filled rows with two
  names is an unchecked package.
- Reading the signature dates only against each other. A correctly ordered
  set can still sit after the issue date, which means the sheet went out
  unsigned.
- Treating the customer acceptance block as mandatory. It is filled by the
  receiving organisation, not the issuer.
- Trusting the document count. It is a claim about the index, and a
  duplicated index line is the usual reason the two disagree.

## Behavior contract (gate 3)

The header field order, the unknown-field refusal, the mandatory-field and
integer validation, the package number derivation and comparison, the
approval block role validation with the duplicate-name, signing-order and
issue-date rules, and the document count to index reconciliation are
exercised by the gate 3 contract test:
scripts/test_q20_eidp_example_cover.py against
scripts/q20_eidp_example_cover_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_eidp_example_cover.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

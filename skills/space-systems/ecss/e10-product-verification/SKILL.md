---
name: e10-product-verification
description: "Use when verify a product against its Technical Specification and close the verification out under ECSS-E-ST-10C clause 5.5.2: confirm each requirement carries at least one recognized verification method, resolve each assigned method to a status from its recorded objective evidence, partition the product's requirements into verified, open, failed and no-method-assigned, and decide whether the verification file supports close-out. Trigger: ecss, e-st-10-system-scope, product-verification, verification-methods, objective-evidence, close-out, djf, verification-file, technical-specification."
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
  tags: [ecss, e-st-10-system-scope, product-verification, verification-methods, objective-evidence, close-out, verification-file]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Product Verification Close-out (space-systems/ecss/e10-product-verification)

Use when the task is to verify a product against its Technical
Specification under ECSS-E-ST-10C clause 5.5.2 and close the
verification out on recorded objective evidence captured in the
verification file (DJF).

## Domain quick reference

- Four verification methods are recognized: test, analysis, inspection
  and review of design. A method outside that set is an input error,
  not an extra method -- the close-out argument rests on the evidence
  each recognized method is expected to produce.
- A requirement carrying no verification method at all is its own
  outcome, distinct from one whose methods are simply not finished.
  It means nobody has yet decided how the requirement will be shown to
  be met, which is a planning gap rather than an execution backlog.
- An assigned method's status is read from its evidence records, and a
  failing record wins over a passing one recorded for the same method.
  A later pass does not overwrite an earlier failure: the failure must
  be dispositioned explicitly, not averaged away.
- A method with no evidence recorded yet is open. Open is not a soft
  pass -- absence of evidence is exactly what close-out requires be
  eliminated.
- Requirement outcomes are ordered by severity: a requirement with any
  failing method is failed, otherwise any method still open leaves it
  open, and only a requirement whose every assigned method is verified
  is verified.
- The product's requirements partition into verified, open, failed and
  no-method-assigned -- each requirement lands in exactly one bucket,
  so the four lists together account for the whole specification.
- Close-out is reached only when the open, failed and
  no-method-assigned lists are all empty. A duplicated requirement
  identifier is rejected: the same requirement must not be counted
  twice in the close-out argument.

## Workflow

1. Validate each assigned verification method against the recognized
   set.
2. For a requirement with no assigned method, record it as
   no-method-assigned and move on.
3. For each assigned method, resolve its status from the evidence
   recorded against that method -- failed if any record fails,
   verified if at least one passes and none fail, otherwise open.
4. Roll the per-method statuses into the requirement's outcome,
   applying failed over open over verified.
5. Partition every requirement of the product's specification into the
   four outcome lists, rejecting a duplicate requirement identifier.
6. Declare the product verification-complete only when open, failed
   and no-method-assigned are all empty.

## Pitfalls

- Filing a requirement with no assigned method under "open". It hides
  a planning gap inside an execution backlog, and the two are closed
  out by different work.
- Letting a later passing record supersede an earlier failure on the
  same method. The failure is the finding; a retest closes it only
  through an explicit disposition, not by arriving afterwards.
- Treating a method with no evidence as passing because the analysis
  "was done". Close-out rests on the record, so an unrecorded result
  is an open method.
- Closing a requirement because one of its several assigned methods
  passed. Every assigned method must reach a verified state; the
  methods were assigned because each was judged necessary.
- Reporting a percentage verified as the close-out criterion. Clause
  5.5.2 close-out is all-or-nothing across the specification.
- Allowing the same requirement identifier twice in the product's
  list, which double-counts it and can make a failed requirement look
  covered by its duplicate.

## Behavior contract (gate 3)

The method validation, per-method status, requirement close-out,
product partition and completeness logic is exercised by the gate 3
contract test: scripts/test_e10_product_verification.py against
scripts/e10_product_verification_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e10_product_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

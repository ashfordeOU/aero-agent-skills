---
name: e10-verif-general
description: "Use when plan and manage system-level product verification under ECSS-E-ST-10C clause 5.5.1, consistently with the verification process of E-ST-10-02 and the testing scope of E-ST-10-03: assign recognized verification methods to a system requirement, link its approach back to the verification policy in the System Engineering Plan, track each method to a status, require an evidence reference before any method counts as closed, and aggregate the methods into the requirement's verification status. Trigger: ecss, e-st-10-system-scope, verification-planning, verification-policy, sep, verification-methods, method-status, closure-evidence, deviation."
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
  tags: [ecss, e-st-10-system-scope, verification-planning, verification-policy, verification-methods, closure-evidence, deviation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — System-Level Verification Management (space-systems/ecss/e10-verif-general)

Use when the task is to plan and manage product verification at
system level under ECSS-E-ST-10C clause 5.5.1 -- consistently with the
verification process of ECSS-E-ST-10-02 and the testing scope of
ECSS-E-ST-10-03, against the verification policy recorded in the
project's System Engineering Plan (SEP).

## Domain quick reference

- Four verification methods are recognized: test, analysis, inspection
  and review of design. The assignment for a requirement must be
  non-empty and free of duplicates -- a method listed twice usually
  means two verification plans were merged without reconciling them.
- Every requirement's verification approach must reference the SEP
  verification policy it follows. Without that link the approach
  cannot be shown consistent with the project policy, which is the
  substance of clause 5.5.1 at system level.
- The status register and the method assignment must agree in both
  directions. An assigned method with no status is untracked work; a
  status recorded for a method never assigned is a record pointing at
  verification nobody planned. Each is a separate finding.
- Closure comes in two flavours -- closed, and closed against an
  accepted deviation -- and both are closed. The deviation is part of
  the verification record, not a failure, but it propagates: a
  requirement whose methods include one closed with a deviation is
  itself closed with a deviation.
- Either closure requires an evidence reference on record. A method
  marked closed with nothing to point at is the finding this check
  exists to surface.
- The requirement's aggregate status is severity-ordered: one failed
  method makes the requirement failed regardless of the rest;
  otherwise it is closed (or closed with a deviation) only when every
  method has reached a closed status; while any method remains, it is
  in progress if any method is in progress, else open.
- A requirement is verified only when it carries no violations *and*
  every assigned method reached a closed status. Clean records on
  unfinished work are not verification.

## Workflow

1. Validate and normalize the methods assigned to the requirement,
   rejecting an empty list, an unrecognized method and a duplicate.
2. Confirm the requirement's approach references a SEP verification
   policy; record a linkage finding if it does not.
3. Cross-check the assignment against the status register in both
   directions and record the unstatused and unassigned findings.
4. For each method at a closed status, with or without a deviation,
   confirm an evidence reference is on record.
5. Aggregate the method statuses into the requirement's verification
   status under the severity ordering.
6. The requirement is verified only when the violation list is empty
   and every assigned method is closed.

## Pitfalls

- Treating "closed with an accepted deviation" as a failure, or as
  indistinguishable from plain closure. It closes the method, and it
  must still show on the requirement's aggregate status so the
  deviation stays visible at system level.
- Checking only that every assigned method has a status. The reverse
  direction -- a status for a method never assigned -- points at a
  requirement whose plan changed while its register did not.
- Accepting a closed method with no evidence reference because the
  test was witnessed. The verification record is the evidence, and a
  closure with nothing to cite cannot be audited.
- Letting a requirement report closed while one method has failed.
  Failure dominates the aggregate however many methods passed.
- Reporting a requirement as verified because its records are clean
  while methods are still open. No violations is not the same as
  finished.
- Omitting the SEP policy reference on the grounds that the methods
  are obviously appropriate. The link is what ties the requirement's
  approach to the project's declared policy.

## Behavior contract (gate 3)

The method and status validation, assignment normalization, SEP policy
linkage, assignment/status cross-check, closure-evidence and aggregate
status logic is exercised by the gate 3 contract test:
scripts/test_e10_verif_general.py against
scripts/e10_verif_general_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_verif_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

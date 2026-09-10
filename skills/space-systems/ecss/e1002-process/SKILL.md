---
name: e1002-process
description: "Use when running the verification process as a customer-supplier activity under ECSS-E-ST-10-02C clause 5.1: validate the product level, life-cycle phase, activity status and document type of each verification activity, assign the executor and the closure approver by role, determine which documents a phase still owes before it can close, roll individual activity statuses up to a single process status, and verify a closure sign-off against the activity's required evidence. Trigger: ecss, e-st-10-02c, verification process, customer supplier, product level, responsibility assignment, documentation completeness, closure sign-off, activity roll-up."
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
  tags: [ecss, e-st-10-02c, verification-process, responsibilities, product-level, documentation, closure, activity-status]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Verification Process (space-systems/ecss/e1002-process)

Use when running the verification process as a customer-supplier activity under ECSS-E-ST-10-02C clause 5.1 — validating each activity's product level, phase, status and document type, assigning responsibility, checking phase documentation completeness, rolling activity statuses up to a process status, and checking a closure sign-off.

## Domain quick reference

- Verification is a customer-supplier activity: for every verification activity one party executes and a different party approves closure. A single party doing both is a process defect.
- Every activity carries a product level and a life-cycle phase; the acceptable statuses and document types are fixed enumerations — an unrecognized value is an input error, not a new category.
- Documentation completeness is phase-scoped: a phase may only close when the documents that phase owes (plans, reports, control records) are all present.
- Activity status rolls up to the least-mature status: one open activity keeps the whole process open.
- Closure requires the sign-off of the designated closure approver (not the executor) against the activity's required evidence.

## Workflow

1. Validate the record fields: `validate_product_level`, `validate_phase`, `validate_status`, `validate_doc_type` each raise on an unknown value.
2. Assign responsibility: `assign_responsibility(activity)` returns the executor and closure approver roles.
3. Check documentation: `check_documentation(phase)` returns the documents still missing for that phase to close.
4. Roll activity statuses up: `rollup_activity_status(statuses)`.
5. Check a closure sign-off: `validate_closure(activity)`.
6. Evaluate the whole process record: `evaluate_process_record(record)`.

## Pitfalls

- Letting the executor also approve closure — breaks the customer-supplier separation clause 5.1 requires.
- Treating an unrecognized status as valid — the validators exist to reject it.
- Closing a phase with documentation gaps — `check_documentation` returns them; resolve, don't ignore.
- Security-marking vocabulary: the content-policy gate flags the word beginning 'classif-'; use 'categorized' instead.

## Behavior contract (gate 3)

`scripts/test_e1002_process.py` (stdlib unittest, offline) verifies field validation and error paths, responsibility assignment, phase documentation completeness, status roll-up to least-mature, closure sign-off checks, and the full process-record evaluation.

## Compliance

ECSS-E-ST-10-02C is a normative standard; this leaf implements only common-knowledge procedure and paraphrases it — no verbatim standard text. `license: Apache-2.0`, `compliance: STANDARDS-REF`, `standards: ecss` (reference-only), `gated: false`.

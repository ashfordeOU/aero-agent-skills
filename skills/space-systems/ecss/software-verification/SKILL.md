---
name: software-verification
description: "Use when you must plan the ECSS-E-ST-40C verification of spacecraft flight software: select the verification method (test, analysis, inspection, review) for each requirement category (functional, performance, interface, resource, safety, data), determine the verification depth and independence required by the software criticality, and list the verification records each method must produce. Produces the per-requirement method map, the criticality depth verdict, and the record list that closes the verification plan. Trigger: ecss verification, software test method, verification depth, verification records, requirement category, criticality, flight software, analysis inspection review."
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
  tags: [ecss, verification, verification-method, test-method, verification-depth, verification-records, e-st-40c]
  version: 0.1.0
  author: AeroSkills
---

# ECSS Software Verification (space-systems/ecss/software-verification)

Use when the task is ECSS-E-ST-40C software verification planning:
mapping requirement categories to verification methods, sizing
verification depth from criticality, and listing the records.

## Domain quick reference

- ECSS-E-ST-40C (space software engineering) expects every software
  requirement to be closed by a verification method: test, analysis,
  inspection, or review.
- Method choice follows the requirement category: functional and
  performance needs are proven mainly by test, resource budgets by
  analysis, interface agreements by test and inspection, safety needs
  combine test, analysis and review, and data items close by
  inspection and review.
- Verification depth scales with software criticality; catastrophic
  and critical software demand independent verification with formal
  records.
- Verification records (test procedures and results, analysis reports,
  inspection sheets, review minutes) are the evidence that each
  requirement was verified, and acceptance is gated on complete
  records.
- Independence of the verification activity grows with criticality:
  higher categories are verified by people independent of the
  development team.

## Workflow

1. Collect the software requirements with their category (functional,
   performance, interface, resource, safety, data).
2. Select the verification method for each requirement with
   verify_method.
3. Determine the verification depth, independence, and records for the
   software criticality with verification_depth.
4. Build the verification plan with plan_verdict and confirm every
   requirement received a method.
5. Close each requirement with its verification record before
   acceptance.

## Pitfalls

- Using test for every requirement instead of matching the method to
  the requirement category.
- Verifying resource budgets by test only when analysis is the primary
  method.
- Skipping independent verification for catastrophic or critical
  software.
- Treating inspection as a depth level instead of a method.
- Closing a requirement without its verification record.

## Behavior contract (gate 3)

The method-selection, depth, and plan-verdict logic is exercised by
the gate 3 contract test: scripts/test_software_verification_logic.py
against scripts/software_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_software_verification_logic.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

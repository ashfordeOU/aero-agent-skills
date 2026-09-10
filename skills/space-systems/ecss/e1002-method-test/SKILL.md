---
name: e1002-method-test
description: "Use when determine whether the test method can serve as the
  formal verification method for a requirement under ECSS-E-ST-10-02C clause
  5.2.2.2: check that the requirement's outcome is physically measurable, a
  representative test article is available, the operational environment is
  reproducible in a facility, and pass/fail criteria are defined; validate
  that a test-method record delegates detailed procedure, configuration, and
  criteria-level detail to an E-ST-10-03 test specification rather than
  embedding it; and roll up a requirement set's test-readiness and
  delegation-compliance status. Trigger: ecss, e-st-10-02c, test method,
  formal verification, verification conditions, test applicability,
  e-st-10-03, test specification delegation, pass/fail criteria, test
  readiness roll-up."
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
  tags: [ecss, e-st-10-02c, test-method, formal-verification, verification-conditions, e-st-10-03, test-specification-delegation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Test Method Applicability & Delegation (space-systems/ecss/e1002-method-test)

Use when the task is deciding whether the test method qualifies as the
formal verification method for a requirement under ECSS-E-ST-10-02C
clause 5.2.2.2, and checking that a test-method verification record
properly delegates procedural detail to an ECSS-E-ST-10-03 test
specification instead of embedding it.

## Domain quick reference

- Clause 5.2.2.2 treats test as a formal verification method only when
  four conditions all hold for the requirement: the requirement's
  outcome is physically measurable or observable via instrumentation;
  a representative test article (engineering, qualification, or
  flight-configuration hardware or an equivalent representative model)
  is available; the operational or induced environment relevant to the
  requirement can be reproduced or simulated in a test facility; and
  quantitative pass/fail criteria are defined ahead of the test. A
  requirement missing even one condition cannot be closed by test as a
  formal method and must be reselected (analysis, review of design, or
  inspection) or deferred until the missing condition is met.
- Once test is applicable, E-ST-10-02C fixes only the verification-level
  linkage (which requirement, which article, which environment, which
  criteria) and delegates the detailed "how" -- step-by-step procedure,
  test-article configuration, facility setup, instrumentation, and
  procedure-level acceptance thresholds -- to an ECSS-E-ST-10-03 test
  specification referenced by identifier. A record that embeds that
  procedural detail directly, instead of pointing at a test
  specification, has collapsed the two standards' scopes and is a
  delegation violation even if the test itself is otherwise applicable.
- A test-method record only closes to a terminal passed or failed
  status when it carries an evidence reference (test report or log
  identifier); a waived status requires a waiver reference. A record
  cannot be closed to a terminal status while it is still missing an
  applicability condition or a test-specification reference -- those
  are blocking findings, not administrative gaps.

## Workflow

1. For each requirement proposed for test-method verification, capture
   its four applicability conditions (measurable outcome, test article
   available, environment reproducible, pass/fail criteria defined).
   Reject the test method for that requirement if any condition is
   unmet, and record which condition(s) failed.
2. For each requirement where test is applicable, capture whether a
   test-specification reference is on record and whether the record
   itself embeds a detailed step-by-step procedure. Flag a delegation
   violation when the reference is missing, when a procedure is
   embedded, or both.
3. Before recording a terminal status (passed, failed, waived) for a
   requirement, confirm test is applicable and, for passed/failed,
   that an evidence reference is present, or for waived, that a waiver
   reference is present. Reject the status change otherwise.
4. Roll up the requirement set: count how many are test-applicable,
   how many carry a delegation violation, and how many are closed
   versus still pending. The set is test-verification-ready only when
   every applicable requirement has zero delegation violations and
   every non-pending requirement carries the evidence or waiver
   reference its status requires.

## Pitfalls

- Marking a requirement verified by test when the environment cannot
  actually be reproduced in a facility -- an unreproducible environment
  makes the four-condition check fail, and the requirement must be
  reselected to another method, not test method with a caveat.
- Writing the full test procedure, configuration, and instrumentation
  list directly into the E-ST-10-02C verification record -- that detail
  belongs in the referenced E-ST-10-03 test specification; embedding it
  is a delegation violation even when the underlying test is sound.
- Closing a requirement to passed on the strength of a favorable test
  run description alone, with no evidence reference recorded -- a
  terminal status without an evidence or waiver reference is not
  closeable and must stay pending.
- Treating "test specification reference present" as sufficient on its
  own -- a record can carry a reference and still separately embed a
  detailed procedure; both failure modes are checked independently.

## Behavior contract (gate 3)

The applicability-condition, delegation-violation, and status-closure
logic is exercised by the gate 3 contract test:
scripts/test_e1002_method_test.py against
scripts/e1002_method_test_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_method_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

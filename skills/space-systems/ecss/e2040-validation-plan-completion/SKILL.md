---
name: e2040-validation-plan-completion
description: "Assess whether the device Validation Plan is genuinely closed out so validation activities can formally begin. Use when an ECSS-E-ST-20-40C clause 5.7.4 implementation phase is ending: trace every requirement owing validation to a case, catch cases that trace nothing, flag cases carrying no pass criterion or no named environment, detect cases still written against a superseded build instead of the final implementation baseline, grade each mandated plan section on the maturity ladder, and combine coverage, runnability and section maturity into one closure index. Refuses an unknown maturity word, a section outside the mandated set and a case tracing an unregistered requirement. Trigger: ecss, e-st-20-40c, device-validation-plan-completion, validation-case-traceability, validation-pass-criterion, validation-plan-baseline-configuration, mandated-plan-section-maturity, validation-start-readiness."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-validation-plan-completion, device-validation-plan-completion, validation-case-traceability, validation-pass-criterion, validation-plan-baseline-configuration, mandated-plan-section-maturity, validation-start-readiness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Validation Plan Completion (space-systems/ecss/e2040-validation-plan-completion)

Use when the task is the validation-plan closure step of ECSS-E-ST-20-40C
clause 5.7.4 — deciding whether the Validation Plan for an ASIC, FPGA or IP
core has actually been completed at the end of the implementation phase, so
that validation of the device may formally start rather than start against a
plan that is still being written.

## Domain quick reference

- Closure is not a signature. A plan is closed out when three separate
  things hold at once: every device requirement that owes validation is
  traced to at least one validation case, every case is runnable as
  written, and every mandated plan section has reached final maturity.
  Any one of them alone is a partial answer.
- The denominator of the coverage figure is the set of requirements that
  owe validation, not the whole requirement register. A requirement
  discharged by verification during design does not owe a validation
  case, and counting it dilutes the shortfall that matters. A case that
  traces such a requirement is worth reporting the other way round: it
  suggests the register and the plan disagree about scope.
- A case is runnable when it states a pass criterion and, for a case
  carried by test, the environment it runs in. An analysis or
  review-of-design case has no bench, so demanding an environment of it
  manufactures a finding that is not there.
- The implementation phase has just produced the final build. A case
  still carrying a layout-phase configuration reference is not a
  formatting defect; it means the case was written against a device that
  no longer exists, and running it would produce evidence for the wrong
  article.
- Plan issue and section maturity are independent. Sections can all be
  final while the plan itself is still circulating as a draft issue, and
  the plan can be issued as final over sections that are not, so both
  are read and both are reported.

## Workflow

1. Validate the plan record, the requirement register and the case
   register. A malformed maturity word, a section outside the mandated
   set, a duplicate identifier or a case tracing an unregistered
   requirement is an input error, not a zero score.
2. Partition the requirement register into those that owe validation and
   those that do not, and refuse a register where nothing owes
   validation — that is a scoping mistake upstream of this step.
3. Trace requirements to cases both ways: collect requirements with no
   case, and cases with no requirement.
4. Assess each case for a pass criterion, and each test case for a named
   environment, to obtain the runnable fraction.
5. Compare every case configuration reference with the plan baseline and
   collect the cases still pointing at a superseded build.
6. Grade the mandated sections against the maturity ladder, separating
   absent sections from present-but-immature ones.
7. Combine coverage, runnability and section maturity into the weighted
   closure index, absorbing representation error at unity with a named
   tolerance, and report the verdict with every finding that produced
   it — including a plan issued below final.

## Pitfalls

- Reading full requirement coverage as closure. Coverage says a case
  exists; it says nothing about whether that case has a pass criterion
  or points at the right build, and both of those independently stop
  validation from starting.
- Counting requirements that do not owe validation in the coverage
  denominator. That inflates the score and hides the real gap; the
  cleaner signal is to report those requirements separately when a case
  claims them anyway.
- Demanding a validation environment of an analysis case. Only cases
  carried by test need a bench, and applying the test rule to every
  method produces findings a reviewer will correctly reject.
- Accepting a case whose configuration reference predates the
  implementation build. The reference is the whole point of the check:
  evidence gathered on a superseded article does not validate the
  delivered one.
- Treating the plan issue state as a formality once the sections are
  final. The two are read separately here precisely because they drift
  apart in practice.
- Relaxing the closure test to let a near-unity index pass. An index a
  few bits below one is a representation question, handled by the named
  tolerance inside the comparison; the closure condition itself is not
  widened.

## Behavior contract (gate 3)

The plan, requirement and case validation, two-way traceability, case
runnability, baseline-configuration comparison, mandated-section maturity
grading and the weighted closure index are exercised by the gate 3 contract
test: scripts/test_e2040_validation_plan_completion.py against
scripts/e2040_validation_plan_completion_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2040_validation_plan_completion.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

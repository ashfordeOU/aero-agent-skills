---
name: e1002-approach
description: "Use when defining the verification approach under ECSS-E-ST-10-02C clause 5.2.1: decide which requirements enter verification, check whether a chosen method is applicable at a given life-cycle stage, assess the risks for requirements that cannot be verified by test and the mitigations for them, validate a per-requirement strategy, roll closure status up by verification level, and confirm the plan is complete. Trigger: ecss, e-st-10-02c, verification approach, verification strategy, method applicability, stage, risk assessment, mitigation, plan completeness, closure roll-up."
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
  tags: [ecss, e-st-10-02c, verification-approach, strategy, method-applicability, risk-assessment, roll-up, plan-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Verification Approach (space-systems/ecss/e1002-approach)

Use when defining the verification approach under ECSS-E-ST-10-02C clause 5.2.1 — deciding which requirements enter verification, checking method applicability at a life-cycle stage, assessing risk for requirements not verified by test, validating a per-requirement strategy, and rolling closure status up by level.

## Domain quick reference

- Not every requirement enters verification: some categories (informative, derived-from-policy) are excluded — decide this first, before choosing a method.
- A verification method is only applicable at certain life-cycle stages; choosing a method the stage cannot carry is an approach defect.
- A requirement not verified by test needs a risk assessment: what could go unverified, and what mitigates it. A missing mitigation is a violation.
- Closure rolls up per verification level (e.g. unit, subsystem, system) so a level is only 'done' when its own activities are done.
- The plan is complete only when the roll-up has at least one entry and every entry is fully closed.

## Workflow

1. Decide entry: `requirement_needs_verification(category)`.
2. Check applicability: `is_method_applicable_at_stage(method, stage)`.
3. Assess risk: `risk_assessment_violations(assessment)`.
4. Validate a strategy: `verification_strategy_violations(requirement)`.
5. Roll up closure: `rollup_status(entries)`.
6. Confirm completeness: `is_verification_plan_complete(rollup)`.

## Pitfalls

- Choosing a method the stage cannot carry — check applicability before recording the method.
- Recording 'not by test' without a risk assessment and mitigation — that is a clause violation.
- Comparing roll-up percentages for exact equality in tests — compute as 100.0*closed/total and compare with a tolerance; the last ulp differs by operation order.
- Security-marking vocabulary: the content-policy gate flags the word beginning 'classif-'; use 'categorized' instead.

## Behavior contract (gate 3)

`scripts/test_e1002_approach.py` (stdlib unittest, offline) verifies entry decisions, method/stage applicability, risk-assessment violations, strategy validation, per-level roll-up, and plan-completeness. Float percentages compare with tolerance.

## Compliance

ECSS-E-ST-10-02C is a normative standard; this leaf implements only common-knowledge procedure and paraphrases it — no verbatim standard text. `license: Apache-2.0`, `compliance: STANDARDS-REF`, `standards: ecss` (reference-only), `gated: false`.

---
name: e1002-method-general
description: "Use when you need to determine which verification method or combination of methods -- test, analysis, review-of-design, inspection -- satisfies a requirement under ECSS-E-ST-10-02C clause 5.2.2.1: categorize the requirement, filter to the methods eligible for that category, enforce that a safety-critical requirement always carries test, apply the test-over-analysis-over-review-of-design-over-inspection precedence rule with a stated rationale whenever a more rigorous eligible method is skipped, and roll up a verification plan's per-method counts and its non-compliant requirement ids. Trigger: ecss, e-st-10-02c, verification method selection, test analysis review-of-design inspection, method precedence, verification plan completeness, safety-critical verification, method applicability rules."
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
  tags: [ecss, e-st-10-02c, verification-method, test, analysis, review-of-design, inspection, verification-plan]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — General Method Selection (space-systems/ecss/e1002-method-general)

Use when the task is selecting, for a single requirement, the
verification method or combination of methods under
ECSS-E-ST-10-02C clause 5.2.2.1 -- test, analysis, review-of-design,
inspection -- applying the applicability rules for the requirement's
category, the precedence among methods, and the completeness rules
for the resulting verification plan.

## Domain quick reference

- Clause 5.2.2.1 recognizes four verification methods: test (the
  requirement is verified by observing the actual behavior of the
  item, or a representative model of it, under real or simulated
  conditions), analysis (verified by calculation, modeling, or
  similarity to previously verified items), review-of-design (verified
  by examining the design process and its records rather than the
  hardware/software product itself), and inspection (verified by
  visual or dimensional examination of a physical characteristic).
  A requirement may be closed by one method or by a stated combination
  of more than one.
- Not every method is eligible for every requirement category:
  a purely procedural requirement (e.g. "a safety analysis shall be
  performed and recorded") is closed by review-of-design, not by
  testing the hardware; a workmanship requirement (e.g. "connectors
  shall be free of visible damage") is closed by inspection, not by
  analysis; a functional or performance requirement is normally closed
  by test or analysis. Proposing a method outside the category's
  eligible set is a plan error, not a stylistic choice.
  A safety-critical requirement additionally always requires test in
  its method set -- analysis alone, even if otherwise eligible, is
  never sufficient to close it.
- The four methods carry an implicit precedence from most to least
  rigorous: test, then analysis, then review-of-design, then
  inspection. Selecting a lower-rigor method while a higher-rigor one
  is eligible is allowed, but only when the plan states a rationale
  substantial enough to justify the deviation (e.g. "test is
  destructive to the flight unit" or "test access is not physically
  possible in the assembled configuration") -- a rationale that is
  missing or too brief to carry that justification is itself a
  finding against the plan.
- A verification plan is a set of these per-requirement method
  decisions; it is summarized by rolling up how many requirements each
  method closes and which requirement ids fail their eligibility,
  rationale, or safety-critical rule -- the plan is not complete until
  that non-compliant list is empty.

## Workflow

1. Categorize the requirement (functional, performance, physical,
   workmanship, design-process, or safety-critical). Reject an
   unrecognized category before selecting a method.
2. Look up the methods eligible for that category and filter the
   requirement's proposed method(s) against it. A requirement with no
   eligible method left after filtering is a plan error.
3. Require a non-empty, stated rationale for every requirement's
   method choice; a missing rationale is a plan error regardless of
   which method was chosen.
4. If the requirement is safety-critical, confirm test is among the
   selected methods; a safety-critical requirement closed by analysis
   alone is a plan error.
5. Determine the primary (most rigorous) method actually selected.
   If a more rigorous method was eligible but not selected, check the
   rationale is substantial enough to justify the deviation; a brief
   or generic rationale for a precedence deviation is a plan warning.
6. Aggregate every requirement's outcome into a plan summary: counts
   of requirements closed per method, and the list of requirement ids
   that are not compliant. The plan is complete only when that list is
   empty.

## Pitfalls

- Accepting a method the requirement's category does not make
  eligible (e.g. closing a workmanship requirement by analysis) just
  because it was written in the verification matrix -- the category
  determines the eligible set, not the plan author's preference.
- Treating a safety-critical requirement closed by analysis-only as
  compliant because analysis is eligible for its category in general
  -- the safety-critical rule additionally always requires test in the
  method set, independent of general category eligibility.
- Reading a one-line or boilerplate rationale as sufficient to skip a
  more rigorous eligible method -- a precedence deviation needs a
  rationale specific enough to explain why the higher-rigor method was
  not used, not just a rationale field that is merely non-empty.
- Rolling up a plan's method counts without checking each
  requirement's individual compliance -- a requirement can have a
  countable primary method and still be non-compliant (missing
  rationale, ineligible method, or a violated safety-critical rule).

## Behavior contract (gate 3)

The category-eligibility, safety-critical, precedence-deviation, and
plan-roll-up logic is exercised by the gate 3 contract test:
scripts/test_e1002_method_general.py against
scripts/e1002_method_general_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_method_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

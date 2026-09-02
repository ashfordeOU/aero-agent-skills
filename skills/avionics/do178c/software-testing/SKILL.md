---
name: software-testing
description: "Generate requirements-based-testing test cases for DO-178C airborne software and count the test cases each structural-coverage metric demands: statement coverage needs 1 case per statement, decision coverage 2 cases per decision, and mc-dc needs n+1 cases for a compound boolean condition with n independent terms. Use when a task asks how many test cases a boolean condition requires, how to derive tests from high-level and low-level requirements, which coverage objectives apply per software level (level A requires mc-dc, B decision coverage, C statement coverage, D and E none), or how to measure and document structural coverage against the DO-178C Table A-7 objectives. Trigger: requirements-based-testing, mc-dc test-case-count, structural-coverage measurement, coverage-objectives per level, test case generation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
gated: false
domain: avionics
pack: avionics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: do178c
  tags: [requirements-based-testing, structural-coverage, mc-dc, statement-coverage, decision-coverage, test-case-count, coverage-objectives]
  version: 0.1.0
  author: Aero Agent Skills
---

# DO-178C Requirements-Based Software Testing (avionics/do178c/software-testing)

Use when the task is generating test cases from DO-178C requirements,
counting the test cases a structural coverage metric demands for a boolean
condition, or measuring statement, decision, and MC/DC coverage against the
objectives for the software level.

## Domain quick reference

- Requirements-based testing: every high-level and low-level requirement is
  exercised by at least one test case derived from that requirement (normal
  range, plus robustness and boundary cases the requirement implies).
- Statement coverage: every executable statement runs at least once. Test
  cases needed per statement: 1.
- Decision coverage: every decision (boolean expression) takes both
  outcomes. Test cases needed per decision: 2.
- MC/DC (modified condition/decision coverage): every condition in a
  decision takes both outcomes, and each condition independently affects
  the decision outcome. For a compound condition with n independent terms:
  n + 1 test cases.
- Worked count: A AND B AND C (3 terms) needs 4 MC/DC cases: TTT, FTT,
  TFT, TTF.
- Worked count: A OR B OR C OR D (4 terms) needs 5 MC/DC cases: FFFF,
  TFFF, FTFF, FFTF, FFFT.
- Coverage objectives per level (DO-178C Table A-7, summarized): level A =
  statement + decision + MC/DC; level B = statement + decision; level C =
  statement; levels D and E = none required.
- Required structural coverage: 100% of the metric the level demands. The
  test case count for one compound condition is: MC/DC n + 1, decision 2,
  statement 1.

## Workflow

1. Confirm the software level (DAL) and the coverage depth it demands
   (A MC/DC, B decision, C statement, D/E none).
2. Derive test cases from each high-level and low-level requirement:
   normal-range inputs first, then robustness and boundary cases the
   requirement implies.
3. For each compound boolean condition in the software, count its
   independent terms n and compute the required test cases: level A n + 1,
   level B 2, level C 1.
4. Generate the minimal MC/DC vector set for each compound condition
   (n + 1 assignments: all-true plus one-false-per-term for AND, all-false
   plus one-true-per-term for OR).
5. Run the test cases on the target or host with instrumentation; measure
   statement, decision, and MC/DC coverage.
6. Compare measured coverage against the objectives for the level;
   investigate every shortfall.
7. Document the coverage analysis; justify residual uncovered code (dead
   code, masked logic) instead of claiming 100% without evidence.

## Pitfalls

- Confusing this leaf with avionics/do178c/verification: that leaf covers
  the verification process (reviews, analyses, independence, verification
  results); this leaf is specifically requirements-based test case
  generation and structural coverage measurement.
- Confusing this leaf with avionics/do254/verification: DO-254 verifies
  airborne electronic hardware; DO-178C software testing applies to
  software items.
- Using 2n cases for MC/DC: a 3-term AND needs 4 cases (TTT, FTT, TFT,
  TTF), not 6.
- Covering a level A decision with statement or decision coverage only:
  level A demands MC/DC, level B demands decision coverage.
- Forgetting that levels D and E have no structural coverage objectives,
  while requirements-based testing still applies to them.
- Counting operators instead of terms: A AND (B OR C) has 3 independent
  conditions, so MC/DC needs 4 cases.
- Ignoring short-circuit evaluation: assignments that are unreachable must
  not be counted as satisfied outcomes.
- Reporting 100% coverage without instrumented evidence: coverage is
  measured on executed code, not inferred from test design.

## Behavior contract (gate 3)

The test-case counting and coverage-objective logic is exercised by the
gate 3 contract test: scripts/test_software_testing.py against
scripts/software_testing_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_software_testing.py

## Compliance

- Standards referenced, not reproduced: DO-178C text is proprietary
  (RTCA/EUROCAE); summary-only per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.

---
name: e1003-eq-general
description: "Use when verifying the general equipment-level test requirements under ECSS-E-ST-10-03C clause 5.1, ahead of picking the qualification, acceptance, or protoflight test baseline: confirm the test model carries the correct campaign (qualification/acceptance/protoflight), validate the test configuration is flight-representative or has documented deviations with every required interface simulated, check that mechanical/electrical interface checks bookend the test sequence, and run the functional-test-before/after and performance-test-bookend rules across the sequence. Trigger: ecss, e-st-10-03c, equipment test requirements, test configuration, interface check, functional test, performance test, test model applicability, general equipment tests."
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
  tags: [ecss, e-st-10-03c, equipment-test, test-configuration, interface-check, functional-test, performance-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Equipment General Test Requirements (space-systems/ecss/e1003-eq-general)

Use when the task is the general, campaign-independent equipment-level
test requirements of ECSS-E-ST-10-03C clause 5.1 -- model applicability,
test configuration, interface checks, and functional/performance test
rules -- ahead of selecting the qualification (clause 5.2), acceptance
(clause 5.3), or protoflight (clause 5.4) test baseline.

## Domain quick reference

- ECSS-E-ST-10-03C clause 5.1 sets the rules that apply to every
  equipment test campaign regardless of which baseline (qualification,
  acceptance, protoflight) is run: which test model carries which
  campaign, how the test configuration must relate to the flight
  configuration, when interface checks are mandatory, and when
  functional and performance tests must be run.
- Test-model applicability: a qualification model (QM) carries the
  qualification campaign, a protoflight model (PFM) carries the
  protoflight campaign, and a flight model (FM) carries the acceptance
  campaign. An engineering model (EM) carries no formal test campaign
  under this clause. See the sibling e1002-models leaf for full model
  definitions; this leaf only checks which campaign a model is
  entitled to run.
- Test configuration: the equipment under test must be in a
  flight-representative configuration; any departure from that
  configuration must be recorded as a documented deviation, and every
  interface the campaign depends on must be represented by GSE or an
  interface simulator.
- Interface checks: a mechanical/electrical interface check (fit,
  continuity, insulation) is mandatory before the first test and after
  the last test of the sequence, to bound whether the campaign
  introduced interface damage.
- Functional/performance rules: a functional test is run immediately
  before and after every step of the sequence, to attribute any
  degradation to that specific step; a performance test is run at the
  start and end of the whole sequence, to trend parameters across the
  campaign.

## Workflow

1. Determine the test model under test (EM, QM, PFM, FM, ...) and the
   campaign being claimed for it (qualification, acceptance,
   protoflight). Confirm the model is entitled to that campaign --
   flag a mismatch (e.g. an FM run through a qualification campaign)
   before any test is planned.
2. Record the test configuration: whether it is flight-representative,
   any documented deviations if it is not, and which required
   interfaces are represented by GSE or simulators. Flag an
   undocumented departure from the flight configuration and any
   required interface left unsimulated.
3. Build the ordered test sequence (one entry per test step) and
   confirm the mandatory interface check bookends: a pre-interface
   check before the first step, a post-interface check after the last
   step.
4. Confirm the functional-test rule: every step in the sequence carries
   a functional test immediately before and immediately after it.
5. Confirm the performance-test rule: the first and last steps of the
   sequence carry a performance test.
6. Aggregate model-applicability, configuration, interface-check, and
   functional/performance violations into one review; the campaign is
   not ready to open until every category is empty. Hand a compliant
   review to baseline selection (the sibling e1003-eq-qual /
   e1003-eq-acceptance / e1003-eq-protoflight leaves).

## Pitfalls

- Running a campaign the test model is not entitled to (e.g. treating
  an EM as if it carried a qualification campaign) -- the campaign
  result carries no compliance weight for the wrong model.
- Accepting an unrepresentative test configuration without a recorded
  deviation -- the test result can no longer be traced back to the
  flight configuration it is meant to stand in for.
- Treating the interface check as optional mid-sequence -- clause 5.1
  only mandates the bookend checks (before the first step, after the
  last); the rule is about detecting change across the whole campaign,
  not auditing every step.
- Skipping the functional test after a step because "nothing failed" --
  the before/after pair is what makes a degradation attributable to
  that specific step.
- Running the performance test only once -- a single measurement gives
  no trend; the rule needs both the start-of-campaign and
  end-of-campaign performance test to compare against.

## Behavior contract (gate 3)

The model-applicability, configuration, interface-check, and
functional/performance-test logic is exercised by the gate 3 contract
test: scripts/test_e1003_eq_general.py against
scripts/e1003_eq_general_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_eq_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

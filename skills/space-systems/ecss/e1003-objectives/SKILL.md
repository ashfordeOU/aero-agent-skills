---
name: e1003-objectives
description: "Use when defining the test objectives for a qualification, acceptance or protoflight test campaign under ECSS-E-ST-10-03C clause 4.5: define the demonstrated-margin and workmanship-screen objectives assigned to each campaign type, derive the required test level (qualification level vs acceptance level) and duration class (full vs reduced) that those objectives imply, and validate a proposed test definition against the campaign's assigned objectives before test conditions, levels and durations are locked in downstream. Trigger: test objectives, qualification testing, acceptance testing, protoflight testing, demonstrated margin, workmanship screen, e-st-10-03, ecss, e-st-10c."
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
  tags: [ecss, e-st-10-03c, test-objectives, qualification, acceptance, protoflight]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Objectives (space-systems/ecss/e1003-objectives)

Use when the task is setting the objective of a test campaign under
ECSS-E-ST-10-03C: what a qualification, acceptance, or protoflight
campaign must demonstrate before its levels, durations, and conditions
are defined.

## Domain quick reference

- ECSS-E-ST-10-03C clause 4.5 assigns each test campaign type a
  distinct objective. Qualification testing demonstrates, on a
  qualification (or protoflight) article, that the design meets its
  requirements with margin beyond the levels and duration expected in
  the mission environment -- it exists to uncover marginal design
  weaknesses.
- Acceptance testing demonstrates the absence of workmanship and
  manufacturing defects in the deliverable/flight article. It runs at
  levels representative of the expected flight environment, with no
  added margin, for the minimum duration needed to screen workmanship
  -- adding margin or duration only risks damaging or consuming the
  life of hardware that is meant to fly as-is.
- Protoflight testing is applied to a flight article that also serves
  the qualification role, so it combines both objectives on one
  article: it uses qualification-level severity to demonstrate margin,
  but only the reduced, acceptance-like duration, so the flight
  article's operational life margin is not consumed before flight.
- A test definition's level and duration are downstream of its
  campaign's objective, not independent choices: the required level
  and duration for a campaign are derived from what that campaign must
  demonstrate, not set ad hoc per test.

## Workflow

1. Identify the test campaign type for the article under test:
   qualification, acceptance, or protoflight.
2. Derive the objective set assigned to that campaign: qualification
   needs to demonstrate margin only; acceptance needs to screen
   workmanship only; protoflight needs both, since it demonstrates
   margin and screens workmanship on the same flight article.
3. Derive the required test level from the objective set: margin
   demonstration (qualification, protoflight) needs qualification
   level; workmanship screening alone (acceptance) needs acceptance
   level, representative of the expected flight environment.
4. Derive the required duration class from the objective set and
   whether the article is flight-life-at-risk: full duration only for
   qualification (a dedicated, non-flight article); reduced duration
   for acceptance and protoflight, since both put the deliverable or
   flight article's remaining operational life at risk.
5. Before test conditions and numeric levels/durations are defined
   downstream (e1003-eq-qual / e1003-eq-acceptance /
   e1003-eq-protoflight, e1003-test-conditions), validate any proposed
   test definition's level and duration against the campaign's derived
   objectives and flag mismatches rather than assuming they are
   correct.

## Pitfalls

- Running a qualification test at acceptance-level severity or
  duration -- it will not demonstrate the design margin the
  campaign exists to prove.
- Adding margin above flight levels to an acceptance test -- it does
  not improve workmanship screening and instead risks damaging
  deliverable or flight hardware that has no qualification margin.
- Running a protoflight test for the full qualification duration
  instead of the reduced, acceptance-like duration -- it consumes the
  flight article's operational life margin before it ever flies.
- Treating protoflight as "qualification testing on a flight article"
  without also reducing duration, or as "acceptance testing with
  extra margin" without recognizing it must still demonstrate margin
  -- protoflight is the combination of both objectives, not either one
  alone.

## Behavior contract (gate 3)

The objective-assignment, required-level/duration-derivation, and
test-definition-validation logic is exercised by the gate 3 contract
test: scripts/test_e1003_objectives.py against
scripts/e1003_objectives_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_objectives.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

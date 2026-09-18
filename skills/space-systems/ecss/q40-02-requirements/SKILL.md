---
name: q40-02-requirements
description: "Audit a space-project hazard-analysis programme against the general requirements of ECSS-Q-ST-40-02C clause 5.1. Use when the task is confirming that the analysis reaches every mission phase and every planned operation rather than the flight phases alone, that a hazard log and a hazard report duty exist with a named custodian and an agreed update interval, that the analysis techniques and supporting tools are declared before the work starts, and that the events forcing a re-analysis - design change, operational anomaly, procedure change, milestone review, newly identified hazard - are written down instead of left to judgement. Trigger: ecss, q-st-40-02c, hazard-analysis-programme-coverage, hazard-log-custody, hazard-report-duty, hazard-analysis-review-trigger, mission-phase-hazard-coverage, hazard-analysis-tool-declaration."
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
  tags: [ecss, q-st-40-02-hazard-analysis-scope, q40-02-requirements, hazard-analysis-programme-coverage, hazard-log-custody, hazard-report-duty, hazard-analysis-review-trigger, mission-phase-hazard-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hazard Analysis — General Requirements (space-systems/ecss/q40-02-requirements)

Use when the task is the general hazard-analysis requirement of
ECSS-Q-ST-40-02C clause 5.1 — deciding how far the analysis has to
reach, who holds the hazard log, what the hazard report is owed for,
which techniques and tools were declared, and what reopens the work.

## Domain quick reference

- The reach of the analysis is derived from the project, not declared
  by it. A project that flies a launch segment owns the ascent phase
  whether or not its plan mentions it; one that brings hardware back
  owns descent, landing and recovery; one that carries crew owns the
  habitation phase on top. Reading the phase set out of the project
  profile is what stops a programme shrinking its own obligation by
  writing a short plan.
- Coverage is phases and operations together. A phase list with no
  operations underneath it is an index, and an operation sitting in a
  phase the analysis never reaches is a hole. Both halves have to be
  present before the coverage claim means anything.
- The hazard log is a custody object. It needs somebody named to hold
  it and an agreed interval at which its status is refreshed, because
  a log nobody owns drifts out of date silently and still reads as a
  log. An interval longer than roughly half a year outruns the design
  changes that feed it.
- The hazard report duty is set by severity and has a floor. A project
  may agree to raise reports for more severities than the floor, never
  for fewer: the catastrophic and critical entries are the ones a
  reviewer outside the project has to be able to read.
- Techniques and tools are declared before the work, not inferred
  after it. An undeclared technique cannot be reviewed for fitness
  against the project it was used on, so the declaration is part of
  the requirement rather than documentation of it.
- The events that reopen the analysis are written down. Design change,
  operational anomaly, procedure change, milestone review and a newly
  identified hazard are the ones that recur; an undeclared trigger
  means the reopening decision fell to judgement, and judgement leaves
  no audit trail.

## Workflow

1. Validate the project profile: the segments flown, whether crew is
   carried. Reject an unknown segment and reject a crewed profile with
   no orbital segment, because the habitation phase has nowhere to sit.
2. Derive the required phase set from the profile and compare it with
   the declared coverage. Report each missing phase, and list the
   declared phases that fall outside the derived set separately rather
   than counting them as coverage.
3. Place every planned operation in a phase and flag the operations
   whose phase is not covered. These are the holes a phase-level
   coverage percentage hides.
4. Check hazard-log custody: maintained, a named custodian, an update
   interval on record and inside the limit. Check the hazard-report
   duty covers the mandatory severities.
5. Check that at least one analysis technique and one supporting tool
   are named.
6. Check the re-analysis triggers against the required set and list
   each one left undeclared.
7. Aggregate. The programme is compliant only when no finding stands;
   the coverage fraction is reported alongside so a partial programme
   can be sized, not only rejected.

## Pitfalls

- Reading the phase set from the plan instead of the project. A plan
  that never mentions transport and storage still owes it, and taking
  the plan as the requirement makes the gap invisible.
- Reporting a coverage percentage with the operations unchecked. Every
  phase can be covered while an operation sits in a phase the analysis
  does not reach, and the percentage reads clean.
- Treating a hazard log with no custodian as an administrative detail.
  An unowned log still accepts entries, still looks current, and is
  the usual way a hazard stops being tracked without anyone deciding.
- Agreeing a hazard-report duty for the severities the project finds
  convenient. The catastrophic and critical floor exists so the
  reports a reviewer needs are not the ones the project dropped.
- Leaving the re-analysis triggers unwritten because "obviously we
  would redo it". The trigger list is the auditable part; without it
  the decision to reopen is unreviewable either way it went.

## Behavior contract (gate 3)

The profile-derived phase set, phase and operation coverage, hazard-log
custody, report-duty floor, technique and tool declaration, and
review-trigger logic is exercised by the gate 3 contract test:
scripts/test_q40_02_requirements.py against
scripts/q40_02_requirements_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_02_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

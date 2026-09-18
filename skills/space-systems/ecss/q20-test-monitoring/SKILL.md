---
name: q20-test-monitoring
description: "Monitor the quality surveillance of a test while it runs, under ECSS-Q-ST-20C clause 5.6.4: derive which timeline steps demand a product-assurance presence and which add the customer, compare that demand with the attendance record end to end rather than by sampling, grade each mandatory hold point for release by its owning authority and for a following step that started before the release, and check every anomaly was logged, attributable to a step window and witnessed by the roles that owed presence. Use when a run is being watched live or a run log is reconstructed afterwards. Trigger: ecss, q-st-20c-clause-5-6-4, qa-test-surveillance-coverage, mandatory-hold-point-release, test-anomaly-witnessing, run-log-attendance-record, hold-point-sequence-violation."
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
  tags: [ecss, q-st-20-quality-assurance-scope, q20-test-monitoring, qa-test-surveillance-coverage, mandatory-hold-point-release, test-anomaly-witnessing, run-log-attendance-record, hold-point-sequence-violation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Quality Assurance -- Test Performance Monitoring (space-systems/ecss/q20-test-monitoring)

Use when the task is the surveillance of test performance of
ECSS-Q-ST-20C clause 5.6.4: a test is running, or its run log is being
reconstructed, and the question is whether quality assurance was
actually present where the test demanded it, whether the hold points did
their job, and whether the anomalies were witnessed by the people who
were supposed to see them.

## Domain quick reference

- Surveillance demand is derived from the timeline, not declared. A step
  that consumes the article's margin or cannot be repeated demands a
  product-assurance presence; a step the customer has reserved demands
  the customer as well, and still demands product assurance. Deriving
  the demand is what turns a witness list into a check.
- Presence is an interval question. A surveillance role covers a step
  only when one attendance interval spans the whole step window --
  arriving halfway through a pyro firing is not attendance at it. The
  coverage is therefore counted over role-step pairs, not over steps, so
  a step missing one of two demanded roles is visibly two thirds covered
  rather than simply failed.
- A hold point is a gate with an owner. It fails four separate ways: it
  is never released; it is released by somebody who does not own it; it
  is released before the step it holds has even finished; or the next
  step starts before the release timestamp, which means the gate was
  physically walked through. The last one is the finding that hurts,
  because the run continued on an unreleased hold.
- An anomaly has to be attributable. A time stamp that falls in no step
  window means the run log and the anomaly log disagree, and no
  witnessing statement about it can be graded until that is resolved.
- A witness statement is checked against attendance, not taken on trust.
  A product-assurance witness recorded for a step nobody from product
  assurance attended is a record defect in its own right.

## Workflow

1. Normalise the timeline: unique step identifiers, unique sequence
   numbers, a window that does not end before it starts, and a
   criticality drawn from the recognised vocabulary.
2. Normalise the attendance record and refuse an interval that leaves
   before it arrives.
3. Derive the surveillance demand per step and count the covered
   role-step pairs, keeping the uncovered pairs by name.
4. Check that the steps actually ran in their sequence order; a step
   starting before its predecessor is a timeline defect that invalidates
   the hold-point reasoning that follows.
5. Grade each hold point on all four failure modes, resolving the
   following step from the sequence order rather than from the list
   order.
6. Grade each anomaly: logged, attributable to a step window, witnessed
   by every role that owed presence at that step, and with those witness
   claims backed by attendance.
7. Return the coverage fraction and the findings; the run is
   surveillance-complete only when nothing is outstanding.

## Pitfalls

- Counting a step as covered because somebody signed the run log. The
  signature is not the interval; presence has to span the window the
  step occupied.
- Grading hold points in list order. The gate is about what ran next on
  the timeline, so the following step comes from the sequence order, and
  a list written out of order silently grades the wrong pair.
- Treating an early hold-point release as harmless. Releasing before the
  held step finished means the gate was signed on an expectation rather
  than on a result.
- Accepting an anomaly with a witness list and no attendance behind it.
  The two records have to agree, and where they do not, the attendance
  record is the one that reflects who was in the room.
- Reporting surveillance as a single pass or fail. The covered fraction
  and the named uncovered pairs are what a reviewer needs to decide
  whether the run is recoverable.

## Behavior contract (gate 3)

The timeline normalisation, attendance intervals, surveillance demand
derivation, role-step coverage, sequence-order check, the four
hold-point failure modes and the anomaly witnessing checks are exercised
by the gate 3 contract test: scripts/test_q20_test_monitoring.py against
scripts/q20_test_monitoring_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_test_monitoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

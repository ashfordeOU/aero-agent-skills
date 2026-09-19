---
name: e50-inter-spacecraft-network-exception-reporting
description: "Assess whether an inter-spacecraft network really reports its exceptions to the entity that manages it, per ECSS-E-ST-50C clause 5.7.4.4. Follow one exception through the three places it is lost: reporting latency against the allowance its severity group carries, the store needed to hold exceptions raised while the path to the manager is down, and a rate limiter that discards whatever it will not pass. Show where one limiter shared across severity groups lets a storm of routine reports crowd out an alarm. Use when reviewing fault reporting on a formation or relay network. Trigger: ecss, e-st-50c-clause-5-7-4-4, inter-spacecraft-exception-reporting, exception-reporting-latency-budget, exception-retention-during-outage, exception-rate-limiter-suppression, severity-group-limiter-partition."
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
  tags: [ecss, e-st-50c-clause-5-7-4-4, e50-inter-spacecraft-network-exception-reporting, inter-spacecraft-exception-reporting, exception-reporting-latency-budget, exception-retention-during-outage, exception-rate-limiter-suppression, severity-group-limiter-partition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Inter-Spacecraft Network Exception Reporting (space-systems/ecss/e50-inter-spacecraft-network-exception-reporting)

Use when an inter-spacecraft network has to tell its manager that something
went wrong, per ECSS-E-ST-50C clause 5.7.4.4 — whether the report actually
arrives, in time, and without being thrown away on the way.

## Domain quick reference

- Raising an exception is not reporting one. The obligation is
  discharged when the managing entity has it, so the design is graded on
  arrival and the three ways arrival fails: too late, not held through
  an outage, or discarded by a limiter.
- Latency is a sum of stages, and the stages are not all under the same
  owner. Detection sits with the node, queueing with the on-board
  software, propagation with the network diameter and forwarding with
  the relay, and a design that only budgets the last one understates
  the total badly.
- The allowance belongs to the severity group, not to the network. An
  alarm and a routine notice travel the same path but are owed
  different arrival times, so each group is graded against its own
  allowance rather than against a single network figure.
- An outage does not excuse a lost exception; it converts the
  requirement into a store. Exceptions raised while the path to the
  manager is down have to be held until it returns, and the store size
  is rate times outage times record size, summed over every flow.
- A rate limiter protecting the link is a deliberate loss mechanism
  pointed at the reporting path. Whatever it does not pass is never
  reported, so a limiter is part of the assessment rather than a
  mitigation of it.
- One limiter shared across severity groups is the defect worth looking
  for. Routine reports are numerous and alarms are rare, so the shared
  limiter is nearly always saturated by the routine traffic at the exact
  moment the rare report appears. Giving each severity group its own
  share fixes it; raising the shared limit only moves the storm.

## Workflow

1. Describe each exception flow as a severity group with its own rate,
   record size, stage latencies and arrival allowance. Reject an unknown
   severity or an unknown field rather than defaulting it.
2. Sum detection, queueing, per-hop propagation and forwarding into a
   reporting latency for each group.
3. Compare each latency against that group's allowance with a relative
   tolerance so a flow landing exactly on the allowance passes on every
   build host.
4. Compute the store the declared outage asks for, summing every flow,
   and compare it with the store provided under the same tolerance.
5. Determine what the rate limiter discards. Grade a per-group limiter
   against each group's own rate; grade a shared limiter against the
   aggregate offered load of all groups together.
6. Where a shared limiter saturates, say plainly that the most urgent
   group present can be crowded out by the others, and recommend
   partitioning the limit per group rather than raising it.
7. Report the verdict as reported only when latency, retention and
   suppression all hold, and give each shortfall its own remedy number:
   the store required, or the rate the store already provided survives.

## Pitfalls

- Grading the network against one arrival time. Severity groups carry
  different allowances, and a single figure either over-engineers the
  routine traffic or lets an alarm arrive late.
- Budgeting only the link. Detection and queueing usually dominate the
  total on a short-diameter network, so a latency built from
  propagation alone looks comfortable and is not.
- Treating an outage as a period with no exceptions in it. Outages are
  when exceptions happen; the flow continues and the store is what
  decides whether any of it survives.
- Sizing the store for one flow. Every flow competes for the same store
  during the same outage, so the requirement is the sum and a
  per-flow check passes a design that overflows.
- Leaving the rate limiter out of the assessment. It is a loss
  mechanism, and a report that grades latency and retention while
  ignoring the limiter can call a design compliant that drops alarms.
- Answering a saturated shared limiter by raising the shared limit. The
  routine traffic scales with the network and will saturate the new
  limit too; only a per-group partition protects the rare report.

## Behavior contract (gate 3)

Flow and severity validation, the staged latency sum, the per-group
allowance comparison at its exact boundary, the outage retention sum and
its rate inverse, per-group versus shared limiter suppression, the
most-urgent-group selection and the combined verdict are exercised by
the gate 3 contract test:
scripts/test_e50_inter_spacecraft_network_exception_reporting.py against
scripts/e50_inter_spacecraft_network_exception_reporting_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e50_inter_spacecraft_network_exception_reporting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e3311-in-service-feedback-launch-site-procedures-monitoring
description: "Monitor an explosive item through service under ECSS-E-ST-33-11C clause 4.16, covering information feedback, launch-site procedures and storage monitoring. Use when the task is deciding whether an installed or stored device may still be used: counting shelf life and surveillance interval in whole days to a disposition of serviceable, surveillance due, life extended or expired, propagating an in-service anomaly across every item sharing the failed explosive batch and, for a design-rooted anomaly, the build standard, validating the launch-site step order that keeps the item inert until the area is clear, and accumulating excursion hours against the allowance. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, explosive-shelf-life-surveillance, in-service-anomaly-batch-propagation, launch-site-arming-sequence, explosive-storage-excursion-hours, explosive-requalification-trigger."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-in-service-feedback-launch-site-procedures-monitoring, explosive-shelf-life-surveillance, in-service-anomaly-batch-propagation, launch-site-arming-sequence, explosive-storage-excursion-hours, explosive-requalification-trigger]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — In-Service Feedback, Launch-Site Procedures and Monitoring (space-systems/ecss/e3311-in-service-feedback-launch-site-procedures-monitoring)

Use when the task is the in-service requirement of ECSS-E-ST-33-11C
Rev.1 clause 4.16 -- keeping an explosive item accounted for between
delivery and use: how old it is allowed to get, what an anomaly
somewhere else in the fleet obliges you to do about it, and in what
order it may be brought to life at the pad.

## Domain quick reference

- Age is tracked on two independent clocks. Declared shelf life says
  when the item stops being usable at all; the surveillance interval
  says when the evidence that it is still good goes stale. An item can
  be years inside its shelf life and still unusable because the
  surveillance test is overdue.
- A life extension is a decision, not an inference. Once shelf life is
  spent the item is expired unless an extension has been approved
  against test evidence; software that quietly keeps counting past the
  limit is the failure mode this clause exists to stop.
- Information feedback runs from one item to a population. The failed
  unit's explosive batch reaches every sibling from that batch
  regardless of where it sits, and if the root cause is in the design
  rather than the batch, it reaches every item of that build standard
  too. The two propagation paths are different sets and are reported
  separately.
- A launch-site procedure is an ordering problem. Bridge resistance is
  measured while the item is still safed, the initiation circuit is
  connected while it is still safed, the area is cleared before the
  safing device comes out, arming follows that, and firing is last.
  Every one of those is a precedence rule, and a rule with its earlier
  step missing entirely is as much a finding as one out of order.
- Once the safing device is out, every remaining step is a two-person
  operation. The second person is the control, not a convenience.
- Monitoring is cumulative. A single excursion rarely condemns an item;
  the accumulated hours outside the envelope do, and they are summed
  across the whole record, hot and cold alike, against a stated
  allowance.

## Workflow

1. Compute remaining shelf life and days to next surveillance in whole
   days from the manufacture and last-surveillance day indices, and
   refuse a today-index that precedes either.
2. Resolve the disposition from both clocks plus the extension flag,
   and report the overdue amount in the finding rather than a bare
   state name.
3. Propagate any reported anomaly across the inventory, recording for
   each reached item why it was reached, and flag quarantine when the
   reached set is non-empty.
4. Normalise the launch-site steps, reject duplicate step identifiers
   and unknown actions, then grade every precedence pair including the
   case where the earlier action is absent.
5. Confirm firing is the final step, and that every hazardous step at
   or after the safing-device removal carries at least two people.
6. Walk the monitoring record, count excursions in both directions,
   accumulate their hours, and compare the total against the allowance
   with a tolerance so an exactly-on-allowance record is not condemned.
7. Merge the findings from all four strands into one clear-to-use
   verdict, so a clean sequence does not mask an expired item.

## Pitfalls

- Reading serviceability off shelf life alone. The surveillance clock
  fails first for most stored hardware, and it is the one usually
  missing from the stock system.
- Treating an expiry as a paperwork item to be renewed. Without an
  approved extension backed by test evidence, an expired item is
  expired; changing the date changes nothing about the explosive.
- Scoping an anomaly to the failed unit. The batch is the population,
  and a design-rooted cause widens it further; a fleet action that
  recalls one serial number has not been performed.
- Measuring continuity after the safing device is out. The measurement
  current is small, but the barrier that made it safe is gone, and the
  order is exactly what the procedure exists to fix.
- Letting a hazardous step run single-handed because the crew is
  short. The two-person rule is the last control left once the item is
  armed.
- Judging monitoring one excursion at a time. Each may be inside
  tolerance while the accumulated exposure has long passed the
  allowance, and the accumulation is the quantity the allowance is
  written against.

## Behavior contract (gate 3)

The shelf-life and surveillance counters, disposition resolution,
anomaly propagation across batch and build standard, launch-site
precedence and two-person checks, excursion accumulation and
requalification decision are exercised by the gate 3 contract test:
scripts/test_e3311_in_service_feedback_launch_site_procedures_monitoring.py
against
scripts/e3311_in_service_feedback_launch_site_procedures_monitoring_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3311_in_service_feedback_launch_site_procedures_monitoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

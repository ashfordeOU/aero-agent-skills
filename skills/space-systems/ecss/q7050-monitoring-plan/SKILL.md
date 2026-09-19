---
name: q7050-monitoring-plan
description: "Produce the particle contamination monitoring plan a project owes under ECSS-Q-ST-70-50C: size the sampling locations of each zone from its floor area, set the revisit interval of airborne counting, witness-plate fallout and tape-lift sampling from the criticality of the work done there, count the occurrences across the campaign and total the samples committed. Use when writing or reviewing a contamination control plan, defending a sampling frequency, or sizing the monitoring workload of an integration campaign. Trigger: ecss, q-st-70-50c, particle-monitoring-plan, monitoring-location-sizing, monitoring-frequency-selection, cleanroom-zone-sampling-schedule, contamination-monitoring-workload."
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
  tags: [ecss, q-st-70-50c-particle-contamination-monitoring, q-st-70-50c, q7050-monitoring-plan, particle-monitoring-plan, monitoring-location-sizing, monitoring-frequency-selection, cleanroom-zone-sampling-schedule, contamination-monitoring-workload]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle Monitoring — Monitoring Plan (space-systems/ecss/q7050-monitoring-plan)

Use when the task is the programme clause of ECSS-Q-ST-70-50C: producing the
monitoring plan that states where particle monitoring happens, by which
method, and how often, for the zones a project works its hardware in.

## Domain quick reference

- A plan is three answers per zone and not one. Locations say where, method
  says what is measured, interval says how often; a plan that names a method
  without a location count and a period is a statement of intent.
- Location count scales with the square root of floor area, not with area
  itself. Doubling a bay does not double the sampling effort, which is why a
  large hall and a small airlock end up closer together than floor plans
  suggest, and why a minimum location count has to be stated separately.
- The minimum exists because a single point cannot show a gradient. Two
  locations in a small zone catch the difference between the supply diffuser
  and the return, which is the whole reason for sampling a zone rather than
  its air handler.
- Frequency follows the criticality of the work, not the size of the room. A
  bay where an optic is open shortens every interval it carries; the same
  bay used for boxed storage does not.
- An interval has a floor. Below about a day a routine sampling plan has
  become a continuous monitoring requirement, which is a different instrument
  and a different budget, so the plan should say so instead of quietly asking
  for it.
- A plan commits a workload, and the workload is locations times occurrences.
  Summing it before the campaign starts is what turns a plan into something a
  facility can actually resource.
- Two samples are the smallest number that can show a trend. A method that
  runs once across a campaign has produced a snapshot, and a snapshot cannot
  demonstrate that a zone held its condition.

## Workflow

1. Validate each zone: identifier, floor area, declared cleanroom class where
   it has one, the methods assigned to it, and the criticality band.
2. Size the sampling locations from the floor area, apply the minimum, and
   let an operator request raise the count but never lower it.
3. Set each method's interval from its base revisit period, shortened by the
   criticality factor of the zone and floored at one day.
4. Count the occurrences of each method across the campaign, counting both
   the opening sample and the one that lands on the closing day.
5. Multiply locations by occurrences for the committed sample count, and
   total the plan per method so the workload is visible.
6. Raise the plan-level findings: a zone declared twice, a zone with no
   method, a declared cleanroom class with no airborne counting behind it,
   and any method yielding a single occurrence across the campaign.

## Pitfalls

- Scaling locations linearly with floor area. The square-root rule is what
  keeps a large hall affordable, and a linear count buries the plan in
  samples it will quietly stop taking by the second month.
- Sampling a zone at one point. One location cannot separate a supply-side
  reading from a return-side one, so the minimum count is a structural part
  of the plan rather than a conservative extra.
- Setting frequency from room size. A small airlock where an optic is opened
  needs shorter intervals than a large hall handling boxed units, so the
  criticality of the work is what shortens the period.
- Letting an interval fall below a day without saying so. That is continuous
  monitoring, with a different instrument and a different cost, and it should
  be raised as a change rather than absorbed as a short period.
- Writing a plan without totalling it. Locations times occurrences is the
  commitment the facility has to staff, and a plan whose workload was never
  summed is the one that gets sampled at half its stated rate.
- Accepting a single occurrence as coverage. One sample records a moment; the
  plan exists to show a zone held its condition across the campaign, which
  takes at least two.

## Behavior contract (gate 3)

The zone validation, location sizing from floor area, interval derivation
from the criticality band, occurrence counting across the campaign, workload
totals and the plan-level findings are exercised by the gate 3 contract test:
scripts/test_q7050_monitoring_plan.py against
scripts/q7050_monitoring_plan_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7050_monitoring_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

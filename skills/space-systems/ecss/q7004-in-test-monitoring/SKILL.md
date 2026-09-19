---
name: q7004-in-test-monitoring
description: "Monitor the temperatures, pressures and functional parameters an ECSS thermal test is defined by, and grade the record they produced. Use when ECSS-Q-ST-70-04C in-test monitoring has to be planned or audited: confirm every one of the three monitored roles has a channel behind it, measure each channel's sampling against the interval the plan required and name the intervals long enough to be recording gaps, measure how much of the test window the record actually spans, merge consecutive out-of-limit samples into timed excursion events, then return one adequacy verdict with its findings. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-in-test-monitoring, thermal-monitoring-channel-coverage, thermal-recording-gap-detection, thermal-limit-excursion-event, thermal-chamber-pressure-monitoring."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-in-test-monitoring, thermal-in-test-monitoring, thermal-monitoring-channel-coverage, thermal-recording-gap-detection, thermal-limit-excursion-event, thermal-chamber-pressure-monitoring]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — In-Test Monitoring (space-systems/ecss/q7004-in-test-monitoring)

Use when the task is the in-test monitoring clause of ECSS-Q-ST-70-04C —
deciding what has to be watched while the item is under test, at what rate,
and afterwards whether the record that came back is good enough to conclude
anything from.

## Domain quick reference

- Three families of quantity are monitored, not one. Temperature says what
  the item experienced, chamber pressure says the environment was the one the
  test was written for, and the functional parameters say whether the item
  kept working while it experienced it. A record missing any of the three
  cannot support the test report.
- Monitoring is a rate requirement as well as a presence requirement. A
  channel that exists but samples far slower than the plan called for cannot
  resolve the events the plan was written to catch, so the interval between
  successive samples is graded, not just the channel list.
- A gap is defined against the required interval, not against a fixed number
  of seconds. The same two-minute silence is routine on a slow pressure
  channel and a loss of data on a fast thermocouple.
- Coverage and gaps are different failures. A channel can sample perfectly
  and still start late or stop early, leaving part of the test window
  unwitnessed, and that shows up as a coverage shortfall rather than a gap.
- An excursion is an event, not a set of samples. Consecutive out-of-limit
  readings belong to one departure with a start, a duration and an extreme
  value; counting samples instead makes the severity depend on the sampling
  rate.
- A departure below a limit and one above it are different events even when
  they touch, because the mechanism and the consequence differ, so a side
  change starts a new event.

## Workflow

1. Validate every channel: identity, one of the three monitored roles,
   ordered limits, required sampling interval, and a strictly time-ordered
   record of at least two samples.
2. Check role coverage across the whole channel set before grading any single
   channel, so a missing family is reported as itself.
3. For each channel, take the successive sampling intervals and report those
   beyond the gap threshold, keeping the longest interval seen.
4. Measure the overlap of the record with the planned test window as a
   coverage ratio and compare it with the minimum inside a named tolerance.
5. Walk the record for limit excursions, merging consecutive readings on the
   same side into one timed event with its extreme value.
6. Combine role coverage, gaps, coverage and excursions into one adequacy
   verdict carrying every finding.

## Pitfalls

- Listing channels and calling that a monitoring plan. Presence says nothing
  about rate, span or limits, and all three are what make the record usable.
- Judging a gap against a single absolute threshold for every channel. That
  either floods a slow channel with false gaps or hides real dropouts on a
  fast one; the threshold is a multiple of each channel's own interval.
- Counting out-of-limit samples as the excursion measure. Double the sampling
  rate and the same physical departure doubles in apparent severity; the
  duration and the extreme value are what the report needs.
- Merging an under-limit and an over-limit departure because they are
  adjacent in time. They are different events and the record has to keep them
  apart.
- Treating a late start or an early stop as a gap. Nothing is missing between
  two samples there; what is missing is the part of the window the channel
  never witnessed, and that is a coverage finding.
- Comparing the coverage ratio against its minimum with a bare strict
  inequality. The ratio is a float built from a division, so a channel
  spanning the window exactly is compared within a named tolerance while the
  minimum stays as the plan set it.

## Behavior contract (gate 3)

The channel validation, role coverage, sampling-interval and gap detection,
window coverage ratio, merged limit-excursion events and the combined
adequacy verdict are exercised by the gate 3 contract test:
scripts/test_q7004_in_test_monitoring.py against
scripts/q7004_in_test_monitoring_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7004_in_test_monitoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q7080-machine-monitoring
description: "Monitor the process parameters of a metallic powder bed fusion build and assess the build data log under ECSS-Q-ST-70-80C: find every contiguous excursion outside a control window, compute its duration and worst deviation, attribute it to the layers it sits under, compare the sampling interval, largest gap and coverage against the logging requirement, name the required channels that never reached the record, and close with a per-parameter and a whole-build verdict. Use when a build log is reviewed, an alarm fires mid-build, or a defect has to be traced to a layer. Trigger: ecss, q-st-70-80c, pbf-process-parameter-monitoring, pbf-build-data-logging, pbf-parameter-excursion-episodes, pbf-layer-excursion-attribution, pbf-log-coverage-gaps."
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
  tags: [ecss, q-st-70-80c-powder-bed-fusion, q-st-70-80c, q7080-machine-monitoring, pbf-process-parameter-monitoring, pbf-build-data-logging, pbf-parameter-excursion-episodes, pbf-layer-excursion-attribution, pbf-log-coverage-gaps]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Powder Bed Fusion — Machine Monitoring (space-systems/ecss/q7080-machine-monitoring)

Use when the task is the in-process monitoring and build data clause of
ECSS-Q-ST-70-80C: reading a build log after the fact, deciding whether the
build stayed in control, and turning an excursion on a time axis into the
layers a nonconformance has to follow.

## Domain quick reference

- A build log has two independent failure modes and both are graded here. A
  parameter left its window, or the record itself is incomplete. The second is
  the quieter one: a build that was in control and cannot be shown to have
  been is treated the same way as a build that was not.
- An excursion is an episode, not a sample. Contiguous readings outside the
  window belong to one event with a start, an end, a duration and a worst
  deviation, and counting samples instead of episodes double counts a single
  dip on a fast channel and misses a slow drift on a slow one.
- An episode closes at the reading that comes back inside the window, so an
  episode caught by one sample still lasts one sampling interval rather than
  zero. An episode that never returns closes at the last sample in the record.
- The deviation is measured from the bound that was crossed, upper or lower,
  and the bound is reported with it. A reading exactly on a bound is inside
  the window.
- Not every excursion is a nonconformance. A control window carries an
  excursion allowance; an episode inside it is recorded as an observation, and
  only an episode past it raises the parameter.
- A defect is found on a part, not on a time axis. Layer attribution is what
  makes the log usable: with a layer time, an episode resolves to the layer
  indices it sits under, and those indices are what the inspection, the cut-up
  and the disposition all work from.
- The record is graded on three of its own properties: the median sampling
  interval against the required one, the largest gap against the allowed gap,
  and the fraction of the build actually covered. A channel that was required
  and never logged at all is a fourth, and it is the one most often missed
  because nothing in the file points at it.

## Workflow

1. Declare the build: duration, layer time, the channels logged, the control
   window and excursion allowance for each, and the channels the project
   required.
2. Validate each time series before reading anything out of it — at least two
   readings, strictly increasing timestamps, no reading after the end of the
   build.
3. Walk each channel and collect the episodes: start, end, duration, sample
   count, worst value, worst deviation and the bound crossed.
4. Attribute every episode to its layers using the layer time, and take the
   union across channels so the build carries one affected-layer list.
5. Grade the record itself for each channel: median interval, largest gap,
   coverage fraction.
6. Take the difference between required and logged channels.
7. Close with the per-parameter verdicts and one build verdict: nonconforming
   on a long episode, a missing channel or an inadequate record; observations
   where only short excursions appear; clean otherwise.

## Pitfalls

- Counting out-of-limit samples instead of episodes. One dip sampled ten times
  a second becomes ten findings, and one slow drift sampled once a minute
  becomes one, so the count ranks the channels by sampling rate rather than by
  severity.
- Giving a one-sample episode zero duration. It lasted at least until the next
  reading, and a zero duration always fits inside any allowance, which turns
  the shortest and sharpest excursions into non-events.
- Comparing an episode duration with its allowance by bare arithmetic. The
  duration is a difference of sample times, so an episode that lasts exactly
  the allowed time can land a few units in the last place above it; the
  comparison absorbs that representation error while the allowance stays
  untouched.
- Reporting an excursion as a time. Nobody inspects a timestamp. Without the
  layer attribution the finding cannot be joined to the part, and the
  disposition ends up covering the whole build instead of a band of layers.
- Reading a clean channel set as a clean log. The channels that are present
  are the ones that can be graded; the required channel that was never
  recorded leaves no trace in the file, so it has to be looked for from the
  requirement side.
- Accepting a record whose median interval passes while one long gap sits in
  the middle. The median describes the typical sample and says nothing about
  the worst one, so the largest interval is graded separately.

## Behavior contract (gate 3)

The window and time-series validation, episode detection, duration and worst
deviation, layer attribution, sampling interval, gap and coverage grading,
missing channel detection and the build verdict are exercised by the gate 3
contract test: scripts/test_q7080_machine_monitoring.py against
scripts/q7080_machine_monitoring_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7080_machine_monitoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

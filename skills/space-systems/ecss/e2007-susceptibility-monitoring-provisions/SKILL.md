---
name: e2007-susceptibility-monitoring-provisions
description: "Verify that the unit-under-test stays watched for degradation or malfunction throughout every susceptibility exposure under ECSS-E-ST-20-07C clause 5.2.7.4: validate each monitored parameter against its acceptance limits, confirm the monitor resolves a drift inside that band and samples faster than the shortest upset the campaign undertakes to detect, merge the declared monitoring windows and report any interval of the exposure left unwatched, then group every run and return the campaign verdict. Use when a susceptibility test plan or report must show the monitoring provisions actually cover the exposure. Trigger: ecss, e-st-20-07c, susceptibility-monitoring-provisions, exposure-coverage-gap, monitor-sample-interval, malfunction-detection-resolution, susceptibility-run-observability."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-susceptibility-monitoring-provisions, susceptibility-monitoring-provisions, exposure-coverage-gap, monitor-sample-interval, malfunction-detection-resolution, susceptibility-run-observability, emc-susceptibility-exposure-watch]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Susceptibility Monitoring Provisions (space-systems/ecss/e2007-susceptibility-monitoring-provisions)

Use when the task is the clause 5.2.7.4 obligation of ECSS-E-ST-20-07C: while
a susceptibility stimulus is applied, somebody has to be able to see the unit
degrade. The clause is about the watching, not the stimulus — a run where the
unit was stressed but nobody could have noticed it faltering proves nothing,
however cleanly the amplifier swept.

## Domain quick reference

- The obligation is continuous, not sampled at the ends. Reading the unit
  before the run and again after it establishes that it survived, not that it
  stayed within its performance limits while the field was on. An upset that
  self-recovers between the stimulus stopping and the reading being taken is
  invisible to a before-and-after check and is exactly the failure mode the
  clause exists to catch.
- Coverage is an interval question. Monitoring windows are merged, the
  exposure is walked, and anything the merged windows do not reach is an
  unwatched interval — whether it sits at the start because the monitor was
  armed late, at the end because it was stopped early, or in the middle
  because the data link dropped.
- A monitor that cannot resolve a drift inside the acceptance band is not
  monitoring. If the parameter is acceptable across a band and the monitor
  steps in units comparable to that band, the reading is the same number at
  the nominal value and at the limit, and the degradation the clause names
  passes unrecorded.
- Sampling rate is a separate question from resolution. A monitor can resolve
  a millivolt and still step over a transient upset if it samples more slowly
  than the shortest event the campaign undertakes to detect; at least two
  samples must land inside that event.
- Observability during the exposure is its own precondition. A parameter that
  can only be read with the chamber open, or that is derived from a telemetry
  dump taken after the run, is not a susceptibility monitor no matter how
  precise it is.
- Findings and limitations are different outcomes. An unwatched interval or a
  blind monitor is a finding that keeps the run from closing; a run watched
  throughout by monitors that all resolve and keep up is adequate, and the
  campaign verdict follows the worst run, never the average.

## Workflow

1. Validate each monitored parameter: a name, an acceptance band whose upper
   limit strictly exceeds its lower limit, a positive resolution, a positive
   sample interval, and an explicit statement that it can be observed while
   the exposure runs.
2. Compute the acceptance band and the number of monitor steps that fit across
   it; a monitor resolving fewer steps than the programme requires is reported
   as unable to see a drift to the band edge.
3. Compare the sample interval against the shortest upset the campaign
   undertakes to detect, requiring at least the declared number of samples
   inside that event, and absorbing float representation error at equality
   rather than relaxing the bound.
4. Validate the exposure span and merge the declared monitoring windows into
   ordered disjoint spans, joining windows that abut exactly.
5. Walk the exposure against the merged windows and return every uncovered
   interval, with its duration, as a finding naming the run.
6. Grade the run: adequate only when no interval is unwatched and every
   parameter resolves and keeps up; otherwise inadequate, with the specific
   monitor or interval named.
7. Aggregate the campaign: counts per category, the run leaving the most
   exposure unwatched, the total unwatched time, and a verdict that is
   adequate only when no run carries a finding.

## Pitfalls

- Treating a pre-test and post-test functional check as the monitoring
  provision. It answers survival, not performance during exposure, and a
  self-recovering upset never appears in it.
- Arming the monitor after the stimulus starts, or stopping it at the last
  swept frequency rather than at the end of the dwell. Both leave a real
  interval unwatched that a duration-only summary will not show.
- Logging a parameter at high precision that the monitor cannot actually
  resolve. Precision in the record is not resolution in the instrument, and
  the acceptance band is the yardstick that decides.
- Sampling at a convenient housekeeping rate. Telemetry cadences are chosen
  for bandwidth, not for upset detection, and a one-second cadence cannot see
  a twenty-millisecond transient.
- Monitoring only the parameter that is easy to bring out of the chamber. The
  clause asks for degradation or malfunction of the unit, so the monitored
  set has to include the performance the unit is there to deliver.
- Averaging coverage across the campaign so a well-watched run compensates for
  a badly watched one. Each exposure has to be covered on its own.

## Behavior contract (gate 3)

The parameter validation, resolution and sampling adequacy checks, window
merging, exposure coverage-gap walk, run grading and campaign aggregation
logic is exercised by the gate 3 contract test:
scripts/test_e2007_susceptibility_monitoring_provisions.py against
scripts/e2007_susceptibility_monitoring_provisions_logic.py (stdlib unittest,
offline, deterministic). Run:
python3 scripts/test_e2007_susceptibility_monitoring_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

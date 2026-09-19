---
name: q7050-data-recording-and-trending
description: "Analyze a recorded series of cleanliness monitoring results against its alert and action levels under ECSS-Q-ST-70-50C. Use when a monitoring location holds a time-ordered record, the programme has set an action limit with a derived alert level, and the question is whether the location is drifting toward that limit rather than merely conforming today. Computes the record mean and sample spread, fits a least-squares drift, projects the days remaining until the fit reaches the action limit, counts the trailing run of results above the alert level, and reports a record whose points are unordered, too sparse to trend, or separated by a sampling gap. Trigger: ecss, q-st-70-50, particle-monitoring-trend, alert-and-action-level, least-squares-drift-slope, days-to-action-limit, consecutive-alert-run, monitoring-record-gap."
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
  tags: [ecss, q-st-70-cleanliness-monitoring-scope, q7050-data-recording-and-trending, particle-monitoring-trend, alert-and-action-level, least-squares-drift-slope, days-to-action-limit, consecutive-alert-run]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Monitoring — Data Recording and Trending (space-systems/ecss/q7050-data-recording-and-trending)

Use when the task is the recording and trending step of ECSS-Q-ST-70-50C
cleanliness monitoring — turning a location's accumulated results into a
statement about where it is heading, not only whether today's sample
conformed.

## Domain quick reference

- Conformance today and control over time are different questions. A
  record every point of which conforms can still be walking steadily
  toward its action limit, and the whole reason the results are recorded
  rather than merely checked is to see that before it arrives.
- The alert level is derived from the action limit, not set beside it.
  Deriving it by a stated fraction keeps the alert below the action by
  construction, so a programme that changes the action limit cannot
  leave an alert level stranded above it.
- A trend needs a third point. Two points define a line exactly and
  therefore describe scatter and drift identically; the fit is only
  informative once there is a residual it could have failed to explain.
- The projection that matters is from the last observation, not from
  the fitted intercept. It answers how long the location has at its
  current drift, and it is meaningless when the drift is flat or
  falling, where the honest output is no projection rather than a large
  positive number.
- A run of consecutive results above the alert level is a trigger in its
  own right. Several points in a row above the alert say the process
  moved even when no single point reached the action limit, and a run
  broken by one result exactly at the alert level is a broken run.
- A record with a sampling gap wider than the programme's interval is
  not a denser record with missing rows; the drift through the gap is
  unobserved, and the fit spans it as if it were sampled.

## Workflow

1. Validate the record: strictly increasing days, non-negative results,
   at least two points. An out-of-order or repeated timestamp is a data
   defect, not something to sort away silently.
2. Derive the alert level from the action limit by the stated fraction.
3. Form the record statistics: mean, sample spread, extremes and span.
4. Categorize every point as conforming, alert or action, absorbing an
   exact equality at either boundary with a named tolerance.
5. Fit a least-squares line over elapsed days and read the drift slope
   and the residual; refuse to fit a record with fewer than three
   points and say so as a finding.
6. Project the days from the last observation to the action limit, and
   report it only when the drift rises.
7. Count the trailing run above the alert level, list the sampling gaps
   when an interval is stated, and report every finding alongside the
   trend rather than collapsing them to a single verdict.

## Pitfalls

- Reporting the mean of a drifting record. The mean of a location that
  doubled over the campaign describes no week of it, and it hides the
  one property the record was kept to expose.
- Projecting from a flat or falling fit. Dividing by a slope near zero
  produces an enormous or negative time-to-limit that reads as a
  comfortable margin; no projection is the correct output there.
- Fitting across a sampling gap as if it were sampled. The drift inside
  the gap is unobserved, and a fit through it borrows confidence the
  record does not have.
- Treating an alert run as merely several conforming points. The run is
  its own trigger, and waiting for a single point past the action limit
  discards the warning the alert level exists to give.
- Nudging the alert level up so a run clears. The alert is derived from
  the action limit; changing the derivation to clear a run removes the
  only margin the location had.

## Behavior contract (gate 3)

The record validation, alert derivation, statistics, per-point
categorization, least-squares drift, time-to-limit projection, trailing
alert run and gap detection are exercised by the gate 3 contract test:
scripts/test_q7050_data_recording_and_trending.py against
scripts/q7050_data_recording_and_trending_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7050_data_recording_and_trending.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

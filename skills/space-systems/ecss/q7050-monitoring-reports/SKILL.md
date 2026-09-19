---
name: q7050-monitoring-reports
description: "Audit a cleanliness monitoring report package against the reporting obligations the programme imposed under ECSS-Q-ST-70-50C. Use when a reporting period has closed, the programme names the content items, the submission turnaround and the monitoring locations, and the package must be shown complete before its results feed a contamination budget. Merges the reported monitoring intervals to measure how much of the period was actually covered, locates every unmonitored gap and double-counted stretch, checks that each result names the instrument and method behind it, grades submission latency from the close of the period, and reports the fraction of required content delivered. Trigger: ecss, q-st-70-50, monitoring-report-package, reporting-period-coverage, unmonitored-interval-gap, result-instrument-traceability, submission-turnaround-latency, report-content-completeness."
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
  tags: [ecss, q-st-70-cleanliness-monitoring-scope, q7050-monitoring-reports, monitoring-report-package, reporting-period-coverage, unmonitored-interval-gap, result-instrument-traceability, submission-turnaround-latency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Monitoring — Monitoring Reports (space-systems/ecss/q7050-monitoring-reports)

Use when the task is the reporting step of ECSS-Q-ST-70-50C cleanliness
monitoring — showing that what the programme asked to be reported for a
closed period was reported, before anything downstream is built on the
numbers inside it.

## Domain quick reference

- A report covers a period, and the coverage is the merged reported
  intervals against that period. Merging first is what makes the measure
  honest: two intervals over the same fortnight are a double count, not
  extra coverage, and summing raw durations can show a period more than
  fully covered while a month of it was never sampled.
- Days the period contains and the intervals do not are unmonitored
  days, not simply missing rows. An interval ending exactly where the
  next begins is contiguous, and treating that boundary as a gap
  manufactures a finding out of arithmetic.
- Every result needs to name the instrument that produced it and the
  method it was produced by. Without both, a result that later turns
  into an exceedance cannot be chased back to an instrument-control
  record, and the exceedance cannot be bounded to the instruments that
  were out of control.
- Location coverage is a separate question from period coverage. A
  fully covered period with one of the named locations never sampled is
  a complete-looking report about the wrong thing, while a location
  nobody asked for is extra information and not a defect.
- Turnaround runs from the close of the period, not from the last
  sample. Measuring it from the last sample lets a report that stopped
  sampling early look punctual, which inverts the incentive the
  turnaround exists to create.

## Workflow

1. Validate the reporting period and every reported interval: positive
   duration, ordered bounds, at least one interval.
2. Merge the intervals into disjoint covered stretches and measure the
   covered days against the period length.
3. List the gaps inside the period, the overlaps between reported
   intervals, and any interval extending outside the period.
4. Grade submission timeliness as latency from the close of the period
   against the allowed turnaround, and refuse a submission dated before
   the period closed.
5. Check each result for its location, its instrument identifier and
   its method, and name what each untraceable result is missing.
6. Check the reported locations against the locations the programme
   named, listing missing ones as a defect and unexpected ones as
   information.
7. Grade the content items against the programme's list and report the
   fraction delivered alongside every finding.

## Pitfalls

- Summing raw interval durations for coverage. Overlapping intervals
  then add to more than the period, and the report reads as fully
  covered with weeks of it unsampled.
- Reading a contiguous boundary as a gap. An interval ending on the day
  the next begins covers the period continuously, and a tolerance in
  the comparison is what stops the arithmetic inventing a finding.
- Measuring turnaround from the last sample. A report whose sampling
  stopped a month early then looks punctual, and the lateness is hidden
  inside the coverage gap instead of showing as lateness.
- Accepting a result with no instrument reference. When it later turns
  into an exceedance there is no way to bound which instrument produced
  it, so the exceedance cannot be scoped to a control record.
- Treating full period coverage as a complete report. Coverage,
  location completeness, traceability, timeliness and content are
  separate obligations, and a report can satisfy any four of them and
  still be unusable.

## Behavior contract (gate 3)

The interval validation, merging, period coverage and gap location,
overlap detection, submission latency, result traceability, location
coverage and content completeness are exercised by the gate 3 contract
test: scripts/test_q7050_monitoring_reports.py against
scripts/q7050_monitoring_reports_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7050_monitoring_reports.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

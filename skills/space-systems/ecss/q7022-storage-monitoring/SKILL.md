---
name: q7022-storage-monitoring
description: "Monitor the store's temperature and humidity record under ECSS-Q-ST-70-22 and account for the exposure it evidences: grade the sampling cadence first, treat any gap wider than the required interval as unmonitored time rather than in-limit time, attribute out-of-limit hours between samples by the midpoint rule, group consecutive breaches into excursion events with their axes and peak deviation, and separate an inadequate record from an exceeded exposure. Use when a storage log is reviewed, an alarm is dispositioned, or a lot's exposure history is needed before issue. Trigger: ecss, q-st-70-22, storage-condition-monitoring, storage-excursion-accounting, storage-log-sampling-cadence, storage-exposure-allowance, storage-excursion-peak-deviation."
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
  tags: [ecss, q-st-70-22-limited-shelf-life-materials, q-st-70-22, q7022-storage-monitoring, storage-condition-monitoring, storage-excursion-accounting, storage-log-sampling-cadence, storage-exposure-allowance, storage-excursion-peak-deviation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limited Shelf Life — Storage Monitoring and Exposure (space-systems/ecss/q7022-storage-monitoring)

Use when the task is the monitoring side of ECSS-Q-ST-70-22 storage: the store
is instrumented, the readings are logged, and somebody has to say what exposure
the material in it actually accumulated.

## Domain quick reference

- The record is graded before the material is. A log with a twelve-hour hole in
  it cannot evidence twelve in-limit hours; it evidences nothing over that span.
  Absence of readings is a record finding in its own right, and it is a
  different finding from an exposure that went over allowance — they call for
  different corrective actions.
- Out-of-limit time between two samples has to be attributed by a stated rule.
  The midpoint rule used here gives each interval a weight of a half per
  out-of-limit endpoint, so one isolated hot reading between two good ones owns
  half the interval on each side rather than the whole span or none of it.
- An excursion is an event, not a set of independent samples. Consecutive
  breaches belong to one event carrying its span, the axes it broke, and the
  worst single-axis deviation inside it. Counting samples instead of events
  makes a slow sampler look better than a fast one over the same excursion.
- Two limits govern, and they catch different failures: a cumulative allowance
  in hours catches long mild drift, a peak-deviation limit catches a short
  violent spike. A material can pass one and fail the other.
- A band edge reached exactly is inside the envelope. Deviations are
  differences of declared decimals, so the comparison carries a named tolerance
  instead of relying on an exact float compare.

## Workflow

1. Validate the envelope and the reading series: strictly advancing
   timestamps, finite temperatures, humidity inside its physical range, every
   sample inside the declared monitoring period.
2. Form the coverage picture: the widest gap, how many gaps exceed the required
   interval, the unmonitored hours, and the monitored fraction. Count the span
   before the first sample and after the last one as gaps too.
3. Compute the per-axis deviation of each reading, zeroing anything inside the
   named tolerance so a band edge does not read as a breach.
4. Accumulate out-of-limit hours across the series by the midpoint rule.
5. Group consecutive out-of-limit readings into excursion events, each with its
   start, end, axes, sample count and peak deviation.
6. Compare the accumulated hours with the allowance and the peak with its own
   limit, when one is declared.
7. Close with a disposition: record-inadequate outranks everything, then
   exposure-exceeded, then exposure-within-allowance, then no-excursion.

## Pitfalls

- Reading a sparse log as a clean log. Two in-limit samples a day apart say
  nothing about the hours between them; the gap is the finding.
- Attributing a whole interval to one out-of-limit endpoint, or none of it.
  Both are defensible only if stated; silently switching between them makes two
  reviews of the same log disagree.
- Reporting excursion sample counts instead of excursion hours. Sample count is
  a property of the logger, not of what the material experienced.
- Using only a cumulative allowance. A brief excursion far outside the band can
  do more damage than many hours just outside it, which is what the peak limit
  is for.
- Collapsing record-inadequate into a pass or a fail of the material. The
  material may well be fine; what is missing is the evidence, and the action is
  to restore monitoring, not to scrap the lot.
- Comparing a reading against a band edge with a bare float compare. An exact
  edge value can land either side of the limit; the tolerance belongs in the
  comparison, not in a relaxed limit.

## Behavior contract (gate 3)

The envelope and series validation, coverage and gap accounting, per-axis
deviation, midpoint-rule exposure accumulation, event grouping, peak deviation
and the disposition precedence are exercised by the gate 3 contract test:
scripts/test_q7022_storage_monitoring.py against
scripts/q7022_storage_monitoring_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7022_storage_monitoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2001-seeding-effectiveness-verification
description: "Use when validate that multipactor electron-seeding is actually working during test-bed validation with a reference-sample of known breakdown-threshold under ECSS-E-ST-20-01C clause 6.5.6: express every validation-run threshold as a decibel-offset from the reference-sample value, combine the reference-uncertainty and facility-uncertainty into one acceptance-band, separate an offset that signals weak-seeding from one that signals a degraded reference-sample, grade run-to-run repeatability and the detection-onset-latency, and refuse a validation whose frequency, gap or pressure conditions are not representative of the planned run-conditions. Trigger: ecss, e-st-20-01c, seeding-effectiveness, reference-sample-threshold, decibel-offset, acceptance-band, weak-seeding, onset-latency, representative-conditions."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-seeding-effectiveness-verification, seeding-effectiveness, reference-sample-threshold, acceptance-band, onset-latency, representative-conditions]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Seeding Effectiveness Verification (space-systems/ecss/e2001-seeding-effectiveness-verification)

Use when the task is the seeding-effectiveness demonstration of
ECSS-E-ST-20-01C clause 6.5.6 -- proving during test-bed validation
that the electron-seeding arrangement really does start a discharge,
by running a reference-sample whose breakdown-threshold is already
known and checking the bed reproduces that number.

## Domain quick reference

- A seeding arrangement cannot be verified against the flight item,
  because the flight item's threshold is the unknown the campaign is
  there to find. The only usable yardstick is a reference-sample with
  an independently established breakdown-threshold, run under the same
  seeding and detection chain.
- Thresholds are compared logarithmically. Each validation-run
  threshold becomes a decibel-offset relative to the reference-sample
  value, so a sample twice as hard to break down reads as about
  +3 dB regardless of the absolute level.
- The acceptance-band is not the facility specification alone: the
  reference-sample carries its own uncertainty and the bed carries
  another, and the two combine in quadrature into a single band the
  offset is graded against.
- The sign of an out-of-band offset names the defect. A threshold
  measured markedly higher than the known value means the discharge
  was late or missed -- weak seeding, and the dangerous direction,
  because the same weakness on a flight item reads as a pass. A
  threshold measured markedly lower points at the reference-sample or
  the level calibration, not at the seeding.
- Two further symptoms come out of the run set. A wide run-to-run
  spread says the free-electron supply is intermittent even when the
  mean looks right, and a long detection-onset-latency -- the dwell
  between reaching the threshold and the first detected event -- says
  the arrangement is waiting on a chance electron instead of supplying
  one.
- A validation is only evidence for the campaign it precedes. If the
  frequency, the gap or the residual pressure of the validation run
  departs from the planned run-conditions by more than the declared
  tolerance, the demonstration does not transfer.

## Workflow

1. Validate the reference-sample threshold and the run set (at least
   the declared minimum number of runs, every measured threshold
   strictly positive).
2. Convert each measured threshold to a decibel-offset against the
   reference-sample value.
3. Combine the reference-sample uncertainty and the facility
   uncertainty in quadrature into one acceptance-band.
4. Categorize every offset: inside the band, above it (weak-seeding),
   or below it (reference-sample or calibration suspect).
5. Compute the run-to-run spread and the sample deviation of the
   offsets and grade the spread against its limit.
6. Grade each run's detection-onset-latency against the maximum dwell
   allowed before an event has to appear.
7. Check the validation frequency, gap and pressure against the
   planned run-conditions within the declared fractional tolerances.
8. Report every finding; the seeding arrangement is demonstrated
   effective only when the finding list is empty, and the reported
   seeding-margin is the unused part of the band on the weak-seeding
   side.

## Pitfalls

- Accepting the mean offset and never looking at the spread. A set
  alternating between on-threshold and far-above averages into the
  band while proving the electron supply is intermittent.
- Treating a high measured threshold as a good result. It is the exact
  signature of under-seeding, and it is the failure that later turns a
  multipactor-prone item into a clean report.
- Grading the offset against the facility specification alone. Leaving
  the reference-sample's own uncertainty out of the band narrows it
  artificially and produces findings the data cannot support.
- Validating once at a convenient frequency and gap and reusing it for
  every campaign. Seeding effectiveness depends on the geometry and the
  residual pressure, so a validation outside the planned run-conditions
  is not transferable evidence.
- Ignoring how long the bed waited for the first event. A run that
  eventually broke down after a long dwell has found the discharge by
  luck, not by seeding, and the latency is the only place that shows.

## Behavior contract (gate 3)

The offset, acceptance-band, categorization, repeatability, latency and
representativeness logic is exercised by the gate 3 contract test:
scripts/test_e2001_seeding_effectiveness_verification.py against
scripts/e2001_seeding_effectiveness_verification_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_seeding_effectiveness_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

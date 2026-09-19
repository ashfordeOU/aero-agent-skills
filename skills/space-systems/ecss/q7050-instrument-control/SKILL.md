---
name: q7050-instrument-control
description: "Verify that a particle counter or sizing microscope is under control before its cleanliness monitoring data is accepted under ECSS-Q-ST-70-50C. Use when an instrument carries a calibration record, a measured sample flow against its nominal, a counting-efficiency check at the smallest reported channel and a filtered zero run, and the monitoring result depends on all of them holding at once. Computes the concentration bias a flow deviation injects, grades calibration currency in days with a recall warning band, grades threshold sensitivity against its acceptance window, grades background against the allowed rate, and withholds fitness whenever one check fails. Trigger: ecss, q-st-70-50, particle-counter-flow-accuracy, counting-efficiency-at-threshold, zero-run-background-rate, calibration-currency-days, sampled-concentration-bias, microscope-stage-micrometer-bias."
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
  tags: [ecss, q-st-70-cleanliness-monitoring-scope, q7050-instrument-control, particle-counter-flow-accuracy, counting-efficiency-at-threshold, zero-run-background-rate, calibration-currency-days, microscope-stage-micrometer-bias]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Monitoring — Instrument Control (space-systems/ecss/q7050-instrument-control)

Use when the task is the instrument-control step of ECSS-Q-ST-70-50C
cleanliness monitoring — deciding whether a particle counter or a sizing
microscope is in a state where the numbers it produces can be used, before
those numbers reach a trend or a disposition.

## Domain quick reference

- Instrument control is a conjunction, not a score. Calibration
  currency, flow accuracy, threshold sensitivity and background all have
  to hold at the same time; a counter with perfect flow and a dirty
  background is not three-quarters fit, it is unfit.
- A counter reports concentration by dividing its counts by the nominal
  sampled volume, not by the volume it actually drew. A flow running low
  therefore over-reports concentration and a flow running high
  under-reports it, and the bias is the nominal over the measured flow
  less one — not the flow deviation itself, and in the opposite
  direction to the intuition.
- The counting efficiency at the smallest reported channel is what makes
  that channel a channel. It is accepted inside a window around its
  target, because a threshold that counts everything is sizing nothing
  and one that counts almost nothing silently deletes the smallest
  particles from every result.
- A filtered zero run measures the instrument, its tubing and its
  optics, not the room. Its rate scales to a volume, so a short zero run
  with one stray count can look worse than a long one with several; the
  grading is on rate, not on raw counts.
- A sizing microscope has no flow, and its equivalent check is a
  certified stage micrometer. A bias there multiplies straight through
  into every recorded particle size and therefore into which size
  channel each particle was counted in.

## Workflow

1. Validate the instrument record and its kind; a counter and a
   microscope owe different checks and neither substitutes for the
   other.
2. Grade calibration currency in days: current, due-soon inside the
   recall warning band, or expired past the interval. Expiry withholds
   fitness; due-soon is a finding that does not.
3. Grade the sample flow against its tolerance and compute the
   concentration bias the deviation injects into every reported result.
4. Grade the counting efficiency at the smallest reported channel
   against the window around its target.
5. Grade the filtered zero run as a rate per unit volume against the
   allowed background.
6. For a microscope, grade the stage-micrometer bias against its
   tolerance instead of flow, efficiency and background.
7. Report every check, the list of failed checks, the overall fitness
   as their conjunction, and a finding per failure naming the effect on
   the data rather than only the failure.

## Pitfalls

- Applying the flow deviation as the data correction. The bias on the
  reported concentration is the nominal over the measured flow less
  one, which has the opposite sign and a different magnitude from the
  deviation; correcting with the deviation moves the number the wrong
  way twice.
- Accepting data taken after the calibration interval ran out because
  the instrument was recalibrated afterwards and passed. A pass at the
  next calibration bounds the drift but does not restore traceability
  to the readings already taken.
- Grading the zero run on counts. Two counts in a short run and two in
  a long run are different background rates, and the short run is the
  worse instrument.
- Treating a low counting efficiency as conservative. It deletes the
  smallest particles from the result, which is the channel carrying the
  largest allowance and usually the one driving the level.
- Averaging the checks into an overall figure of merit. Any single
  failed check withholds fitness; the passing checks do not compensate
  for it.

## Behavior contract (gate 3)

The calibration currency grading, flow deviation and concentration bias,
counting-efficiency window, background rate, microscope sizing bias and
the conjunction that produces fitness are exercised by the gate 3
contract test: scripts/test_q7050_instrument_control.py against
scripts/q7050_instrument_control_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7050_instrument_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

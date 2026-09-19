---
name: e50-time-correlation
description: "Derive the correlation between onboard time and the reference time scale under ECSS-E-ST-50C clause 5.6.14.6, which asks that the two be correlated to a stated accuracy. Remove the one-way light time first, because it biases every pair alike and no fit can recover a common bias. Then fit offset and drift by least squares, take the residual spread and the standard error of the drift, and turn the stated accuracy into a validity horizon — the interval after which the correlation must be taken again. Use when sizing a time-correlation cadence or reviewing onboard clock accuracy. Trigger: ecss, e-st-50-communications, onboard-time-correlation, onboard-clock-drift-fit, time-correlation-validity-horizon, correlation-light-time-bias, recorrelation-interval-sizing."
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
  tags: [ecss, e-st-50-communications, e50-time-correlation, onboard-time-correlation, onboard-clock-drift-fit, time-correlation-validity-horizon, correlation-light-time-bias, recorrelation-interval-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Time Correlation (space-systems/ecss/e50-time-correlation)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.6.14.6 —
that onboard time is correlated with the reference time scale to a stated
accuracy — and the question is how good the correlation is and how long it lasts.

## Domain quick reference

- A correlation is a fit, not a number. One pair gives an offset that is
  already stale when it is written down; the pair set gives an offset, a
  drift, and a statement about how well each is known.
- The stated accuracy is what makes the obligation checkable. Without a
  bound there is nothing to compare the residuals against, and without a
  drift uncertainty there is no interval over which to compare it.
- Propagation delay is a bias every pair shares, which is exactly the
  error a fit cannot remove. A reference timestamp taken at ground
  reception is late by the one-way light time, and the fit obligingly
  absorbs that into the offset as though it were real.
- Two pairs are the trap. They determine a straight line exactly, the
  residuals come out at zero, and every quality metric derived from
  those residuals reports a perfect correlation that is simply
  unmeasured.
- Drift is the onboard oscillator's frequency error seen end to end, and
  its standard error is what sets the validity horizon. A well-fitted
  drift decays slowly; a poorly fitted one makes yesterday's correlation
  useless today.
- The horizon is the deliverable. Operators do not act on a residual
  spread; they act on how long they may go before correlating again.

## Workflow

1. Collect the pairs as onboard reading against reference instant, and
   reject a set that does not strictly advance in onboard time.
2. Remove the one-way light time from the reference side before fitting
   anything, and record the correction applied so the bias is visible.
3. Fit the offset between the scales against onboard time by least
   squares, anchored at the first reading, yielding offset and drift.
4. Take the residuals and their root mean square. This is the dispersion
   the pairs themselves show, and it is compared against the bound.
5. Take the standard error of the drift. With fewer than three pairs it
   does not exist, and the assessment says so rather than reporting zero.
6. Turn the bound into a validity horizon: the margin left after the
   residual spread, divided by the rate the drift uncertainty consumes
   it. Report it as the re-correlation interval.
7. Call out a light-time correction larger than the accuracy bound —
   it is the one error that would have passed every residual check.

## Pitfalls

- Fitting uncorrected reference timestamps. Every residual looks fine,
  the drift is right, and the offset is wrong by the one-way light time
  for the whole mission.
- Correlating from two pairs and reporting the residuals. They are zero
  because two points define a line, not because the clocks agree.
- Reporting an offset with no drift. The offset is only valid at the
  epoch it was fitted at, and a consumer who applies it later is wrong
  by the drift times the interval, silently.
- Treating an unestimated drift uncertainty as zero. That turns an
  unmeasured fit into one that never expires, which is the most
  dangerous of the three possible answers.
- Quoting accuracy without a horizon. A correlation inside the bound
  today says nothing about the pass it will actually be used on.
- Extrapolating far past the fitted span. The drift standard error is
  estimated over the span the pairs cover, and beyond it the stated
  error is an assumption rather than a measurement.

## Behavior contract (gate 3)

Pair-set validation with strictly advancing onboard time, the light-time
correction as a pure offset bias, the least-squares offset and drift, residuals
and their spread, the drift standard error with its undefined two-pair case,
extrapolation, and the validity horizon in its finite, never-decaying,
already-exceeded and undetermined forms are exercised by the gate 3 contract
test:
scripts/test_e50_time_correlation.py against
scripts/e50_time_correlation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_time_correlation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

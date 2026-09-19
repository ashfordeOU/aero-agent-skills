---
name: q2007-monitoring
description: "Monitor and measure the execution of a test campaign at a space test centre under ECSS-Q-ST-20-07C clause 5.8.1: rate every acquisition channel on its sample-rate ratio against the frequency of interest, its dropout fraction and its calibration validity; adjudicate each hold point on witness presence and named release authority; merge the logged surveillance intervals over the test window for the covered fraction and the unwatched gaps. Use when a test-centre monitoring plan, a surveillance log or an acquisition channel list has to be assessed before, during or after test execution. Trigger: ecss, q-st-20-07c, test-centre-monitoring, data-acquisition-channel-check, acquisition-nyquist-margin, test-hold-point-release, witness-point-adjudication, test-execution-surveillance, surveillance-coverage-gap."
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
  tags: [ecss, q-st-20-test-centre-scope, q2007-monitoring, test-centre-monitoring, data-acquisition-channel-check, test-hold-point-release, test-execution-surveillance, surveillance-coverage-gap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Monitoring and Measurement of Test Activities (space-systems/ecss/q2007-monitoring)

Use when the task is the monitoring and measurement step of ECSS-Q-ST-20-07C
clause 5.8.1 — deciding whether the way a test centre watched, sampled and
held a test campaign is enough to support the results it reports.

## Domain quick reference

- Monitoring has three legs and a campaign fails on the weakest one:
  the measurement chain that acquires the data, the hold points that gate
  the sequence, and the human surveillance that watches the article and the
  facility between those gates. A perfect acquisition record taken while
  nobody was watching the chamber is not a monitored test.
- An acquisition channel is fit for a frequency of interest only through its
  oversampling ratio. Two samples per cycle carries the frequency but not its
  amplitude; a peak, a transient or a notch needs roughly five before the
  sampled extreme can be reported as the article's extreme. A channel whose
  ratio sits between the two is usable for presence and unusable for level.
- Dropped samples are not noise. A gap in the record is a stretch of the test
  for which no statement can be made, so a dropout fraction is graded against
  a stated ceiling, not averaged away over a long run.
- Calibration validity is a property of the moment of acquisition, not of the
  moment of reporting. A channel whose validity ran out mid-run invalidates
  the data from the expiry onwards even when it reads plausibly.
- A hold point is a release decision, not a pause. Two things make it real:
  the witness the plan demanded was there, and a named authority released it.
  Execution that continued across a hold point still open is the most serious
  monitoring finding available, because every later result inherits it.
- Surveillance coverage is the union of the logged watch intervals clipped to
  the test window, so a second observer logging the same stretch adds nothing
  to coverage. What the gaps are matters more than what the fraction is: a
  single gap across the transition to the extreme condition weighs more than
  the same minutes scattered over a soak.

## Workflow

1. Validate the test window; a zero-length or inverted window is an input
   error, not a degenerate campaign.
2. Assess each acquisition channel: form its oversampling ratio, compare
   against the carry-the-frequency bound and the resolve-the-peak bound,
   grade the dropout fraction against its ceiling, and reject a channel
   already outside calibration validity.
3. Adjudicate each hold point: witness required versus witness present,
   release recorded against a named authority, and execution continued
   across a hold point still open.
4. Merge the logged surveillance intervals, refusing any interval that falls
   outside the test window, and compute the covered fraction over the union
   rather than the sum so duplicated watch time cannot inflate it.
5. Enumerate the gaps and place them against the test profile before reading
   the fraction as a verdict.
6. Compare the coverage with the required value, absorbing floating-point
   representation error at the boundary with a named tolerance rather than
   by relaxing the requirement.
7. Report every channel, hold point and gap, and call the campaign monitored
   only when no leg produced a finding.

## Pitfalls

- Summing the surveillance intervals instead of merging them. Two observers
  logging the same hour report two hours of coverage and a window can appear
  more than fully watched while a genuine gap stays open.
- Reading the coverage fraction alone. A high fraction with its one gap at
  the ramp to the extreme condition is worse than a lower fraction with the
  gaps spread over a stable soak.
- Accepting a channel on the two-samples-per-cycle bound when the result
  being reported is an amplitude. The frequency survives that ratio; the peak
  does not, and the reported extreme is then an artefact of the sampling.
- Treating expired calibration as a paperwork item to be closed afterwards.
  The validity has to hold at acquisition time, so a late certificate does
  not restore the data taken after the expiry.
- Logging a hold point as released because the sequence moved on. Release is
  a decision with an owner; execution that continued across an open hold
  point is a finding, not evidence that the hold point was released.
- Widening the required coverage to make an exact-equality case pass. An
  equality at the limit is a representation question, handled by the
  tolerance inside the comparison; the required value stays as specified.

## Behavior contract (gate 3)

The window validation, channel rating, interval merging, coverage and gap
computation, hold-point adjudication and campaign aggregation are exercised
by the gate 3 contract test:
scripts/test_q2007_monitoring.py against
scripts/q2007_monitoring_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_monitoring.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

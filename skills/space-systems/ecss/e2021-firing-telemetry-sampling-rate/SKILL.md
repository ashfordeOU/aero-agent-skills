---
name: e2021-firing-telemetry-sampling-rate
description: "Determine the housekeeping sampling rate current and voltage telemetry should carry while a long duration actuator is firing, per clause 5.5.3 of ECSS-E-ST-20-21C. Use when a firing duration, a shortest feature of interest and a telemetry buffer have to settle a rate rather than leave it to habit: decide first whether the firing is long enough for the recommendation to bite, size the rate from the feature with an oversampling factor rather than at bare Nyquist, hold the recommended floor underneath it, then count the samples across both monitored channels and report the firing duration the buffer actually covers. Trigger: ecss, e-st-20-21c, firing-telemetry-sampling-rate, long-duration-actuator-firing, housekeeping-sample-interval, feature-oversampling-factor, telemetry-buffer-depth, firing-current-voltage-monitoring."
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
  tags: [ecss, e-st-20-21-actuator-interface-scope, e-st-20-21c-clause-5-5-3, e2021-firing-telemetry-sampling-rate, e-st-20-21c, firing-telemetry-sampling-rate, long-duration-actuator-firing, housekeeping-sample-interval, feature-oversampling-factor, telemetry-buffer-depth]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuator Interface — Firing Telemetry Sampling Rate (space-systems/ecss/e2021-firing-telemetry-sampling-rate)

Use when the task is clause 5.5.3 of ECSS-E-ST-20-21C: while a long
duration actuator is firing, its current and the voltage across it are
recommended into housekeeping at a rate that leaves a usable record.
This leaf turns a firing duration, a shortest feature and a buffer depth
into that rate, and says how much of the firing survives.

## Domain quick reference

- The recommendation has an entry condition, and it is the firing being
  long duration. Below the threshold there is no record to speak of and
  the rate question does not arise; a firing landing exactly on the
  threshold is inside the condition, because the threshold admits rather
  than excludes.
- The rate is set by the shortest feature the record has to show -- the
  step at initiation, a momentary dropout, a resistance change part way
  through the stroke. Nothing in the firing duration itself sets it.
- Two samples per feature is the limit at which a feature can be said to
  have existed. Reading its shape needs several, so the rate is sized
  from an oversampling factor, and a plan built at bare Nyquist produces
  a record that confirms an event without characterising it.
- A recommended floor sits underneath the feature-driven figure. A slow
  feature must not drag the rate down, so the rate adopted is whichever
  of the two is larger, and a plan is graded against that.
- Rate alone does not produce a record. Current and voltage are two
  monitored channels, so the sample count over the firing is the rate
  times the duration times the channel count, and counting one channel
  halves the budget and hides a buffer that overflows.
- What the buffer covers is the honest figure. A depth that runs out
  part way through loses the end of the firing, which is where a stall,
  a late dropout or a failure to release would show, so the covered
  duration is reported next to the firing duration rather than as a
  pass or fail alone.

## Workflow

1. Validate the specification: a positive long-duration threshold, a
   positive recommended floor rate, an oversampling factor of at least
   two samples per feature, and at least one monitored channel.
2. Validate each actuator: a positive firing duration, a positive
   shortest feature, and a feature no longer than the firing that is
   supposed to contain it.
3. Decide applicability from the duration against the threshold,
   absorbing floating-point representation error at an exact match with
   a named tolerance rather than by moving the threshold.
4. Size the feature-driven rate from the oversampling factor and take
   the required rate as the larger of that and the recommended floor.
5. Adopt the declared rate when the plan states one and grade it against
   the required rate; adopt the required rate when the plan states none,
   so the leaf returns a recommendation rather than a failure.
6. Count the samples the firing generates across every monitored channel
   and compare them with the declared buffer depth.
7. Report the sample interval, the covered duration, the coverage
   fraction and the verdict, raising findings only where the
   recommendation applies, and grade a set on the actuator covering the
   least of its own firing.

## Pitfalls

- Sizing the rate from the firing duration. A long firing with a fast
  step needs a fast rate, and a slow rate over a long firing produces a
  large record with the interesting part missing.
- Settling for two samples per feature. That establishes the feature
  occurred and nothing about its shape, so a current dropout and a
  current step become indistinguishable in the record.
- Letting a slow feature pull the rate below the recommended floor. The
  floor exists for the features nobody listed, and a rate derived only
  from the declared feature has no margin for them.
- Counting the samples on one channel. Current and voltage are both
  sampled, so the true budget is twice the single-channel count and a
  buffer sized on the half figure overflows before the firing ends.
- Reporting the plan as adequate because the rate is adequate. A
  correct rate into a buffer that runs out half way through still loses
  the second half of the firing, and that is the half where a stall
  appears.
- Raising findings on a short firing. The recommendation applies to long
  duration actuators; grading a millisecond initiation against it
  produces noise that buries the actuators the clause is about.

## Behavior contract (gate 3)

The specification validation, applicability decision, feature-driven and
floor rate sizing, sample budget across both monitored channels, buffer
coverage and worst-actuator grading are exercised by the gate 3 contract
test: scripts/test_e2021_firing_telemetry_sampling_rate.py against
scripts/e2021_firing_telemetry_sampling_rate_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2021_firing_telemetry_sampling_rate.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

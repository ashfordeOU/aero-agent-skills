---
name: e2001-detection-rise-time
description: "Use when verify that a global multipactor detection chain answers fast enough for the pulsed drive it watches under ECSS-E-ST-20-01C clause 7.3.3: convert each stage bandwidth into a stage rise-time, combine the stages root-sum-square into one chain rise-time, size that chain rise-time against the applied radio-pulse-width through the speed-ratio the verification-plan committed to, subtract the turn-on blanking and the edge itself to find the observation-window left inside the pulse, derive the minimum sample-rate that still resolves the leading edge, and confirm the detector baseline recovers inside the inter-pulse gap. Trigger: ecss, e-st-20-01c, detection-rise-time, radio-pulse-width, chain-rise-time, observation-window, minimum-sample-rate, baseline-recovery."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-detection-rise-time, detection-rise-time, radio-pulse-width, chain-rise-time, observation-window, baseline-recovery]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Detection Rise Time (space-systems/ecss/e2001-detection-rise-time)

Use when the task is the detection-speed duty of ECSS-E-ST-20-01C clause
7.3.3 -- showing that a global multipactor detection method answers far
faster than the radio-pulse-width it is watching, so a discharge that
starts inside a pulse is seen while that pulse is still on.

## Domain quick reference

- A pulsed multipactor run gives the detector a short window per pulse.
  The chain has to rise, settle and register inside that window, so the
  figure of merit is the chain rise-time compared against the applied
  radio-pulse-width. The verification-plan states the comparison as a
  speed-ratio -- a chain an order faster than the pulse is the usual
  commitment, and the ratio, not a fixed number of nanoseconds, is what
  travels between items of different pulse-width.
- Each stage contributes its own rise-time. A stage quoted by bandwidth
  converts through the rise-time-bandwidth product (about 0.35 for the
  single-pole and Gaussian responses that describe detector diodes,
  video amplifiers and digitiser front ends). Stages combine
  root-sum-square, not by addition: two equal stages are only about 1.41
  times slower than one, and one dominant slow stage sets the chain
  almost by itself, which is where corrective effort belongs.
- Rise-time eats the pulse twice. It delays the answer, and together
  with the turn-on blanking applied across the drive transient it
  shortens the observation-window actually available for a decision.
  A chain that formally meets the speed-ratio can still leave too little
  window once blanking is counted, so the window fraction is graded as
  its own criterion.
- Digitising adds a second speed constraint. Resolving the leading edge
  needs several samples across the rise, so the minimum sample-rate
  follows from the chain rise-time, not from the pulse-width. A
  sample-rate set from the pulse repetition alone under-samples the edge
  and reports a late, rounded onset.
- Between pulses the detector has to return to baseline before the next
  pulse arrives, or the per-pulse decision inherits the tail of the
  previous one. Recovery scales with the chain rise-time; the inter-pulse
  gap follows from the pulse-width and the duty cycle.

## Workflow

1. Assemble the stage rise-times, converting any stage quoted by
   bandwidth through the rise-time-bandwidth product. Reject a
   non-positive bandwidth or rise-time before it enters the chain.
2. Combine the stages root-sum-square into the chain rise-time, and note
   which single stage dominates it.
3. Compute the required rise-time as the speed-ratio times the applied
   radio-pulse-width and compare. Absorb representation error in the
   comparison -- a root-sum-square landing a few ULPs over an exact
   limit is compliant -- and never widen the ratio itself.
4. Compute the observation-window left in the pulse after the turn-on
   blanking and the chain rise-time, and grade it against the minimum
   usable fraction of the pulse. A window driven to zero means the chain
   cannot decide inside the pulse at all.
5. Derive the minimum sample-rate from the samples wanted across the
   leading edge and compare it against the digitiser actually used.
6. Convert pulse-width and duty cycle into the inter-pulse gap, compare
   it against the recovery time implied by the chain rise-time, and flag
   a gap too short for the baseline to return.
7. Aggregate. The chain is speed-compliant for this pulse pattern only
   when all four criteria hold; report the shortest pulse-width the chain
   could support, which is what the item's future runs need.

## Pitfalls

- Adding stage rise-times arithmetically. Root-sum-square is the correct
  combination for cascaded responses; summing overstates the chain and
  buys hardware that was never needed.
- Grading the chain against the pulse repetition period instead of the
  pulse-width. The decision has to be made inside the pulse; the period
  only governs baseline recovery.
- Declaring compliance from the speed-ratio alone while blanking has
  already consumed most of the pulse. The window fraction is an
  independent criterion, not a restatement of the ratio.
- Setting the digitiser rate from the pulse-width. The edge, not the
  pulse, sets the sample-rate, and an under-sampled edge reports an
  onset later than it happened.
- Reusing a chain qualified on a long pulse for a shorter one without
  re-deriving the shortest supported pulse-width. Speed is a ratio; a
  chain that was ten times faster than a microsecond pulse is not
  faster than a hundred-nanosecond one.

## Behavior contract (gate 3)

The rise-time conversion, root-sum-square chain, speed-ratio grading,
observation-window, sample-rate and baseline-recovery logic is exercised
by the gate 3 contract test: scripts/test_e2001_detection_rise_time.py
against scripts/e2001_detection_rise_time_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_detection_rise_time.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

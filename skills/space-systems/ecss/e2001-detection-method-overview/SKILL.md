---
name: e2001-detection-method-overview
description: "Use when assess whether the multipactor-detection arrangement declared for an ECSS-E-ST-20-01C clause 7.1 test-campaign meets the minimum expectations: confirm at least two detection channels are wired, that one delivers global-coverage of the RF-chain and one delivers local-coverage of the critical-gap, that the channels rest on independent observable-families so a single instrumentation-fault cannot hide a discharge, that each declared detection-threshold keeps a sensitivity-margin above the expected event-signature, and that every response-time is short enough to register the shortest credible discharge-duration. Trigger: ecss, e-st-20-01c, multipactor-detection-arrangement, global-coverage-channel, local-coverage-channel, observable-family-independence, detection-sensitivity-margin, detection-response-time, event-registration-threshold."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-detection-method-overview, multipactor-detection-arrangement, global-coverage-channel, local-coverage-channel, observable-family-independence, detection-sensitivity-margin, detection-response-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Detection Method Overview (space-systems/ecss/e2001-detection-method-overview)

Use when the task is the minimum-expectation check of
ECSS-E-ST-20-01C clause 7.1 -- deciding whether the set of
multipactor-detection channels an RF-item's test-campaign declares is
capable, as an arrangement, of registering a discharge at all: enough
channels, the right coverage mix, independent observables, sufficient
sensitivity-margin and fast-enough response.

## Domain quick reference

- Clause 7.1 constrains the detection arrangement, not a single
  instrument. A campaign declares a set of detection channels; the
  arrangement is adequate only when the set as a whole would register
  a discharge that a single channel could miss or mis-attribute.
- Every channel carries two descriptors that must be normalized before
  the arrangement can be graded. Coverage-scope is either
  global-coverage (the channel observes the whole RF-chain through a
  transmitted or reflected quantity and localizes nothing) or
  local-coverage (the channel observes one suspect region -- the
  critical-gap, a window, a probe port -- and says nothing about the
  rest of the item). Observable-family is the physical quantity the
  channel actually watches: rf-power-balance, spectral-sideband,
  charged-particle, optical-emission, gas-pressure or thermal-rise.
  An unrecognized scope or family is rejected, never defaulted.
- Two channels are independent only when their observable-families
  differ. Two channels of the same family share a failure path: a
  mis-set reference, a de-calibrated coupler or a blocked view-port
  takes both down together, so a duplicated family adds redundancy but
  adds no independence, and the arrangement is graded on the count of
  distinct families, not the count of channels.
- Each channel declares a detection-threshold in dBm and is placed
  against the expected event-signature in dBm. The
  sensitivity-margin is the signature minus the threshold; a channel
  whose margin sits below the campaign's required-margin cannot be
  relied on to separate a discharge from the noise-floor. The margin
  is a difference of two dB quantities, so a case that is exactly on
  the required-margin can land a few ULPs low: the comparison absorbs
  that representation error rather than relaxing the required-margin.
- Each channel also declares a response-time in ms, which is compared
  against the shortest credible discharge-duration for the item. A
  channel slower than that duration integrates the event away and
  registers nothing, however good its sensitivity-margin is.

## Workflow

1. Normalize every declared channel: identifier, coverage-scope,
   observable-family, detection-threshold in dBm, response-time in ms
   and calibration state. Reject an unrecognized coverage-scope or
   observable-family, a non-positive response-time and a missing
   identifier before any grading starts.
2. Count the channels. Fewer than the minimum arrangement size (two)
   is a finding on its own -- a lone channel has nothing to
   corroborate it and cannot separate a discharge from an artefact.
3. Summarize coverage: the arrangement needs at least one
   global-coverage channel and at least one local-coverage channel.
   An all-global set sees that something happened but never where; an
   all-local set watches one region and misses a discharge anywhere
   else in the RF-chain.
4. Count distinct observable-families. Below the minimum independent
   count (two), record a family-independence finding and name the
   duplicated family.
5. Per channel, compute the sensitivity-margin (event-signature minus
   detection-threshold) and compare it with the required-margin,
   absorbing the dB-difference representation error at the exact
   boundary. Compare the response-time with the shortest credible
   discharge-duration under the same tolerance. A channel failing
   either check is recorded as non-registering, with the reason.
6. Require at least one registering channel in each coverage-scope:
   an arrangement whose only global-coverage channel is too slow is
   not rescued by a fast local-coverage channel, and the reverse.
7. Flag every uncalibrated channel. The arrangement is adequate only
   when the channel-count, coverage-mix, family-independence,
   per-channel registration and calibration findings are all empty.

## Pitfalls

- Counting channels instead of observable-families and calling three
  rf-power-balance instruments an independent arrangement -- they
  share one reference path and fail together, so the arrangement holds
  one independent observable, not three.
- Accepting an all-global-coverage set because it is the most
  sensitive one available -- clause 7.1 expects the arrangement to
  localize as well as notice, and a global-only set cannot attribute a
  discharge to the critical-gap that the design analysis flagged.
- Grading sensitivity-margin alone and ignoring response-time -- a
  channel with a large margin and a slow integrator registers nothing
  for a short discharge, and it will still report a comfortable margin
  on the bench.
- Widening the required-margin because an exactly-on-the-limit case
  keeps failing -- the failure is dB-subtraction representation error,
  and it belongs in the comparison tolerance, never in the engineering
  limit.
- Treating an uncalibrated channel as a pass because its declared
  numbers look healthy -- an uncalibrated threshold is an assumption,
  not a measurement, and clause 7.1 expects the declared capability to
  be traceable.

## Behavior contract (gate 3)

The channel-normalization, coverage-mix, family-independence,
sensitivity-margin, response-time and arrangement-aggregation logic is
exercised by the gate 3 contract test:
scripts/test_e2001_detection_method_overview.py against
scripts/e2001_detection_method_overview_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_detection_method_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

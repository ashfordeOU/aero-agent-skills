---
name: q7080-process-window-qualification
description: "Evaluate whether a declared additive-manufacturing parameter window is qualified by the coupon campaign actually run. Use when a window is taken into service, or brought back after a machine or feedstock change, and the evidence has to be graded rather than assumed: grade every run's recorded parameters against the window, treat an unrecorded parameter exactly like an excursion, demand a build at each bound and expect one in the interior, check each required characteristic was measured and met its limit, then separate an outright fail from a window that stands with a coverage finding attached. Trigger: ecss, q-st-70-80-additive-manufacturing, am-process-window-qualification, am-qualification-coupon-campaign, am-parameter-excursion-grading, am-window-bound-coverage, am-build-repeatability-runs."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-process-window-qualification, am-process-window-qualification, am-qualification-coupon-campaign, am-parameter-excursion-grading, am-window-bound-coverage, am-build-repeatability-runs]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Process Window Qualification (space-systems/ecss/q7080-process-window-qualification)

Use when the task is the process clause of ECSS-Q-ST-70-80 that qualifies a
parameter window with test coupons: showing that a machine running anywhere
inside the declared window produces conforming material repeatably, and
saying which part of that claim the campaign failed to evidence.

## Domain quick reference

- The claim is about a window, not a setpoint. Parts will be built at
  every value the window permits, so evidence gathered only at the
  nominal centre qualifies a setpoint and leaves the corners of the
  window unevidenced.
- A bound that was never run was never qualified. The extremes are where
  the melt pool is furthest from nominal, which is why a build at each
  bound of each parameter is required and a missing one is fatal rather
  than a completeness note.
- Interior coverage is a different question with a different weight. A
  campaign that ran both bounds but nothing between them has evidenced
  the hard cases and skipped the working point, which is a finding on a
  qualification that still stands.
- An unrecorded parameter and an out-of-window parameter break the same
  claim. Neither shows the process was inside the window being
  qualified, so they are listed together rather than triaged apart.
- Repeatability cannot come from one build. A single good build shows
  the machine managed it once, which is a weaker statement than the one
  the hardware will rely on.
- A characteristic that was not measured is not a characteristic that
  passed. Unmeasured and failed are separated in the report because they
  need different corrective action, but both block the verdict.
- Recorded setpoints pass through unit conversion and logger rounding, so
  a value exactly on a bound can read a few units in the last place
  outside it. The comparison absorbs that; the window is not widened.

## Workflow

1. Validate the declared window first. Every parameter needs a bound
   pair, an inverted pair is an input error, and a fixed setpoint is
   expressed as a pair whose bounds coincide.
2. Grade each build's recorded parameters against the window, refusing a
   parameter the window never declared and recording a missing value as
   an excursion in its own right.
3. Count the builds. Below the minimum, the campaign has made no
   repeatability claim, and that is stated rather than inferred from the
   coupons.
4. Grade bound coverage: for each parameter, look for a build at the low
   bound and a build at the high bound, allowing a small fraction of the
   span as the sampling band.
5. Grade interior coverage separately, skipping a fixed setpoint, which
   has no interior to sample.
6. Grade the coupons: every required characteristic measured on some
   coupon of every build, and every measured value inside its acceptance
   limit, with an exact limit value counted as a pass.
7. Give the verdict: not qualified on too few builds, any excursion, any
   missing bound, any unmeasured characteristic or any failed coupon;
   qualified with findings when only interior coverage is thin; qualified
   when nothing was raised.

## Pitfalls

- Qualifying the window from builds that all sat at nominal. The
  campaign then evidences a setpoint, and the first production build
  near a bound is the experiment nobody ran.
- Treating a thin interior as equivalent to a missing bound. One is a
  finding on a standing qualification, the other is an unsampled risk
  region, and collapsing them either blocks good machines or passes
  unevidenced windows.
- Filling an unrecorded parameter with its nominal value. Nothing was
  measured, so nothing is known, and the campaign silently qualifies a
  window it never demonstrated.
- Widening the window after an excursion so the build counts. The window
  is then evidenced by a single build at its new edge, which is the
  region the campaign was supposed to cover properly.
- Reading a coupon set as complete because coupons exist. Completeness is
  per characteristic and per build, and a campaign can carry many coupons
  while never measuring one required property.

## Behavior contract (gate 3)

The window validation, run-parameter grading, bound and interior coverage,
coupon acceptance and completeness checks and the overall qualification
verdict are exercised by the gate 3 contract test:
scripts/test_q7080_process_window_qualification.py against
scripts/q7080_process_window_qualification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_process_window_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

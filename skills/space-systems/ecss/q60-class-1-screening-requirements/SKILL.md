---
name: q60-class-1-screening-requirements
description: "Evaluate the screening regime applied to Class 1 parts before they enter flight standard hardware. Use when a screened lot has to be dispositioned: require every delivered device to be screened for a flight build, check the performed screens against the set the part family carries, reject an unapproved screening facility, convert the burn-in actually run to its equivalent at the reference condition by an Arrhenius acceleration and report a shortfall, count devices whose monitored drift exceeds the delta limit, and disposition the lot on percent defective. Trigger: ecss, ecss-q-st-60c-clause-4-3-3, class-1-flight-lot-screening, burn-in-arrhenius-equivalence, screening-delta-drift-limit, screening-percent-defective-allowable, approved-screening-facility."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-1-screening-requirements, ecss-q-st-60c-clause-4-3-3, class-1-flight-lot-screening, burn-in-arrhenius-equivalence, screening-delta-drift-limit, screening-percent-defective-allowable, approved-screening-facility]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 EEE Parts — Screening Requirements (space-systems/ecss/q60-class-1-screening-requirements)

Use when the task is the screening regime of ECSS-Q-ST-60C clause 4.3.3 — the
sequence of stress and measurement applied to every Class 1 device destined
for flight standard hardware, and the lot disposition that follows from what
the sequence removed.

## Domain quick reference

- Screening is a hundred-percent operation on a flight build. It removes the
  weak members of a population, which a sample cannot do: a sampled screen
  tells you the lot's health and still ships the unscreened devices.
- Hardware standard decides the regime, not the part. The same device bought
  for ground support equipment can be sampled; bought for flight it cannot,
  so the standard is an input to the assessment rather than an assumption.
- The screen set belongs to the part family. Seal and radiographic screens
  exist only where there is a cavity to seal and image; a solid part takes
  thermal shock in their place, and demanding them there produces a waiver
  for a test that was never meaningful.
- Burn-in brackets its own electrical measurements. Without a pre-burn-in
  reading there is nothing to measure drift against, so the two electricals
  are part of the screen, not paperwork around it.
- A burn-in at a different temperature is not a different burn-in. An
  Arrhenius acceleration on absolute temperature converts what was run into
  its equivalent at the reference condition, so a hotter oven buys hours and
  a cooler one owes them.
- Drift is a screen in its own right. A device inside its specification
  limits at both ends can still have moved far enough across burn-in to be an
  unstable member of the population, and the delta limit is what removes it.
- Percent defective disposition the lot, not the devices. Removals are
  counted over the devices that entered burn-in; a lot above the allowance is
  rejected whole, because the removals are evidence about the population the
  survivors also came from.

## Workflow

1. Validate the declared hardware standard and the lot arithmetic, and raise
   a finding when a flight build screened fewer devices than it delivered.
2. Resolve the screen set for the part family and report any required screen
   absent from the performed list; an extra screen is not a shortfall.
3. Validate the screening facility and reject one the customer has not
   approved.
4. Convert the burn-in actually run to the hours owed at its temperature
   against the reference condition, and report a shortfall with a
   representation-sized tolerance at the boundary.
5. Compute the drift of each monitored parameter across burn-in and mark the
   devices whose drift exceeds the delta limit, counting a device once
   however many of its parameters moved.
6. Add the catastrophic failures, compute percent defective over the devices
   that entered burn-in, and disposition the lot against its allowance.
7. Report the per-device records and a verdict carrying every finding.

## Pitfalls

- Screening a sample and calling the lot screened. The devices that reach the
  board are exactly the ones the screen never saw.
- Reading the screen set off another family's flow. A non-hermetic part has
  no seal to test, and the resulting waiver hides the screens it does owe.
- Shortening burn-in because the oven ran hot without doing the conversion.
  The trade is legitimate and the arithmetic is not optional; guessing it
  usually under-runs the hours.
- Treating a hotter burn-in as automatically sufficient. Below the equivalent
  hours it is still a shortfall, however high the temperature went.
- Judging drift against the specification limits. A device can sit inside its
  limits at both ends and still have moved several times the delta allowance.
- Counting a multi-parameter device twice in the percent defective. The
  removal is the device, so the count is over devices, not readings.
- Trimming the removals and shipping the remainder of a lot that failed its
  allowance. The disposition is a statement about the population.
- Stopping at the first finding. The lot owner needs the whole list to
  disposition once rather than once per finding.

## Behavior contract (gate 3)

The family screen sets, the missing-screen report, the Arrhenius acceleration
and equivalent burn-in hours, the burn-in shortfall finding, the drift and
delta removal rules, the percent defective arithmetic, the lot disposition
and the overall regime verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_1_screening_requirements.py against
scripts/q60_class_1_screening_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_screening_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

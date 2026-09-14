---
name: e2008-blocking-diode-surge-test
description: "Evaluate a planar blocking diode surge test under ECSS-E-ST-20-08C clause 12.6.17, where short pulses whose peak current sits far above the rated average are driven through the device: refuse a peak that never clears the rated average by the demanded multiple, refuse a pulse long enough to be an overload rather than a surge, take the action integral from the waveform shape and weigh it against the device withstand from both sides, keep junction headroom to the ceiling, demand a recovery interval between pulses and an electrical readout after the last one, then sentence each device and the lot. Use when a blocking diode surge pulse train has to be specified, sentenced or repeated. Trigger: ecss, e-st-20-08c-clause-12-6-17, blocking-diode-surge-pulse-train, blocking-diode-peak-to-rated-current-ratio, blocking-diode-pulse-action-integral, blocking-diode-surge-under-stress, blocking-diode-inter-pulse-recovery, blocking-diode-post-surge-readout."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-surge-test, e-st-20-08c-clause-12-6-17, blocking-diode-surge-pulse-train, blocking-diode-peak-to-rated-current-ratio, blocking-diode-pulse-action-integral, blocking-diode-surge-under-stress, blocking-diode-inter-pulse-recovery, blocking-diode-post-surge-readout]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Planar Blocking Diodes -- Surge Test (space-systems/ecss/e2008-blocking-diode-surge-test)

Use when the task is clause 12.6.17 of ECSS-E-ST-20-08C: short pulses
carrying a peak current well above the current the device is rated to carry
continuously are driven through it, and the question is whether the part is
still a diode afterwards. This leaf reads one declared pulse train against one
device rating and returns both halves of that answer -- whether the train is a
surge worth running, and what each surged device became.

## Domain quick reference

- The pulse train and the devices are two separate verdicts. A train that
  never stressed anything can still return four clean parts, and reporting
  that as a pass records a result nobody obtained.
- A peak that barely clears the rated average is not a surge. The clause turns
  on the peak sitting well above the rated average current, so a multiple is
  demanded and a train that misses it proves nothing about the device.
- Short is part of the definition. A pulse wide enough to reach thermal
  equilibrium is an overload test with different acceptance criteria, and
  quietly widening the pulse until the part survives changes the test rather
  than passing it.
- The action integral, not the peak, does the damage, and it depends on the
  waveform. A rectangular pulse and a half-sine pulse of equal peak and equal
  width carry different energy, so the shape factor is applied before anything
  is compared with a withstand.
- The withstand window has two sides. A pulse far below it demonstrates
  nothing, and one above it removes parts by design and says nothing about the
  population they came from, so both the demonstration floor and the
  overstress ceiling are checked and a tie is admissible on either.
- Junction headroom is its own arm. The train can sit inside the action
  integral window and still drive the junction past its ceiling, because the
  temperature depends on the forward drop and the thermal capacity rather than
  on the action integral alone.
- Pulses have to be spaced. A train fired faster than the junction cools is a
  single longer event, which is the overload test again wearing a pulse count.
- A missing post-surge reading is not a survival. The device has not been
  evaluated, and recording it as withstood turns absent evidence into
  favourable evidence.

## Workflow

1. Validate the device rating, the pulse train and the criteria set first: a
   non-blank specification reference, a positive rated average current,
   withstand, forward drop and thermal capacity, a recognised waveform, a
   pulse count of at least one, and a demonstration floor that does not sit
   above the overstress ceiling.
2. Take the peak against the rated average current and compare the ratio with
   the demanded multiple, a tie being admissible.
3. Check the pulse is still short enough to be a surge rather than an
   overload.
4. Take the action integral of one pulse from its peak, its width and its
   waveform shape factor, express it as a fraction of the device withstand,
   and test that fraction against the demonstration floor and the overstress
   ceiling as two separate arms.
5. Turn the pulse into dissipated energy at the forward drop, divide by the
   thermal capacity for the junction rise, and check the headroom left to the
   junction ceiling.
6. Require an interval between pulses that lets the junction return to its
   reference temperature whenever more than one pulse is fired, and require a
   readout after the last pulse.
7. Name every deficiency the train carries rather than the first one found,
   and close the train on adequate or inadequate.
8. For each device, pair the pre-surge and post-surge readings, take the drift
   in the sense that parameter degrades in, test the post-surge reading
   against its own absolute limit as a separate arm, fail the device on any
   listed observed condition, and hold a device missing a reading as not
   evaluated.
9. Roll the devices up: group the modes by device, weigh the failed share
   against its allowance, and refuse to pass the campaign while the train was
   inadequate or any device is unevaluated.

## Pitfalls

- Passing a campaign whose train never stressed anything. Four clean parts
  under an under-stressed pulse are four parts nobody tested.
- Comparing peaks instead of action integrals. Two trains with the same peak
  and the same width can differ by a factor of three in the energy they
  deliver, and only the shape says which.
- Widening the pulse to get a survivable stress. A long pulse is a different
  test, and the acceptance criteria that came with the surge do not follow it.
- Checking the action integral and forgetting the junction. The temperature
  depends on the forward drop and the thermal capacity, so a train inside the
  withstand window can still cook the die.
- Firing the train faster than the part cools. The pulse count then describes
  the equipment rather than the stress, and the junction never sees the
  reference temperature the readings were taken at.
- Sentencing on the post-surge reading alone. A device that started near its
  ceiling and crept is a different finding from one that ran away, and only
  the movement across the train separates them.
- Recording a missing post-surge reading as a survival. It is the one error
  the verdict alone cannot reveal.
- Stopping at the first deficiency or the first mode. The repair depends on
  which appeared together.

## Behavior contract (gate 3)

The rating, profile and criteria validation, the peak-to-rated multiple, the
surge duration limit, the waveform shape factor and the pulse and train action
integrals, the demonstration floor and overstress ceiling as two arms with
admissible ties, the junction rise and its headroom, the inter-pulse recovery
interval, the required closing readout, the per-device drift and absolute
arms, the observed condition arm, the not-evaluated verdict, the failed share
against its allowance and the campaign verdict are exercised by the gate 3
contract test: scripts/test_e2008_blocking_diode_surge_test.py against
scripts/e2008_blocking_diode_surge_test_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_blocking_diode_surge_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

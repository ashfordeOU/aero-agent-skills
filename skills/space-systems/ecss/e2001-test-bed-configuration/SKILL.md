---
name: e2001-test-bed-configuration
description: "Use when verify that a multipactor test bed meets the minimum configuration conditions of ECSS-E-ST-20-01C clause 8.2 before an article is installed: categorize every bed element as vacuum-system, rf-chain, instrumentation, electron-seeding or detection-method; confirm the chamber reaches the required vacuum-pressure-level with pump-down and bake-out on record; check each measurement instrument carries an in-date calibration-certificate covering the planned run date; size the rf-chain so the source rating covers the maximum applied-power raised by the required run-margin in decibels; and confirm at least one global and one local multipactor-detection method plus an electron-seeding source are present. Trigger: ecss, e-st-20-01c, multipactor-test-bed, vacuum-pressure-level, calibration-certificate, calibrated-instrumentation, rf-chain-capability, electron-seeding-source, detection-method-coverage, test-bed-configuration."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-test-bed-configuration, multipactor-test-bed, vacuum-pressure-level, calibrated-instrumentation, electron-seeding-source, detection-method-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor -- Test Bed Minimum Configuration (space-systems/ecss/e2001-test-bed-configuration)

Use when the task is establishing that a multipactor test bed satisfies the
minimum conditions of ECSS-E-ST-20-01C clause 8.2 -- the vacuum-pressure-level
the chamber holds, the calibration state of every measurement instrument, the
rf-chain headroom above the maximum applied-power, the electron-seeding source
and the multipactor-detection coverage -- before any article is mounted in it.

## Domain quick reference

- A multipactor test bed is only admissible when its own environment cannot
  mask or mimic the effect under investigation. Clause 8.2 therefore fixes a
  floor on five element families, and a bed element that belongs to none of
  them is outside the configuration record: vacuum-system (chamber, pumps),
  rf-chain (source, amplifier, circulator, coupler, load), instrumentation
  (power-meter, spectrum-analyser, network-analyser, vacuum-gauge,
  residual-gas-analyser, thermocouple), electron-seeding (ultraviolet lamp,
  radioactive source, electron gun) and detection-method.
- The vacuum-pressure-level matters because the discharge physics changes with
  residual gas: above the free-molecular threshold a gas discharge can ignite
  and be mistaken for a resonant-electron event, so the bed must pump below the
  required level and hold it. Pump-down alone is not the condition; bake-out or
  an equivalent outgassing treatment is what keeps the level stable while
  radio-frequency power is applied.
- Every instrument that produces a number entering the verdict carries a
  calibration-certificate with a due date. The admissible question is not
  whether a certificate exists but whether it is still in date on the planned
  run date, computed against that date, not against today.
- The rf-chain is sized from the maximum applied-power and the run-margin the
  test specification requires above it. The margin is stated in decibels, so
  the required source rating is the applied-power scaled by ten raised to the
  margin over ten; comparing watts against decibels directly is the classic
  sizing error.
- Detection is split into global methods, which observe the whole device
  (forward and reverse power nulling, third-harmonic emission, close-to-carrier
  noise, phase-noise), and local methods, which observe the gap directly
  (electron probe current). A bed carrying two global methods and no local one
  has redundancy but no independence: clause 8.2 coverage needs at least one of
  each family.

## Workflow

1. Categorize every element in the bed record into one of the five families.
   An unrecognized element type is rejected before the assessment continues --
   it means the record and the hardware have drifted apart.
2. Check the vacuum condition: measured chamber pressure at or below the
   required level, and an outgassing treatment (bake-out or equivalent) on
   record. A measured pressure that sits on the limit within numerical
   tolerance is compliant; a missing bake-out entry is a finding even when the
   pressure reads well below the limit.
3. For each measurement instrument, compute the days remaining between the
   planned run date and the calibration due date. Zero days remaining is still
   in date; a negative value is an expired certificate and a finding naming
   that instrument.
4. Size the rf-chain: required source rating equals maximum applied-power times
   ten raised to the run-margin over ten. Compare the installed source rating
   against it, treating an exact-limit rating as sufficient.
5. Check the electron-seeding family: at least one seeding source is present
   and its emission is directed into the device gap region. A seeding source
   listed but marked inactive does not satisfy the condition.
6. Check detection coverage: at least one global and at least one local
   multipactor-detection method, each mapped to an instrument that is itself
   in calibration. A detection method resting on an expired instrument is not
   counted.
7. Aggregate the findings. The bed is configuration-compliant only when every
   check above returns empty; the aggregate reports which family failed so the
   bed can be repaired rather than re-run blind.

## Pitfalls

- Reading a low gauge pressure as a satisfied vacuum condition while the
  bake-out record is absent -- the chamber walls reload the volume once
  radio-frequency power heats them, and the level drifts up during the run.
- Checking calibration against the date the record was written rather than the
  planned run date -- a certificate that expires between the two reads as valid
  and the run produces uncalibrated numbers.
- Adding the run-margin in decibels to a power in watts, or comparing a watt
  rating against a decibel margin -- the margin is a ratio and must be applied
  multiplicatively before any comparison.
- Counting two global detection methods as coverage -- both families see the
  same aggregate signature, and a local probe is what discriminates a genuine
  gap discharge from an rf-chain artefact.
- Treating a listed but inactive electron-seeding source as present -- without
  free electrons in the gap the onset power observed is the statistical
  delay, not the physical threshold, and the bed reports an optimistic result.

## Behavior contract (gate 3)

The element-categorization, vacuum-readiness, calibration-validity, rf-chain
sizing, electron-seeding and detection-coverage logic is exercised by the
gate 3 contract test: scripts/test_e2001_test_bed_configuration.py against
scripts/e2001_test_bed_configuration_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e2001_test_bed_configuration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

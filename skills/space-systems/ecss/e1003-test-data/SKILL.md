---
name: e1003-test-data
description: "Use when record, reduce, and deliver test measurement data for a spacecraft test campaign under ECSS-E-ST-10C §4.3.5: determine the minimum sampling rate for each channel type (vibration, acoustic, thermal, pressure, electrical, strain), validate that raw data records carry complete metadata (channel ID, calibration coefficients, timestamp, format), compute storage requirements, apply linear calibration to convert raw counts to engineering units, categorize each data channel as primary, secondary, or housekeeping, and confirm that the delivery package bundles a calibration file, test report reference, and all required traceability fields before handover. Trigger: ecss, e-st-10-system-scope, test-data, sampling-rate, data-reduction, data-delivery, calibration, test-measurement, storage-requirement."
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
  tags: [ecss, e-st-10-system-scope, test-data, sampling-rate, data-reduction, data-delivery, calibration, storage-requirement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Data — Record, Reduce and Deliver (space-systems/ecss/e1003-test-data)

Use when the task is to record, reduce, and deliver test measurement data
for a spacecraft test campaign under ECSS-E-ST-10C §4.3.5 -- determining
adequate sampling rates, validating metadata completeness, computing
storage budgets, applying calibration, and confirming the delivery package
is ready for handover.

## Domain quick reference

- §4.3.5 requires that every measurement channel is sampled at a rate no
  lower than the Nyquist floor for its signal family: vibration channels
  at ≥ 2 000 Hz, acoustic at ≥ 10 000 Hz, strain at ≥ 1 000 Hz,
  electrical at ≥ 100 Hz, pressure and displacement at ≥ 10 Hz, and
  thermal at ≥ 1 Hz. Sampling below the floor invalidates the record.
- Each channel record must carry a complete traceability block: a unique
  test identifier, a channel identifier, the actual sampling rate, the
  physical unit, the calibration slope and offset, the UTC timestamp of
  the first sample, and the file format. A record missing any of these
  fields is incomplete and must not be used for verification.
- Storage sizing is a worst-case estimate: channels × duration × rate ×
  bits-per-sample / 8, with no compression assumed. This number drives
  the storage procurement and redundancy plan.
- Channels are assigned a traceability priority: primary (vibration,
  acoustic, strain — directly tied to the verification objective),
  secondary (pressure, electrical, displacement — supporting evidence),
  or housekeeping (thermal, power, status — operational context only).
  This priority controls the minimum redundancy level required for each
  channel's stored record.
- Retention periods are set by test phase: development data is kept for
  at least one year; acceptance, qualification, and protoflight data for
  at least ten years; in-service monitoring data for at least five years
  post-mission.
- Before handover the delivery package must bundle the data file, a
  calibration file, the test title, date, facility, operator identity,
  channel list, and the agreed file format. A package with any field
  absent must not be released.

## Workflow

1. Inventory all measurement channels for the test and assign each one a
   channel type (vibration, acoustic, thermal, pressure, electrical,
   strain, displacement). Reject any channel whose type is not in the
   §4.3.5 recognized set before it enters configuration.
2. For each channel, confirm the configured sampling rate meets the
   §4.3.5 floor for its type. Flag under-rate channels immediately;
   do not proceed with a test run until every primary channel meets its
   floor.
3. Compute the total raw storage requirement (channels × duration ×
   rate × bits-per-sample / 8) and verify the allocated storage medium
   is large enough to hold the run without truncation. Include a
   minimum 20 % overhead margin for header and index data.
4. During or immediately after the test run, check each channel record
   for the complete traceability block (test ID, channel ID, sampling
   rate, unit, calibration slope, calibration offset, UTC timestamp,
   format). Quarantine any incomplete records.
5. Apply the linear calibration (engineering value = slope × raw count +
   offset) to every raw sample to produce the engineering-unit dataset.
   Verify that the slope is non-zero before applying; a zero slope is
   an invalid calibration and must be treated as an instrumentation fault.
6. Scan the timestamp sequence for data gaps -- consecutive samples whose
   interval exceeds 1.5 × the nominal sample period. Log each gap as a
   data-quality finding attached to the affected channel.
7. Categorize each channel as primary, secondary, or housekeeping and
   confirm the storage redundancy level matches the category requirement.
8. Assemble the delivery package: data file, calibration file, test
   title, date (UTC), facility, operator, channel list, and format.
   Validate that all mandatory fields are present before releasing the
   package to the customer or archive.

## Pitfalls

- Applying the configured nominal rate rather than the measured actual
  rate to storage sizing -- if the data acquisition system resampled or
  dropped samples, the actual rate differs and the record is incomplete.
- Treating an incomplete traceability block as a minor annotation gap --
  a missing calibration coefficient makes the engineering-unit dataset
  unreproducible; the record must be quarantined, not annotated.
- Compressing storage estimates by assuming a compression ratio before
  the format is known -- size to the raw worst case and let the
  compression be a bonus, not a dependency.
- Skipping the timestamp gap scan on secondary and housekeeping channels
  because they "only support" the primary data -- a gap in a housekeeping
  thermal channel during a thermal-vacuum test is itself a finding.
- Releasing a delivery package with a zero-byte calibration file or a
  placeholder operator field -- the validation check for non-empty fields
  catches these; fix before release, not after.

## Behavior contract (gate 3)

The sampling-rate validation, storage computation, linear calibration,
record completeness, delivery-package validation, channel categorization,
retention lookup, gap detection, format check, and data-rate computation
are exercised by the gate 3 contract test:
scripts/test_e1003_test_data.py against scripts/e1003_test_data_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1003_test_data.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

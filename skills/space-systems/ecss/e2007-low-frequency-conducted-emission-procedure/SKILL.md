---
name: e2007-low-frequency-conducted-emission-procedure
description: "Execute and audit one low-frequency conducted-emission run under ECSS-E-ST-20-07C clause 5.4.2.4: confirm the mandatory steps were all carried out and in their proper order, compare the instrument soak against the required warm-up, judge the system-check read-back error against its decibel tolerance, size the tuning step and the per-point dwell from the resolution bandwidth, derive the point count and the scan time the sweep occupies, and separate outright findings from margins merely worth carrying. Use when running or reviewing a low-frequency conducted-emission measurement on a built bench. Trigger: ecss, e-st-20-07c, lf-conducted-emission-procedure, emi-receiver-warm-up, conducted-emission-system-check, conducted-emission-step-size, conducted-emission-dwell-time, conducted-emission-scan-time."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-low-frequency-conducted-emission-procedure, lf-conducted-emission-procedure, emi-receiver-warm-up, conducted-emission-system-check, conducted-emission-step-size, conducted-emission-dwell-time, conducted-emission-scan-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Low-Frequency Conducted-Emission Procedure (space-systems/ecss/e2007-low-frequency-conducted-emission-procedure)

Use when the task is the run sequence of ECSS-E-ST-20-07C clause 5.4.2.4
-- the walk from switching the instruments on, through the checks that
prove the chain is reading truthfully, to the stepped sweep that produces
the record, and the decision on whether the run as executed can be
believed.

## Domain quick reference

- The clause is an ordered sequence, and the order carries meaning. A
  system check run after the recording proves the chain was healthy at
  the end, not while the data was taken; an ambient check taken after the
  unit is already radiating proves nothing at all.
- Warm-up is a stability requirement on the receiver and the source, not
  a courtesy. Local oscillators and reference levels drift for tens of
  minutes from cold, and a sweep started early carries that drift into
  every recorded level as an unrecorded error.
- The system check is the only step that proves the whole chain. A known
  current injected at the probe and read back at the receiver exercises
  the probe, the cable, the attenuators and the receiver together; every
  instrument can be in calibration while the chain still reads wrong
  because a connector is loose.
- The read-back error is graded against a decibel tolerance, and the
  comparison happens on the magnitude of the error, so a chain reading
  high fails on the same footing as one reading low.
- Tuning step and resolution bandwidth are one decision, not two. Step
  wider than a fraction of the bandwidth and the sweep walks over a
  narrowband emission between measured points, recording a clean band
  that is not clean.
- Dwell per point is bounded below by the reciprocal of the bandwidth. A
  shorter dwell reads the resolution filter before it has settled, which
  understates every narrowband level in the record.
- Scan time is a derived quantity, the point count times the dwell, and
  it is the number that collides with the time the chamber is booked
  for. Deriving it before the run is what stops the sweep being coarsened
  halfway through.

## Workflow

1. Normalize the executed steps, reject a repeat, and reduce the list to
   the absent steps and whether the executed order matches the clause.
2. Compare the elapsed soak with the required warm-up and keep the
   headroom; a soak that only just reaches the requirement is a margin
   worth recording.
3. Compute the magnitude of the system-check read-back error and compare
   it with the tolerance, absorbing representation error only.
4. Derive the tuning-step ceiling and the dwell floor from the resolution
   bandwidth, then compare the planned step and dwell with them.
5. Derive the point count over the band and multiply by the dwell for the
   scan time; compare it with the time the run is allowed when one is
   stated.
6. Aggregate the findings and the limitations. The run stands only when
   no finding stands.

## Pitfalls

- Treating the step list as a checklist rather than a sequence, so every
  step is ticked and the system check happened after the sweep.
- Starting the sweep while the receiver is still warming because the
  slot is tight, then attributing the drift to the unit.
- Skipping the system check on the grounds that every instrument is in
  calibration. Calibration is per instrument; the check is per chain.
- Grading the read-back error with a sign, so a chain reading high is
  waved through while one reading low is rejected.
- Choosing the tuning step for the scan time rather than the bandwidth,
  and recording a band as quiet that was simply stepped over.
- Shortening the dwell to fit the booking, which understates precisely
  the narrowband emissions the run exists to find.
- Discovering the scan time only when the sweep is running, and
  coarsening the plan mid-run so two halves of the record were taken
  under different settings.

## Behavior contract (gate 3)

The step sequencing, warm-up headroom, system-check error grading,
step-ceiling and dwell-floor derivation, point-count and scan-time
arithmetic and the run aggregation logic is exercised by the gate 3
contract test:
scripts/test_e2007_low_frequency_conducted_emission_procedure.py against
scripts/e2007_low_frequency_conducted_emission_procedure_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_low_frequency_conducted_emission_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

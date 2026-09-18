---
name: e2007-radio-frequency-conducted-emission-procedure
description: "Execute and audit one radio-frequency conducted-emission run under ECSS-E-ST-20-07C clause 5.4.3.4: confirm every mandatory phase ran and in the clause order, compare the instrument soak against the required warm-up, carry the injected calibration current through the current-probe transfer impedance to the level the receiver should read back, grade the chain error and the pre-to-post drift against their decibel tolerances, confirm the capture segments tile the method band without a gap, derive each segment sweep-time floor from its resolution bandwidth, and separate findings from margins worth carrying. Use when running or reviewing an RF conducted-emission measurement on a built bench. Trigger: ecss, e-st-20-07c, rf-conducted-emission-procedure, rf-conducted-warm-up-soak, current-probe-chain-verification, probe-transfer-impedance-readback, conducted-capture-segment-coverage, conducted-chain-drift-check, rf-conducted-sweep-time-floor."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radio-frequency-conducted-emission-procedure, rf-conducted-emission-procedure, rf-conducted-warm-up-soak, current-probe-chain-verification, probe-transfer-impedance-readback, conducted-capture-segment-coverage, rf-conducted-sweep-time-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radio-Frequency Conducted-Emission Procedure (space-systems/ecss/e2007-radio-frequency-conducted-emission-procedure)

Use when the task is the run sequence of ECSS-E-ST-20-07C clause 5.4.3.4
-- the walk from the instruments coming up to temperature, through the
check that proves the current-probe chain reads a known injected current
truthfully, to the swept capture that produces the record and the repeat
of that chain check once the capture is finished.

## Domain quick reference

- The radio-frequency method reads current, not voltage. A current probe
  clamped over the lead converts that current to a voltage through its
  transfer impedance, so the level the receiver should show for an
  injected calibration current is an addition in decibels:
  dBuV = dBuA + dBohm, less the insertion loss of the cable and the
  attenuators between probe and receiver. The chain error is the distance
  between that expected level and the level actually read back.
- The chain check is the only step that exercises the probe, the cable,
  the attenuators and the receiver together. Every instrument can be
  inside its own calibration while the chain still reads wrong, because a
  connector is loose or an attenuator is the wrong value.
- The check is run twice, before the capture and after it, and the pair
  carries information the single reading does not: the movement between
  them is drift, and a record taken across a drifting chain cannot be
  attributed to the unit. Drift is graded against its own tolerance,
  tighter than the absolute chain tolerance.
- Both the chain error and the drift are graded on magnitude. A chain
  reading high overstates every emission in the record and is a defect on
  the same footing as one reading low.
- Warm-up is a stability requirement on the receiver, the probe and the
  injection source. Local oscillators and reference levels move for tens
  of minutes from cold, and a capture started early carries that movement
  into the record as an unrecorded error.
- The method band is covered by a set of swept segments, each with its
  own resolution bandwidth. Sweep time per segment is bounded below by
  the span divided by the square of the bandwidth: narrow the bandwidth
  by two and the same span needs four times as long, because the
  resolution filter settles that much more slowly.
- Segments are graded as a set, not one at a time. A band edge left
  outside every segment is an uncaptured stretch of the method band and a
  finding; segments that overlap record the same stretch twice, which
  costs time and is carried as a limitation rather than a defect.

## Workflow

1. Normalize the executed phases, reject a repeat, and reduce the list to
   the absent phases and whether the executed order matches the clause.
2. Compare the elapsed soak with the required warm-up and keep the
   headroom; a soak that only just reaches the requirement is a margin
   worth recording, not a pass to stay silent about.
3. Carry the injected current through the transfer impedance and the
   insertion loss to the expected read-back level, then grade the
   magnitude of the pre-capture and post-capture errors against the chain
   tolerance, absorbing representation error only.
4. Grade the movement between the two read-backs against the drift
   tolerance.
5. Validate each capture segment: recognized detector, positive
   bandwidth, and a sweep time at or above the floor its bandwidth sets.
6. Grade the segment set against the method band for gaps and overlaps,
   and sum the segment sweep times into the capture time the run occupies.
7. Aggregate findings and limitations. The run stands only when no
   finding stands.

## Pitfalls

- Reading the injected current straight off the receiver as a current.
  Without the transfer impedance the expected level is wrong by the whole
  dBohm figure, and a healthy chain looks broken or a broken one healthy.
- Forgetting the insertion loss of the cable run and the attenuator pad,
  which biases the expected level and so biases every graded error.
- Running the chain check once, at the start, and calling the record
  attributable. Drift across a long capture is exactly what the second
  check exists to catch.
- Grading the chain error with a sign, so a chain reading high is waved
  through while one reading low is rejected.
- Starting the capture while the receiver is still warming because the
  chamber slot is tight, then attributing the movement to the unit.
- Sweeping a narrow-bandwidth segment at the speed that suited a wide one.
  The floor moves with the square of the bandwidth, so the segment that
  looks quiet is the one swept too fast to see anything.
- Choosing segment edges to suit the instrument and leaving a stretch of
  the method band between two segments, which reads as a clean band that
  was never looked at.

## Behavior contract (gate 3)

The phase sequencing, warm-up headroom, transfer-impedance read-back
derivation, chain-error and drift grading, per-segment sweep-time floor,
band-coverage reduction and run aggregation logic is exercised by the
gate 3 contract test:
scripts/test_e2007_radio_frequency_conducted_emission_procedure.py
against
scripts/e2007_radio_frequency_conducted_emission_procedure_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radio_frequency_conducted_emission_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

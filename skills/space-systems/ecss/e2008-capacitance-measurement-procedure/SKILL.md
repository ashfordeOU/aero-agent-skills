---
name: e2008-capacitance-measurement-procedure
description: "Use when a capacitance campaign is about to start on a bench nobody proved ready. Prepare the equipment of a solar cell capacitance measurement before any data is gathered, per ECSS-E-ST-20-08C clause 11.1.3: hold the preparation steps in their order, count the calibration validity left on the test date, confirm the open, short and load compensation was taken at the test frequency, hold the instrument warm-up and the bias source settling, place the ambient inside its declared band, and close the whole chain against a reference capacitor in parts per million. Trigger: ecss, e-st-20-08c-clause-11-1-3, solar-cell-capacitance-equipment-preparation, capacitance-fixture-compensation, capacitance-calibration-currency, capacitance-warm-up-and-settling, reference-capacitor-ppm-gate."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-capacitance-measurement-procedure, solar-cell-capacitance-equipment-preparation, capacitance-fixture-compensation, capacitance-calibration-currency, capacitance-warm-up-and-settling, reference-capacitor-ppm-gate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Capacitance Measurement Procedure (space-systems/ecss/e2008-capacitance-measurement-procedure)

Use when the task is clause 11.1.3 of ECSS-E-ST-20-08C -- getting the
measurement equipment into the state a solar cell capacitance reading
can be taken from. The clause is about what happens before the first
number, and the reason it is a clause of its own is that the number
carries no trace of it. A bridge answers the moment it is asked;
nothing in the answer says whether the instrument was warm, whether the
fixture had been compensated at the frequency in use, whether the bias
had settled, or whether the scale behind it was still in date.

## Domain quick reference

- The preparation steps are a sequence, not a checklist. Warm-up comes
  first because gain and oscillator drift settle first, and a
  compensation taken on a cold instrument is thrown away by the warm
  one. A record with every box ticked in the wrong order has not
  prepared the bench.
- Open, short and load compensation remove three different fixture
  terms: the stray of the empty fixture, the residual of the closed
  one, and the behaviour of the pair against a known article. Dropping
  one leaves its term in every reading.
- Compensation is only valid at the frequency it was taken at. Fixture
  stray and lead residual are both frequency dependent, so a
  compensation run at a convenient frequency and reused at another is
  not a compensation; the two frequencies agree to within a small
  relative tolerance or the terms do not transfer.
- Calibration currency is arithmetic on dates, not a sticker. The
  interval runs from the calibration day, and a reading taken past it
  has no traceable scale behind it however well the bench behaved.
- Bias matters because a solar cell is a junction: its capacitance
  moves with the voltage across it, so an unsettled bias source is
  measuring the cell at a bias nobody recorded.
- The reference capacitor check is the only step that exercises the
  whole chain -- instrument, leads, fixture and compensation together
  -- which is why its result is carried as a signed deviation in parts
  per million rather than as a pass mark. The sign says which way the
  chain is biased.
- Ambient temperature belongs to the preparation because both the
  reference standard and the article have temperature coefficients; a
  bench outside its declared band moves the standard and the cell at
  once.

## Workflow

1. Collect the preparation evidence and refuse the assessment when any
   of it is absent, rather than assuming a default for a step nobody
   recorded.
2. Place the recorded steps against the sequence: report entries that
   are not steps, steps still owed, and steps performed before a step
   that has to precede them, as three separate findings.
3. Count the calibration validity remaining on the test date from the
   calibration date and the interval, in whole days.
4. Form the relative distance between the compensation frequency and
   the test frequency and hold it inside the tolerance.
5. Take the warm-up and bias settling margins as elapsed less required,
   keeping the shortfall as a signed number so the report says how far
   short the bench is.
6. Place the ambient inside its declared band, edges included.
7. Form the signed reference deviation in parts per million and gate on
   its magnitude, absorbing representation error at the limit with a
   named tolerance while the limit itself stays as written.
8. Report every derived term and a verdict that stays open while any
   finding stands.

## Pitfalls

- Treating the sequence as an unordered checklist. Order is the point:
  a compensation taken before warm-up is not merely early, it is
  invalid, and a tick against it hides that.
- Reusing yesterday's compensation at today's frequency. It looks like
  preparation and it removes the wrong terms, in a direction no repeat
  will reveal.
- Reading calibration currency off a label rather than off the dates.
  The label is written at calibration; the interval expires silently.
- Starting the sweep while the bias source is still moving. A junction
  capacitance follows the bias, so the early points belong to a
  different operating point than the late ones.
- Recording the reference capacitor check as a pass mark. Dropping the
  signed parts-per-million figure throws away the one diagnostic that
  says which way the whole chain is biased and by how much.
- Comparing a parts-per-million deviation or an offset fraction against
  its limit by bare arithmetic. Both are quotients of floats that can
  land a few units in the last place either side of a round limit, so
  the comparison absorbs that error while the limit is never relaxed.
- Leaving the ambient out because the laboratory feels stable. The
  reference standard and the cell both move with it, and the reference
  check will absorb part of the drift and disguise the rest.

## Behavior contract (gate 3)

The preparation sequence, unrecognised and incomplete and out-of-order
step detection, calibration day arithmetic, compensation frequency
offset, warm-up and bias settling margins, ambient band test and signed
reference deviation in parts per million are exercised by the gate 3
contract test:
scripts/test_e2008_capacitance_measurement_procedure.py against
scripts/e2008_capacitance_measurement_procedure_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_capacitance_measurement_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

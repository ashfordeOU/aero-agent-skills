---
name: e2008-diode-contact-thickness-test
description: "Document the metallisation thickness present on each protection diode contact at acceptance under ECSS-E-ST-20-08C clause 9.6.8: refuse a gauge whose resolution cannot split the specified band, refuse a reading whose calibration had lapsed on the measurement day, require the declared replicates and hold their spread inside the repeatability limit, take their mean as the contact figure, sentence it against the thickness band, and treat a polarity or a device with no record as unsentenced rather than passed. Use when protection diode contact thickness readings have to become an acceptance record and a lot verdict. Trigger: ecss, e-st-20-08c-clause-9-6-8, diode-contact-metallisation-thickness, diode-thickness-gauge-resolution, diode-gauge-calibration-validity, diode-replicate-repeatability-spread, diode-acceptance-lot-record-coverage."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-diode-contact-thickness-test, diode-contact-metallisation-thickness, diode-thickness-gauge-resolution, diode-gauge-calibration-validity, diode-replicate-repeatability-spread, diode-acceptance-lot-record-coverage, diode-thickness-record-quantisation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Diode Contact Thickness Test (space-systems/ecss/e2008-diode-contact-thickness-test)

Use when the task is the acceptance measurement of ECSS-E-ST-20-08C
clause 9.6.8 -- the metallisation thickness present on each protection
diode contact has to be measured and written down, and the record is
what somebody reads years later when the string opens.

## Domain quick reference

- An acceptance clause is about the record as much as the number. A
  figure written down without the three things that make it a
  measurement is a number, and it is indistinguishable in the file from
  a number that means something.
- The gauge has to split the band it sentences against. A six
  micrometre band read by an instrument stepping in two micrometres
  cannot tell a part near the floor from a part under it, and every
  reading it returns is honest without discriminating.
- A gauge too coarse for the band closes the record as not established.
  It does not fail the part -- nothing has been shown about the part
  either way, and failing it scraps hardware on an instrument choice.
- A calibration has a date on it. A reading taken after it lapsed is
  not a bad reading but a reading of unknown bias, which is worse,
  because it looks exactly like a good one in the record.
- Repeatability comes before the mean. One reading cannot show that the
  surface, the fixture and the operator agree, so the clause is worked
  with replicates and their spread is checked before their mean is
  used. Averaging replicates that disagree produces a confident figure
  from an unrepeatable one.
- Sentencing is asymmetric on purpose. Under the floor the metal is not
  there to weld an interconnect onto and the contact is rejected. Over
  the ceiling the metal is present in excess -- a plating bath running
  long, a weld parameter about to drift -- and that is a review rather
  than scrap.
- The figure entering the record is quantised to the gauge step.
  Quoting a mean of replicates to more digits than the instrument can
  resolve writes a precision into the file the gauge never had.
- A polarity or a device with no record is unsentenced, not passed. A
  diode accepted on its anode figure while nobody measured the cathode
  has been shown half of what the clause asks for, and an acceptance
  run short of its declared sample speaks for the devices it measured.

## Workflow

1. Validate the criteria set first: thickness floor and ceiling, gauge
   resolution allowance as a fraction of the band, replicate count,
   repeatability limit and acceptance sample floor. A band whose
   ceiling sits at or under its floor is refused rather than used.
2. Normalise each polarity contact, its gauge and its replicate set,
   refusing a measurement with no replicate recorded.
3. Run the record gates in order before any figure is sentenced: gauge
   resolution against the band, calibration against the measurement
   day, replicate count, then replicate spread against the
   repeatability limit. Any one of them short closes the contact as not
   established.
4. Take the mean of the replicates as the contact figure and quantise a
   copy of it to the gauge step for the record.
5. Sentence the figure against the band: under the floor rejects, over
   the ceiling goes to review, inside is accepted. A value landing
   exactly on a bound passes; the comparison tolerance absorbs
   representation error and the bound itself does not move.
6. Roll up over both polarities, refusing to sentence a diode while
   either carries no record.
7. Close the run against its declared sample rather than against the
   records that arrived, and report every finding, not the first.

## Pitfalls

- Sentencing a part with a gauge that cannot split the band. The
  readings are honest and the verdict is arithmetic on noise.
- Rejecting a part because the gauge was wrong. Nothing was shown about
  the part, so it is unsentenced and goes back to a calibrated
  instrument.
- Letting a lapsed calibration through because the number looks
  reasonable. Unknown bias is the one error that leaves no trace in the
  figure.
- Averaging replicates before checking they agree. The mean of an
  unrepeatable set is the most confident wrong number in the file.
- Treating an over-thick contact as scrap. Excess metal is a process
  question, and scrapping on it hides the bath that caused it.
- Writing the mean into the record at full float precision. The record
  then claims a resolution the gauge never had.
- Accepting a diode on one polarity, or a lot on the devices that
  happened to carry a record.
- Comparing a thickness, a resolution or a spread against its limit by
  bare arithmetic. These are differences and quotients of measured
  values, so a figure that should sit exactly on a bound can evaluate a
  few units in the last place off it; the comparison absorbs that
  representation error while the bound stays untouched.

## Behavior contract (gate 3)

The criteria validation, the band width, the gauge resolution gate, the
calibration currency gate, the replicate count and repeatability gates,
the replicate mean, the record quantisation to the gauge step, the
asymmetric band sentencing, the two-polarity completeness rule and the
declared-sample rule are exercised by the gate 3 contract test:
scripts/test_e2008_diode_contact_thickness_test.py against
scripts/e2008_diode_contact_thickness_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_diode_contact_thickness_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

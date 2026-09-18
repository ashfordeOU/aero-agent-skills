---
name: q7029-concentration-determination
description: "Determine the concentration of each offgassing product from its chromatographic response under ECSS-Q-ST-70-29: subtract the system blank, convert peak area to mass on the bracketing calibration rather than an extrapolated one, correct for recovery, then normalise to sample mass and to vessel volume so both figures stay traceable. Use when identified peaks must become defensible concentrations feeding the toxicity and acceptance steps, and a below-limit result has to be reported as below-limit, not as zero. Trigger: ecss, q-st-70-29, offgassing-concentration-determination, offgassing-calibration-bracket, offgassing-blank-subtraction, offgassing-recovery-correction, offgassing-limit-of-quantitation, offgassing-mass-normalisation, crew-compartment-offgassing."
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
  tags: [ecss, q-st-70-materials-scope, q7029-concentration-determination, offgassing-concentration-determination, offgassing-calibration-bracket, offgassing-blank-subtraction, offgassing-recovery-correction, offgassing-limit-of-quantitation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Offgassing — Concentration Determination (space-systems/ecss/q7029-concentration-determination)

Use when the task is the quantification step of ECSS-Q-ST-70-29: turning the
integrated response of an identified offgassing product into a concentration
that is traceable to the mass of material tested and to the volume it offgassed
into, so that the toxicity and acceptance steps downstream have a number they
can stand behind.

## Domain quick reference

- The measured quantity is response, not mass. A calibration series relates
  injected mass to area for one compound on one instrument configuration, and
  a response outside the span of that series has no calibrated meaning. The
  correct answer there is to refuse and re-calibrate, not to run the straight
  line out past its last point.
- The system contributes its own peaks. A blank run through the same vessel,
  sorbent and instrument gives the background that is subtracted before the
  calibration is applied. A sample area at or below its blank is not a
  negative mass; it is a non-detection, and it is reported as one.
- Collection is not complete. The recovery fraction of the sampling and
  desorption train is measured on a spike and divides the recovered mass to
  give the mass actually released. A recovery that is not in the open interval
  between zero and one is an input error.
- Two normalisations are reported and they answer different questions. Mass
  per gram of sample characterises the material; mass per unit vessel volume
  is the airborne concentration the toxicity step scales from. Reporting one
  and calling it the other is the most common transcription error in the
  chain.
- A result between detection and quantitation limits is real but not
  quantifiable. It carries the limit-of-quantitation value with a
  below-quantitation marker so the acceptance step can treat it conservatively
  instead of silently reading it as zero.

## Workflow

1. Validate the run conditions: positive sample mass, positive vessel volume,
   positive conditioning duration, and a recovery fraction inside its open
   interval.
2. Validate the calibration series for the compound: at least two points,
   strictly increasing in injected mass and in area, all positive.
3. Subtract the blank area from the sample area. A non-positive difference
   ends in a non-detection record, not in a negative concentration.
4. Convert the corrected area to mass by interpolating between the bracketing
   calibration points; refuse a corrected area outside the calibrated span.
5. Divide by the recovery fraction to recover the released mass.
6. Compare the released mass with the limit of quantitation and with the limit
   of detection, tagging the record quantified, below-quantitation or
   non-detected. A mass sitting exactly on a limit counts as meeting it, with
   representation error absorbed by a named tolerance.
7. Normalise to micrograms per gram of sample and to milligrams per cubic
   metre of vessel volume, and carry both into the record.
8. Aggregate the per-compound records into a total released mass and report
   every finding: uncalibrated response, non-detection, below-quantitation.

## Pitfalls

- Extrapolating the calibration to keep an over-range peak in the table. The
  response is not linear past its last calibrated point; the result is a
  number with no traceability.
- Recording a below-quantitation result as zero. Zero is a measurement claim;
  the honest record is the quantitation limit with its marker, and the
  acceptance step is entitled to treat it as present.
- Subtracting the blank after the calibration instead of before it. The
  calibration is not linear through the origin in general, so the order of the
  two operations changes the answer.
- Applying a recovery correction twice — once in the instrument software and
  again in the report. The corrected and uncorrected masses must be separately
  named in the record so the double division cannot happen silently.
- Dividing by the wrong normaliser. Per-gram and per-volume figures differ by
  orders of magnitude; the record must carry both with their units rather than
  one bare number.

## Behavior contract (gate 3)

The run validation, calibration bracketing, blank subtraction, recovery
correction, quantitation-limit tagging, dual normalisation and aggregation are
exercised by the gate 3 contract test:
scripts/test_q7029_concentration_determination.py against
scripts/q7029_concentration_determination_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7029_concentration_determination.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

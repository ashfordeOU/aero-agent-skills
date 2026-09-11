---
name: e1002-inspection-report
description: "Use when produce or audit an inspection report against the ECSS-E-ST-10-02 clause 5.3.2.4 and Annex E Document Requirements Definition: judge each variable characteristic against its own tolerance band with the limits included, take an attribute characteristic's recorded result, confirm the measuring equipment held a calibration valid on the day the measurement was taken, confirm the inspector appears on the qualified roster, and separate characteristics never inspected from those inspected and found out of tolerance. Trigger: ecss, e-st-10-02c, inspection-report, annex-e-drd, tolerance-band, calibration-validity, inspector-qualification, conformity."
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
  tags: [ecss, e-st-10-02c, inspection-report, annex-e-drd, tolerance-band, calibration-validity, conformity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Inspection Report DRD (space-systems/ecss/e1002-inspection-report)

Use when the verification method is inspection under ECSS-E-ST-10-02
clause 5.3.2.4 and Annex E -- a measurement or observation made on the
actual article, whose worth depends on the instrument, the inspector and
the tolerance it was judged against.

## Domain quick reference

- Calibration is checked against the day the measurement was taken, not
  against today. An instrument recalibrated last week says nothing about
  a reading it produced after its previous certificate lapsed, and a
  present-tense calibration check silently accepts exactly that.
- Calibration expiring *on* the inspection day still covers it. The
  certificate is valid through its due date.
- Equipment with no calibration date on record is treated as invalid,
  not as unknown. An unverifiable instrument cannot support a
  measurement.
- Tolerances are magnitudes. A negative tolerance is an input error, not
  a reversed band -- reversing it silently would invert the conformity
  test and pass every out-of-tolerance part.
- A value exactly on a limit conforms. The tolerance band is the
  requirement itself, not an open interval, and treating limits as
  exclusive rejects parts that meet the drawing.
- Variable and attribute characteristics are judged differently: the
  first against its band, the second by its recorded observation. An
  attribute characteristic needs no measuring equipment, so the
  equipment check does not apply to it.
- A characteristic with no reading is *not inspected*, which is distinct
  from inspected and nonconforming. One is missing work, the other is a
  known defect, and they are closed differently.
- Inspector qualification is checked against the roster, not asserted in
  the report.
- A lapsed calibration invalidates a conforming result just as much as a
  nonconforming one -- the reading itself is not trustworthy.

## Workflow

1. Confirm the report names the article and the inspection day.
2. Check the inspector against the qualified roster.
3. For each variable characteristic, confirm measuring equipment is
   declared and its calibration covered the inspection day.
4. Judge each variable characteristic against its tolerance band, and
   take each attribute characteristic's recorded result.
5. Partition characteristics into conforming, nonconforming and not
   inspected, rejecting duplicate identifiers.
6. The inspection is acceptable only when everything was inspected,
   everything conforms, and no equipment or inspector finding stands.

## Pitfalls

- Checking that an instrument is "in calibration" at audit time rather
  than at measurement time, which accepts every reading taken while it
  was lapsed.
- Treating tolerance limits as exclusive, rejecting parts that are
  exactly on the drawing limit.
- Accepting a negative tolerance and silently building a reversed band.
- Filing an uninspected characteristic with the nonconforming ones, or
  worse with the conforming ones by defaulting a blank reading.
- Applying the measuring-equipment check to attribute characteristics
  and generating findings against visual inspections that need none.
- Accepting a conforming measurement from a lapsed instrument because
  the part passed anyway. The number is not evidence.

## Behavior contract (gate 3)

The tolerance-band, limit-inclusive conformity, calibration-validity,
equipment, inspector-qualification and partition logic is exercised by
the gate 3 contract test: scripts/test_e1002_inspection_report.py
against scripts/e1002_inspection_report_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e1002_inspection_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

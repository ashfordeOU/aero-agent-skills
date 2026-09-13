---
name: e2001-measurement-facility-calibration
description: "Use when verify that a secondary-emission measurement-facility holds valid calibration under ECSS-E-ST-20-01C clause 9.5.2: check every instrumented channel -- beam-current, collector-current, beam-energy, base-pressure, sample-temperature -- was calibrated before the run and still inside its validity interval, confirm each calibration is traceable to a recognized reference-standard, compare pre-run against post-run check readings for instrument-drift beyond the stated tolerance, combine the per-channel uncertainty contributions by root-sum-square into a combined-standard-uncertainty and expand it with a declared coverage-factor, and confirm the calibration-record actually reached the customer with recipient, issue date and covered channels. Trigger: ecss, e-st-20-01c, measurement-facility-calibration, calibration-validity-interval, metrological-traceability, instrument-drift-check, calibration-record-delivery."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-measurement-facility-calibration, measurement-facility-calibration, calibration-validity-interval, metrological-traceability, instrument-drift-check, calibration-record-delivery]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Measurement-Facility Calibration (space-systems/ecss/e2001-measurement-facility-calibration)

Use when the task is the clause 9.5.2 obligation of ECSS-E-ST-20-01C:
establishing that the facility used for a secondary-electron-emission
yield measurement was calibrated, that the calibration was still in
force when the run happened, and that the calibration results were put
in the customer's hands rather than filed in the laboratory.

## Domain quick reference

- Clause 9.5.2 carries two coupled duties. The first is metrological:
  the measurement-facility is calibrated, and the calibration is real
  -- dated, traceable, and still inside its validity interval on the
  day of the run. The second is contractual: the calibration results
  are made available to the customer. A facility can satisfy the first
  and fail the second, and the clause is then unmet.
- Five channels carry the emission-yield result and are therefore
  required: beam-current, collector-current, beam-energy,
  base-pressure and sample-temperature. Further channels (chamber
  residual-gas composition, stage position) are supplementary --
  recorded, never counted as required. A channel name that matches
  neither list is uncategorized and never discharges a required
  channel.
- Validity is an interval, not a date. A channel calibrated on day D
  with an interval of N days is in force for measurements on days D
  through D+N inclusive; a run on D+N+1 is out of calibration, and a
  run before D means the certificate postdates the data it is meant to
  underwrite, which is an error rather than a finding.
- Traceability is the property that links a facility reading to a
  recognized reference-standard through an unbroken chain. This leaf
  accepts a declared chain to a national-metrology-institute, an
  accredited-calibration-laboratory, or a certified transfer-standard.
  A channel calibrated against an in-house instrument with no declared
  chain is untraceable, whatever its paperwork says.
- Instrument-drift is checked by reading a stable reference before and
  after the run. The relative drift is the change divided by the
  pre-run reading, in percent, against a per-channel tolerance. A
  pre-run reading of zero makes the relative drift undefined and is
  rejected rather than divided through.
- The uncertainty budget combines independent per-channel standard
  contributions by root-sum-square into a combined-standard-
  uncertainty, then multiplies by a declared coverage-factor to report
  an expanded uncertainty. The coverage-factor must be stated and
  positive; reporting an expanded value without naming the factor
  makes the number uninterpretable.

## Workflow

1. Categorize every declared channel as required, supplementary or
   uncategorized, and reject a channel entry that is not a mapping or
   carries no name.
2. For each channel, parse the calibration date and the measurement
   date, reject a calibration dated after the run, and place the run
   inside or outside the validity interval (inclusive at both ends).
3. Confirm each channel's declared traceability chain resolves to a
   recognized reference-standard; flag any channel whose chain is
   absent or unrecognized.
4. Where pre-run and post-run check readings exist, compute the
   relative instrument-drift and compare it with the channel
   tolerance, absorbing representation residue in the comparison so a
   drift sitting exactly on the tolerance is not failed by rounding.
5. Combine the per-channel standard uncertainty contributions by
   root-sum-square, compare the combined value with the facility
   budget under the same tolerance discipline, and expand it with the
   declared coverage-factor.
6. Check the delivery record: a named recipient, an issue date not
   earlier than the latest calibration date, and coverage of every
   required channel. Aggregate the metrological and delivery findings
   -- the clause is met only when both lists are empty and no required
   channel is missing.

## Pitfalls

- Reading "calibrated" as a boolean. A certificate with no date, no
  interval or no traceability chain establishes nothing; the audit is
  of the three attributes together, not of the word.
- Failing a run that falls exactly on the last day of the validity
  interval. The interval is inclusive; an off-by-one here rejects
  perfectly valid data and invites the laboratory to widen intervals
  to compensate.
- Summing uncertainty contributions arithmetically. Independent
  contributions combine in quadrature; a linear sum overstates the
  combined-standard-uncertainty and can push a compliant facility over
  its budget for no physical reason.
- Comparing a root-sum-square against its budget with a bare
  inequality. A quadrature sum of exactly-budgeted contributions lands
  a few units in the last place above the budget; absorb that in the
  comparison, never by raising the budget.
- Treating an internal file copy as availability to the customer.
  Clause 9.5.2 is discharged by delivery -- recipient, date, and the
  channels covered -- not by the existence of a certificate somewhere
  in the facility's archive.
- Letting a supplementary channel stand in for a required one. A
  well-calibrated residual-gas channel does not compensate for an
  uncalibrated collector-current channel.

## Behavior contract (gate 3)

The channel categorization, validity-interval placement, traceability
check, drift computation, uncertainty combination and delivery check
are exercised by the gate 3 contract test:
`scripts/test_e2001_measurement_facility_calibration.py` against
`scripts/e2001_measurement_facility_calibration_logic.py`
(stdlib unittest, offline). Run:
python3 scripts/test_e2001_measurement_facility_calibration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

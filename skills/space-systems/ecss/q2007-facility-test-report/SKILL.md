---
name: q2007-facility-test-report
description: "Produce the facility test report for one campaign under ECSS-Q-ST-20-07C clause 5.7.4.1: assemble the record of which facility, which configuration and which conditions the run was actually carried out under, confirm every mandatory section is present, identify each configuration item by its own reference, find the stretches of the campaign window the condition log left uncovered, and flag any instrument whose calibration expired before the campaign ended. Use when a facility record is being written after a run or audited for whether it can support the results. Returns the coverage fraction, the gaps and a complete-or-incomplete verdict. Trigger: ecss, q-st-20-07c-clause-5-7-4-1, facility-test-report-record, facility-configuration-item-identification, campaign-condition-log-coverage, instrument-calibration-validity-window."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-facility-test-report, facility-test-report-record, facility-configuration-item-identification, campaign-condition-log-coverage, instrument-calibration-validity-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres -- Facility Test Report (space-systems/ecss/q2007-facility-test-report)

Use when the task is the facility-report clause of ECSS-Q-ST-20-07C
clause 5.7.4.1 -- the record a test centre keeps of the facility side of
a campaign: which installation, in which configuration, holding which
conditions, measured by which instruments, for the whole time the
specimen was in it.

## Domain quick reference

- The facility report answers a different question from the test
  report. The test report says what the specimen did; the facility
  report says what the specimen was subjected to and on what evidence.
  Without the second, the first is an assertion.
- Configuration items are identified individually or not at all. A
  chamber named by type, a fixture named by drawing with no issue, or a
  pump with no serial cannot be traced back to a maintenance record, so
  the identification has to carry the item's own reference.
- A condition log is judged on coverage, not on sample count. Ten
  thousand samples in the first hour of a six-hour campaign leave five
  hours unevidenced; the question is always the longest unsampled
  stretch against the interval the record is supposed to keep.
- Coverage has three kinds of gap and they are easy to conflate: a late
  first sample after the campaign opened, a long stretch between two
  samples, and a last sample that stops before the campaign closed. All
  three leave the same hole in the evidence.
- Calibration validity is judged against the campaign, not against the
  day the report is written. An instrument whose certificate expired
  partway through the run produced valid readings up to that point and
  unsupported ones afterwards, so the expiry date belongs in the
  comparison alongside the campaign end.
- Completeness is mechanical and should be reported as such. A missing
  section, an unidentified item, an uncovered stretch and a lapsed
  certificate each have an owner and a fix, so listing them beats a
  single adjective about report quality.

## Workflow

1. Validate the campaign window: a start, an end that genuinely follows
   it, and a maximum sampling interval greater than zero.
2. List the mandatory report sections that are absent or present but
   empty.
3. Validate the configuration items: each carries an identifier and a
   configuration reference, and no identifier appears twice.
4. Order the condition samples by time, refuse a sample outside the
   campaign window, and walk the window from its start to its end
   collecting every stretch longer than the maximum interval, including
   the leading and trailing stretches.
5. Compute the covered fraction of the window by crediting each sample
   with at most one maximum interval of evidence.
6. Compare each instrument's calibration expiry against the campaign
   end and report the ones that lapsed inside the run.
7. Aggregate the sections, items, gaps and calibration findings into a
   complete-or-incomplete verdict.

## Pitfalls

- Reporting sample count as coverage. Density in one part of the window
  says nothing about the rest, and a high count is the usual way an
  uncovered stretch goes unnoticed.
- Skipping the leading and trailing stretches. The first sample after
  the specimen went in, and the last before it came out, bound the
  evidence, and the uncovered ends are where the transitions live.
- Identifying a fixture by drawing number without an issue or revision.
  The drawing names a family; the issue names the object that was in the
  facility that week.
- Judging calibration at report-writing time. A certificate valid today
  can have expired mid-campaign, which invalidates part of the run and
  not the whole of it.
- Treating a sample exactly one interval after the previous one as a
  gap. That is the interval being met; the comparison absorbs float
  representation error rather than tightening the requirement.

## Behavior contract (gate 3)

The campaign validation, mandatory-section list, configuration-item
validation, condition-log gap walk, coverage fraction, calibration
comparison and the complete-or-incomplete verdict are exercised by the
gate 3 contract test: scripts/test_q2007_facility_test_report.py against
scripts/q2007_facility_test_report_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q2007_facility_test_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

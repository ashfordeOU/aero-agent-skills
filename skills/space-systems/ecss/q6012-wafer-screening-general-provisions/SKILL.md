---
name: q6012-wafer-screening-general-provisions
description: "Assess a wafer level screening campaign against the baseline provisions of ECSS-Q-ST-60-12C clause 10.2.1: lot coverage read in both directions, declared stress conditions against the agreed floor, and the record every screened wafer has to carry. Use when a die procurement must show that no wafer of the lot sat outside the campaign, that soak temperature and duration were declared rather than implied, and that the measured results are retained and traceable for the agreed period. Reports an uncovered wafer and an out-of-lot record separately, because the two have different remedies. Trigger: ecss, q-st-60-12c-clause-10-2-1, wafer-level-screening-baseline, wafer-lot-screening-coverage, screening-condition-declaration, wafer-screening-record-retention, wafer-lot-traceability-break."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-wafer-screening-general-provisions, q-st-60-12c-clause-10-2-1, wafer-level-screening-baseline, wafer-lot-screening-coverage, screening-condition-declaration, wafer-screening-record-retention, wafer-lot-traceability-break]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Wafer Level Screening — General Provisions (space-systems/ecss/q6012-wafer-screening-general-provisions)

Use when the task is the baseline of ECSS-Q-ST-60-12C clause 10.2.1: the
conditions a wafer level screening campaign runs under, the wafers it has
to reach, and the records it leaves behind once the wafers have moved on.

## Domain quick reference

- Screening is a campaign over a lot, not a test on a sample. The unit of
  coverage is the wafer, and a lot is covered only when every wafer of it
  sits inside the campaign. A wafer screened by reputation because its
  neighbours passed is the defect the provision exists to stop.
- Coverage has to be read in both directions, and the two gaps are not the
  same finding. A lot wafer no record covers is an unscreened wafer that
  will ship anyway; a record naming a wafer the lot never contained is a
  traceability break in the paperwork. One is fixed by screening, the other
  by correcting the identification, and merging them hides which.
- Conditions are owed as declarations, not as defaults. Soak temperature,
  soak duration, the bias applied during the stress and the temperature the
  measurements are taken at are each stated; an undeclared condition is a
  finding in its own right, separate from a condition that is declared and
  too low.
- A condition written to sit exactly on the agreed minimum is compliant. It
  is a common way to specify a soak, so the comparison carries a relative
  tolerance and the verdict does not turn on which machine evaluated it.
- Records outlive the campaign and that is their purpose. Who ran the
  screen, on what equipment, when, and where the measured data now lives
  are what let a failure two years downstream be traced to the wafer it
  came from. A retention period shorter than agreed quietly removes that.
- The three parts fail independently. A campaign can cover the whole lot at
  correct conditions and keep records for two of the ten years owed, and
  the disposition has to name which part is short rather than reduce the
  campaign to a single pass or fail.

## Workflow

1. State the lot as its wafer identifiers and the campaign as the wafers it
   reports. Refuse a repeated identifier as an input defect: collapsing it
   makes a lot with a duplicate look fully covered.
2. Difference the two sets both ways. Report the lot wafers outside the
   campaign in lot order, and the reported wafers outside the lot
   separately, and carry the coverage fraction alongside them.
3. Check each baseline condition is declared at all before checking its
   value, so an absent bias statement is not read as a satisfied one.
4. Compare the declared soak temperature and duration against the agreed
   floor with a relative tolerance, so a soak specified at the minimum is
   accepted everywhere it is run.
5. Walk each screened wafer's record for the fields that make it traceable,
   treating a blank string as absent rather than as a value.
6. Compare the retention period held against the period owed and report the
   years still outstanding, not merely that it is short.
7. Close with a disposition that ranks the findings: a condition defect is
   non-compliant screening, while coverage, record and retention gaps leave
   an incomplete campaign that can still be finished.

## Pitfalls

- Treating a sampled wafer set as lot coverage. Screening is applied per
  wafer, and a lot that reports four screened wafers out of six is two
  wafers short however good those four look.
- Reporting only the wafers that are missing. A record naming a wafer from
  another lot is the more dangerous of the two gaps, because it makes the
  coverage count look right.
- Reading an absent condition as a nominal one. An undeclared bias is not a
  zero bias, and assuming it turns a missing declaration into an invented
  measurement.
- Deciding a soak at the agreed minimum with a bare inequality. Two
  arithmetically identical campaigns then disagree across build hosts, and
  the one that fails is the one that was specified most precisely.
- Accepting a record that exists but names nothing. A blank operator or an
  empty data reference satisfies a key check and defeats the traceability
  the record was kept for.
- Collapsing the disposition to pass or fail. A complete campaign with a
  short retention period needs an archive decision, not a re-screen, and a
  single verdict sends it to the wrong place.

## Behavior contract (gate 3)

Identifier, temperature, duration and retention validation, the duplicate
wafer refusal, both directions of the coverage difference, the coverage
fraction, condition declaration and floor comparison at the exact bound,
record field completeness, the retention shortfall and the ranked
disposition are exercised by the gate 3 contract test:
scripts/test_q6012_wafer_screening_general_provisions.py against
scripts/q6012_wafer_screening_general_provisions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_wafer_screening_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

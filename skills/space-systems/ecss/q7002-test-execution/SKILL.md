---
name: q7002-test-execution
description: "Analyze the run log of a thermal-vacuum outgassing exposure. Use when a soak has finished under ECSS-Q-ST-70-02C and the question is how much of it counts: check that pump-down, heating, stabilisation, soak and cool-down were stamped in the only order they can occur in, credit an interval only when the samples at both ends had specimen temperature, collector temperature and chamber pressure inside their limits together, gather the failing stretches into excursions with their causes, and report qualified soak time beside wall-clock elapsed time. Trigger: ecss, q-st-70-02c, outgassing-exposure-execution, outgassing-qualified-soak-time, outgassing-run-log-excursion, outgassing-exposure-phase-order, outgassing-collector-temperature-hold, outgassing-chamber-pressure-hold."
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
  tags: [ecss, q-st-70-02-outgassing-scope, q7002-test-execution, outgassing-qualified-soak-time, outgassing-run-log-excursion, outgassing-exposure-phase-order, outgassing-collector-temperature-hold, outgassing-chamber-pressure-hold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening -- Exposure Execution (space-systems/ecss/q7002-test-execution)

Use when the task is the exposure step of a thermal-vacuum outgassing
screening under ECSS-Q-ST-70-02C: the specimens have been heated under vacuum
against cooled collectors, the run log has been downloaded, and the question
is how much qualified soak time the run delivered and what has to be reported
about the way it delivered it.

## Domain quick reference

- Soak time is a conjunction. It accrues only while specimen temperature,
  collector temperature and chamber pressure are all inside their limits at
  the same moment; two of three is not a partial credit, it is a gap.
- Crediting an interval needs both of its ends. A dropout between two samples
  is not interpolated away: the interval before and the interval after the
  failing sample both stop counting, which is the conservative and
  reproducible reading of the same log.
- Wall-clock elapsed time and qualified soak time are different quantities. A
  run that sat in the chamber for twenty-six hours and qualified for sixteen
  delivered sixteen, and reporting the twenty-six is how a short soak survives
  review.
- A stretch of failing samples is one event. It has a start, an end and the
  set of reasons it failed, and the longest such event is the first thing a
  reviewer asks about; a finding per sample buries that.
- The phases occur in one order. Stamps that do not increase through
  pump-down, heating, stabilisation, soak start, soak end and cool-down
  describe a run nobody can reconstruct, whatever the channels say.

## Workflow

1. Validate the run log: every sample carries a time and three channels, the
   pressure is positive, and the time stamps strictly increase.
2. Test each sample against the three limits and keep the reasons it failed
   rather than a single boolean, so the cause survives into the report.
3. Walk the intervals and credit one only when the samples at both ends
   qualified, summing the credited intervals into the qualified soak time.
4. Group consecutive failing samples into excursions, merging their causes,
   and close a stretch that runs to the end of the log.
5. Compare the qualified soak time with the required duration, absorbing an
   exact equality as representation error rather than by rounding the
   requirement.
6. Report the qualified time, the elapsed time, every excursion with its
   causes and the longest one, and check the phase stamps when they are given.

## Pitfalls

- Reporting elapsed time as soak time. They agree only on a run with no
  excursion at all, which is exactly the run where the distinction is free.
- Interpolating across a dropout. Nothing is known about the interval a
  failed sample sits in, and crediting half of it is an invention that always
  favours the run.
- Raising one finding per failing sample. A four-hour excursion sampled every
  minute becomes two hundred findings and the reviewer stops reading.
- Dropping the cause when the sample recovers. A soak lost to pressure and a
  soak lost to collector control call for different corrective action.
- Reading the phase stamps as paperwork. An out-of-order stamp usually means
  the soak clock started before the chamber was stable, and the qualified time
  is then being measured against the wrong window.

## Behavior contract (gate 3)

The run-log validation, per-sample limit test, interval crediting, excursion
grouping, longest-excursion reporting, phase-order check and the delivered
soak verdict are exercised by the gate 3 contract test:
scripts/test_q7002_test_execution.py against
scripts/q7002_test_execution_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7002_test_execution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

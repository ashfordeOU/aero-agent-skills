---
name: e2007-radiated-electric-emission-reporting
description: "Audit the radiated electric emission report package of ECSS-E-ST-20-07C clause 5.4.6.5, where the recorded levels must travel with a statement of measuring-antenna electrical continuity. Use when an emission report is assembled or reviewed: name every antenna the data was taken through, find the ones no statement covers, group each statement as continuous, marginal or open against its resistance allowance, reject statements taken outside the run window they are offered as support for, resolve duplicate statements to the worst case, and compute the margin of every recorded level against its limit. Trigger: ecss, e-st-20-07c, radiated-electric-emission-reporting, antenna-electrical-continuity-statement, emission-report-package-completeness, radiated-emission-margin-record, emission-antenna-continuity-resistance."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-electric-emission-reporting, antenna-electrical-continuity-statement, emission-report-package-completeness, radiated-emission-margin-record, emission-antenna-continuity-resistance, emission-statement-run-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Electric Emission Reporting (space-systems/ecss/e2007-radiated-electric-emission-reporting)

Use when the task is the reporting requirement of ECSS-E-ST-20-07C
clause 5.4.6.5 -- delivering recorded radiated electric field levels
together with a statement that the measuring antenna was electrically
continuous, so the reader knows a quiet trace means a quiet unit
rather than a disconnected antenna.

## Domain quick reference

- The clause exists because the two most common ways to record a
  clean radiated emission trace are a clean unit and a broken
  measurement path. A cracked antenna element, a connector backshell
  that lost its bond, a coaxial braid opened at a strain relief --
  each of them reads as compliance. The continuity statement is what
  separates the two, which is why it is required alongside the data
  rather than filed somewhere else.
- Coverage is per antenna, not per report. A campaign that swaps a
  biconical for a horn partway up the band has two measurement paths
  and needs two statements; one statement and two antennas leaves half
  the data unsupported, and the half is usually the high band where
  the swap happened.
- A statement has to belong to the run. Continuity measured at
  incoming inspection says the antenna was sound in the store, not
  that it was sound after being carried into the chamber and mated.
  A statement whose timestamp falls outside the run window is
  therefore not support; it is a different measurement of the same
  part.
- Resistance groups three ways, not two. Comfortably under the
  allowance is continuous; closed but sitting on the allowance is
  marginal and worth a note, because that is the value that drifts
  into an open path over a campaign; above the allowance is open and
  the data behind it cannot be reported.
- Two statements for one antenna are not a contradiction to resolve by
  choosing. The worst-case value governs, and the fact that there were
  two is itself worth recording.
- A two-wire continuity measurement carries its own lead resistance
  into the number. At the fractions of an ohm this clause cares about
  that is a real share of the reading, so the method belongs in the
  statement and a two-wire result is a limitation on it.
- Exceedances are the unit's problem, not the report's. A level over
  its limit is recorded and carried; it does not stop the package from
  being a complete and deliverable package.

## Workflow

1. Validate the recorded levels: positive frequency, a level and a
   limit, a named antenna and a recognized polarization.
2. Validate the continuity statements: a named antenna, a
   non-negative resistance, a measurement time, a recognized method
   and a signatory.
3. List the antennas the data was taken through and subtract the
   antennas that carry a statement, to name what is unsupported.
4. Group each governing statement as continuous, marginal or open
   against the resistance allowance.
5. Reject statements whose measurement time falls outside the run
   window, and resolve duplicate statements to the worst case.
6. Compute the margin of every recorded level against its limit and
   collect the exceedances and the worst margin.
7. Aggregate: a missing statement, an open path or a statement outside
   the run are findings; a marginal resistance, a two-wire method,
   duplicate statements and an exceedance are limitations.

## Pitfalls

- Filing the continuity result as a separate test record. It is
  evidence for these levels; separated from them, a later reader
  cannot tell which run it supports.
- Checking that a continuity statement exists and stopping there. An
  existing statement reading well above the allowance is worse than a
  missing one, because it looks like support.
- Matching statements to the report rather than to the antennas. One
  statement per report passes a presence check and still leaves every
  antenna after the first uncovered.
- Comparing a resistance against the allowance with a bare inequality.
  A value written as the allowance can land a few bits either side,
  and the verdict should not flip on that.
- Treating an over-limit level as a report defect. The package is
  complete; the unit is not compliant, and those are different
  findings addressed to different people.

## Behavior contract (gate 3)

The statement and record validation, continuity grouping, antenna
coverage subtraction, run-window currency, duplicate resolution to the
worst case, margin and exceedance computation, package grouping and
the aggregate verdict are exercised by the gate 3 contract test:
scripts/test_e2007_radiated_electric_emission_reporting.py against
scripts/e2007_radiated_electric_emission_reporting_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_radiated_electric_emission_reporting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

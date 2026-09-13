---
name: e2008-standard-test-environment-conditions
description: "Audit the ambient pressure, temperature and relative humidity a room held while solar-array hardware was inspected, tested or stored briefly under ECSS-E-ST-20-08C clause 4.3.1: take the band the declared activity owes, size every reading that leaves it per parameter and per bound, weight the out-of-band dwell by logged time instead of reading count, compute the room dew point and the margin the coldest hardware surface keeps above it, and settle on one of four verdicts - inside the band, accepted against a recorded excursion, rejected, or rejected for condensation risk, which outranks every excursion because a record does not dry a bond line. Use when handling, test or storage conditions for an array must be shown to have stayed in band. Trigger: ecss, e-st-20-electrical-scope, e-st-20-08c, solar-array-ambient-test-environment, solar-array-cleanroom-humidity-band, solar-array-handling-dew-point-margin, solar-array-short-term-storage-conditions, solar-array-environment-excursion-record."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-standard-test-environment-conditions, solar-array-ambient-test-environment, solar-array-cleanroom-humidity-band, solar-array-handling-dew-point-margin, solar-array-short-term-storage-conditions, solar-array-environment-excursion-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Array — Standard Test Environment Conditions (space-systems/ecss/e2008-standard-test-environment-conditions)

Use when the task is clause 4.3.1 of ECSS-E-ST-20-08C -- the ambient
pressure, temperature and relative-humidity band a room holds while
solar-array hardware is inspected, tested or kept for a short period,
in every case where the test itself does not call for its own
environment. The hardware that this band protects is the part of an
array that shows no mark when it is damaged: bare cell edges,
interconnect welds and adhesive bond lines.

## Domain quick reference

- Three parameters define the band: ambient pressure, room temperature
  and relative humidity. Inspection and testing hold the same band;
  short-term storage is allowed a cooler and drier room, because
  nobody is working in it and dryness is the cheaper risk.
- A reading sitting exactly on a bound is inside the band. Bounds are
  written as decimal literals and readings arrive from instruments
  that may have been converted between units, so the comparison
  absorbs the last-place difference rather than failing a compliant
  room on representation error.
- An excursion is sized per parameter and per bound, not counted. A
  room three points over the humidity ceiling and a room twenty points
  over are the same count and entirely different findings, and the
  bound that was crossed says which direction the facility has to
  move.
- Time matters as much as magnitude. Two readings out of four is not
  half the run if one lasted ten minutes and the other ninety, so the
  dwell outside the band is weighted by logged duration.
- Relative humidity alone does not decide condensation. What decides
  it is the dew point of the room against the coldest hardware
  surface, so a cold panel carried in from a thermal chamber can wet
  in a room whose humidity never left the band.
- A condensation risk is not an excursion to record. An excursion
  record closes a departure that did no harm; moisture that has
  already reached a bond line is not undone by documenting it, so that
  verdict outranks every other outcome.
- The recordable exceedance sizes and the allowed dwell are declared
  project policy rather than physical constants, so they are stated
  with the verdict and a project may substitute its own.

## Workflow

1. Name the activity -- inspection, testing or short-term storage --
   and take the band from it, or declare an explicit envelope where a
   test calls for its own. Reject an uncategorized activity instead of
   defaulting it to the strictest band.
2. Normalise the log. Each reading carries pressure, temperature,
   humidity and the duration it stood for; refuse a humidity above
   saturation or at zero, a temperature at absolute zero and a
   non-positive duration, since each of these silently distorts the
   dwell or the dew point.
3. Size every excursion by parameter and bound, and keep the largest
   seen on each parameter across the log rather than the last one.
4. Weight the time spent outside the band against the total logged
   time to get the dwell fraction.
5. Where a coldest hardware surface is known, compute the dew point at
   every reading and take the smallest margin the surface kept above
   it. Compare that against the declared condensation margin.
6. Settle the verdict in priority order: condensation risk first, then
   a clean run, then an excursion small enough and short enough to be
   closed by a record, then rejection -- and say which of the two
   limits, size or dwell, the rejection turned on.

## Pitfalls

- Judging condensation from relative humidity alone. The band can be
  held all day and a panel at fourteen degrees will still wet in a
  room at twenty-two and sixty percent; the comparison that matters is
  surface temperature against dew point.
- Averaging the log before testing it against the band. A mean
  humidity inside the band hides the hour that was not, and the mean
  of a compliant and a non-compliant hour is always compliant.
- Counting out-of-band readings instead of weighting their duration.
  An instrument that logs every minute during an excursion and every
  hour otherwise reports a dwell that is an artefact of the sampling
  rate.
- Recording an excursion that should have been a rejection. The record
  is only admissible while both limits hold -- the exceedance small
  enough and the dwell short enough -- and a record written over a
  large exceedance transfers the risk to the flight hardware without
  telling anyone.
- Failing a reading that sits exactly on a bound. The band is
  inclusive and a bound compared by bare arithmetic against a
  converted reading rejects a compliant room, which trains the
  facility to stop logging the marginal hours.
- Treating short-term storage as the handling band. The storage band
  is drier and cooler on purpose, and applying it to an inspection
  bench passes rooms that were never fit to work in.

## Behavior contract (gate 3)

The activity band selection, envelope and policy validation, reading
normalisation, per-parameter excursion sizing, time-weighted dwell,
Magnus dew point, condensation margin and the four-way verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_standard_test_environment_conditions.py against
scripts/e2008_standard_test_environment_conditions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_standard_test_environment_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

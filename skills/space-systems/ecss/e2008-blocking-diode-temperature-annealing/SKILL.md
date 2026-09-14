---
name: e2008-blocking-diode-temperature-annealing
description: "Verify that the thermal anneal of a blocking diode really sits between the first and the second post-irradiation electrical measurement under ECSS-E-ST-20-08C clause 12.6.12: hold the four events in order so the soak cannot merge with either reading, bound the wait between the exposure ending and the first reading so the part has not already recovered at ambient, check the dwell against its floor and the soak temperature against both its floor and the package rating, confirm the two readings share a temperature closely enough to subtract, and take the share of the shift the soak gave back. Use when an anneal between two post-irradiation readings is planned or audited. Trigger: ecss, e-st-20-08c-clause-12-6-12, blocking-diode-anneal-insertion-order, blocking-diode-post-irradiation-reading-pair, blocking-diode-soak-dwell-floor, blocking-diode-package-rating-ceiling, blocking-diode-reading-temperature-gap, blocking-diode-recovered-shift-share."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-blocking-diode-temperature-annealing, blocking-diode-anneal-insertion-order, blocking-diode-post-irradiation-reading-pair, blocking-diode-soak-dwell-floor, blocking-diode-package-rating-ceiling, blocking-diode-reading-temperature-gap, blocking-diode-recovered-shift-share]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Blocking Diode Temperature Annealing (space-systems/ecss/e2008-blocking-diode-temperature-annealing)

Use when the task is the clause 12.6.12 step of ECSS-E-ST-20-08C: a
blocking diode has come out of its electron exposure, and a thermal anneal
has to be placed between the first post-irradiation electrical measurement
and the second one.

## Domain quick reference

- The clause fixes a position in a sequence, not a number. The exposure
  ends, the part is measured, the part is soaked, the part is measured
  again. Almost everything that goes wrong with this step is a way of
  losing that ordering rather than a way of getting a temperature wrong.
- The order is what makes the second reading mean anything. The first
  reading catches the part at its worst, while the damage is fully
  present; the soak lets it recover whatever it will recover; the second
  reading is what the array will fly. Two readings on the same side of the
  soak give a number that looks like a recovery and is not one.
- A first reading taken long after the exposure has already let the part
  anneal at ambient. The shift it reports is then smaller than the exposure
  caused, and the soak looks less effective than it was. The wait is
  therefore bounded, and a late first reading closes the review rather than
  being noted and passed.
- The two readings have to share a temperature. A second reading taken
  warmer or cooler than the first is being differenced against a thermal
  coefficient as much as against a recovery, and the recovered share that
  falls out of it is not attributable to the soak.
- The soak still has to be a soak: hot enough and long enough to move
  anything, and below the rating of the package it is applied to. A profile
  that clears its dwell floor by running above the package rating has
  damaged the part it was meant to recover, so both bounds are held at
  once.
- The recovered share is the output worth keeping. One means the soak
  returned the characteristic to where it started, zero means it moved
  nothing, and a negative share means the part kept drifting through the
  soak. The last of those is a finding about the part, not an arithmetic
  error.
- Events that touch end to end are admitted. A soak beginning at the hour
  the first reading was taken has not merged with it, and the comparison
  tolerance exists to absorb representation error rather than to loosen the
  ordering.

## Workflow

1. Validate the declared anneal policy first: soak temperature floor,
   dwell floor, package rating ceiling, the largest admissible wait before
   the first reading, the reading temperature tolerance and the recovery
   share below which an advisory is raised. A soak floor above the package
   rating describes no profile and is refused rather than used.
2. Confirm the timeline carries all four events: an exposure end, a first
   measurement, a soak profile and a second measurement. A timeline missing
   any of them closes the review on sequence not established, because the
   anneal cannot be shown to sit anywhere.
3. Validate each measurement: the hour it was taken, the temperature it was
   taken at, and the forward drop and reverse leakage read from it. A soak
   whose end does not follow its start is refused as not a dwell.
4. Check the ordering and name every break, not the first: a first reading
   before the exposure ended, a soak beginning before the first reading, a
   second reading falling inside the soak.
5. Take the wait between the exposure ending and the first reading against
   its bound. Past the bound the review closes, because the part has
   already recovered at ambient and the comparison is no longer the one the
   clause asks for.
6. Hold the soak profile against all three of its bounds at once and name
   every one it misses.
7. Take the gap between the two reading temperatures against the tolerance,
   and close on reading conditions not comparable when the gap is too wide
   to subtract across.
8. Where a pre-exposure reading exists, take the share of the forward drop
   shift and of the leakage shift that the soak gave back, and raise an
   advisory when the forward share sits under the policy expectation.
   Advisories are reported with the verdict and do not move it.
9. Close on one verdict: anneal sequence not established, soak profile out
   of bounds, reading conditions not comparable, or anneal insertion
   accepted.

## Pitfalls

- Treating the soak as a free-standing test. It is an inserted step, and a
  soak run before the first measurement or after the campaign closed has
  satisfied a temperature profile while answering none of the question.
- Letting the first reading slip by days because the bench was busy. Room
  temperature anneals the part too, and the recovered share then
  understates what the soak did.
- Reading the second measurement warm because the part had just come out of
  the oven. The reading has to be taken back at the temperature the first
  one used, or the difference between them is partly a coefficient.
- Judging the soak on temperature alone. A hot, short dwell and a long,
  cool one both miss, and only holding both bounds catches the second.
- Reporting a recovered share without saying which characteristic it came
  from. Forward drop and reverse leakage recover at different rates, and a
  single unlabelled share hides which one was quoted.

## Behavior contract (gate 3)

The policy validation, the four-event completeness check, the ordering
breaks, the bounded wait before the first reading, the soak profile bounds
held together, the reading temperature gap against its tolerance, the
recovered shares, the small-recovery advisory and the closing verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_temperature_annealing.py against
scripts/e2008_blocking_diode_temperature_annealing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_blocking_diode_temperature_annealing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

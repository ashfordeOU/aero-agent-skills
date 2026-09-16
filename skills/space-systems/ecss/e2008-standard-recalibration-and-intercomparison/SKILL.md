---
name: e2008-standard-recalibration-and-intercomparison
description: "Use when a standard's recalibration or cross-comparison status gates an array measurement. Determine whether a solar-array reference standard is still fit under ECSS-E-ST-20-08C clause 10.2.5, where recalibration and cross comparison run at intervals agreed with the customer: count the days elapsed against each agreed interval, size the deviation a working standard shows against the primary, fit a drift rate across past cross comparisons, project the day that drift carries the deviation onto the agreed band edge, and rank the verdicts so a deviation outside the band outranks any amount of calendar validity. Trigger: ecss, e-st-20-electrical-scope, e-st-20-08c, solar-array-standard-recalibration-interval, standard-cell-intercomparison-deviation, primary-to-working-standard-drift-rate, customer-agreed-calibration-interval, standard-cell-band-edge-projection."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-standard-recalibration-and-intercomparison, solar-array-standard-recalibration-interval, standard-cell-intercomparison-deviation, primary-to-working-standard-drift-rate, customer-agreed-calibration-interval, standard-cell-band-edge-projection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Array — Standard Recalibration and Intercomparison (space-systems/ecss/e2008-standard-recalibration-and-intercomparison)

Use when the task is clause 10.2.5 of ECSS-E-ST-20-08C -- the periodic
recalibration of a solar-array standard and the cross comparison of the
standards against one another, both at intervals that the customer has
agreed rather than at intervals the laboratory finds convenient. A
standard cell never announces that it has moved: it goes on producing a
plausible current while its calibration drifts, and only a schedule
catches that.

## Domain quick reference

- Two controls, two different questions. A calendar says the standard
  is in date. A cross comparison says the standard still agrees with
  the one above it. Either can fail while the other passes, which is
  why the clause names both and why neither substitutes for the other.
- The interval is a contractual number, not a laboratory habit. The
  agreed value overrides any house default, and the default exists only
  so a case with nothing agreed still lands somewhere defensible.
- The cross comparison is a signed deviation, measured as the working
  standard against the primary, in percent of the primary. Sign is
  worth keeping: a working cell reading consistently low biases every
  array measurement in the same direction, and the sign is what reveals
  it.
- The agreed band is symmetric around the primary. A deviation inside
  the band closes the comparison; a deviation outside it invalidates
  measurements taken since the last comparison passed.
- A series of past comparisons is more than a pass record. Fitted
  against elapsed days it yields a drift rate, and the drift rate
  projects the day the deviation reaches the band edge. If that day
  falls before the next agreed activity, the interval is too long for
  this cell whatever the agreement says.
- Precedence matters and runs against intuition: an out-of-band
  deviation outranks every calendar state, because an in-date
  certificate does not make a drifted cell correct.
- A primary standard has nothing above it to be compared against. Its
  schedule rests on recalibration by the calibrating body, so a gap in
  its cross-comparison record is a different finding from the same gap
  on a working cell.

## Workflow

1. Declare the role of the standard and the intervals in force, taking
   a customer-agreed interval over the default wherever one is stated.
2. Place each day count inside its interval: in date, inside the
   warning fraction, or past the interval entirely. Report the days
   remaining as a signed number so an overdue case reads as overdue.
3. Where a comparison pair exists, compute the signed deviation of the
   working standard against the primary and grade it against the agreed
   band.
4. Where a comparison history exists, fit the drift rate per year by
   least squares, rejecting a history with fewer than two distinct
   days rather than fitting noise.
5. Project the day the drift reaches the band edge and compare it
   against the next agreed activity; flag the interval as too long when
   the edge arrives first.
6. Rank the findings into one verdict -- out of band, recalibration
   overdue, cross comparison overdue, due soon, or in date and
   consistent -- and state whether the standard may still serve a
   measurement.

## Pitfalls

- Reading an in-date certificate as agreement. The calendar records
  when the standard was last checked, not what it reads today; a cell
  can drift out of band in the first month of a two-year interval.
- Letting the laboratory's habitual interval stand in for the agreed
  one. The clause ties the period to the customer agreement, so a house
  default applied silently is an undeclared deviation from contract.
- Discarding the sign of the deviation. An unsigned magnitude hides a
  consistent bias, which is precisely the failure a cross comparison
  exists to expose.
- Treating a comparison history as a list of passes. The information is
  in the slope: a run of passes that each sit a little further out is a
  standard on its way out of band, and the schedule should shorten
  before the next comparison fails.
- Expecting a working-standard cross comparison to cover the primary.
  Nothing on the floor sits above the primary, so its interval is
  carried entirely by the external calibrating body.
- Comparing a deviation with the band by bare arithmetic. A deviation
  landing exactly on the band edge can fall a few units in the last
  place either side of it, so the comparison absorbs that
  representation error while the agreed band stays untouched.

## Behavior contract (gate 3)

The agreed-interval resolution, interval placement, signed deviation,
band grading, least-squares drift fit, band-edge projection and verdict
precedence are exercised by the gate 3 contract test:
scripts/test_e2008_standard_recalibration_and_intercomparison.py against
scripts/e2008_standard_recalibration_and_intercomparison_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2008_standard_recalibration_and_intercomparison.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2020-overcurrent-trip-off-timing
description: "Evaluate whether a limiter switches off inside its tabulated trip-time window, per ECSS-E-ST-20C clause 5.2.4.1.1. Use when measured or simulated switch-off times have to be judged against the whole table rather than one nominal delay: form the overcurrent ratio against the declared limit, bracket it between tabulated rows, interpolate the minimum and maximum permitted times, hold the last row past the end of the table, and categorize every event as too fast to ride a legitimate inrush, inside the window, too slow to protect the harness, or never opened at all. Trigger: ecss, e-st-20-electrical-scope, overcurrent-trip-off-timing, trip-time-band-interpolation, overcurrent-ratio-bracketing, minimum-trip-time-nuisance-trip, maximum-trip-time-harness-protection, limiter-switch-off-window."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-overcurrent-trip-off-timing, overcurrent-trip-off-timing, trip-time-band-interpolation, overcurrent-ratio-bracketing, minimum-trip-time-nuisance-trip, maximum-trip-time-harness-protection, limiter-switch-off-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Overcurrent Trip-Off Timing (space-systems/ecss/e2020-overcurrent-trip-off-timing)

Use when the task is the switch-off timing requirement of ECSS-E-ST-20C
clause 5.2.4.1.1 -- showing that once the load current passes the
limiter's declared limit, the limiter opens inside the window the
trip-time table fixes for that much overcurrent, rather than merely
opening eventually.

## Domain quick reference

- The requirement is a window with two edges, and both of them are
  requirements. A limiter slower than the tabulated maximum leaves the
  harness, the connector and the upstream source carrying fault current
  for longer than the design assumed. A limiter faster than the
  tabulated minimum opens on things that were never faults -- a
  capacitive inrush, a motor start, a transient the bus is built to
  absorb -- and sheds a healthy load while looking impressively quick
  on the bench.
- The table is indexed on a ratio, not on a current. The window follows
  the measured current divided by the declared limit, so a measurement
  quoted with no limit behind it cannot be placed in the table at all
  and the assessment closes there.
- Between tabulated rows the window is interpolated rather than rounded
  to the nearest row. Rounding down borrows a window the design was
  never granted; rounding up refuses one it was.
- Past the last tabulated row the window stops shrinking. The table
  ends, so the last row governs and the result says it was held there,
  because a fault far beyond the table is otherwise being judged
  against an extrapolation nobody tabulated.
- Below the first tabulated row no switch-off is demanded. A limiter
  that opens there is not failing on timing, but it is worth naming: it
  tripped where the table asked for nothing, and that is a selectivity
  question rather than a timing one.
- A table that reverses in ratio, or that grants a longer window at a
  harder overcurrent, is not a trip-time table. It is refused rather
  than interpolated, because either defect silently hands the worst
  fault the most generous window.
- Both edges are inclusive. A trip landing exactly on the minimum or
  exactly on the maximum meets the requirement, and the comparison
  tolerance exists to absorb representation error rather than to widen
  the window.

## Workflow

1. Read the trip-time table and check it is usable: at least two rows,
   ratios rising, every row a genuine window, and neither edge ever
   growing as the overcurrent hardens.
2. Read the declared current limit. Without it there is no ratio, so
   the assessment closes rather than assuming one.
3. For each observed or simulated event, form the overcurrent ratio and
   find the rows it falls between.
4. Interpolate the minimum and maximum permitted switch-off time at
   that ratio. Below the first row record that no switch-off was
   demanded; past the last row hold the final row and flag that it was
   held.
5. Categorize the event: never opened, opened before the minimum,
   inside the window, or opened after the maximum. Carry the relative
   distance to the edge it missed rather than a bare verdict.
6. Report the worst event by that relative distance, every finding, and
   the advisories for events that ran past the table or tripped below
   it.

## Pitfalls

- Testing the late edge only. A campaign that records nothing but
  "switched off within the maximum" has verified half the clause, and
  the half it skipped is the one that causes in-flight load drops.
- Judging a measurement against a single nominal delay. The delay
  belongs to one ratio; every other ratio has its own window, and a
  point compared with the wrong row can pass on paper while missing its
  own requirement.
- Rounding a ratio to the nearest tabulated row. The interpolated
  window is the requirement; rounding either direction changes the
  verdict for cases that sit between rows, which is most of them.
- Extrapolating the table past its last row. The trend keeps falling if
  the arithmetic is allowed to run, and the result is a demand no
  switch element can meet and nobody ever wrote down.
- Comparing the trip time with an interpolated edge by bare arithmetic.
  The edge comes out of a float interpolation, so a trip landing
  exactly on it can fall a few units in the last place outside; the
  comparison absorbs that representation error while the tabulated
  edges stay untouched.

## Behavior contract (gate 3)

The table validation, ratio formation, row bracketing, window
interpolation, end-of-table clamping, event categorization and
worst-event report are exercised by the gate 3 contract test:
scripts/test_e2020_overcurrent_trip_off_timing.py against
scripts/e2020_overcurrent_trip_off_timing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_overcurrent_trip_off_timing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

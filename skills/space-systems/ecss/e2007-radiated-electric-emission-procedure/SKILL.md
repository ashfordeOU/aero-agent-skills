---
name: e2007-radiated-electric-emission-procedure
description: "Assess the radiated electric field emission measurement procedure of ECSS-E-ST-20-07C clause 5.4.6.4. Use when a radiated emission run is planned or graded: confirm the receiver completed its warm-up and settled before any level was believed, group that record as settled, under-warmed or drifting, compare each scanning increment against its measurement bandwidth so no frequency falls between cells, merge the steps per antenna polarization to expose sub-bands never recorded, flag steps begun before warm-up ended, and derive the point count and scan time the run needed. Trigger: ecss, e-st-20-07c, radiated-electric-emission-procedure, emission-receiver-warmup-period, radiated-emission-scan-step-size, radiated-emission-polarization-coverage, radiated-emission-scan-dwell."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-electric-emission-procedure, emission-receiver-warmup-period, radiated-emission-scan-step-size, radiated-emission-polarization-coverage, radiated-emission-scan-dwell, radiated-emission-unrecorded-sub-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Electric Emission Procedure (space-systems/ecss/e2007-radiated-electric-emission-procedure)

Use when the task is the procedure requirement of ECSS-E-ST-20-07C
clause 5.4.6.4 -- how a radiated electric field emission measurement
is actually carried out, from bringing the measuring chain up and
letting it settle through to the scanning steps that record the field
level across the declared band.

## Domain quick reference

- Warm-up is not a formality and it is not the same thing as
  stability. A receiver can sit powered for its full specified period
  and still be walking in amplitude, and it can be steady at a minute
  old and drift an hour later. The record therefore groups three ways
  -- settled, under-warmed, drifting -- because the repair differs:
  more time, or a chain that needs investigating.
- Time owed is worth naming as a number. "Not warmed up" tells the
  operator nothing; "600 s still owed" tells them whether to wait or
  to rebook the chamber.
- A level recorded before the chain settled is not a low level, it is
  an unknown level. That is why the offset of each scanning step from
  power-on is carried alongside the step: a step that began inside the
  warm-up window taints its own data regardless of how carefully the
  rest of the scan was run.
- The scanning increment and the measurement bandwidth are a pair. If
  the increment is wider than the bandwidth the receiver jumps past
  frequencies no measurement cell ever covered, and a narrowband
  emitter sitting between two steps is recorded as absent. An
  increment equal to the bandwidth just closes; anything wider skips.
- Coverage is per polarization, not per run. A radiated field couples
  differently into a horizontally and a vertically oriented antenna,
  so a band swept completely in one orientation and partially in the
  other has a hole, and merging every step together hides it. Merge
  within a polarization, then subtract from the declared band.
- Point count and scan time follow from the increment and the dwell,
  and they are the honest cost of the procedure. They belong in the
  report so a schedule argument is made against real numbers rather
  than against an optimistic sweep estimate.
- A dwell or a bandwidth that changes between steps is a limitation,
  not a defect. It makes the run harder to compare against another
  run; it does not lose a frequency.

## Workflow

1. Validate the warm-up record: a named instrument, a positive
   required period, a non-negative elapsed period and a non-negative
   drift.
2. Compute the warm-up shortfall and group the record as settled,
   under-warmed or drifting, with the shortfall outranking the drift.
3. Validate the scanning steps: positive edges, stop above start,
   positive increment, bandwidth and dwell, a non-negative offset from
   power-on, and a recognized polarization.
4. Compare each increment against its measurement bandwidth and flag
   any step that marches past unmeasured frequencies.
5. Merge the steps within each required polarization and subtract the
   union from the declared band to expose sub-bands never recorded.
6. Flag steps whose offset falls inside the warm-up window.
7. Derive the point count and the scan time from the increments and
   dwells, and aggregate: warm-up defects, absent polarizations,
   unrecorded sub-bands, coarse increments and early steps are
   findings; a non-uniform dwell or bandwidth is a limitation.

## Pitfalls

- Reading the warm-up clock and stopping there. Elapsed time answers
  one of the two questions the clause cares about; the amplitude the
  chain is holding answers the other.
- Merging every scanning step into one union. It reports a fully
  covered band from a set of steps that never recorded one
  polarization above a certain frequency.
- Choosing the increment from the span and a round point count. The
  bandwidth sets the largest increment that records everything; the
  span only sets how many of those increments are needed.
- Comparing step edges with a bare equality. Edges written by a
  controller can differ in the last bits, and a bare comparison turns
  a touching pair into a spurious gap.
- Treating a changed dwell as a rerun trigger. It costs comparability
  between steps; it never loses a frequency.

## Behavior contract (gate 3)

The warm-up record validation, shortfall and grouping, scanning-step
validation, increment-against-bandwidth check, per-polarization
coverage merge and unrecorded sub-band detection, early-step
detection, point count, scan duration and the aggregate verdict are
exercised by the gate 3 contract test:
scripts/test_e2007_radiated_electric_emission_procedure.py against
scripts/e2007_radiated_electric_emission_procedure_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_radiated_electric_emission_procedure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

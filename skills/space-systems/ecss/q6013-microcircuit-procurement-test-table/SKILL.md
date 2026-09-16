---
name: q6013-microcircuit-procurement-test-table
description: "Use when microcircuit procurement test results have to become a lot verdict. Evaluate a commercial microcircuit lot against its procurement test matrix under ECSS-Q-ST-60-13C Table 8-6: validate each row's method, sample size and accept number, hold a consuming row such as construction analysis to accept-on-zero, compute the burn-in percent defective allowable on the devices that entered burn-in after a bounded exclusion of handling damage, count parameter-drift rejects against their delta limits, require the electrical row to cover cold, room and hot, and hold a life test that stopped short of its declared duration. Trigger: ecss, q-st-60-13c-table-8-6, microcircuit-procurement-test-matrix, burn-in-percent-defective-allowable, microcircuit-parameter-drift-delta, electrical-temperature-point-coverage, life-test-duration-shortfall, microcircuit-destructive-row-accept-on-zero."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-microcircuit-procurement-test-table, q-st-60-13c-table-8-6, microcircuit-procurement-test-matrix, burn-in-percent-defective-allowable, microcircuit-parameter-drift-delta, electrical-temperature-point-coverage, life-test-duration-shortfall]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial Parts — Microcircuit Procurement Test Table (space-systems/ecss/q6013-microcircuit-procurement-test-table)

Use when the task is the microcircuit row of the procurement testing
provisions of ECSS-Q-ST-60-13C Table 8-6 — taking the test methods, sample
sizes and acceptance limits the table sets for a microcircuit family and
turning an executed campaign on one purchased lot into an accept-or-hold
verdict.

## Domain quick reference

- The burn-in rate is taken on the devices that entered burn-in, not on the
  devices that came out of it. A denominator built from survivors lets a lot
  improve its rate by failing more units, which inverts the whole point of
  the row.
- Excluding a failure as handling damage is admissible and bounded. A few
  mechanically damaged devices are credible; an exclusion carrying most of
  the failures is no longer a correction, it is the result, and it is
  reported for challenge instead of being absorbed silently.
- Parameter drift is a reject path of its own. A device whose delta between
  initial and post-stress readings exceeds the declared limit is a reject
  even when both readings sit inside the datasheet window, because a drifting
  commercial die is what the stress was applied to expose.
- The electrical row is three measurements, not one. Cold, room and hot each
  catch a different defect population, and a campaign that ran room only has
  not performed the row however many devices it measured.
- Life-test hours are the stress. A run stopped early is a different test,
  not a softer pass, so a shortfall holds the lot on its own and is reported
  in hours rather than as a generic failure.
- A row that consumes its devices is judged accept-on-zero. There is no rate
  to tolerate on a sample of four devices taken apart, so an accept number
  above zero on such a row is a specification error.

## Workflow

1. Validate each matrix row: a sample larger than the lot, a zero sample, an
   accept number above the sample or more failures than units sampled is an
   input error, not a degenerate case to clamp. Refuse a matrix that repeats
   a method, and refuse an accept number above zero on a consuming row.
2. Compute the burn-in rate on the entered population after subtracting the
   declared exclusions, refusing an exclusion count larger than the failures
   recorded and flagging one that runs past the cap.
3. Take the parameter-drift readings against the delta limit by magnitude, so
   a downward drift counts, and refuse a zero initial reading where relative
   drift is undefined.
4. Check the electrical row covered cold, room and hot, collapsing repeats and
   naming the missing points rather than reporting a bare shortfall.
5. Compare the life-test hours with the declared duration and the life-test
   failures with the accept number, absorbing floating-point representation
   error at the boundary with a named tolerance rather than by relaxing the
   duration.
6. Convert each row's failures into a percent defective, compare it with the
   allowance as well as the accept number, and report every rejecting row
   with a marginal-row advisory where an accepted row used up its allowance.

## Pitfalls

- Dividing burn-in failures by the surviving devices. The rate falls as the
  lot gets worse, and a bad build reports cleaner than a good one.
- Absorbing the handling-damage exclusions into the rate without reporting
  them. The verdict then rests on an attribution nobody reviewed.
- Judging drift on the end-point limits alone. A device inside its window
  that moved more than the declared delta is a reject, and reading only the
  final value loses that entirely.
- Accepting a room-temperature electrical run as the row. The cold and hot
  points are where the parametric failures live; sample size does not
  substitute for them.
- Widening a limit to pass an exact-equality case. An equality at the limit is
  a representation question handled by the tolerance inside the comparison;
  the declared limit stays as specified.

## Behavior contract (gate 3)

The row validation and accept-on-zero rule, the burn-in percent defective
allowable with its bounded exclusion, parameter-drift counting, temperature
point coverage, the life-test duration check and the overall accept-or-hold
disposition are exercised by the gate 3 contract test:
scripts/test_q6013_microcircuit_procurement_test_table.py against
scripts/q6013_microcircuit_procurement_test_table_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_microcircuit_procurement_test_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

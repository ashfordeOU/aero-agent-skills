---
name: test-point-matrix-design
description: "Design the flight test point matrix: expand the altitude, speed, and weight sweeps across the aircraft configurations into the full grid of test conditions, mark the repeat points for data quality, sequence the points so configuration changes and altitude hops are minimized for flight efficiency, and check the flown points against the steady state tolerance of each condition. Use when the task is building the test point matrix for a flight test program, laying out condition sweeps, choosing repeat points, or ordering the points for efficient flying. Trigger: test point matrix, condition sweep, altitude sweep, speed sweep, weight sweep, repeat point, steady state tolerance, test sequencing."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: planning
  tags: [test-point-matrix-design, condition-sweep, altitude-sweep, speed-sweep, weight-sweep, configuration-change, repeat-point, steady-state-tolerance, test-sequencing, flight-test-efficiency]
  version: 0.1.0
  author: Aero Agent Skills
---

# Test Point Matrix Design (flight-test-operations/planning/test-point-matrix-design)

Use when the task is designing the test point matrix for a flight test
program: expanding the condition sweeps into the full grid, marking the
repeat points, sequencing the points for efficiency, and checking the
steady state data quality at each point.

## Domain quick reference

- Condition sweeps: the test conditions vary along one axis at a time:
  the altitude levels, the speed levels, the weight levels, and the
  aircraft configuration (gear and flap setting). The matrix is the
  cartesian product of the sweep levels.
- Grid expansion: the full grid is built altitude-major, then speed,
  then weight, then configuration, so every combination of the sweep
  levels becomes a test point with a unique id.
- Repeat points: every N-th point in grid order is marked as a repeat
  and flown twice, to confirm that the data is repeatable and to catch
  outliers; a repeat is a data quality instrument, not a new condition.
- Sequencing: fly all points of one configuration before reconfiguring,
  and within a configuration sweep altitude once and then the speed
  levels, so configuration changes and altitude hops are minimized.
- Steady state check: a flown point counts as valid when the observed
  altitude, speed, and weight each sit inside the tolerance band around
  the planned condition; a point outside the band is invalid and must
  be reflown.

## Workflow

1. Collect the sweep levels: the altitude list, the speed list, the
   weight list, and the configuration list.
2. Expand the grid with build_test_matrix(altitudes, speeds, weights,
   configurations); review the point count before the program starts.
3. Mark the repeats with add_repeat_points(points, repeat_interval);
   use an interval of at least 2 so the repeats sample the grid.
4. Order the flying with sequence_for_efficiency(points) so each
   configuration is flown in one block and altitude is swept once.
5. After each flight, run steady_state_check(points, tolerances,
   observed) and refly every invalid point before closing the matrix.

## Pitfalls

- Expanding an empty sweep: every sweep list must be non-empty; a grid
  built from an empty list has no test points and is rejected.
- Negative or zero conditions: a negative altitude, a zero speed, or a
  zero weight is nonsense and is rejected by ValueError.
- Interval 1 repeats: every point becomes a repeat, which carries no
  information; the repeat interval must be at least 2.
- Sequencing by risk instead of configuration: the efficiency order
  groups by configuration first, then altitude, then speed; do not
  hand-shuffle the groups.
- A point missing from the observed record: steady_state_check rejects
  the run instead of silently counting the point as valid.
- A tolerance band of zero: an exact match is required, which no real
  flight can hold; use a small nonzero band.
- Sweeping two conditions at once: one axis changes per sweep so a
  deviation is traceable to one condition.

## Behavior contract (gate 3)

The grid expansion, repeat marking, efficiency sequencing, and steady
state check logic is exercised by the gate 3 contract test:
scripts/test_test_point_matrix_design.py against
scripts/test_point_matrix_design_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_test_point_matrix_design.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 set the flight
  test and certification context; the condition sweep, repeat point,
  sequencing, and steady state practice is common flight-test
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: flight-test-planning
description: "Use when you must plan a flight test program: order the test points with the build-up approach so risk increases step by step and every prerequisite is flown before the dependent point, check that the instrumentation covers the required sensors, and confirm the test matrix covers every test objective. Produces the risk-ordered flight sequence with missing prerequisites flagged, the missing instrumentation list with the completeness verdict, the uncovered objectives with the matrix verdict, and the go/no-go gate verdict that releases or blocks the flight. Trigger: build-up approach, test matrix, flight test planning, instrumentation completeness, go/no-go gate, prerequisites."
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
  tags: [flight-test-planning, build-up-approach, test-matrix, instrumentation, go-no-go, flight-test, safety-review, envelope-expansion, prerequisites, test-point, risk-ordered]
  version: 0.1.0
  author: Aero Agent Skills
---

# Flight Test Planning (flight-test-operations/planning/flight-test-planning)

Use when the task is planning a flight test program: build-up
ordering of the test points, test matrix construction and coverage,
instrumentation completeness, and the go/no-go gate before each
flight.

## Domain quick reference

- Build-up approach: order the test points from lowest to highest
  risk so the envelope is expanded step by step; a point may only be
  flown after its prerequisites, and a prerequisite that is not part
  of the point set must be flagged before the program starts.
- Test matrix: rows are test points, columns are test objectives; a
  point covers an objective when it exercises it. The matrix is
  complete when every objective has at least one covering point.
- Instrumentation completeness: compare the required sensor set
  against the installed set; every missing instrument blocks the
  affected test point.
- Go/no-go gate: weather, aircraft readiness, instrumentation, and
  the safety review must all pass; any single failed check forces
  NO-GO and names the blocker.

## Workflow

1. Collect the test points with their risk level and prerequisites.
2. Order them with build_up_order(test_points); review the flagged
   missing prerequisites before the program starts.
3. Assemble the required and installed instrumentation sets and check
   them with instrumentation_complete(required, provided).
4. Build the test matrix and check coverage with
   test_matrix_complete(points, objectives); add points until every
   objective is covered.
5. Before each flight, run the gate with
   go_no_gate(weather_ok, aircraft_ready, instrumentation_ok,
   safety_review_ok) and fly only on a GO verdict.

## Pitfalls

- Ordering by risk without checking prerequisites: a point whose
  prerequisite is missing from the set is flagged, never silently
  ordered.
- Risk ties: the sort keeps the input order, so identical risks stay
  in the order you listed them; do not hand-shuffle ties.
- A matrix with one uncovered objective is incomplete even when every
  other objective is covered.
- Instrumentation names match exactly after stripping whitespace; a
  renamed sensor counts as missing.
- The gate rejects non-boolean inputs: "yes" or 1 is an error, not a
  pass.
- Expanding the envelope in large steps: the build-up approach
  increments risk so every step stays testable and recoverable.

## Behavior contract (gate 3)

The build-up ordering, instrumentation completeness, test matrix
coverage, and go/no-go gate logic is exercised by the gate 3 contract
test: scripts/test_flight_test_planning.py against
scripts/flight_test_planning_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_flight_test_planning.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 set the
  flight test and certification context; the build-up approach, test
  matrix, instrumentation, and go/no-go practice is common
  flight-test methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

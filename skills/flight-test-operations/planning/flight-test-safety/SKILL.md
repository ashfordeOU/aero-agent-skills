---
name: flight-test-safety
description: "Assess the flight test safety package: score the hazards on the severity by likelihood risk matrix, check that every test point stays inside the flight envelope limits, confirm the emergency procedures cover the required conditions, verify the safety pilot duties are assigned, run the go/no-go criteria gate, and list the mitigation gaps. Use when the task concerns flight test safety: risk assessment, flight envelope limits, emergency procedures, safety pilot duties, go/no-go criteria, risk mitigation. Trigger: flight test safety, risk assessment, safety pilot duties, emergency procedures, go/no-go criteria, flight envelope limits."
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
  tags: [flight-test-safety, risk-assessment, risk-matrix, flight-envelope-limits, emergency-procedures, safety-pilot-duties, go-no-go-criteria, risk-mitigation]
  version: 0.1.0
  author: Aero Agent Skills
---

# Flight Test Safety (flight-test-operations/planning/flight-test-safety)

Use when the task is the flight test safety package: hazard risk
assessment, flight envelope limits for the test points, emergency
procedure coverage, safety pilot duties, the go/no-go criteria gate,
and the risk mitigation plan.

## Domain quick reference

- Risk assessment: score every hazard on a severity (1-5) by
  likelihood (1-5) matrix with assess_risks; the risk index is the
  product, and a hazard with an index of 15 or more is high risk and
  must be mitigated before the flight.
- Flight envelope limits: every test point must stay inside the speed
  and load factor limits with envelope_violations; a point on the
  boundary is inside, a point beyond any limit is a violation and is
  never flown.
- Emergency procedures: every foreseeable emergency condition needs a
  procedure with concrete steps; a required condition with no
  procedure is flagged as missing before the program starts.
- Safety pilot duties: the required duties are assigned to the safety
  pilot with safety_pilot_assignment; an unassigned duty is a gap.
- Go/no-go criteria: every criterion must pass with go_no_go; any
  single failed criterion forces NO-GO and names the failure.
- Risk mitigation: every risk needs at least one assigned mitigation
  with mitigation_gaps; an unmitigated risk blocks the flight.

## Workflow

1. Collect the hazards and score them with assess_risks(hazards);
   review the high-risk list and mitigate before the program starts.
2. Set the envelope limits and check every test point with
   envelope_violations(limits, points); fix or drop the violations.
3. Build the emergency procedure library and check the coverage with
   procedure_coverage(required, library); add the missing procedures.
4. Assign the safety pilot duties and verify them with
   safety_pilot_assignment(required_duties, assigned).
5. Run the gate with go_no_go(criteria) before each flight and fly
   only on a GO verdict.
6. Close the loop with mitigation_gaps(risks, mitigations); an
   unmitigated risk keeps the flight on the ground.

## Pitfalls

- Scoring a severity or likelihood outside 1-5: the matrix is bounded;
  an out-of-range value is an error, never a low risk.
- A point on the limit boundary counts as inside the envelope; only a
  strict crossing is a violation.
- A required condition with no procedure is flagged as missing, never
  assumed covered.
- A safety pilot duty left unassigned is reported as missing-duties
  and the flight is not released.
- The go/no-go gate rejects non-boolean inputs: "yes" or 1 is an
  error, not a pass.
- A mitigation for a risk id that is not in the risk list is an error:
  mitigations must reference the assessed risks exactly.

## Behavior contract (gate 3)

The risk assessment, envelope limit check, emergency procedure
coverage, safety pilot duty assignment, go/no-go criteria gate, and
risk mitigation logic is exercised by the gate 3 contract test:
scripts/test_flight_test_safety.py against
scripts/flight_test_safety_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_flight_test_safety.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 set the
  flight test and certification context; the risk matrix, envelope
  limit discipline, emergency procedures, safety pilot practice, and
  go/no-go criteria is common flight-test methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

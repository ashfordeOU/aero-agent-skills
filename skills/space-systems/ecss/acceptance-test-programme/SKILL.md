---
name: acceptance-test-programme
description: "Use when plan and execute acceptance proof and leak tests on flight hardware under ECSS-E-ST-32C clause 5.5: determine the required proof pressure for each pressurized assembly from its maximum design pressure and the applicable proof factor, confirm the applied test pressure meets or exceeds the requirement and that the hold duration satisfies the minimum dwell time, evaluate the measured leak rate against the allowable limit for each sealed assembly, and determine overall programme acceptance only when every test item passes. Trigger: ecss, e-st-32c, acceptance-test, proof-test, leak-test, flight-hardware, pressure-vessel, structural-acceptance."
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
  tags: [ecss, e-st-32c, acceptance-test, proof-test, leak-test, flight-hardware, pressure-vessel, structural-acceptance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural Mechanical Systems — Acceptance Test Programme (space-systems/ecss/acceptance-test-programme)

Use when the task is planning and executing the acceptance proof and leak
test programme for flight hardware per ECSS-E-ST-32C clause 5.5 --
determining proof pressure requirements, verifying test execution
conditions, evaluating leak rates, and recording the overall programme
outcome.

## Domain quick reference

- Clause 5.5 defines two mandatory test families for flight hardware
  acceptance: proof tests (applied to pressurized assemblies to
  demonstrate structural integrity at the maximum design pressure with
  a prescribed proof factor) and leak tests (applied to sealed
  assemblies to confirm that the actual leak rate does not exceed the
  allowable limit derived from the mission requirement). Both families
  must be completed and passed before a hardware item is accepted.
- The required proof pressure for a pressurized assembly is its maximum
  design pressure (MDP) multiplied by the proof factor. The proof
  factor at acceptance level is 1.0 for flight hardware (as distinct
  from the higher qualification proof factor used during development
  testing). The hardware must sustain the proof pressure for a minimum
  hold duration without leakage, collapse, or permanent deformation
  beyond the permitted limit.
- A leak test records the measured leak rate under the prescribed
  differential pressure condition and compares it against the allowable
  leak rate. An assembly with zero allowable leak rate on record cannot
  be evaluated and the missing requirement is itself a finding. The
  acceptance test programme as a whole is satisfied only when every
  individual test item in both families has a recorded pass.

## Workflow

1. Inventory every pressurized and sealed assembly on the flight
   hardware and assign each one to the appropriate test family: proof,
   leak, or both. Reject an assembly with an unrecognized test type
   before it enters the programme.
2. For each assembly requiring a proof test, compute the required proof
   pressure from the MDP and the applicable proof factor. Confirm the
   applied test pressure meets or exceeds this value, and that the
   measured hold duration meets the minimum dwell time specified in the
   test procedure. Flag any shortfall as a proof-test violation.
3. For each assembly requiring a leak test, compare the measured leak
   rate against the allowable leak rate from the contamination and
   sealing requirement. Flag an exceedance as a leak-test violation.
   Flag a missing allowable limit as an unrecorded requirement.
4. Aggregate the violation lists per assembly; an assembly is accepted
   only when its list is empty. The full acceptance test programme
   passes only when every assembly in the programme is accepted.
5. Record the test outcome for each assembly and the overall programme
   verdict in the test report. A programme with any open violation must
   not be closed out until all findings are resolved and the relevant
   tests are re-run to a clean outcome.

## Pitfalls

- Applying the qualification proof factor at acceptance level -- clause
  5.5 uses the acceptance proof factor (1.0 × MDP for typical
  pressurized structures), and overloading flight hardware with a
  higher qualification factor risks damage and is a test configuration
  error.
- Treating a hold duration that is marginally short as acceptable
  without re-test -- the minimum dwell time is a hard limit; a short
  hold makes the test inconclusive regardless of the pressure level
  reached.
- Accepting a sealed assembly with no allowable leak rate on record as
  compliant because no exceedance was computed -- an unrecorded
  allowable means the sealing requirement was never captured, which is
  itself a finding.
- Closing out the programme before all assemblies have a recorded pass
  -- the programme verdict is the logical AND of all individual test
  results; a single open finding blocks the programme.

## Behavior contract (gate 3)

The proof-pressure computation, proof-test condition check, leak-test
evaluation, and programme aggregation logic is exercised by the gate 3
contract test: scripts/test_acceptance_test_programme.py against
scripts/acceptance_test_programme_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_acceptance_test_programme.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
